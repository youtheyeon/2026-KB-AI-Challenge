"""
validate_bottleneck_detection.py — 병목 진단 엔진 검증

목적: "규칙 기반 계산기에 LLM 설명만 붙인 것 아니냐"는 의문에,
     실제로 병목 진단 엔진이 의도한 문제를 정확히 찾아내는지 검증 결과로 답한다.

방법: 특정 병목이 있다고 '설계'한 테스트 케이스 5개를 mock 데이터로 만들고,
     bottleneck_detector.py가 그 의도한 병목을 1순위(최고 심각도)로 정확히
     찾아내는지 비교한다.

정직하게 밝히는 것: '플랫폼 수수료 과다'처럼 지금 구현되지 않은 병목 유형은
     테스트 케이스에서 제외했다 (억지로 있는 척하지 않음).
"""

from mock_pos_data import generate_mock_pos_data
from bottleneck_detector import compute_time_of_day_benchmark_with_sample_size, detect_bottlenecks

SEVERITY_RANK = {"심각": 3, "뚜렷": 2, "경미": 1}

TEST_CASES = [
    {"case": "Case 1", "design": "저녁 매출 부족", "mock_scenario": "evening_weak", "expected_type": "time_of_day_weakness"},
    {"case": "Case 2", "design": "원가 과다", "mock_scenario": "high_cost_ratio", "expected_type": "high_cost_ratio"},
    {"case": "Case 3", "design": "인건비 과다", "mock_scenario": "high_labor_ratio", "expected_type": "high_labor_ratio"},
    {"case": "Case 4", "design": "좌석 포화", "mock_scenario": "seat_shortage", "expected_type": "seat_capacity_shortage"},
    {"case": "Case 5", "design": "재구매율 저조", "mock_scenario": "low_repeat", "expected_type": "low_repeat_rate"},
]

# 정직하게 밝히는 부분: 아래 유형은 현재 시스템에 아예 구현되어 있지 않아 테스트에서 제외함
NOT_IMPLEMENTED_NOTE = "'플랫폼 수수료 과다' 등 온라인 채널 비용 관련 병목 유형은 현재 미구현 상태라 검증 대상에서 제외"


def top_bottleneck(findings: list) -> dict:
    """발견된 병목 중 심각도가 가장 높은 것을 1순위로 반환."""
    if not findings:
        return None
    return max(findings, key=lambda f: SEVERITY_RANK.get(f["severity"], 0))


def run_validation():
    time_benchmark, sample_size = compute_time_of_day_benchmark_with_sample_size()

    results = []
    all_findings_flat = []

    for case in TEST_CASES:
        pos_data = generate_mock_pos_data(scenario=case["mock_scenario"], monthly_revenue=7_500_000)
        findings = detect_bottlenecks(pos_data, time_benchmark, time_benchmark_sample_size=sample_size)
        all_findings_flat.extend(findings)

        top = top_bottleneck(findings)
        detected_type = top["bottleneck_type"] if top else None
        matched = detected_type == case["expected_type"]

        results.append({
            **case,
            "detected_type": detected_type,
            "detected_title": top["title"] if top else "(탐지 안 됨)",
            "detected_severity": top["severity"] if top else "-",
            "all_findings_count": len(findings),
            "matched": matched,
        })

    return results, all_findings_flat


def print_results(results: list, all_findings_flat: list):
    print("=" * 90)
    print("병목 진단 엔진 검증 결과")
    print("=" * 90)
    print(f"{'테스트 사업장':<10} {'설계한 상태':<14} {'1순위 탐지 병목':<22} {'결과':<6}")
    print("-" * 90)

    match_count = 0
    for r in results:
        result_label = "일치" if r["matched"] else "불일치"
        if r["matched"]:
            match_count += 1
        print(f"{r['case']:<10} {r['design']:<14} {r['detected_title']:<22} {result_label:<6}")

    accuracy = match_count / len(results) * 100
    print("-" * 90)
    print(f"\n1순위 탐지 정확도: {match_count}/{len(results)} ({accuracy:.0f}%)")
    print(f"※ {NOT_IMPLEMENTED_NOTE}")

    # 근거가 실제 데이터인지 가정치인지 비율
    real_data_count = sum(1 for f in all_findings_flat if f["confidence_badge"] == "높음")
    assumption_count = sum(1 for f in all_findings_flat if f["confidence_badge"] == "보통")
    mock_count = sum(1 for f in all_findings_flat if f["confidence_badge"] == "낮음")
    total = len(all_findings_flat)

    print(f"\n검증 과정에서 발견된 전체 병목 {total}건의 근거 구성:")
    print(f"  실제 데이터 기반(신뢰도 높음): {real_data_count}건 ({real_data_count/total*100:.0f}%)")
    print(f"  업계 가정치 기반(신뢰도 보통): {assumption_count}건 ({assumption_count/total*100:.0f}%)")
    print(f"  사용자 데이터 기반, mock 상태(신뢰도 낮음): {mock_count}건 ({mock_count/total*100:.0f}%)")

    # 실패 케이스가 있으면 구체적으로 왜 실패했는지도 출력 (숨기지 않음)
    failed = [r for r in results if not r["matched"]]
    if failed:
        print(f"\n[불일치 상세]")
        for r in failed:
            print(f"  {r['case']} ({r['design']}): 의도한 병목은 '{r['expected_type']}'였으나, "
                  f"실제 1순위는 '{r['detected_type']}'(으)로 탐지됨")


if __name__ == "__main__":
    results, all_findings_flat = run_validation()
    print_results(results, all_findings_flat)