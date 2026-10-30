from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import ForeignKey, String, Text, Boolean, Integer, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def uid():
    return str(uuid4())


def now():
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class Record:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    created_at: Mapped[str] = mapped_column(String, default=now)


class Program(Record, Base):
    __tablename__ = 'programs'
    name: Mapped[str] = mapped_column(String(160))
    policy: Mapped[str] = mapped_column(Text, default='')
    authorization: Mapped[str] = mapped_column(Text, default='')
    authorized: Mapped[bool] = mapped_column(Boolean, default=False)


class Asset(Record, Base):
    __tablename__ = 'assets'
    program_id: Mapped[str] = mapped_column(ForeignKey('programs.id', ondelete='CASCADE'))
    pattern: Mapped[str] = mapped_column(String(253))
    allowed: Mapped[bool] = mapped_column(Boolean)
    note: Mapped[str] = mapped_column(Text, default='')


class Investigation(Record, Base):
    __tablename__ = 'investigations'
    program_id: Mapped[str] = mapped_column(ForeignKey('programs.id', ondelete='CASCADE'))
    title: Mapped[str] = mapped_column(String(200))
    target: Mapped[str] = mapped_column(String(253))


class Journal(Record, Base):
    __tablename__ = 'journals'
    investigation_id: Mapped[str] = mapped_column(ForeignKey('investigations.id', ondelete='CASCADE'))
    body: Mapped[str] = mapped_column(Text)


class Evidence(Record, Base):
    __tablename__ = 'evidence'
    investigation_id: Mapped[str] = mapped_column(ForeignKey('investigations.id', ondelete='CASCADE'))
    filename: Mapped[str] = mapped_column(String(200))
    storage_name: Mapped[str] = mapped_column(String(50), unique=True)
    sha256: Mapped[str] = mapped_column(String(64))
    size: Mapped[int] = mapped_column(Integer)
    provenance: Mapped[str] = mapped_column(Text)


class Finding(Record, Base):
    __tablename__ = 'findings'
    investigation_id: Mapped[str] = mapped_column(ForeignKey('investigations.id', ondelete='CASCADE'))
    title: Mapped[str] = mapped_column(String(200))
    severity: Mapped[str] = mapped_column(String(20))
    cwe: Mapped[str] = mapped_column(String(30), default='')
    owasp: Mapped[str] = mapped_column(String(120), default='')
    hypothesis: Mapped[str] = mapped_column(Text, default='')
    verified: Mapped[str] = mapped_column(Text, default='')
    conclusion: Mapped[str] = mapped_column(Text, default='')
    steps: Mapped[str] = mapped_column(Text, default='')
    impact: Mapped[str] = mapped_column(Text, default='')
    remediation: Mapped[str] = mapped_column(Text, default='')
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(30), default='draft')
    reward_cents: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(3), default='USD')
    submission_reference: Mapped[str] = mapped_column(String(500), default='')


class Report(Record, Base):
    __tablename__ = 'reports'
    investigation_id: Mapped[str] = mapped_column(ForeignKey('investigations.id', ondelete='CASCADE'))
    language: Mapped[str] = mapped_column(String(2))
    markdown: Mapped[str] = mapped_column(Text)


class Consent(Record, Base):
    __tablename__ = 'consents'
    investigation_id: Mapped[str] = mapped_column(ForeignKey('investigations.id', ondelete='CASCADE'))
    provider: Mapped[str] = mapped_column(String(20))
    model: Mapped[str] = mapped_column(String(160))
    payload: Mapped[str] = mapped_column(Text)
    digest: Mapped[str] = mapped_column(String(64))
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class Analysis(Record, Base):
    __tablename__ = 'analyses'
    investigation_id: Mapped[str] = mapped_column(ForeignKey('investigations.id', ondelete='CASCADE'))
    provider: Mapped[str] = mapped_column(String(20))
    model: Mapped[str] = mapped_column(String(160))
    result: Mapped[str] = mapped_column(Text)
    usage: Mapped[dict] = mapped_column(JSON, default=dict)
