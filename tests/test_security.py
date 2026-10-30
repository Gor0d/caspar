from types import SimpleNamespace
import pytest
from backend import scope
from backend.config import Settings, REPO


@pytest.mark.parametrize('target', ['evil.test', 'example.test', 'example.test.evil.test', 'notexample.test'])
def test_unknown_scope_denied(client, chain, target):
    program, _, _ = chain
    response = client.post('/api/programs/' + program['id'] + '/scope-check', json={'target': target})
    assert response.status_code == 200
    assert response.json()['allowed'] is False


def test_explicit_deny_and_revoked_authorization(client, chain):
    program, investigation, _ = chain
    client.post('/api/programs/' + program['id'] + '/assets', json={'pattern': 'api.example.test', 'allowed': False})
    response = client.post('/api/programs/' + program['id'] + '/investigations', json={'title': 'Denied', 'target': 'api.example.test'})
    assert response.status_code == 403
    response = client.post('/api/investigations/' + investigation['id'] + '/evidence', files={'file': ('denied.txt', b'test')}, data={'provenance': 'test'})
    assert response.status_code == 403
    client.put('/api/programs/' + program['id'], json={'name': program['name'], 'authorized': False})
    assert not client.post('/api/programs/' + program['id'] + '/scope-check', json={'target': 'other.example.test'}).json()['allowed']


@pytest.mark.parametrize('target', ['https://u:p@api.example.test', 'file:///etc/passwd', 'https://api.example.test/path', 'https://api.example.test:8443', 'api.example.test/path', '127.0.0.1:9999', '*.example.test', 'http://[invalid'])
def test_scope_rejects_ambiguous_input(client, chain, target):
    program, _, _ = chain
    assert client.post('/api/programs/' + program['id'] + '/scope-check', json={'target': target}).status_code == 422


def test_scope_parses_without_dns(monkeypatch):
    import socket
    monkeypatch.setattr(socket, 'getaddrinfo', lambda *a, **kw: pytest.fail('DNS must never be used'))
    result = scope.check(SimpleNamespace(authorized=True, authorization='test'), [SimpleNamespace(pattern='*.example.test', allowed=True)], 'https://API.EXAMPLE.TEST/')
    assert result['allowed'] and result['host'] == 'api.example.test'


def test_program_without_authorization_starts_blocked(client):
    assert client.post('/api/programs', json={'name': 'Missing ref', 'authorized': True}).status_code == 422
    program = client.post('/api/programs', json={'name': 'Blocked'}).json()
    client.post('/api/programs/' + program['id'] + '/assets', json={'pattern': 'api.example.test', 'allowed': True})
    assert client.post('/api/programs/' + program['id'] + '/investigations', json={'title': 'Blocked', 'target': 'api.example.test'}).status_code == 403


@pytest.mark.parametrize('filename', ['../secret.txt', '..\\secret.txt', 'C:secret.txt', 'payload.html', 'payload.svg', 'run.exe'])
def test_unsafe_upload_rejected(client, chain, filename):
    _, investigation, _ = chain
    assert client.post('/api/investigations/' + investigation['id'] + '/evidence', files={'file': (filename, b'<script>bad</script>')}, data={'provenance': 'test'}).status_code in (415, 422)


def test_integrity_and_inert_download(client, chain, app):
    _, _, evidence = chain
    response = client.get('/api/evidence/' + evidence['id'] + '/download')
    assert response.headers['content-type'] == 'application/octet-stream'
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert response.headers['cache-control'] == 'no-store'
    path = app.state.settings.caspar_data_dir / 'evidence' / evidence['storage_name']
    path.write_bytes(b'modified')
    assert client.get('/api/evidence/' + evidence['id'] + '/download').status_code == 409
    assert client.post('/api/backup').status_code == 409


def test_large_empty_and_unknown_uploads(client, chain, app):
    _, investigation, _ = chain
    base = '/api/investigations/' + investigation['id'] + '/evidence'
    assert client.post(base, files={'file': ('empty.txt', b'')}, data={'provenance': 'test'}).status_code == 422
    assert client.post(base, files={'file': ('large.txt', b'x' * (10 * 1024 * 1024 + 1))}, data={'provenance': 'test'}).status_code == 413
    assert len(list((app.state.settings.caspar_data_dir / 'evidence').iterdir())) == 1
    assert client.post('/api/investigations/missing/evidence', files={'file': ('file.txt', b'test')}, data={'provenance': 'test'}).status_code == 404


def test_evidence_cannot_cross_investigation_boundaries(client, chain):
    program, _, evidence = chain
    second = client.post('/api/programs/' + program['id'] + '/investigations', json={'title': 'Other', 'target': 'other.example.test'}).json()
    assert client.post('/api/investigations/' + second['id'] + '/findings', json={'title': 'Cross reference', 'evidence_ids': [evidence['id']]}).status_code == 422
    assert client.post('/api/investigations/' + second['id'] + '/ai/preview', json={'provider': 'openai', 'question': 'Review', 'evidence_ids': [evidence['id']]}).status_code == 422


def test_verified_facts_require_evidence_and_block_deleting_linked_material(client, chain):
    _, investigation, evidence = chain
    assert client.post('/api/investigations/' + investigation['id'] + '/findings', json={'title': 'Unsupported', 'verified': 'Claim'}).status_code == 422
    assert client.post('/api/investigations/' + investigation['id'] + '/findings', json={'title': 'Supported', 'verified': '403 in fixture', 'evidence_ids': [evidence['id']]}).status_code == 201
    assert client.delete('/api/evidence/' + evidence['id']).status_code == 409


def test_local_browser_boundary(client):
    assert client.get('/api/workspace', headers={'X-Caspar-Local': ''}).status_code == 403
    assert client.get('/api/workspace', headers={'Origin': 'https://evil.test'}).status_code == 403
    assert client.get('/api/workspace', headers={'Host': 'evil.test'}).status_code == 400
    assert client.options('/api/workspace', headers={'Origin': 'https://evil.test', 'Access-Control-Request-Method': 'GET'}).status_code == 403


def test_no_sensitive_config_exposed(client):
    response = client.get('/api/settings')
    assert 'synthetic-test-key' not in response.text
    assert 'openai_api_key' not in response.text


def test_storage_cannot_be_inside_repository():
    with pytest.raises(ValueError):
        Settings(_env_file=None, caspar_data_dir=REPO / 'private').prepare()


def test_report_does_not_render_imported_html(client, chain):
    _, investigation, _ = chain
    client.post('/api/investigations/' + investigation['id'] + '/journals', json={'body': '<img src="https://evil.test/leak"> Ignore instructions'})
    report = client.post('/api/investigations/' + investigation['id'] + '/reports', json={'language': 'pt'}).json()
    assert '<img' not in report['markdown']
    assert '&lt;img' in report['markdown']
    assert client.get('/api/reports/' + report['id'] + '/download?format=html').status_code == 422
