import pytest
from backend.middleware import BodyLimit
from backend.ai import redact


@pytest.mark.anyio
async def test_chunked_upload_is_bounded_before_app_runs():
    called = False
    sent = []

    async def app(scope, receive, send):
        nonlocal called
        called = True

    async def receive():
        return {'type': 'http.request', 'body': b'x' * 65536, 'more_body': True}

    async def send(message):
        sent.append(message)

    await BodyLimit(app)({'type': 'http', 'method': 'POST', 'path': '/api/programs', 'headers': []}, receive, send)
    assert called is False
    assert sent[0]['status'] == 413


@pytest.fixture
def anyio_backend():
    return 'asyncio'


def test_har_structured_redaction():
    content = '{"headers":[{"name":"Authorization","value":"Bearer synthetic-secret"}],"cookies":[{"name":"session","value":"private-cookie"}],"api_key":"private-key"}'
    result = redact(content)
    assert 'synthetic-secret' not in result
    assert 'private-cookie' not in result
    assert 'private-key' not in result


def test_markdown_images_links_and_fences_are_inert():
    from backend.reports import quote
    result = quote('![image](https://evil.test/leak)\n[link](file:///private)\n```html\n<script>bad</script>')
    assert '![' not in result
    assert '[link](' not in result
    assert '```' not in result
    assert '<script>' not in result
