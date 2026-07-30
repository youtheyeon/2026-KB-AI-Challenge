"""
formula_disclosure.py — A/B/C 배분 비율이 어떻게 나왔는지 계산 과정 전부 공개

"AI가 정했다"로 끝내지 않기 위해, allocation_draft_generator.py 내부에서
실제로 일어나는 계산을 단계별로 그대로 노출한다. 여기엔 숨겨진 로직이 없다.

계산식:
  병목 심각도(경미=1, 뚜렷=2, 심각=3)
  × 카테고리 연관도(병목 유형 -> 대응 카테고리 매핑, 1:1)
  → 카테고리별 점수 합산
  → 최소 비중(5%) 적용
  → 100% 정규화
"""

from mock_pos_data import generate_mock_pos_data
from bottleneck_detector import compute_time_of_day_benchmark_with_sample_size, detect_bottlenecks
from allocation_draft_generator import (
    SEVERITY_WEIGHT, BOTTLENECK_TO_CATEGORY, MIN_CATEGORY_SHARE, CATEGORIES,
    _severity_score_by_category,
)


def disclose_calculation(findings: list, draft_type: str = "balanced"):
    print("=" * 80)
    print(f"[{draft_type}] 배분 비율 계산 과정 전체 공개")
    print("=" * 80)

    # 1단계: 각 병목의 심각도 점수
    print("\n[1단계] 병목별 심각도 점수 (경미=1, 뚜렷=2, 심각=3)")
    for f in findings:
        weight = SEVERITY_WEIGHT.get(f["severity"], 1)
        category = BOTTLENECK_TO_CATEGORY.get(f["bottleneck_type"], "(매핑 없음)")
        print(f"  {f['title']}: 심각도={f['severity']}({weight}점) -> 연관 카테고리: {category}")

    # 2단계: 카테고리별 점수 합산
    scores = _severity_score_by_category(findings)
    print("\n[2단계] 카테고리별 점수 합산 (같은 카테고리에 매핑된 병목들의 점수를 더함)")
    for cat in CATEGORIES:
        print(f"  {cat}: {scores.get(cat, 0)}점")

    # 3단계: 최소 비중 적용 + 정규화 (진단 비례 대응형 B안 기준으로 시연)
    print(f"\n[3단계] 최소 비중({MIN_CATEGORY_SHARE*100:.0f}%) 우선 배정")
    allocation = {c: MIN_CATEGORY_SHARE for c in CATEGORIES}
    for cat in CATEGORIES:
        print(f"  {cat}: 최소 {MIN_CATEGORY_SHARE*100:.0f}% 배정")

    remaining = 1 - MIN_CATEGORY_SHARE * len(CATEGORIES)
    score_total = sum(scores.values()) if scores else 1
    print(f"\n[4단계] 남은 비중({remaining*100:.0f}%)을 카테고리 점수 비율대로 추가 배분")
    print(f"  전체 점수 합계: {score_total}점")
    for cat, score in scores.items():
        added = remaining * (score / score_total)
        allocation[cat] += added
        print(f"  {cat}: {remaining*100:.0f}% × ({score}점/{score_total}점) = +{added*100:.1f}%p")

    # 5단계: 정규화 (반올림 오차 등을 100%로 재조정)
    total = sum(allocation.values())
    final_allocation = {c: round(v / total, 3) for c, v in allocation.items()}
    print(f"\n[5단계] 100% 정규화 (전체 합 {total*100:.2f}% -> 정확히 100%로 조정)")
    for cat, pct in final_allocation.items():
        print(f"  {cat}: 최종 {pct*100:.1f}%")

    print("\n" + "=" * 80)
    print("이 계산 과정에 'AI가 임의로 정한' 값은 없습니다.")
    print("유일한 사전 설계값은: 심각도별 점수(1/2/3), 최소비중(5%), 병목-카테고리 매핑표입니다.")
    print("이 값들은 allocation_draft_generator.py에 상수로 고정되어 있으며 실행마다 동일합니다.")
    print("=" * 80)

    return final_allocation


if __name__ == "__main__":
    time_benchmark, sample_size = compute_time_of_day_benchmark_with_sample_size()
    pos_data = generate_mock_pos_data(scenario="multi_bottleneck", monthly_revenue=7_500_000)
    findings = detect_bottlenecks(pos_data, time_benchmark, time_benchmark_sample_size=sample_size)

    disclose_calculation(findings, draft_type="B안 (진단 비례 대응형)")