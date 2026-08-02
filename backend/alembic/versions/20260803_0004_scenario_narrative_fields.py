# 시나리오에 AI가 생성하는 배분 근거·SCB 성장 가능성 서사 컬럼을 추가하는 마이그레이션
"""add scenario narrative fields"""

import sqlalchemy as sa

from alembic import op

revision = "20260803_0004"
down_revision = "20260731_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scenarios", sa.Column("allocation_rationale", sa.Text(), nullable=True))
    op.add_column("scenarios", sa.Column("scb_growth_outlook", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("scenarios", "scb_growth_outlook")
    op.drop_column("scenarios", "allocation_rationale")
