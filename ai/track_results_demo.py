"""
track_results_demo.py — 결과 추적 데모 (성공만 하지 않는 버전)

목적: "이 서비스가 추천한 대로 하면 다 잘 된다"는 인상을 주지 않기 위해,
     1회차 진단 -> 배분 실행 -> (가상의) N개월 후 실제 결과 -> 2회차 진단이
     섞인 결과(일부 개선, 일부 악화)로 이어지는 걸 보여준다.

주의: 실제 서비스에서는 진짜 POS 연동 데이터로 이 추적이 이뤄진다.
     여기서는 mock으로 '있음직한 2회차 결과'를 직접 설계해서 보여주는 데모다.
     이 점을 발표에서도 명시해야 한다 (실측 사례라고 과장하면 안 됨).
"""

from mock_pos_data import generate_mock_pos_data
from bottleneck_detector import compute_time_of_day_benchmark_with_sample_size, detect_bottlenecks
from allocation_draft_generator import generate_scenario_drafts
from financial_calculator import calculate_financial_projection


def run_round(label, pos_data, time_benchmark, sample_size, loan_amount, chosen_allocation=None):
    findings = detect_bottlenecks(pos_data, time_benchmark, time_benchmark_sample_size=sample_size)

    print(f"\n{'='*80}")
    print(f"{label}")
    print("=" * 80)

    if not findings:
        print("발견된 병목 없음")
    for f in findings:
        print(f"  [{f['title']}] {f['priority_badge']} / 신뢰도 {f['confidence_badge']}")
        print(f"    {f['detail']}")

    if chosen_allocation:
        fin = calculate_financial_projection(chosen_allocation, loan_amount, pos_data["monthly_revenue"])
        print(f"\n  [선택한 배분안 재실행 결과] 잔여현금: {fin['remaining_cash_after_payment']:,}원 / 위험도: {fin['risk_level']}")

    return findings


if __name__ == "__main__":
    time_benchmark, sample_size = compute_time_of_day_benchmark_with_sample_size()
    loan_amount = 15_000_000

    # ── 1회차: 저녁 매출 부족 진단, B안(진단 비례 대응형) 선택했다고 가정 ──
    round1_pos = generate_mock_pos_data(scenario="evening_weak", monthly_revenue=7_500_000)
    round1_findings = run_round("1회차 (시뮬레이션 시점)", round1_pos, time_benchmark, sample_size, loan_amount)

    drafts = generate_scenario_drafts(round1_findings)
    chosen = next(d for d in drafts if d["scenario_id"] == "B")
    print(f"\n  -> 사용자가 선택: [{chosen['scenario_id']}안 - {chosen['label']}] {chosen['allocation']}")

    # ── 2회차: 3개월 후 '가정된 실제 결과' ──
    # 이 부분이 데모의 핵심: 전부 좋아지지 않았다는 걸 의도적으로 설계함
    #   - 저녁 시간대 매출 비중: 개선됨 (12.0% -> 19.5%, 벤치마크 21.6%에 근접)  [성공]
    #   - 원가율: 오히려 악화됨 (온라인 채널 확대로 배달 수수료/포장재 비용 증가 반영) [실패]
    #   - 고용: 변화 없음 (그대로) [계획대로]
    #   - 매출 자체는 소폭 개선되었지만 원가 상승분을 상쇄하지 못함 [손익분기 미달]
    round2_pos = generate_mock_pos_data(scenario="normal", monthly_revenue=8_100_000)  # 매출은 7.5M -> 8.1M로 소폭 개선(+8%)
    round2_pos["time_of_day_sales"] = {
        "TMZON_00_06_SELNG_AMT": round(8_100_000 * 0.01),
        "TMZON_06_11_SELNG_AMT": round(8_100_000 * 0.16),
        "TMZON_11_14_SELNG_AMT": round(8_100_000 * 0.32),
        "TMZON_14_17_SELNG_AMT": round(8_100_000 * 0.27),
        "TMZON_17_21_SELNG_AMT": round(8_100_000 * 0.195),  # 12.0% -> 19.5%로 개선
        "TMZON_21_24_SELNG_AMT": round(8_100_000 * 0.045),
    }
    round2_pos["monthly_cogs"] = round(8_100_000 * 0.58)  # 원가율 45%(정상) -> 58%로 악화
    round2_pos["monthly_labor_cost"] = round(8_100_000 * 0.18)  # 인건비는 그대로

    round2_findings = run_round("2회차 (3개월 후, 가정된 실제 결과)", round2_pos, time_benchmark, sample_size, loan_amount)

    # ── 두 회차 비교 요약 ──
    print(f"\n{'='*80}")
    print("1회차 -> 2회차 변화 요약 (성공/실패 혼재)")
    print("=" * 80)
    round1_types = {f["bottleneck_type"] for f in round1_findings}
    round2_types = {f["bottleneck_type"] for f in round2_findings}

    resolved = round1_types - round2_types
    newly_emerged = round2_types - round1_types
    persisted = round1_types & round2_types

    print(f"  개선되어 사라진 병목: {resolved or '없음'}")
    print(f"  새로 발생한 병목: {newly_emerged or '없음'}")
    print(f"  여전히 남아있는 병목: {persisted or '없음'}")

    fin2 = calculate_financial_projection(chosen["allocation"], loan_amount, round2_pos["monthly_revenue"])
    breakeven_met = fin2["remaining_cash_after_payment"] >= 0
    print(f"\n  2회차 재무 재점검: 잔여현금 {fin2['remaining_cash_after_payment']:,}원 "
          f"({'손익분기 충족' if breakeven_met else '손익분기 조건 일부 미달'})")

    print("\n  결론: 배분안 실행 결과 저녁 시간대 병목은 개선됐으나, 원가율 병목이 새로 부각됨.")
    print("       -> 다음 회차 배분안 추천 시 원가율(설비·재고관리) 비중을 높이는 방향으로 갱신되어야 함.")
    print("\n  ※ 이 2회차 데이터는 실제 POS 연동 결과가 아니라, '있음직한 시나리오'로 설계한 데모입니다.")