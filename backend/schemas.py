from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class ProgramInput(Input):
    name: str = Field(min_length=1, max_length=160)
    policy: str = Field(default='', max_length=20000)
    authorization: str = Field(default='', max_length=10000)
    authorized: bool = False

    @model_validator(mode='after')
    def authorization_required(self):
        if self.authorized and not self.authorization:
            raise ValueError('Registre a referência e condições da autorização.')
        return self


class AssetInput(Input):
    pattern: str = Field(min_length=1, max_length=253)
    allowed: bool
    note: str = Field(default='', max_length=5000)


class ScopeInput(Input):
    target: str = Field(min_length=1, max_length=500)


class InvestigationInput(ScopeInput):
    title: str = Field(min_length=1, max_length=200)


class JournalInput(Input):
    body: str = Field(min_length=1, max_length=20000)


class FindingInput(Input):
    title: str = Field(min_length=1, max_length=200)
    severity: Literal['info', 'low', 'medium', 'high', 'critical'] = 'info'
    cwe: str = Field(default='', pattern=r'^(CWE-\d{1,6})?$', max_length=30)
    owasp: str = Field(default='', max_length=120)
    hypothesis: str = Field(default='', max_length=20000)
    verified: str = Field(default='', max_length=20000)
    conclusion: str = Field(default='', max_length=20000)
    steps: str = Field(default='', max_length=20000)
    impact: str = Field(default='', max_length=20000)
    remediation: str = Field(default='', max_length=20000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=100)
    status: Literal['draft', 'submitted', 'triaged', 'accepted', 'resolved', 'duplicate', 'rejected'] = 'draft'
    reward_cents: int = Field(default=0, ge=0, le=100000000000)
    currency: str = Field(default='USD', pattern=r'^[A-Z]{3}$')
    submission_reference: str = Field(default='', max_length=500)

    @model_validator(mode='after')
    def verified_needs_evidence(self):
        if self.verified and not self.evidence_ids:
            raise ValueError('Fatos verificados exigem evidência vinculada.')
        return self


class ReportInput(Input):
    language: Literal['pt', 'en'] = 'pt'


class PreviewInput(Input):
    provider: Literal['openai', 'ollama']
    evidence_ids: list[str] = Field(min_length=1, max_length=20)
    question: str = Field(min_length=1, max_length=2000)


class ApproveInput(Input):
    consent_id: str
    digest: str
    approved: Literal[True]


class DeleteInput(Input):
    confirmation: Literal['DELETE ALL LOCAL DATA']
