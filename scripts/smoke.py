"""Real loopback HTTP smoke with synthetic data, isolated temp storage and no AI requests."""
from contextlib import closing
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

import httpx


def main():
    repo = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='caspar-smoke-') as temp:
        env = os.environ | {'CASPAR_DATA_DIR': str(Path(temp) / 'personal'),
                            'OPENAI_API_KEY': '', 'OPENAI_MODEL': '', 'OLLAMA_MODEL': ''}
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        subprocess.run([sys.executable, '-m', 'backend.cli', 'demo'], cwd=repo, env=env, check=True, creationflags=flags)
        with closing(socket.socket()) as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'backend.main:create_app', '--factory',
                                    '--host', '127.0.0.1', '--port', str(port), '--no-access-log'],
                                   cwd=repo, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, creationflags=flags)
        try:
            with httpx.Client(base_url=f'http://127.0.0.1:{port}', headers={'X-Caspar-Local': '1'}, timeout=5, trust_env=False) as client:
                for _ in range(50):
                    if process.poll() is not None:
                        raise RuntimeError(process.stderr.read().decode(errors='replace'))
                    try:
                        if client.get('/api/health').status_code == 200:
                            break
                    except httpx.ConnectError:
                        pass
                    time.sleep(.2)
                else:
                    raise RuntimeError('Local server did not start')
                response = client.get('/')
                assert response.status_code == 200 and 'CASPAR' in response.text
                import re
                asset = re.search(r'src="([^"]+\.js)"', response.text).group(1)
                assert client.get(asset).status_code == 200
                workspace = client.get('/api/workspace').json()
                assert len(workspace['programs']) == 1 and len(workspace['evidence']) == 1
                investigation = workspace['investigations'][0]['id']
                plan_body = {'title': 'Manual synthetic review', 'objective': 'Compare an offline response fixture',
                             'technique': 'Offline fixture review', 'steps': 'Read the already imported synthetic response',
                             'expected_result': '403 Forbidden', 'stop_conditions': 'Stop if real user data is present'}
                plan_response = client.post(f'/api/investigations/{investigation}/test-plans', json=plan_body)
                assert plan_response.status_code == 201
                plan_id = plan_response.json()['id']
                approval = client.get(f'/api/test-plans/{plan_id}/approval-preview?expected_revision=1').json()
                assert client.post(f'/api/test-plans/{plan_id}/approve', json={'approved': True, 'expected_revision': 1, 'context_digest': approval['context_digest']}).status_code == 200
                run_response = client.post(f'/api/test-plans/{plan_id}/runs', json={
                    'expected_revision': 1, 'performed_at': datetime.now(timezone.utc).isoformat(),
                    'outcome': 'expected_behavior', 'observed_result': 'Synthetic fixture contains 403. No live test performed.',
                    'limitations': 'Synthetic data only.', 'evidence_ids': [workspace['evidence'][0]['id']]})
                assert run_response.status_code == 201
                run_id = run_response.json()['id']
                assert client.post(f'/api/test-runs/{run_id}/review', json={
                    'reviewed': True, 'review_notes': 'No vulnerability demonstrated by this fixture.',
                    'finding_id': workspace['findings'][0]['id']}).status_code == 200
                report = client.post(f'/api/investigations/{investigation}/reports', json={'language': 'en'})
                assert report.status_code == 201
                assert run_id in report.json()['markdown']
                pdf = client.get('/api/reports/' + report.json()['id'] + '/download?format=pdf')
                assert pdf.content.startswith(b'%PDF-')
                assert client.post('/api/backup').status_code == 200
                print('PASS: real loopback HTTP, frontend + JS, manual plan/approval/run/review, English report/PDF and backup. No target or AI calls.')
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            if process.stderr:
                process.stderr.close()


if __name__ == '__main__':
    main()
