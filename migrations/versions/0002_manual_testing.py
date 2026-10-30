"""Manual test plans, one-use approval and immutable run records."""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'


def upgrade():
    def text(name, size=None):
        return sa.Column(name, sa.String(size) if size else sa.Text(), nullable=False)

    op.create_table('test_plans',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.String(), nullable=False),
        sa.Column('investigation_id', sa.String(36), sa.ForeignKey('investigations.id', ondelete='CASCADE'), nullable=False),
        text('title', 200), text('objective'), text('technique', 200), text('preconditions'), text('steps'), text('expected_result'), text('stop_conditions'),
        sa.Column('revision', sa.Integer(), nullable=False), text('status', 20),
        sa.Column('approved_revision', sa.Integer(), nullable=False), sa.Column('approved_at', sa.String(), nullable=False), text('approval_context', 64))
    op.create_table('test_runs',
        sa.Column('id', sa.String(36), primary_key=True), sa.Column('created_at', sa.String(), nullable=False),
        sa.Column('investigation_id', sa.String(36), sa.ForeignKey('investigations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('test_plan_id', sa.String(36), sa.ForeignKey('test_plans.id', ondelete='CASCADE'), nullable=False),
        sa.Column('plan_snapshot', sa.JSON(), nullable=False), sa.Column('performed_at', sa.String(), nullable=False), text('outcome', 30), text('observed_result'), text('limitations'),
        sa.Column('evidence_ids', sa.JSON(), nullable=False),
        sa.Column('finding_id', sa.String(36), sa.ForeignKey('findings.id', ondelete='SET NULL'), nullable=True),
        text('review_notes'), sa.Column('reviewed_at', sa.String(), nullable=False))


def downgrade():
    op.drop_table('test_runs')
    op.drop_table('test_plans')
