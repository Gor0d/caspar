"""Offline planning and records of manual tests performed outside CASPAR. No network/executor."""
from datetime import datetime, timezone, timedelta
import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from . import models as m, schemas as s

PLAN_FIELDS = ('title', 'objective', 'technique', 'preconditions', 'steps', 'expected_result', 'stop_conditions')


def register_testing(app, db, get, rows, save, allowed, linked_evidence, read_evidence, root):
    router = APIRouter(prefix='/api')

    def context(session, plan):
        investigation = get(session, m.Investigation, plan.investigation_id)
        allowed(session, investigation)
        program = get(session, m.Program, investigation.program_id)
        snapshot = {'program_id': program.id, 'target': investigation.target,
                    'authorization': program.authorization, 'policy': program.policy,
                    'assets': [{'id': a.id, 'pattern': a.pattern, 'allowed': a.allowed, 'note': a.note}
                               for a in rows(session, m.Asset, program_id=program.id)]}
        digest = hashlib.sha256(json.dumps(snapshot, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        return snapshot, digest

    def revision(plan, expected):
        if plan.revision != expected:
            raise HTTPException(409, 'Plano alterado em outra janela. Recarregue e revise a versão atual.')

    @router.post('/investigations/{id}/test-plans', status_code=201)
    def create(id: str, body: s.TestPlanInput, session: Session = Depends(db)):
        allowed(session, get(session, m.Investigation, id))
        return save(session, m.TestPlan(investigation_id=id, **body.model_dump()))

    @router.put('/test-plans/{id}')
    def update(id: str, body: s.TestPlanUpdate, session: Session = Depends(db)):
        plan = get(session, m.TestPlan, id)
        context(session, plan)
        revision(plan, body.expected_revision)
        for key, value in body.model_dump(exclude={'expected_revision'}).items():
            setattr(plan, key, value)
        plan.revision += 1
        plan.status = 'planned'
        plan.approved_revision = 0
        plan.approved_at = ''
        plan.approval_context = ''
        return save(session, plan)

    @router.get('/test-plans/{id}/approval-preview')
    def approval_preview(id: str, expected_revision: int, session: Session = Depends(db)):
        plan = get(session, m.TestPlan, id)
        revision(plan, expected_revision)
        snapshot, digest = context(session, plan)
        return {'context_digest': digest, 'scope': snapshot}

    @router.post('/test-plans/{id}/approve')
    def approve(id: str, body: s.TestPlanApproval, session: Session = Depends(db)):
        plan = get(session, m.TestPlan, id)
        revision(plan, body.expected_revision)
        _, digest = context(session, plan)
        if body.context_digest != digest:
            raise HTTPException(409, 'Política ou escopo alterado após a prévia. Reabra a aprovação e revise o contexto atual.')
        plan.approved_revision = plan.revision
        plan.approval_context = digest
        plan.approved_at = m.now()
        plan.status = 'approved'
        return save(session, plan)

    @router.post('/test-plans/{id}/runs', status_code=201)
    def record(id: str, body: s.TestRunInput, session: Session = Depends(db)):
        plan = get(session, m.TestPlan, id)
        revision(plan, body.expected_revision)
        scope_snapshot, digest = context(session, plan)
        if plan.status != 'approved' or plan.approved_revision != plan.revision or plan.approval_context != digest:
            raise HTTPException(409, 'Revise e aprove o plano vigente antes de registrar uma execução. Alterações de política ou escopo exigem nova aprovação.')
        if datetime.now(timezone.utc) - datetime.fromisoformat(plan.approved_at) > timedelta(hours=24):
            raise HTTPException(409, 'Aprovação do plano expirada. Revise e aprove novamente.')
        evidence = linked_evidence(session, plan.investigation_id, body.evidence_ids)
        for item in evidence:
            read_evidence(root, item)
        snapshot = {key: getattr(plan, key) for key in PLAN_FIELDS}
        snapshot.update(revision=plan.revision, approved_at=plan.approved_at, scope=scope_snapshot,
                        evidence_manifest={item.id: item.sha256 for item in evidence})
        record = m.TestRun(investigation_id=plan.investigation_id, test_plan_id=plan.id, plan_snapshot=snapshot,
                           **(body.model_dump(exclude={'expected_revision'}) | {'performed_at': body.performed_at.isoformat(), 'evidence_ids': list(dict.fromkeys(body.evidence_ids))}))
        # Atomic commit: recording consumes the approval but never starts an external test.
        plan.approved_revision = 0
        plan.approval_context = ''
        plan.status = 'inconclusive' if body.outcome == 'inconclusive' else 'executed'
        return save(session, record)

    @router.post('/test-runs/{id}/review')
    def review(id: str, body: s.TestRunReview, session: Session = Depends(db)):
        record = get(session, m.TestRun, id)
        if record.reviewed_at:
            raise HTTPException(409, 'Execução já revisada. Registre um reteste para adicionar uma nova avaliação.')
        if body.finding_id:
            finding = get(session, m.Finding, body.finding_id)
            if finding.investigation_id != record.investigation_id:
                raise HTTPException(422, 'Achado pertence a outra investigação.')
        record.finding_id = body.finding_id
        record.review_notes = body.review_notes
        record.reviewed_at = m.now()
        plan = get(session, m.TestPlan, record.test_plan_id)
        latest = rows(session, m.TestRun, test_plan_id=plan.id)[-1]
        if latest.id == record.id and plan.revision == record.plan_snapshot['revision'] and plan.status in ('executed', 'inconclusive'):
            plan.status = 'reviewed'
        return save(session, record)

    app.include_router(router)
