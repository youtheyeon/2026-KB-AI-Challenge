# 시나리오 사전 선택 없이도 집행을 등록할 수 있도록 선택 참조를 선택적으로 바꾸는 마이그레이션
"""make execution selection_id nullable"""

import sqlalchemy as sa

from alembic import op

revision = "20260803_0005"
down_revision = "20260803_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("executions", "selection_id", existing_type=sa.BigInteger(), nullable=True)


def downgrade() -> None:
    op.alter_column("executions", "selection_id", existing_type=sa.BigInteger(), nullable=False)
