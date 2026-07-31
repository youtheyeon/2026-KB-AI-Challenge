# 결과 검증 API에 필요한 집행·사후 데이터 컬럼과 상태 제약을 추가하는 마이그레이션
"""extend result verification schema"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260731_0003"
down_revision = "20260730_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("execution_type", "executions", type_="check")
    op.execute(
        sa.text(
            """
            UPDATE executions e
            SET execution_type = CASE s.code
                WHEN 'A' THEN 'same_as_a'
                WHEN 'B' THEN 'same_as_b'
                WHEN 'C' THEN 'same_as_c'
            END
            FROM scenario_selections ss
            JOIN scenarios s ON s.id = ss.scenario_id
            WHERE e.selection_id = ss.id AND e.execution_type = 'exact_selected'
            """
        )
    )
    op.execute("UPDATE executions SET execution_type = 'mixed' WHERE execution_type = 'modified'")
    op.execute("UPDATE executions SET execution_type = 'custom' WHERE execution_type = 'mock'")
    op.create_check_constraint(
        "execution_type",
        "executions",
        "execution_type IN ('same_as_a', 'same_as_b', 'same_as_c', 'mixed', 'custom')",
    )

    op.add_column("execution_allocations", sa.Column("name", sa.String(255), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE execution_allocations
            SET name = CASE category
                WHEN 'marketing_online' THEN '마케팅·온라인'
                WHEN 'equipment_interior' THEN '설비·인테리어'
                WHEN 'labor' THEN '인력'
                WHEN 'inventory' THEN '재고'
            END
            """
        )
    )
    op.alter_column("execution_allocations", "name", nullable=False)
    op.alter_column("execution_allocations", "category", nullable=True)

    op.drop_constraint("outcome_data_source", "outcome_data", type_="check")
    op.execute(
        sa.text(
            """
            UPDATE outcome_data
            SET source_type = CASE
                WHEN source_type LIKE 'synthetic_%' THEN 'mock'
                WHEN source_type = 'user_input' THEN 'manual_input'
                ELSE 'file_upload'
            END
            """
        )
    )
    op.create_check_constraint(
        "outcome_data_source",
        "outcome_data",
        "source_type IN ('mock', 'file_upload', 'manual_input')",
    )
    op.execute(
        sa.text(
            """
            UPDATE outcome_data
            SET status = CASE
                WHEN lower(status) = 'ready' THEN 'ready'
                WHEN lower(status) = 'mapping_ready' THEN 'mapping_ready'
                ELSE 'failed'
            END
            """
        )
    )
    op.create_check_constraint(
        "outcome_data_status",
        "outcome_data",
        "status IN ('ready', 'mapping_ready', 'failed')",
    )
    op.add_column(
        "outcome_data",
        sa.Column("raw_pos_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column("outcome_data", sa.Column("monthly_sales_amount", sa.BigInteger()))
    op.add_column("outcome_data", sa.Column("operating_profit_amount", sa.BigInteger()))
    op.add_column("outcome_data", sa.Column("online_order_ratio", sa.Numeric(7, 4)))
    op.add_column("outcome_data", sa.Column("cash_after_repayment_amount", sa.BigInteger()))

    op.add_column(
        "outcome_comparisons",
        sa.Column(
            "next_round_pos_data_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    op.drop_constraint("outcome_metric_status", "outcome_comparison_metrics", type_="check")
    op.execute(
        sa.text(
            """
            UPDATE outcome_comparison_metrics
            SET status = CASE status
                WHEN 'met' THEN 'above_expected'
                WHEN 'partially_met' THEN 'within_range'
                WHEN 'not_met' THEN 'below_expected'
                ELSE 'not_comparable'
            END
            """
        )
    )
    op.create_check_constraint(
        "outcome_metric_status",
        "outcome_comparison_metrics",
        "status IN ('above_expected', 'within_range', 'below_expected', 'not_comparable')",
    )

    op.drop_constraint("bottleneck_change_type", "bottleneck_changes", type_="check")
    op.create_check_constraint(
        "bottleneck_change_type",
        "bottleneck_changes",
        "change_type IN ('resolved', 'remaining', 'new', 'not_comparable')",
    )


def downgrade() -> None:
    connection = op.get_bind()
    null_categories = connection.execute(
        sa.text("SELECT count(*) FROM execution_allocations WHERE category IS NULL")
    ).scalar_one()
    if null_categories:
        raise RuntimeError(
            "카테고리가 없는 자유 집행 항목이 있어 20260730_0002로 되돌릴 수 없습니다."
        )
    not_comparable_changes = connection.execute(
        sa.text("SELECT count(*) FROM bottleneck_changes WHERE change_type = 'not_comparable'")
    ).scalar_one()
    if not_comparable_changes:
        raise RuntimeError("미관측 병목 변경 이력이 있어 20260730_0002로 되돌릴 수 없습니다.")

    op.drop_constraint("bottleneck_change_type", "bottleneck_changes", type_="check")
    op.create_check_constraint(
        "bottleneck_change_type",
        "bottleneck_changes",
        "change_type IN ('resolved', 'remaining', 'new')",
    )

    op.drop_constraint("outcome_metric_status", "outcome_comparison_metrics", type_="check")
    op.execute(
        sa.text(
            """
            UPDATE outcome_comparison_metrics
            SET status = CASE status
                WHEN 'above_expected' THEN 'met'
                WHEN 'within_range' THEN 'partially_met'
                WHEN 'below_expected' THEN 'not_met'
                ELSE 'not_comparable'
            END
            """
        )
    )
    op.create_check_constraint(
        "outcome_metric_status",
        "outcome_comparison_metrics",
        "status IN ('met', 'partially_met', 'not_met', 'not_comparable')",
    )

    op.drop_column("outcome_comparisons", "next_round_pos_data_snapshot")
    op.drop_column("outcome_data", "cash_after_repayment_amount")
    op.drop_column("outcome_data", "online_order_ratio")
    op.drop_column("outcome_data", "operating_profit_amount")
    op.drop_column("outcome_data", "monthly_sales_amount")
    op.drop_column("outcome_data", "raw_pos_data")
    op.drop_constraint("outcome_data_status", "outcome_data", type_="check")
    op.drop_constraint("outcome_data_source", "outcome_data", type_="check")
    op.execute(
        sa.text(
            """
            UPDATE outcome_data
            SET source_type = CASE source_type
                WHEN 'mock' THEN 'synthetic_sales'
                ELSE 'user_input'
            END
            """
        )
    )
    op.create_check_constraint(
        "outcome_data_source",
        "outcome_data",
        "source_type IN ('public_data', 'synthetic_sales', 'synthetic_expense', "
        "'synthetic_online_sales', 'user_input', 'benchmark', 'domain_assumption', "
        "'calculated', 'ai_generated_text')",
    )

    op.alter_column("execution_allocations", "category", nullable=False)
    op.drop_column("execution_allocations", "name")
    op.drop_constraint("execution_type", "executions", type_="check")
    op.execute(
        sa.text(
            """
            UPDATE executions
            SET execution_type = CASE execution_type
                WHEN 'same_as_a' THEN 'exact_selected'
                WHEN 'same_as_b' THEN 'exact_selected'
                WHEN 'same_as_c' THEN 'exact_selected'
                WHEN 'mixed' THEN 'modified'
                ELSE 'mock'
            END
            """
        )
    )
    op.create_check_constraint(
        "execution_type",
        "executions",
        "execution_type IN ('exact_selected', 'modified', 'mixed', 'custom', 'mock')",
    )
