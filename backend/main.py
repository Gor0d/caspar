import asyncio
import hashlib
import json
import os
import sqlite3
import tempfile
import zipfile
from contextlib import asynccontextmanager, closing
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, delete, inspect
from sqlalchemy.orm import Session
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import models as m, schemas as s, scope, ai, reports
from .config import Settings, REPO
from .db import database
from .storage import validate_filename, evidence_path, read_evidence, MAX_UPLOAD
from .middleware import BodyLimit


def serialize(record):
    return {col.key: getattr(record, col.key) for col in inspect(record).mapper.column_attrs}


def create_app(settings=None):
    settings = (settings or Settings()).prepare()
    root = settings.caspar_data_dir
    engine, sessions = database(root)

    @asynccontextmanager
    async def lifespan(app):
        yield
        engine.dispose()

    app = FastAPI(title='CASPAR Personal Research', version='0.1.0', lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.state.engine = engine
    app.state.sessions = sessions
    app.state.settings = settings
    app.state.lock = asyncio.Lock()
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', '[::1]'])

    @app.middleware('http')
    async def local_boundary(request: Request, call_next):
        # Browser CSRF and DNS rebinding defense. The header is a local boundary, not authentication.
        origin = request.headers.get('origin')
        if origin and origin not in {'http://127.0.0.1:8000', 'http://localhost:8000', 'http://127.0.0.1:5173', 'http://localhost:5173'}:
            return JSONResponse({'detail': 'Origem não permitida.'}, status_code=403)
        if request.url.path.startswith('/api/') and request.url.path != '/api/health':
            if request.headers.get('x-caspar-local') != '1':
                return JSONResponse({'detail': 'Cabeçalho local obrigatório.'}, status_code=403)
        content_length = request.headers.get('content-length')
        if content_length:
            try:
                if int(content_length) > MAX_UPLOAD + 65536:
                    return JSONResponse({'detail': 'Requisição excede o limite de 10 MiB.'}, status_code=413)
            except ValueError:
                return JSONResponse({'detail': 'Content-Length inválido.'}, status_code=400)
        # Serializing API mutations also keeps backup snapshots consistent with evidence files.
        if request.url.path.startswith('/api/'):
            async with app.state.lock:
                response = await call_next(request)
        else:
            response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        return response

    def db():
        with sessions() as session:
            yield session

    def get(session, model, id):
        record = session.get(model, id)
        if record is None:
            raise HTTPException(404, 'Registro não encontrado.')
        return record

    def rows(session, model, **filters):
        query = select(model).filter_by(**filters).order_by(model.created_at, model.id)
        return list(session.scalars(query))

    def save(session, record):
        session.add(record)
        session.commit()
        session.refresh(record)
        return serialize(record)

    def allowed(session, investigation):
        program = get(session, m.Program, investigation.program_id)
        result = scope.check(program, rows(session, m.Asset, program_id=program.id), investigation.target)
        if not result['allowed']:
            raise HTTPException(403, result['reason'])
        return result

    def linked_evidence(session, investigation_id, ids):
        records = [get(session, m.Evidence, id) for id in dict.fromkeys(ids)]
        if any(record.investigation_id != investigation_id for record in records):
            raise HTTPException(422, 'Evidência pertence a outra investigação.')
        return records

    @app.get('/api/health')
    def health():
        return {'status': 'ok', 'edition': 'personal', 'active_scanning': False}

    @app.get('/api/settings')
    def configuration():
        return {'storage': str(root), 'openai_configured': bool(settings.openai_model and settings.openai_api_key),
                'ollama_configured': bool(settings.ollama_model), 'openai_model': settings.openai_model,
                'ollama_model': settings.ollama_model, 'input_cost_per_million': settings.ai_input_cost_per_million,
                'output_cost_per_million': settings.ai_output_cost_per_million}

    @app.get('/api/workspace')
    def workspace(session: Session = Depends(db)):
        return {model.__tablename__: [serialize(record) for record in rows(session, model)] for model in
                (m.Program, m.Asset, m.Investigation, m.Journal, m.Evidence, m.Finding, m.Report, m.Analysis)}

    @app.post('/api/programs', status_code=201)
    def program_create(body: s.ProgramInput, session: Session = Depends(db)):
        return save(session, m.Program(**body.model_dump()))

    @app.put('/api/programs/{id}')
    def program_update(id: str, body: s.ProgramInput, session: Session = Depends(db)):
        record = get(session, m.Program, id)
        for key, value in body.model_dump().items():
            setattr(record, key, value)
        session.execute(delete(m.Consent).where(m.Consent.investigation_id.in_(select(m.Investigation.id).where(m.Investigation.program_id == id))))
        return save(session, record)

    @app.post('/api/programs/{id}/assets', status_code=201)
    def asset_create(id: str, body: s.AssetInput, session: Session = Depends(db)):
        get(session, m.Program, id)
        try:
            normalized = scope.pattern(body.pattern)
        except (ValueError, UnicodeError) as exc:
            raise HTTPException(422, str(exc))
        return save(session, m.Asset(program_id=id, **(body.model_dump() | {'pattern': normalized})))

    @app.delete('/api/assets/{id}', status_code=204)
    def asset_delete(id: str, session: Session = Depends(db)):
        session.delete(get(session, m.Asset, id))
        session.commit()

    @app.post('/api/programs/{id}/scope-check')
    def scope_check(id: str, body: s.ScopeInput, session: Session = Depends(db)):
        program = get(session, m.Program, id)
        try:
            return scope.check(program, rows(session, m.Asset, program_id=id), body.target)
        except (ValueError, UnicodeError) as exc:
            raise HTTPException(422, str(exc))

    @app.post('/api/programs/{id}/investigations', status_code=201)
    def investigation_create(id: str, body: s.InvestigationInput, session: Session = Depends(db)):
        result = scope_check(id, s.ScopeInput(target=body.target), session)
        if not result['allowed']:
            raise HTTPException(403, result['reason'])
        return save(session, m.Investigation(program_id=id, title=body.title, target=result['host']))

    @app.post('/api/investigations/{id}/journals', status_code=201)
    def journal_create(id: str, body: s.JournalInput, session: Session = Depends(db)):
        get(session, m.Investigation, id)
        return save(session, m.Journal(investigation_id=id, body=body.body))

    @app.post('/api/investigations/{id}/evidence', status_code=201)
    async def evidence_create(id: str, file: UploadFile = File(...), provenance: str = Form(...), session: Session = Depends(db)):
        investigation = get(session, m.Investigation, id)
        allowed(session, investigation)
        name = validate_filename(file.filename)
        if not provenance.strip() or len(provenance) > 10000:
            raise HTTPException(422, 'Informe origem, data e contexto da coleta (até 10 mil caracteres).')
        storage_name = uuid4().hex + '.bin'
        path = evidence_path(root, storage_name)
        digest = hashlib.sha256()
        size = 0
        try:
            with path.open('xb') as target:
                if os.name != 'nt':
                    path.chmod(0o600)
                while chunk := await file.read(65536):
                    size += len(chunk)
                    if size > MAX_UPLOAD:
                        raise HTTPException(413, 'Limite de 10 MiB por evidência.')
                    digest.update(chunk)
                    target.write(chunk)
            if not size:
                raise HTTPException(422, 'Arquivo vazio.')
            return save(session, m.Evidence(investigation_id=id, filename=name, storage_name=storage_name,
                       sha256=digest.hexdigest(), size=size, provenance=provenance.strip()))
        except Exception:
            session.rollback()
            path.unlink(missing_ok=True)
            raise
        finally:
            await file.close()

    def attachment(content, media, filename):
        return Response(content, media_type=media, headers={'Content-Disposition': f'attachment; filename="{filename}"'})

    @app.get('/api/evidence/{id}/download')
    def evidence_download(id: str, session: Session = Depends(db)):
        record = get(session, m.Evidence, id)
        # Original filename never controls a local path or response header.
        return attachment(read_evidence(root, record), 'application/octet-stream', f'evidence-{id}{Path(record.filename).suffix.lower()}')

    @app.delete('/api/evidence/{id}', status_code=204)
    def evidence_delete(id: str, session: Session = Depends(db)):
        record = get(session, m.Evidence, id)
        if any(id in finding.evidence_ids for finding in rows(session, m.Finding, investigation_id=record.investigation_id)):
            raise HTTPException(409, 'Evidência vinculada a um achado. Remova o vínculo antes de excluir.')
        path = evidence_path(root, record.storage_name)
        # Reports/analyses are snapshots; remove them to avoid retaining deleted source data.
        for model in (m.Report, m.Analysis, m.Consent):
            session.execute(delete(model).where(model.investigation_id == record.investigation_id))
        session.delete(record)
        session.commit()
        path.unlink(missing_ok=True)

    @app.post('/api/investigations/{id}/findings', status_code=201)
    def finding_create(id: str, body: s.FindingInput, session: Session = Depends(db)):
        allowed(session, get(session, m.Investigation, id))
        linked_evidence(session, id, body.evidence_ids)
        return save(session, m.Finding(investigation_id=id, **body.model_dump()))

    @app.put('/api/findings/{id}')
    def finding_update(id: str, body: s.FindingInput, session: Session = Depends(db)):
        record = get(session, m.Finding, id)
        linked_evidence(session, record.investigation_id, body.evidence_ids)
        for key, value in body.model_dump().items():
            setattr(record, key, value)
        return save(session, record)

    @app.post('/api/investigations/{id}/reports', status_code=201)
    def report_create(id: str, body: s.ReportInput, session: Session = Depends(db)):
        investigation = get(session, m.Investigation, id)
        program = get(session, m.Program, investigation.program_id)
        markdown = reports.render(program, investigation, rows(session, m.Finding, investigation_id=id),
                                  rows(session, m.Evidence, investigation_id=id), rows(session, m.Journal, investigation_id=id), body.language)
        return save(session, m.Report(investigation_id=id, language=body.language, markdown=markdown))

    @app.get('/api/reports/{id}/download')
    def report_download(id: str, format: str = 'md', session: Session = Depends(db)):
        report = get(session, m.Report, id)
        if format not in ('md', 'pdf'):
            raise HTTPException(422, 'Use md ou pdf.')
        content = reports.pdf(report.markdown) if format == 'pdf' else report.markdown.encode('utf-8')
        return attachment(content, 'application/pdf' if format == 'pdf' else 'text/markdown; charset=utf-8', f'caspar-{id}-{report.language}.{format}')

    @app.post('/api/investigations/{id}/ai/preview', status_code=201)
    def ai_preview(id: str, body: s.PreviewInput, session: Session = Depends(db)):
        allowed(session, get(session, m.Investigation, id))
        model = ai.model_for(settings, body.provider)
        records = linked_evidence(session, id, body.evidence_ids)
        payload, digest = ai.preview(root, records, body.question)
        consent = m.Consent(investigation_id=id, provider=body.provider, model=model, payload=payload, digest=digest)
        save(session, consent)
        return {'consent_id': consent.id, 'digest': digest, 'payload': payload, 'instructions': ai.INSTRUCTIONS,
                'provider': body.provider, 'model': model, 'expires_in_seconds': 600,
                'approximate_input_tokens': (len(payload) + len(ai.INSTRUCTIONS)) // 4,
                'estimated_max_cost_usd': ((len(payload) + len(ai.INSTRUCTIONS)) / 4 * settings.ai_input_cost_per_million + 2000 * settings.ai_output_cost_per_million) / 1000000,
                'warning': 'Revise todo o conteúdo. A redação automática não detecta todos os segredos. OpenAI transmite esta prévia para um serviço externo; Ollama deve usar um modelo local.'}

    @app.post('/api/investigations/{id}/ai/analyze', status_code=201)
    def ai_analyze(id: str, body: s.ApproveInput, session: Session = Depends(db)):
        allowed(session, get(session, m.Investigation, id))
        consent = get(session, m.Consent, body.consent_id)
        if consent.investigation_id != id or consent.used or consent.digest != body.digest:
            raise HTTPException(409, 'Aprovação inválida ou já utilizada.')
        # Verify the approved sources still exist, are linked and have not changed.
        sources = json.loads(consent.payload)['untrusted_evidence']
        for source in sources:
            record = get(session, m.Evidence, source['evidence_id'])
            if record.investigation_id != id or record.sha256 != source['sha256']:
                raise HTTPException(409, 'Evidência alterada. Gere outra prévia.')
            read_evidence(root, record)
        consent.used = True
        session.commit()  # A failed request also consumes approval; never retry automatically.
        try:
            result, usage = ai.run(settings, consent)
        finally:
            consent.payload = ''  # Retain consent metadata without a second copy of evidence text.
            session.commit()
        return save(session, m.Analysis(investigation_id=id, provider=consent.provider, model=consent.model, result=result, usage=usage))

    @app.get('/api/export')
    def export(session: Session = Depends(db)):
        content = workspace(session)
        return attachment(json.dumps(content, ensure_ascii=False, indent=2).encode(), 'application/json', 'caspar-export.json')

    @app.post('/api/backup')
    def backup(session: Session = Depends(db)):
        output = BytesIO()
        with tempfile.TemporaryDirectory(dir=root / 'backups') as temp:
            snapshot = Path(temp) / 'caspar.sqlite3'
            with closing(sqlite3.connect(root / 'caspar.sqlite3')) as source, closing(sqlite3.connect(snapshot)) as dest:
                source.backup(dest)
                # Approval tokens and their content must not survive a restore.
                dest.execute('DELETE FROM consents')
                dest.commit()
            with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
                archive.write(snapshot, 'caspar.sqlite3')
                manifest = {}
                for record in rows(session, m.Evidence):
                    content = read_evidence(root, record)
                    archive.writestr('evidence/' + record.storage_name, content)
                    manifest[record.storage_name] = record.sha256
                archive.writestr('manifest.json', json.dumps({'schema': '0001', 'evidence': manifest}))
        content = output.getvalue()
        name = 'caspar-backup-' + uuid4().hex + '.zip'
        path = root / 'backups' / name
        path.write_bytes(content)
        if os.name != 'nt':
            path.chmod(0o600)
        return attachment(content, 'application/zip', name)

    @app.delete('/api/data', status_code=204)
    def erase(body: s.DeleteInput, session: Session = Depends(db)):
        session.execute(delete(m.Program))  # All dependent rows cascade.
        session.commit()
        # Only fixed storage subdirectories; never follow a user-supplied path or symlink.
        for folder in ('evidence', 'reports', 'backups'):
            base = root / folder
            for path in base.iterdir():
                if path.is_file() or path.is_symlink():
                    path.unlink()
        with engine.connect() as conn:
            conn.exec_driver_sql('PRAGMA wal_checkpoint(TRUNCATE)')
            conn.exec_driver_sql('VACUUM')

    @app.delete('/api/investigations/{id}', status_code=204)
    def investigation_delete(id: str, session: Session = Depends(db)):
        record = get(session, m.Investigation, id)
        paths = [evidence_path(root, e.storage_name) for e in rows(session, m.Evidence, investigation_id=id)]
        session.delete(record)
        session.commit()
        for path in paths:
            path.unlink(missing_ok=True)

    @app.delete('/api/programs/{id}', status_code=204)
    def program_delete(id: str, session: Session = Depends(db)):
        record = get(session, m.Program, id)
        for investigation in rows(session, m.Investigation, program_id=id):
            investigation_delete(investigation.id, session)
        session.delete(record)
        session.commit()

    app.add_middleware(BodyLimit)
    dist = REPO / 'frontend' / 'dist'
    if dist.is_dir():
        app.mount('/', StaticFiles(directory=dist, html=True), name='frontend')
    return app
