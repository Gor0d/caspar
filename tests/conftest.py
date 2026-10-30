import pytest
from fastapi.testclient import TestClient
from backend.config import Settings
from backend.main import create_app
import httpx


@pytest.fixture(autouse=True)
def no_external_http(monkeypatch):
    def blocked(*args, **kwargs):
        pytest.fail('Tests must never make real external HTTP requests.')
    monkeypatch.setattr(httpx.HTTPTransport, 'handle_request', blocked)


@pytest.fixture
def app(tmp_path):
    settings = Settings(_env_file=None, caspar_data_dir=tmp_path / 'personal',
                        openai_api_key='synthetic-test-key', openai_model='test-model', ollama_model='test-local')
    application = create_app(settings)
    yield application
    application.state.engine.dispose()


@pytest.fixture
def client(app):
    with TestClient(app, base_url='http://127.0.0.1:8000', headers={'X-Caspar-Local': '1'}) as test:
        yield test


@pytest.fixture
def chain(client):
    program = client.post('/api/programs', json={'name': 'Synthetic Lab', 'authorization': 'Owned synthetic lab, offline only.', 'authorized': True}).json()
    response = client.post(f'/api/programs/{program["id"]}/assets', json={'pattern': '*.example.test', 'allowed': True})
    assert response.status_code == 201, response.text
    response = client.post(f'/api/programs/{program["id"]}/investigations', json={'title': 'Offline analysis', 'target': 'api.example.test'})
    assert response.status_code == 201, response.text
    investigation = response.json()
    response = client.post(f'/api/investigations/{investigation["id"]}/evidence', files={'file': ('response.txt', b'SYNTHETIC HTTP/1.1 403 Forbidden', 'text/plain')}, data={'provenance': 'Generated test fixture. No target requests.'})
    assert response.status_code == 201, response.text
    return program, investigation, response.json()
