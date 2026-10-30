import hashlib
import json
import sqlite3
import zipfile
from io import BytesIO
from sqlalchemy import inspect
from backend.main import create_app
from backend.config import Settings
from fastapi.testclient import TestClient


def test_complete_persisted_flow(client, chain, app):
    program, investigation, evidence = chain
    inv_id = investigation['id']
    assert evidence['sha256'] == hashlib.sha256(b'SYNTHETIC HTTP/1.1 403 Forbidden').hexdigest()
    assert client.post(f'/api/investigations/{inv_id}/journals', json={'body': 'No impact confirmed; fixture only.'}).status_code == 201
    body = {'title': 'Review of access control', 'severity': 'info', 'cwe': 'CWE-862', 'owasp': 'A01:2021',
            'hypothesis': 'Access check to review', 'verified': 'Fixture contains 403', 'conclusion': 'No vulnerability demonstrated',
            'evidence_ids': [evidence['id']]}
    finding = client.post(f'/api/investigations/{inv_id}/findings', json=body)
    assert finding.status_code == 201, finding.text
    updated = client.put('/api/findings/' + finding.json()['id'], json=body | {'status': 'submitted', 'reward_cents': 12345, 'submission_reference': 'LOCAL-123'})
    assert updated.json()['reward_cents'] == 12345
    for lang, heading in [('pt', 'Laudo técnico'), ('en', 'Technical report')]:
        report = client.post(f'/api/investigations/{inv_id}/reports', json={'language': lang})
        assert report.status_code == 201, report.text
        assert heading in report.json()['markdown']
        assert evidence['sha256'] in report.json()['markdown']
        report_id = report.json()['id']
        md = client.get(f'/api/reports/{report_id}/download?format=md')
        assert 'No vulnerability demonstrated' in md.text
        pdf = client.get(f'/api/reports/{report_id}/download?format=pdf')
        assert pdf.content.startswith(b'%PDF-')
        assert 'attachment' in pdf.headers['content-disposition']
    # A second application process sees the same records, using actual Alembic migrations.
    second = create_app(app.state.settings)
    try:
        with TestClient(second, base_url='http://127.0.0.1:8000', headers={'X-Caspar-Local': '1'}) as test:
            workspace = test.get('/api/workspace').json()
            assert workspace['findings'][0]['status'] == 'submitted'
            assert len(workspace['reports']) == 2
    finally:
        second.state.engine.dispose()


def test_backup_and_export_are_complete(client, chain, app, tmp_path):
    _, _, evidence = chain
    export = client.get('/api/export')
    assert export.json()['evidence'][0]['id'] == evidence['id']
    response = client.post('/api/backup')
    assert response.status_code == 200
    with zipfile.ZipFile(BytesIO(response.content)) as archive:
        manifest = json.loads(archive.read('manifest.json'))
        content = archive.read('evidence/' + evidence['storage_name'])
        assert hashlib.sha256(content).hexdigest() == manifest['evidence'][evidence['storage_name']]
        snapshot = tmp_path / 'snapshot.sqlite3'
        snapshot.write_bytes(archive.read('caspar.sqlite3'))
    with sqlite3.connect(snapshot) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert db.execute('SELECT count(*) FROM evidence').fetchone()[0] == 1
        assert db.execute('SELECT count(*) FROM consents').fetchone()[0] == 0
    # Restore into an empty dedicated data directory and verify original file downloads.
    restore = tmp_path / 'restored'
    restore.mkdir()
    with zipfile.ZipFile(BytesIO(response.content)) as archive:
        archive.extractall(restore)  # Archive is generated in this test, not user input.
    restored = create_app(Settings(_env_file=None, caspar_data_dir=restore))
    try:
        with TestClient(restored, base_url='http://127.0.0.1:8000', headers={'X-Caspar-Local': '1'}) as test:
            assert test.get('/api/evidence/' + evidence['id'] + '/download').content == content
    finally:
        restored.state.engine.dispose()


def test_full_delete_requires_exact_confirmation_and_removes_backups(client, chain, app):
    client.post('/api/backup')
    assert client.request('DELETE', '/api/data', json={'confirmation': 'yes'}).status_code == 422
    assert client.get('/api/workspace').json()['programs']
    assert client.request('DELETE', '/api/data', json={'confirmation': 'DELETE ALL LOCAL DATA'}).status_code == 204
    assert all(not rows for rows in client.get('/api/workspace').json().values())
    root = app.state.settings.caspar_data_dir
    assert list((root / 'evidence').iterdir()) == []
    assert list((root / 'backups').iterdir()) == []


def test_program_deletion_cascades_and_removes_files(client, chain, app):
    program, _, evidence = chain
    assert client.delete('/api/programs/' + program['id']).status_code == 204
    assert all(not rows for rows in client.get('/api/workspace').json().values())
    assert not (app.state.settings.caspar_data_dir / 'evidence' / evidence['storage_name']).exists()


def test_migration_matches_models_and_is_idempotent(app):
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from backend.models import Base
    from backend.db import database
    with app.state.engine.connect() as connection:
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
        assert connection.exec_driver_sql('select version_num from alembic_version').scalar() == '0002'
        assert connection.exec_driver_sql('PRAGMA foreign_keys').scalar() == 1
    engine, _ = database(app.state.settings.caspar_data_dir)
    assert 'findings' in inspect(engine).get_table_names()
    engine.dispose()
