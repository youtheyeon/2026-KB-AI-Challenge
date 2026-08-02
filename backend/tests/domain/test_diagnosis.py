# 진단 SQLAlchemy 모델의 스냅샷 근거와 제약을 검증하는 테스트
from sqlalchemy import CheckConstraint, UniqueConstraint

from app.domain.dataset import BusinessSnapshot, PublicDataSnapshot
from app.domain.diagnosis import Bottleneck, Diagnosis, DiagnosisMetric
from app.domain.enums import DiagnosisEvidenceSource


def test_business_snapshot_is_unique_for_each_business_and_dataset() -> None:
    constraints = BusinessSnapshot.__table__.constraints

    assert any(
        isinstance(constraint, UniqueConstraint)
        and tuple(column.name for column in constraint.columns) == ("business_id", "dataset_id")
        for constraint in constraints
    )


def test_diagnosis_records_its_snapshot_evidence_source() -> None:
    diagnosis = Diagnosis(
        business_snapshot_id=1,
        public_data_snapshot_id=2,
        evidence_source=DiagnosisEvidenceSource.BUSINESS_AND_PUBLIC_DATA,
    )

    assert diagnosis.evidence_source is DiagnosisEvidenceSource.BUSINESS_AND_PUBLIC_DATA
    assert Diagnosis.__table__.c.business_snapshot_id.foreign_keys
    assert Diagnosis.__table__.c.public_data_snapshot_id.foreign_keys


def test_diagnosis_evidence_source_is_stored_as_a_string_check_constraint() -> None:
    constraints = Diagnosis.__table__.constraints

    assert Diagnosis.__table__.c.evidence_source.type.length == 32
    assert any(
        isinstance(constraint, CheckConstraint)
        and "business_and_public_data" in str(constraint.sqltext)
        for constraint in constraints
    )


def test_diagnosis_owns_metrics_and_bottlenecks() -> None:
    metrics = Diagnosis.__mapper__.relationships["metrics"]
    bottlenecks = Diagnosis.__mapper__.relationships["bottlenecks"]

    assert metrics.cascade.delete_orphan is True
    assert bottlenecks.cascade.delete_orphan is True
    assert DiagnosisMetric.__table__.c.diagnosis_id.foreign_keys
    assert Bottleneck.__table__.c.diagnosis_id.foreign_keys


def test_diagnosis_evidence_relations_preserve_source_snapshots() -> None:
    assert Diagnosis.__mapper__.relationships["business_snapshot"].cascade.delete_orphan is False
    assert Diagnosis.__mapper__.relationships["public_data_snapshot"].cascade.delete_orphan is False
    assert PublicDataSnapshot.__mapper__.relationships["diagnoses"].cascade.delete_orphan is False
