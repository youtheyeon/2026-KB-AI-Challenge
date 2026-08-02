"""
재무 계산기 (Financial Calculator) — v4 단순화

원칙: 매출/마진이 얼마나 개선될지는 아예 계산하지 않는다 (사용자 입력도 요구하지 않는다).
     대신 "이 배분안대로 대출을 실행하면, 늘어난 고정비 + 원리금을 감당할 수 있는가"만
     계산한다. 이건 매출 성장 여부와 무관하게 성립하는 순수 지출/상환 계산이다.
"""

DEFAULT_ANNUAL_INTEREST_RATE = 0.045
DEFAULT_LOAN_TERM_MONTHS = 36

# 소상공인실태조사(2023) 기반 실측 영업이익률
ASSUMED_BASELINE_MARGIN = 0.126

# 손익분기 계산용 공헌이익률 (1 - 원가율). bottleneck_detector.py의 업계 참고 원가율(42%)과 동일 기준 사용.
COGS_RATIO_ASSUMPTION = 0.42
CONTRIBUTION_MARGIN_RATE = 1 - COGS_RATIO_ASSUMPTION

RECURRING_RATIO = {
    "marketing_online": 0.6,
    "equipment_interior": 0.1,
    "labor": 1.0,
    "inventory": 0.8,
}
RECURRING_SPEND_PERIOD_MONTHS = 12
FIXED_MONTHLY_WAGE_PER_EMPLOYEE = 2_200_000
EQUIPMENT_MAINTENANCE_RATE_MONTHLY = 0.01
LABOR_HIRE_THRESHOLD = 0.3
LOAN_TO_REVENUE_WARNING_THRESHOLD = 3.0


def calc_monthly_loan_payment(loan_amount: int, annual_rate: float, term_months: int) -> int:
    monthly_rate = annual_rate / 12
    if monthly_rate == 0:
        return round(loan_amount / term_months)
    payment = loan_amount * monthly_rate / (1 - (1 + monthly_rate) ** -term_months)
    return round(payment)


def calc_representative_monthly_payment(
    loan_amount: int,
    annual_rate: float,
    term_months: int,
    grace_months: int,
    repayment_type: str,
) -> int:
    if grace_months < 0 or grace_months >= term_months:
        raise ValueError("거치 기간은 0 이상이고 전체 상환 기간보다 짧아야 합니다.")

    amortizing_months = term_months - grace_months
    monthly_interest = loan_amount * annual_rate / 12
    if repayment_type == "bullet_payment":
        return round(monthly_interest)
    if repayment_type == "equal_principal":
        return round(loan_amount / amortizing_months + monthly_interest)
    return calc_monthly_loan_payment(loan_amount, annual_rate, amortizing_months)


def compute_fixed_cost_effects(allocation: dict, loan_amount: int) -> dict:
    monthly_recurring_cost = 0.0
    for cat, share in allocation.items():
        cat_amount = loan_amount * share
        if cat == "labor":
            continue
        elif cat == "equipment_interior":
            monthly_recurring_cost += cat_amount * EQUIPMENT_MAINTENANCE_RATE_MONTHLY
        else:
            recurring_amount = cat_amount * RECURRING_RATIO.get(cat, 0.5)
            monthly_recurring_cost += recurring_amount / RECURRING_SPEND_PERIOD_MONTHS

    employee_change = 1 if allocation.get("labor", 0) >= LABOR_HIRE_THRESHOLD else 0
    monthly_recurring_cost += employee_change * FIXED_MONTHLY_WAGE_PER_EMPLOYEE

    return {
        "additional_fixed_cost_per_month": round(monthly_recurring_cost),
        "employee_count_change": employee_change,
    }


def check_loan_scale_warning(loan_amount: int, baseline_monthly_revenue: int) -> dict:
    if not baseline_monthly_revenue:
        return {"loan_to_monthly_revenue_ratio": None, "is_warning": False, "message": None}
    ratio = loan_amount / baseline_monthly_revenue
    is_warning = ratio >= LOAN_TO_REVENUE_WARNING_THRESHOLD
    message = None
    if is_warning:
        message = (
            f"대출금이 현재 월매출의 {ratio:.1f}배입니다. "
            f"사업 규모 대비 대출 규모가 큰 편이라 상환 부담이 클 수 있습니다."
        )
    return {"loan_to_monthly_revenue_ratio": round(ratio, 1), "is_warning": is_warning, "message": message}


def calculate_financial_projection(
    allocation: dict,
    loan_amount: int,
    baseline_monthly_revenue: int,
    annual_interest_rate: float = DEFAULT_ANNUAL_INTEREST_RATE,
    loan_term_months: int = DEFAULT_LOAN_TERM_MONTHS,
    avg_daily_customers: int = None,
    grace_months: int = 0,
    repayment_type: str = "equal_payment",
) -> dict:
    """
    매출 성장 가정을 전혀 넣지 않은, 순수 지출/상환 계산.
    '이 배분안을 실행하면 현재 매출 수준 그대로도 감당 가능한가'를 보여준다.

    avg_daily_customers가 주어지면 손익분기 추가 매출을 채우는 데 필요한
    '추가 주문 수'까지 계산한다 (없으면 해당 필드는 None).
    """
    monthly_payment = calc_representative_monthly_payment(
        loan_amount,
        annual_interest_rate,
        loan_term_months,
        grace_months,
        repayment_type,
    )
    fixed_cost_effects = compute_fixed_cost_effects(allocation, loan_amount)
    additional_fixed_cost = fixed_cost_effects["additional_fixed_cost_per_month"]
    employee_change = fixed_cost_effects["employee_count_change"]

    baseline_profit = baseline_monthly_revenue * ASSUMED_BASELINE_MARGIN
    remaining_cash = round(baseline_profit - monthly_payment - additional_fixed_cost)

    loan_scale_warning = check_loan_scale_warning(loan_amount, baseline_monthly_revenue)

    if remaining_cash < 0:
        risk_level = "높음"
    elif loan_scale_warning["is_warning"]:
        risk_level = "중간"
    else:
        risk_level = "낮음"

    # ── 손익분기 관련 3개 필드 (스펙 10.5) ──
    if remaining_cash < 0:
        # 부족분을 메우려면 공헌이익률(매출-변동비 비율) 기준으로 얼마나 더 팔아야 하는지
        breakeven_additional_revenue = round(abs(remaining_cash) / CONTRIBUTION_MARGIN_RATE)
        allowed_revenue_decline = 0  # 이미 적자라 '허용 감소분' 개념 자체가 성립하지 않음
    else:
        breakeven_additional_revenue = 0  # 이미 흑자라 추가로 더 팔아야 할 필요 없음
        # 지금 흑자 폭 안에서 매출이 최대 얼마나 줄어도 버틸 수 있는지
        allowed_revenue_decline = round(remaining_cash / CONTRIBUTION_MARGIN_RATE)

    required_additional_orders = None
    if avg_daily_customers and breakeven_additional_revenue > 0:
        avg_order_value = baseline_monthly_revenue / (avg_daily_customers * 30)
        if avg_order_value > 0:
            required_additional_orders = round(breakeven_additional_revenue / avg_order_value)

    risk_level_basis = (
        "현재 매출 수준 그대로(추가 성장 없이)도 상환·고정비를 감당할 수 있는지로 판정"
    )
    if repayment_type == "bullet_payment":
        risk_level_basis += "했으며 만기에 대출 원금 전액을 별도로 상환해야 합니다."

    return {
        "monthly_loan_payment": monthly_payment,
        "loan_term_months": loan_term_months,  # 대출 자체의 총 상환기간 (계산 아님, 입력조건 그대로)
        "additional_fixed_cost_per_month": additional_fixed_cost,
        "employee_count_change": employee_change,
        "baseline_monthly_profit": round(baseline_profit),
        "remaining_cash_after_payment": remaining_cash,
        "break_even_additional_revenue": breakeven_additional_revenue,
        "required_additional_orders": required_additional_orders,
        "allowed_revenue_decline": allowed_revenue_decline,
        "payback_period": {
            "months": None,
            "status": "UNAVAILABLE",
            "reason": "추가 순현금에 대한 검증된 가정이 없습니다.",
        },
        "risk_level": risk_level,
        "risk_level_basis": risk_level_basis,
        "loan_scale_warning": loan_scale_warning,
    }


if __name__ == "__main__":
    from mock_pos_data import generate_mock_pos_data
    from bottleneck_detector import compute_time_of_day_benchmark, detect_bottlenecks
    from allocation_draft_generator import generate_scenario_drafts

    time_benchmark = compute_time_of_day_benchmark()
    user_data = generate_mock_pos_data(scenario="evening_weak", monthly_revenue=7_500_000)
    findings = detect_bottlenecks(user_data, time_benchmark)
    drafts = generate_scenario_drafts(findings)

    loan_amount = 15_000_000
    baseline_revenue = user_data["monthly_revenue"]
    print(f"대출금: {loan_amount:,}원 / 현재 월매출: {baseline_revenue:,}원\n")

    for d in drafts:
        result = calculate_financial_projection(d["allocation"], loan_amount, baseline_revenue)
        print(f"[{d['scenario_id']}안 - {d['label']}] {d['allocation']}")
        print(f"  월 원리금: {result['monthly_loan_payment']:,}원 / 총 상환기간: {result['loan_term_months']}개월 / 추가 고정비: {result['additional_fixed_cost_per_month']:,}원")
        print(f"  잔여현금(현재 매출 기준): {result['remaining_cash_after_payment']:,}원")
        print(f"  위험도: {result['risk_level']}\n")
