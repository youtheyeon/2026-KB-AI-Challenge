"""
컴포넌트 E: 시나리오별 설명 생성 (llm_explainer.py) — v3

역할:
  - 병목 진단(A)과 재무 계산(B)의 '구조화 데이터·배지'는 여전히 코드가 만든다 (LLM 없음).
  - 이 파일은 A/B/C 시나리오 하나당 1번씩 LLM을 호출해서, 두 부분을 함께 생성한다:
      1) 배분 근거: 이 배분안이 어떤 병목(구체적 수치 포함)에 대응하는지, 왜 이런 비율인지
      2) SCB 성장 가능성: 이 배분이 어떤 SCB 항목 측면에서 성장 가능성으로 이어질 수 있는지
  - 두 부분을 한 번의 호출로 받아서(JSON), UI에서는 별도 섹션으로 나눠 표시한다.
"""

import os
import json
import re
import requests
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """당신은 소상공인 자금 배분 시뮬레이터의 시나리오별 설명 생성 담당입니다.
반드시 아래 두 부분을 각각 작성하고, 다른 말 없이 순수 JSON 객체 하나로만 응답하세요.

{
  "allocation_rationale": "...",
  "scb_growth_outlook": "..."
}

[allocation_rationale] 작성 규칙:
- 입력된 병목 진단 목록(diagnosis) 중, 이 배분안이 실제로 대응하는 병목을 구체적 수치와 함께 언급하며,
  왜 이런 비율로 배분했는지 설명하세요.
- 언급하는 병목의 confidence_badge가 "보통"이나 "낮음"이면, 그 근거가 실제 데이터가 아니라
  업계 가정치이거나 실제 연동 전 데이터라는 한계를 자연스럽게 언급하세요.
- 다른 시나리오(A/B/C)보다 이 안이 낫다고 비교하거나 추천하지 마세요.
- 200~300자.

[scb_growth_outlook] 작성 규칙:
- 입력된 scb_outlook 리스트에 있는 항목만 다루세요. 그 외 항목은 언급하지 마세요.
- "~측면에서 성장 가능성이 높아질 수 있습니다"처럼 완곡한 표현만 쓰고, "오릅니다"처럼 단정하지 마세요.
- 왜 그렇게 연결되는지 메커니즘을 한두 문장으로 구체적으로 설명하세요 (한 줄 요약 금지).
- 200~300자.

공통 규칙:
- 입력에 없는 숫자를 만들지 마세요.
- 호칭("사장님," 등), 감탄사, 격려 멘트 쓰지 마세요. 담백한 서비스 안내문 톤.
- 반드시 JSON 형식만 출력하세요 (마크다운 코드블록도 쓰지 마세요).
"""


def _extract_json(text: str) -> dict:
    # 혹시 코드블록으로 감싸서 응답하면 벗겨내고 파싱
    cleaned = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    return json.loads(cleaned)


def generate_scenario_explanation(scenario_id: str, scenario_label: str, allocation: dict,
                                   diagnosis: list, scb_outlook: list) -> dict:
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY가 설정되지 않았습니다.")

    payload = {
        "시나리오": {"id": scenario_id, "label": scenario_label, "allocation": allocation},
        "diagnosis": [
            {
                "title": d["title"], "detail": d["detail"], "comparison_chip": d["comparison_chip"],
                "confidence_badge": d["confidence_badge"], "suggested_category": d["suggested_category"],
            } for d in diagnosis
        ],
        "scb_outlook": scb_outlook,
    }
    user_prompt = f"아래 데이터를 바탕으로 위 규칙에 맞는 JSON을 작성하세요.\n\n{json.dumps(payload, ensure_ascii=False, indent=2)}"

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": MODEL,
            "max_tokens": 700,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_prompt}],
        },
        timeout=30,
    )
    resp.raise_for_status()
    text = resp.json()["content"][0]["text"]

    try:
        return _extract_json(text)
    except json.JSONDecodeError:
        # 파싱 실패 시 원문이라도 확인할 수 있게 반환 (디버깅용)
        return {"allocation_rationale": text, "scb_growth_outlook": "(JSON 파싱 실패, 원문 표시)"}


# ─────────────────────────────────────────────
# 실행 (테스트)
# ─────────────────────────────────────────────
if __name__ == "__main__":
    from mock_pos_data import generate_mock_pos_data
    from bottleneck_detector import compute_time_of_day_benchmark_with_sample_size, detect_bottlenecks
    from allocation_draft_generator import generate_scenario_drafts
    from financial_calculator import calculate_financial_projection
    from scb_outlook import generate_scb_outlook

    time_benchmark, sample_size = compute_time_of_day_benchmark_with_sample_size()
    user_data = generate_mock_pos_data(scenario="multi_bottleneck", monthly_revenue=7_500_000)
    findings = detect_bottlenecks(user_data, time_benchmark, time_benchmark_sample_size=sample_size)
    drafts = generate_scenario_drafts(findings)

    loan_amount = 15_000_000
    baseline_revenue = user_data["monthly_revenue"]

    print("=== [A] 병목 후보 카드 (코드로 완결, LLM 없음) ===")
    for f in findings:
        print(f"  [{f['title']}] {f['priority_badge']} / 신뢰도 {f['confidence_badge']} — {f['comparison_chip']}")

    print("\n=== [B] + [C] 시나리오별: 재무결과(코드) + 배분근거·SCB설명(LLM, 시나리오당 1회 호출) ===")
    for d in drafts:
        fin = calculate_financial_projection(d["allocation"], loan_amount, baseline_revenue)
        scb_result = generate_scb_outlook(d["allocation"])

        print(f"\n{'='*70}")
        print(f"[{d['scenario_id']}안 - {d['label']}] {d['allocation']}")
        print("=" * 70)
        print(f"[재무 결과] 잔여현금 {fin['remaining_cash_after_payment']:,}원 / 위험도 {fin['risk_level']}")

        explanation = generate_scenario_explanation(
            scenario_id=d["scenario_id"], scenario_label=d["label"], allocation=d["allocation"],
            diagnosis=findings, scb_outlook=scb_result["scb_outlook"],
        )
        print(f"\n[배분 근거]\n{explanation['allocation_rationale']}")
        print(f"\n[SCB 성장 가능성]\n{explanation['scb_growth_outlook']}")
