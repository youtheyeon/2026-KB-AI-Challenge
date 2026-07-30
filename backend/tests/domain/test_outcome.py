# 실제 집행 이후 관측 결과와 병목 재평가 모델을 검증하는 테스트
import pytest
from sqlalchemy import UniqueConstraint

from app.domain.enums import BottleneckChangeType, OutcomeStatus
from app.domain.outcome import (
    BottleneckChange,
    OutcomeComparison,
    OutcomeComparisonMetric,
    OutcomeData,
    ReassessmentSnapshot,
)


def test_outcome_data_rejects_another_business_snapshot() -> None:
    outcome = OutcomeData(simulation_id=1, observed_business_snapshot_id=2)

    with pytest.raises(ValueError, match="같은 사업체"):
        outcome.validate_business(
            simulation_business_id=10,
            snapshot_business_id=11,
            dataset_business_id=10,
        )


def test_outcome_comparison_uses_execution_from_same_simulation() -> None:
    comparison = OutcomeComparison(
        simulation_id=10,
        execution_id=20,
        outcome_data_id=30,
        status=OutcomeStatus.MET,
    )

    comparison.validate_sources(execution_simulation_id=10, outcome_simulation_id=10)

    with pytest.raises(ValueError, match="같은 시뮬레이션"):
        comparison.validate_sources(execution_simulation_id=11, outcome_simulation_id=10)


def test_comparison_metric_uses_condition_and_observation_names_not_prediction() -> None:
    columns = OutcomeComparisonMetric.__table__.c

    assert "target_value" in columns
    assert "break_even_value" in columns
    assert "observed_value" in columns
    assert "predicted_value" not in columns


def test_reassessment_owns_resolved_remaining_and_new_bottleneck_changes() -> None:
    reassessment = ReassessmentSnapshot(
        latest_business_snapshot_id=1,
        changes=[
            BottleneckChange(
                bottleneck_type="high_cost",
                change_type=BottleneckChangeType.RESOLVED,
            ),
            BottleneckChange(
                bottleneck_type="online_fee",
                change_type=BottleneckChangeType.NEW,
            ),
        ],
    )

    assert {change.change_type for change in reassessment.changes} == {
        BottleneckChangeType.RESOLVED,
        BottleneckChangeType.NEW,
    }
    assert ReassessmentSnapshot.__mapper__.relationships["changes"].cascade.delete_orphan


def test_outcome_resources_are_unique_per_simulation() -> None:
    for model in (OutcomeData, OutcomeComparison):
        assert any(
            isinstance(constraint, UniqueConstraint)
            and tuple(column.name for column in constraint.columns) == ("simulation_id",)
            for constraint in model.__table__.constraints
        )
