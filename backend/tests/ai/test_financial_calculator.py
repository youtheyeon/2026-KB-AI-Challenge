# 세 상환 방식과 거치 기간의 대표 월 상환액을 검증하는 테스트
import pytest
from financial_calculator import (
    calc_representative_monthly_payment,
    calculate_financial_projection,
)


def test_equal_payment_uses_remaining_term_after_grace() -> None:
    without_grace = calc_representative_monthly_payment(
        12_000_000,
        0.06,
        36,
        0,
        "equal_payment",
    )
    with_grace = calc_representative_monthly_payment(
        12_000_000,
        0.06,
        36,
        6,
        "equal_payment",
    )

    assert with_grace > without_grace


def test_equal_principal_uses_first_post_grace_payment() -> None:
    payment = calc_representative_monthly_payment(
        12_000_000,
        0.06,
        36,
        6,
        "equal_principal",
    )

    assert payment == 460_000


def test_bullet_payment_uses_monthly_interest() -> None:
    payment = calc_representative_monthly_payment(
        12_000_000,
        0.06,
        36,
        0,
        "bullet_payment",
    )

    assert payment == 60_000


def test_representative_payment_rejects_grace_equal_to_term() -> None:
    with pytest.raises(ValueError, match="거치 기간"):
        calc_representative_monthly_payment(
            12_000_000,
            0.06,
            36,
            36,
            "equal_payment",
        )


def test_financial_projection_uses_repayment_type_and_grace() -> None:
    result = calculate_financial_projection(
        allocation={
            "marketing_online": 0.25,
            "equipment_interior": 0.25,
            "labor": 0.25,
            "inventory": 0.25,
        },
        loan_amount=12_000_000,
        baseline_monthly_revenue=7_500_000,
        annual_interest_rate=0.06,
        loan_term_months=36,
        grace_months=6,
        repayment_type="equal_principal",
    )

    assert result["monthly_loan_payment"] == 460_000


def test_bullet_projection_discloses_maturity_principal_risk() -> None:
    result = calculate_financial_projection(
        allocation={
            "marketing_online": 0.25,
            "equipment_interior": 0.25,
            "labor": 0.25,
            "inventory": 0.25,
        },
        loan_amount=12_000_000,
        baseline_monthly_revenue=7_500_000,
        annual_interest_rate=0.06,
        loan_term_months=36,
        grace_months=0,
        repayment_type="bullet_payment",
    )

    assert "만기" in result["risk_level_basis"]
