# 이메일 사용자를 익명 데모 세션으로 교체하는 Alembic 마이그레이션
"""replace user with demo session"""

from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision = "20260730_0002"
down_revision = "20260730_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "demo_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "expired",
                name="demo_session_status",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            server_default="active",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column(
        "businesses",
        sa.Column("demo_session_id", sa.UUID(), nullable=True),
    )

    connection = op.get_bind()
    migrated_at = datetime.now(UTC)
    business_ids = list(connection.execute(sa.text("SELECT id FROM businesses")).scalars())
    for business_id in business_ids:
        demo_session_id = uuid4()
        connection.execute(
            sa.text(
                """
                INSERT INTO demo_sessions (
                    id,
                    last_accessed_at,
                    expires_at,
                    status
                )
                VALUES (
                    :id,
                    :last_accessed_at,
                    :expires_at,
                    'expired'
                )
                """
            ),
            {
                "id": demo_session_id,
                "last_accessed_at": migrated_at,
                "expires_at": migrated_at,
            },
        )
        connection.execute(
            sa.text(
                """
                UPDATE businesses
                SET demo_session_id = :demo_session_id
                WHERE id = :business_id
                """
            ),
            {
                "demo_session_id": demo_session_id,
                "business_id": business_id,
            },
        )

    op.alter_column("businesses", "demo_session_id", nullable=False)
    op.create_foreign_key(
        op.f("businesses_demo_session_id_fkey"),
        "businesses",
        "demo_sessions",
        ["demo_session_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        op.f("businesses_user_id_fkey"),
        "businesses",
        type_="foreignkey",
    )
    op.drop_column("businesses", "user_id")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")


def downgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.add_column(
        "businesses",
        sa.Column("user_id", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        op.f("businesses_user_id_fkey"),
        "businesses",
        "users",
        ["user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        op.f("businesses_demo_session_id_fkey"),
        "businesses",
        type_="foreignkey",
    )
    op.drop_column("businesses", "demo_session_id")
    op.drop_table("demo_sessions")
