"""
api_schema.py — 내부 결과(한글/스네이크케이스)를 API 스펙(영문 enum/camelCase)으로 변환

원칙: 내부 로직은 그대로 두고, 외부로 나갈 때만 이 레이어를 거친다.
     기존 코드를 뜯어고치지 않기 위한 '번역 레이어'.
"""

SEVERITY_MAP = {"경미": "MILD", "뚜렷": "CLEAR", "심각": "SEVERE"}

STRATEGY_TYPE_MAP = {
    "병목 집중형": "BOTTLENECK_FOCUSED",
    "진단 비례 대응형": "PROPORTIONAL",
    "균등 분산형 (기준선)": "EQUAL_SPLIT",
}

# 내부 evidence_source 문자열 -> (evidenceSourceType enum, evidenceDescription)
EVIDENCE_SOURCE_MAP = {
    "실제 서울시 카페 매출 데이터 기반 벤치마크": ("PUBLIC_DATA", "서울시 카페 시간대별 추정매출"),
    "AI 비지도학습(K-means)으로 분류된 유사 소비패턴 상권군 평균": ("BENCHMARK", "AI 클러스터링 기반 유사 상권군 평균"),
    "업계 가정치 (실증 데이터 없음)": ("DOMAIN_ASSUMPTION", "업계 참고치, 실증 데이터 아님"),
    "업계 가정치 (온라인 채널, 실증 데이터 없음)": ("DOMAIN_ASSUMPTION", "온라인 채널 업계 참고치, 실증 데이터 아님"),
    "사용자 POS 데이터": ("SYNTHETIC_SALES", "사용자 POS 데이터 (현재 mock)"),
    "사용자 온라인 판매·정산 자료 (선택 업로드)": ("SYNTHETIC_ONLINE_SALES", "사용자 온라인 판매·정산 자료 (현재 mock)"),
}

CATEGORY_MAP = {
    "marketing_online": "MARKETING_ONLINE",
    "equipment_interior": "EQUIPMENT_INTERIOR",
    "labor": "LABOR",
    "inventory": "INVENTORY",
}


def bottleneck_to_api_schema(finding: dict) -> dict:
    evidence_type, evidence_desc = EVIDENCE_SOURCE_MAP.get(
        finding.get("evidence_source"), ("DOMAIN_ASSUMPTION", finding.get("evidence_source", ""))
    )
    related_category = CATEGORY_MAP.get(finding.get("suggested_category"))
    return {
        "bottleneckType": finding["bottleneck_type"].upper(),
        "title": finding.get("title"),
        "detail": finding.get("detail"),
        "severity": SEVERITY_MAP.get(finding.get("severity"), "MILD"),
        "evidenceSourceType": evidence_type,
        "evidenceDescription": evidence_desc,
        "methodology": finding.get("methodology"),
        "relatedCategories": [related_category] if related_category else [],
    }


def scenario_to_api_schema(scenario_result: dict) -> dict:
    fin = scenario_result["financial_result"]
    strategy_type = STRATEGY_TYPE_MAP.get(scenario_result["label"], "UNKNOWN")

    allocations = [
        {
            "category": CATEGORY_MAP.get(cat, cat.upper()),
            "ratio": pct,
            "amount": scenario_result["allocation_amounts_won"][cat],
        }
        for cat, pct in scenario_result["allocation"].items()
    ]

    # 한계: allocation_draft_generator.py가 자유 문장(rationale)만 반환하고
    # 구조화된 (병목,카테고리) 쌍은 안 주기 때문에, 지금은 description만 채워진다.
    # 스펙대로 완전히 채우려면 rationale 생성부를 구조화된 리스트로 확장해야 한다.
    draft_reasons = [
        {
            "bottleneckType": None,
            "relatedCategory": None,
            "description": scenario_result.get("allocation_rationale"),
        }
    ]

    return {
        "scenarioCode": scenario_result["scenario_id"],
        "strategyType": strategy_type,
        "title": scenario_result["label"],
        "allocations": allocations,
        "draftReasons": draft_reasons,
        "financialResult": {
            "monthlyLoanPayment": fin["monthly_loan_payment"],
            "monthlyRecurringCost": fin["additional_fixed_cost_per_month"],
            "cashAfterPaymentIfCurrentStateMaintained": fin["remaining_cash_after_payment"],
            "breakEvenAdditionalRevenue": fin["break_even_additional_revenue"],
            "requiredAdditionalOrders": fin["required_additional_orders"],
            "allowedRevenueDecline": fin["allowed_revenue_decline"],
            "paybackPeriodMonths": fin["payback_period"]["months"],
            "paybackStatus": fin["payback_period"]["status"],
            "riskLevel": {"낮음": "LOW", "중간": "MEDIUM", "높음": "HIGH"}.get(fin["risk_level"], "MEDIUM"),
            "riskReasons": [fin["risk_level_basis"]] + (
                [fin["loan_scale_warning"]["message"]] if fin["loan_scale_warning"]["is_warning"] else []
            ),
        },
        "targetMetrics": scenario_result.get("target_metrics", []),
        "scbGrowthOutlook": scenario_result.get("scb_growth_outlook"),
    }


def run_simulation_result_to_api_schema(result: dict) -> dict:
    """run_simulation()의 결과 전체를 API 응답 형식으로 변환."""
    return {
        "status": "COMPLETED",
        "bottlenecks": [bottleneck_to_api_schema(f) for f in result["bottleneck_diagnosis"]],
        "scenarios": [scenario_to_api_schema(s) for s in result["scenario_results"]],
        "disclaimer": {
            "recommendationProvided": False,
            "editable": False,
            "message": "각 시나리오는 진단 결과에 따라 생성된 고정 비교안이며 실제 성과를 예측하거나 보장하지 않습니다.",
        },
        "versions": result.get("versions", {}),
    }