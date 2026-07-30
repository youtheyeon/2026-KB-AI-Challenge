"""
SCB 성장 가능성 방향성 매핑 (scb_outlook.py)

원칙: SCB 점수·등급을 직접 계산하지 않는다. 대신 "이 자금 배분이 SCB가 참고하는
     것으로 알려진 항목(매출, 근로자 수, 유통플랫폼 성장지수, 사업 지속성 등) 중
     어디에 방향성 있게 연결되는지"만 정성적으로(숫자 없이) 보여준다.

근거: SCB는 매출, 업종, 상권, 사업 지속성, 근로자 수, 고객 인지도,
     유통플랫폼 성장지수 등 비금융정보를 활용하는 것으로 알려져 있음
     (원 기획안 배경 설명 참고). 세부 가중치·산식은 비공개라 재현 불가.
"""

CATEGORY_TO_SCB = {
    "marketing_online": [
        {"scb_item": "매출", "direction": "긍정적 방향 가능성"},
        {"scb_item": "유통플랫폼 성장지수", "direction": "긍정적 방향 가능성 (온라인 채널 확대 시)"},
        {"scb_item": "고객 인지도", "direction": "긍정적 방향 가능성"},
    ],
    "equipment_interior": [
        {"scb_item": "사업 지속성", "direction": "긍정적 방향 가능성 (운영 안정성 개선)"},
        {"scb_item": "매출", "direction": "간접적 긍정 가능성 (원가/회전율 개선을 통해)"},
    ],
    "labor": [
        {"scb_item": "근로자 수", "direction": "직접 증가"},
    ],
    "inventory": [
        {"scb_item": "사업 지속성", "direction": "긍정적 방향 가능성 (재고·원가 관리 개선)"},
    ],
}

DISCLAIMER = (
    "SCB 점수·등급은 은행이 직접 산정하며, 본 서비스는 SCB 점수를 계산하거나 예측하지 않습니다. "
    "위 내용은 SCB가 참고하는 것으로 알려진 항목과 자금 배분의 방향성을 정성적으로 안내하는 것입니다."
)


def generate_scb_outlook(allocation: dict) -> dict:
    """
    배분 비율이 큰 카테고리 순으로 관련 SCB 항목을 정리해서 반환한다.
    비율 자체를 근거로 '어느 항목에 더 무게가 실렸는지' 순서만 매기고,
    수치화된 영향도는 절대 제시하지 않는다.
    """
    sorted_cats = sorted(allocation.items(), key=lambda x: -x[1])

    outlook = []
    seen_items = set()
    for cat, share in sorted_cats:
        if share <= 0:
            continue
        for entry in CATEGORY_TO_SCB.get(cat, []):
            key = entry["scb_item"]
            if key in seen_items:
                continue
            seen_items.add(key)
            outlook.append({
                "scb_item": entry["scb_item"],
                "direction": entry["direction"],
                "driven_by": cat,
                "allocation_share_pct": round(share * 100, 1),
            })

    return {"scb_outlook": outlook, "disclaimer": DISCLAIMER}


if __name__ == "__main__":
    from mock_pos_data import generate_mock_pos_data
    from bottleneck_detector import compute_time_of_day_benchmark, detect_bottlenecks
    from allocation_draft_generator import generate_scenario_drafts

    time_benchmark = compute_time_of_day_benchmark()
    user_data = generate_mock_pos_data(scenario="evening_weak", monthly_revenue=7_500_000)
    findings = detect_bottlenecks(user_data, time_benchmark)
    drafts = generate_scenario_drafts(findings)

    for d in drafts:
        print(f"\n[{d['scenario_id']}안 - {d['label']}] {d['allocation']}")
        result = generate_scb_outlook(d["allocation"])
        for item in result["scb_outlook"]:
            print(f"  - {item['scb_item']}: {item['direction']} (근거: {item['driven_by']} {item['allocation_share_pct']}% 배분)")
        print(f"  ※ {result['disclaimer']}")
