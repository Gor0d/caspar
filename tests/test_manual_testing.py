from contextlib import closing
from datetime import datetime, timezone, timedelta
from io import BytesIO
import json
import sqlite3
import zipfile

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from backend import models as m
from backend.config import REPO, Settings
from backend.main import create_app
from fastapi.testclient import TestClient
import pytest


PLAN = {'title': 'Review authorization fixture', 'objective': 'Check the recorded access decision.',
        'technique': 'Offline comparison of synthetic HTTP fixtures', 'preconditions': 'Personal synthetic lab only.',
        'steps': 'Compare the supplied response with the expected access policy. No network requests.',
        'expected_result': '403 Forbidden for unauthorized access.', 'stop_conditions': 'Stop if material contains real user data.'}


def create(client, investigation):
    response = client.post('/api/investigations/' + investigation['id'] + '/test-plans', json=PLAN)
    assert response.status_code == 201, response.text
    return response.json()


def approve(client, plan):
    response = client.get('/api/test-plans/' + plan['id'] + '/approval-preview', params={'expected_revision': plan['revision']})
    if response.status_code != 200:
        return response
    return client.post('/api/test-plans/' + plan['id'] + '/approve', json={'approved': True, 'expected_revision': plan['revision'], 'context_digest': response.json()['context_digest']})


def record(client, plan, evidence, **extra):
    return client.post('/api/test-plans/' + plan['id'] + '/runs', json={
        'expected_revision': plan['revision'], 'performed_at': datetime.now(timezone.utc).isoformat(),
        'outcome': 'expected_behavior', 'observed_result': 'Synthetic fixture shows 403; no vulnerability demonstrated.',
        'limitations': 'Fixture only, not a live test.', 'evidence_ids': [evidence['id']], **extra})


def test_plan_run_review_retest_and_report(client, chain, app):
    _, investigation, evidence = chain
    plan = create(client, investigation)
    assert plan['status'] == 'planned' and plan['revision'] == 1
    assert approve(client, plan).status_code == 200
    first = record(client, plan, evidence)
    assert first.status_code == 201, first.text
    run = first.json()
    assert run['plan_snapshot']['evidence_manifest'][evidence['id']] == evidence['sha256']
    assert run['plan_snapshot']['scope']['target'] == investigation['target']
    assert record(client, plan, evidence).status_code == 409  # Approval is consumed.
    finding = client.post('/api/investigations/' + investigation['id'] + '/findings', json={
        'title': 'Review authorization behavior', 'hypothesis': 'No vulnerability demonstrated.', 'evidence_ids': [evidence['id']]}).json()
    review = client.post('/api/test-runs/' + run['id'] + '/review', json={
        'reviewed': True, 'review_notes': 'Negative result, retain as a reference for retesting.', 'finding_id': finding['id']})
    assert review.status_code == 200, review.text
    assert client.get('/api/workspace').json()['test_plans'][0]['status'] == 'reviewed'
    # A retest gets a new approval and its own immutable run/snapshot.
    assert approve(client, plan).status_code == 200
    second = record(client, plan, evidence, outcome='inconclusive', limitations='Missing a second fixture.')
    assert second.status_code == 201
    assert second.json()['id'] != run['id']
    workspace = client.get('/api/workspace').json()
    assert len(workspace['test_runs']) == 2
    assert workspace['test_runs'][0]['review_notes'] == review.json()['review_notes']
    for language, heading in [('pt', 'Histórico de execuções manuais'), ('en', 'Manual execution history')]:
        report = client.post('/api/investigations/' + investigation['id'] + '/reports', json={'language': language}).json()
        assert heading in report['markdown']
        assert run['id'] in report['markdown'] and finding['id'] in report['markdown']
        assert evidence['sha256'] in report['markdown']
        assert 'Missing a second fixture' in report['markdown']
        assert client.get('/api/reports/' + report['id'] + '/download?format=pdf').content.startswith(b'%PDF-')
    second_app = create_app(app.state.settings)
    try:
        with TestClient(second_app, base_url='http://127.0.0.1:8000', headers={'X-Caspar-Local': '1'}) as reopened:
            assert len(reopened.get('/api/workspace').json()['test_runs']) == 2
    finally:
        second_app.state.engine.dispose()


def test_approval_is_explicit_and_plan_edits_invalidate_it(client, chain):
    _, investigation, evidence = chain
    plan = create(client, investigation)
    assert record(client, plan, evidence).status_code == 409
    assert client.post('/api/test-plans/' + plan['id'] + '/approve', json={'approved': False, 'expected_revision': 1}).status_code == 422
    assert approve(client, plan).status_code == 200
    response = client.put('/api/test-plans/' + plan['id'], json=PLAN | {'steps': 'Revised offline comparison', 'expected_revision': 1})
    assert response.status_code == 200
    revised = response.json()
    assert revised['status'] == 'planned' and revised['revision'] == 2 and revised['approved_revision'] == 0
    assert record(client, plan, evidence).status_code == 409
    assert client.put('/api/test-plans/' + plan['id'], json=PLAN | {'expected_revision': 1}).status_code == 409
    assert approve(client, plan).status_code == 409
    assert approve(client, revised).status_code == 200
    assert record(client, revised, evidence).status_code == 201


def test_recorded_snapshot_survives_plan_changes(client, chain):
    _, investigation, evidence = chain
    plan = create(client, investigation)
    approve(client, plan)
    record(client, plan, evidence)
    client.put('/api/test-plans/' + plan['id'], json=PLAN | {'title': 'New version', 'expected_revision': 1})
    workspace = client.get('/api/workspace').json()
    assert workspace['test_plans'][0]['title'] == 'New version'
    assert workspace['test_runs'][0]['plan_snapshot']['title'] == PLAN['title']


def test_policy_change_invalidates_pending_plan_approval(client, chain):
    program, investigation, evidence = chain
    plan = create(client, investigation)
    approve(client, plan)
    client.put('/api/programs/' + program['id'], json={'name': program['name'], 'authorized': True, 'authorization': program['authorization'], 'policy': 'New restrictions'})
    assert record(client, plan, evidence).status_code == 409
    assert approve(client, plan).status_code == 200
    assert record(client, plan, evidence).status_code == 201


def test_scope_revocation_blocks_new_approvals_and_records(client, chain):
    program, investigation, evidence = chain
    plan = create(client, investigation)
    approve(client, plan)
    client.post('/api/programs/' + program['id'] + '/assets', json={'pattern': investigation['target'], 'allowed': False})
    assert approve(client, plan).status_code == 403
    assert record(client, plan, evidence).status_code == 403
    assert client.put('/api/test-plans/' + plan['id'], json=PLAN | {'expected_revision': 1}).status_code == 403
    assert client.post('/api/investigations/' + investigation['id'] + '/test-plans', json=PLAN).status_code == 403
    assert len(client.get('/api/workspace').json()['test_plans']) == 1


def test_policy_change_between_preview_and_approval_is_rejected(client, chain):
    program, investigation, _ = chain
    plan = create(client, investigation)
    preview = client.get('/api/test-plans/' + plan['id'] + '/approval-preview', params={'expected_revision': 1}).json()
    client.put('/api/programs/' + program['id'], json={'name': program['name'], 'authorized': True, 'authorization': program['authorization'], 'policy': 'Changed after opening the approval dialog'})
    response = client.post('/api/test-plans/' + plan['id'] + '/approve', json={'approved': True, 'expected_revision': 1, 'context_digest': preview['context_digest']})
    assert response.status_code == 409
    assert client.get('/api/workspace').json()['test_plans'][0]['status'] == 'planned'
    assert approve(client, plan).status_code == 200


def test_cross_investigation_evidence_and_finding_rejected(client, chain):
    program, investigation, evidence = chain
    other = client.post('/api/programs/' + program['id'] + '/investigations', json={'title': 'Other', 'target': 'other.example.test'}).json()
    plan = create(client, other)
    approve(client, plan)
    assert record(client, plan, evidence).status_code == 422
    local_plan = create(client, investigation)
    approve(client, local_plan)
    run = record(client, local_plan, evidence).json()
    finding = client.post('/api/investigations/' + other['id'] + '/findings', json={'title': 'Unrelated'}).json()
    assert client.post('/api/test-runs/' + run['id'] + '/review', json={'reviewed': True, 'review_notes': 'Cross reference', 'finding_id': finding['id']}).status_code == 422


def test_evidence_integrity_checked_and_history_protects_deletion(client, chain, app):
    _, investigation, evidence = chain
    plan = create(client, investigation)
    approve(client, plan)
    path = app.state.settings.caspar_data_dir / 'evidence' / evidence['storage_name']
    content = path.read_bytes()
    path.write_bytes(b'changed')
    assert record(client, plan, evidence).status_code == 409
    path.write_bytes(content)
    assert record(client, plan, evidence).status_code == 201
    assert client.delete('/api/evidence/' + evidence['id']).status_code == 409
    assert client.delete('/api/investigations/' + investigation['id']).status_code == 204
    workspace = client.get('/api/workspace').json()
    assert not workspace['test_plans'] and not workspace['test_runs'] and not path.exists()


def test_expired_approval_cannot_record(client, chain, app):
    _, investigation, evidence = chain
    plan = create(client, investigation)
    approve(client, plan)
    with app.state.sessions() as db:
        stored = db.get(m.TestPlan, plan['id'])
        stored.approved_at = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        db.commit()
    assert record(client, plan, evidence).status_code == 409


@pytest.mark.parametrize('extra', [
    {'evidence_ids': []}, {'performed_at': '2026-01-01T12:00:00'},
    {'performed_at': '2999-01-01T12:00:00Z'}, {'outcome': 'inconclusive', 'limitations': ''},
    {'outcome': 'confirmed_vulnerability'}, {'command': 'do not execute anything'},
])
def test_invalid_manual_records_rejected(client, chain, extra):
    _, investigation, evidence = chain
    plan = create(client, investigation)
    approve(client, plan)
    assert record(client, plan, evidence, **extra).status_code == 422


def test_review_is_immutable_and_old_review_does_not_consume_new_approval(client, chain):
    _, investigation, evidence = chain
    plan = create(client, investigation)
    approve(client, plan)
    run = record(client, plan, evidence).json()
    approve(client, plan)
    body = {'reviewed': True, 'review_notes': 'Reviewed without claiming a vulnerability.'}
    assert client.post('/api/test-runs/' + run['id'] + '/review', json=body).status_code == 200
    assert client.get('/api/workspace').json()['test_plans'][0]['status'] == 'approved'
    assert client.post('/api/test-runs/' + run['id'] + '/review', json=body).status_code == 409
    assert record(client, plan, evidence).status_code == 201


def test_backup_includes_manual_history_but_clears_pending_approval(client, chain, tmp_path):
    _, investigation, evidence = chain
    plan = create(client, investigation)
    approve(client, plan)
    record(client, plan, evidence)
    approve(client, plan)
    response = client.post('/api/backup')
    with zipfile.ZipFile(BytesIO(response.content)) as archive:
        assert json.loads(archive.read('manifest.json'))['schema'] == '0002'
        snapshot = tmp_path / 'snapshot.sqlite3'
        snapshot.write_bytes(archive.read('caspar.sqlite3'))
    with closing(sqlite3.connect(snapshot)) as db:
        assert db.execute('SELECT count(*) FROM test_runs').fetchone()[0] == 1
        assert db.execute('SELECT status, approved_revision FROM test_plans').fetchone() == ('planned', 0)
    assert client.get('/api/workspace').json()['test_plans'][0]['status'] == 'approved'  # Live approval unaffected.


def test_upgrade_of_existing_0001_preserves_private_records(tmp_path):
    root = tmp_path / 'existing-v1'
    root.mkdir()
    engine = create_engine('sqlite:///' + (root / 'caspar.sqlite3').as_posix())
    cfg = Config(str(REPO / 'alembic.ini'))
    cfg.set_main_option('script_location', str(REPO / 'migrations'))
    with engine.begin() as connection:
        cfg.attributes['connection'] = connection
        command.upgrade(cfg, '0001')
        connection.execute(text("INSERT INTO programs VALUES ('synthetic-id', '2026-01-01', 'Existing private program', '', '', 0)"))
    engine.dispose()
    upgraded = create_app(Settings(_env_file=None, caspar_data_dir=root))
    try:
        with TestClient(upgraded, base_url='http://127.0.0.1:8000', headers={'X-Caspar-Local': '1'}) as client:
            workspace = client.get('/api/workspace').json()
            assert workspace['programs'][0]['name'] == 'Existing private program'
            assert workspace['test_plans'] == [] and workspace['test_runs'] == []
    finally:
        upgraded.state.engine.dispose()
