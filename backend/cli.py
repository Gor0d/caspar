"""Local operations: python -m backend.cli init|demo|serve."""
import argparse
from .config import Settings
from .db import database
from .models import Program, Asset, Investigation, Journal, Evidence, Finding
from .storage import evidence_path
from sqlalchemy import select
from uuid import uuid4
import hashlib


def main():
    parser = argparse.ArgumentParser(description='CASPAR Personal Research')
    parser.add_argument('command', choices=['init', 'demo', 'serve'])
    args = parser.parse_args()
    if args.command == 'serve':
        import uvicorn
        uvicorn.run('backend.main:create_app', factory=True, host='127.0.0.1', port=8000, access_log=False)
        return
    settings = Settings().prepare()
    engine, sessions = database(settings.caspar_data_dir)
    if args.command == 'demo':
        with sessions() as db:
            if db.scalar(select(Program).where(Program.name == 'CASPAR Synthetic Lab')):
                print('Synthetic demo already installed.')
                return
            program = Program(name='CASPAR Synthetic Lab', policy='Material sintético. Nenhum serviço real. Apenas análise offline.', authorization='Laboratório pessoal fictício; example.test é um domínio reservado.', authorized=True)
            db.add(program)
            db.flush()
            db.add_all([Asset(program_id=program.id, pattern='*.example.test', allowed=True, note='Somente laboratório offline'), Asset(program_id=program.id, pattern='admin.example.test', allowed=False, note='Exemplo de proibição prioritária')])
            inv = Investigation(program_id=program.id, title='Revisão de autorização — laboratório', target='api.example.test')
            db.add(inv)
            db.flush()
            db.add(Journal(investigation_id=inv.id, body='Início da análise de material sintético. Nenhuma requisição executada.'))
            content = b'SYNTHETIC FIXTURE ONLY\nGET /lab/profile/42\nHTTP/1.1 403 Forbidden\nExpected access denial observed. No vulnerability demonstrated.\n'
            storage_name = uuid4().hex + '.bin'
            evidence_path(settings.caspar_data_dir, storage_name).write_bytes(content)
            record = Evidence(investigation_id=inv.id, filename='synthetic-response.txt', storage_name=storage_name, sha256=hashlib.sha256(content).hexdigest(), size=len(content), provenance='Fixture sintética criada pelo comando demo; não coletada de rede.')
            db.add(record)
            db.flush()
            db.add(Finding(investigation_id=inv.id, title='Hipótese de controle de acesso a revisar', severity='info', cwe='CWE-862', owasp='A01:2021 — Broken Access Control', hypothesis='Verificar se a autorização está corretamente documentada.', verified='O material sintético contém uma resposta 403.', conclusion='Nenhuma vulnerabilidade demonstrada por este material.', impact='Nenhum impacto confirmado.', evidence_ids=[record.id]))
            db.commit()
        print('Synthetic demo created. No network requests made.')
    print('Local database ready:', settings.caspar_data_dir)
    engine.dispose()


if __name__ == '__main__':
    main()
