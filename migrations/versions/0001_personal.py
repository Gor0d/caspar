"""Initial personal research schema. Frozen schema, independent of application models."""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None


def upgrade():
    def table(name, *columns):
        op.create_table(name, sa.Column('id', sa.String(36), primary_key=True),
                        sa.Column('created_at', sa.String(), nullable=False), *columns)

    def text(name, size=None):
        return sa.Column(name, sa.String(size) if size else sa.Text(), nullable=False)

    def fk(name, target):
        return sa.Column(name, sa.String(36), sa.ForeignKey(target + '.id', ondelete='CASCADE'), nullable=False)

    table('programs', text('name', 160), text('policy'), text('authorization'), sa.Column('authorized', sa.Boolean(), nullable=False))
    table('assets', fk('program_id', 'programs'), text('pattern', 253), sa.Column('allowed', sa.Boolean(), nullable=False), text('note'))
    table('investigations', fk('program_id', 'programs'), text('title', 200), text('target', 253))
    table('journals', fk('investigation_id', 'investigations'), text('body'))
    table('evidence', fk('investigation_id', 'investigations'), text('filename', 200), sa.Column('storage_name', sa.String(50), nullable=False, unique=True), text('sha256', 64), sa.Column('size', sa.Integer(), nullable=False), text('provenance'))
    table('findings', fk('investigation_id', 'investigations'), text('title', 200), text('severity', 20), text('cwe', 30), text('owasp', 120), *[text(n) for n in ['hypothesis', 'verified', 'conclusion', 'steps', 'impact', 'remediation']], sa.Column('evidence_ids', sa.JSON(), nullable=False), text('status', 30), sa.Column('reward_cents', sa.Integer(), nullable=False), text('currency', 3), text('submission_reference', 500))
    table('reports', fk('investigation_id', 'investigations'), text('language', 2), text('markdown'))
    table('consents', fk('investigation_id', 'investigations'), text('provider', 20), text('model', 160), text('payload'), text('digest', 64), sa.Column('used', sa.Boolean(), nullable=False))
    table('analyses', fk('investigation_id', 'investigations'), text('provider', 20), text('model', 160), text('result'), sa.Column('usage', sa.JSON(), nullable=False))


def downgrade():
    for name in ['analyses', 'consents', 'reports', 'findings', 'evidence', 'journals', 'investigations', 'assets', 'programs']:
        op.drop_table(name)
