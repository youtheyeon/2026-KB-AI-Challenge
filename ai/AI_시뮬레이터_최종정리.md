# AI 시뮬레이터 엔진 — 최종 정리 (v4)
### 병목 진단 + 고정 배분안(A/B/C) + 재무계산 + LLM설명 + 재평가 루프

---

## 0. 지금 이 프로젝트의 정체성 (한 문장)

**"자금을 X에 쓰면 매출이 Y% 오른다"를 예측하지 않는다.**
**실제 데이터 기반 AI 클러스터링으로 "당신의 병목이 뭔지" 진단하고, 그 진단에 따라 만들어진**
**A/B/C 배분안 중 하나를 사용자가 선택하면, 그 배분안대로 실행했을 때의 재무 결과(원리금/잔여현금/손익분기)를**
**투명하게 계산해서 보여준다. 집행 후 3개월 뒤 결과를 다시 진단해서 다음 회차로 이어간다.**

---

## 1. 전체 프로세스 흐름 (v4 최종)

```
[0] 데이터 수집 (배치, 완료)
    소상공인시장진흥공단 API + 서울시 상권분석서비스 API (상가정보/추정매출/점포/유동인구)
        │
[1] 상권 자동 그룹화 (clustering.py) ← 진짜 비지도학습(K-means)
    시간대·요일별 매출 패턴만으로 서울 상권 342개를 3개 그룹으로 자동 분류 (실루엣 0.228)
        │
[2] 사용자 프로필 + POS/장부 데이터 입력
    상권유형 / 업력 / 매출구간 / 대출조건 + 시간대별매출·원가·인건비·재구매율·좌석·(선택)온라인채널
        │
[3] 사용자를 클러스터에 배정 (cluster_benchmark.py)
    사용자 소비패턴 벡터와 가장 가까운 클러스터를 유클리드 거리로 탐색
        │
[4] 병목 진단 (bottleneck_detector.py) — 9종 병목, 3단계 심각도
    실제 클러스터 벤치마크 / 업계 가정치 / 사용자 자체 데이터와 비교
    → 병목 유형 + 심각도(경미/뚜렷/심각) + 근거출처 + 판정방법론(methodology) 반환
        │
[5] 병목 → A/B/C 배분안 생성 (allocation_draft_generator.py)
    심각도 점수 → 카테고리 합산 → 최소비중(5%) → 100% 정규화, 5단계 공식 전부 공개 가능
    A안(병목 집중형) / B안(진단 비례 대응형) / C안(균등 분산형=기준선)
    각 안에 확인해야 할 목표지표(target_metrics)도 함께 부착
    ※ 고정값. 사용자는 그중 하나를 '선택'만 함 (수정 불가)
        │
[6] 재무 계산 (financial_calculator.py) — 매출 성장 가정 없음
    원리금 / 추가고정비 / 잔여현금 / 손익분기추가매출 / 필요추가주문수 / 매출감소허용범위 / 위험등급
        │
[7] SCB 방향성 매핑 (scb_outlook.py) — 숫자 없이 정성적
    배분이 SCB 참고 항목(매출/온라인활동/근로자수/사업지속성) 중 어디에 방향성 있는지만 표시
    업종/상권/업력처럼 고정 정보는 절대 언급 안 함
        │
[8] LLM 설명 생성 (llm_explainer.py) — 유일하게 LLM(Claude Haiku)이 쓰이는 곳
    raw 숫자만 주고, "배분 근거"와 "SCB 성장 가능성"을 LLM이 직접 추론해서 서술
    시나리오당 1회 호출, JSON으로 두 섹션 동시에 받음
        │
[9] 사용자 선택 → (실제 또는 Mock) 집행 → 3개월 후 결과 데이터
        │
[10] 재평가 (outcome_tracker.py) — compare_outcomes()
    해결된 병목 / 남은 병목 / 신규 병목 판별, 손익분기 4단계 판정
    (조건충족/일부충족/미충족/비교불가)
    결과 스냅샷이 다음 회차 run_simulation()의 입력으로 그대로 재사용됨 → 선순환 루프 완성
        │
[11] 통합 (run_simulation.py) — 위 전체를 함수 하나로
    입력: profile, loan, pos_data → 출력: 병목진단+시나리오3개+버전정보 전부 담긴 dict
        │
[12] 스키마 변환 (api_schema.py) — 백엔드 연결용
    내부(한글/스네이크케이스) → 스펙(영문 enum/camelCase)로 변환하는 번역 레이어
```

---

## 2. 파일별 상태 (전체, 최신)

| 파일 | 역할 | 비고 |
|---|---|---|
| `fetch_benchmark_data.py` | 원본 데이터 수집 | 완료 |
| `classify_and_find_codes.py` | 카페 업종코드, 상권 키워드 1차 분류 | 완료 |
| `build_final_benchmark.py` | 세그먼트별 매출 참고치 (용도×규모) | 완료 |
| `clustering.py` | **비지도학습(K-means)** 상권 자동 그룹화 | 완료, k=3, 실루엣 0.228 |
| `cluster_benchmark.py` | 사용자를 클러스터에 배정 | 완료 |
| `mock_pos_data.py` | mock 사용자 데이터 (온라인채널 포함, 시나리오 10종) | 완료 |
| `bottleneck_detector.py` | 병목 진단 9종 (기본5 + 온라인4) | 완료 |
| `allocation_draft_generator.py` | A/B/C 배분안 + target_metrics | 완료 |
| `financial_calculator.py` | 재무계산 (손익분기 3필드 포함) | 완료 |
| `scb_outlook.py` | SCB 방향성 매핑 | 완료 |
| `llm_explainer.py` | LLM 설명 생성 (유일한 LLM 사용처) | 완료 |
| `outcome_tracker.py` | 재평가(compare_outcomes) | 완료 |
| `run_simulation.py` | 전체 통합 진입점 함수 | 완료 |
| `api_schema.py` | 백엔드 연결용 스키마 변환 | 완료 (draftReasons 구조화는 한계로 남음) |
| `api_server.py` | (선택) HTTP 서버로 띄우는 버전 | 완료하지만 이번엔 미사용 — 아래 3번 참고 |
| `validate_bottleneck_detection.py` | 검증: 5개 케이스 병목탐지 정확도 | 완료, 5/5(100%) |
| `formula_disclosure.py` | 검증: 배분비율 계산 5단계 전부 공개 | 완료 |
| `track_results_demo.py` | 검증: 성공/실패 혼재 결과 데모 | 완료 |
| `regression_model.py` | 회귀모델 시도 (유동인구·개업률→매출성장률) | **시도했으나 실패(R²=0.008), 정직한 근거자료로 활용** |

---

## 3. 근거 구성 (실데이터 / 가정치 / mock 비율)

`validate_bottleneck_detection.py` 실행 결과 기준:
- 실제 데이터 기반(신뢰도 높음): 20%
- 업계 가정치(신뢰도 보통): 60%
- mock/사용자 데이터(신뢰도 낮음): 20%

→ 발표 시 이 비율을 숨기지 않고 "우리가 데이터 한계를 정확히 인지하고 라벨링하고 있다"는 근거로 제시.

---

## 4. 알려진 한계 (숨기지 않고 정리)

1. 원가율·인건비율·재구매율·온라인채널 참고치는 여전히 업계 가정치 (실증 데이터 아님)
2. 좌석부족·재구매율 병목은 아직 mock 데이터 기반 (실 POS 연동 전)
3. 클러스터링 실루엣 스코어(0.228)가 아주 높지 않음 — "중간 수준의 구분력"으로 정직하게 표현해야 함
4. `api_schema.py`의 `draftReasons`가 완전히 구조화되지 않음 (LLM 자유문장만 들어감)
5. 회귀모델(유동인구·개업률→매출성장률)은 실패 — R²=0.008, 근거자료로만 활용

---

## 5. 백엔드에서 이 AI 파트를 쓰는 방법 (서버 안 띄우고, 같은 레포에서 직접 import)

### 전제
AI 파트와 백엔드가 **같은 레포(모노레포) 안에서 같이 돌아간다**는 전제. 별도 HTTP 서버(`api_server.py`)는 안 쓰고, 백엔드가 이 폴더의 Python 함수를 **직접 import해서 호출**한다.

### 5-1. 폴더 구조 예시
```
프로젝트루트/
├── ai/                          ← 지금까지 만든 AI 파트 전체
│   ├── run_simulation.py
│   ├── api_schema.py
│   ├── bottleneck_detector.py
│   ├── ... (나머지 전부)
│   ├── raw_data/                ← 사전 계산된 벤치마크/클러스터 결과 (필수)
│   └── .env                     ← ANTHROPIC_API_KEY 등
└── backend/                     ← 백엔드 코드 (Python이라고 가정)
    └── app.py
```

### 5-2. 백엔드에서 호출하는 최소 코드
```python
import sys
sys.path.append("../ai")  # 또는 프로젝트 구조에 맞게 경로 설정 (PYTHONPATH로 관리 권장)

from run_simulation import run_simulation
from api_schema import run_simulation_result_to_api_schema

def handle_simulation_request(profile: dict, loan: dict, pos_data: dict) -> dict:
    """백엔드 API 엔드포인트 핸들러 안에서 이렇게 호출하면 된다."""
    internal_result = run_simulation(profile, loan, pos_data)
    api_response = run_simulation_result_to_api_schema(internal_result)
    return api_response
```

이게 끝이다. 백엔드는 `POST /api/businesses/{id}/simulations` 요청이 들어오면, 요청 바디를 `profile`/`loan`/`pos_data` 형태로 정리해서 `handle_simulation_request()`에 넘기고, 반환된 dict를 그대로 JSON 응답으로 내려주면 된다.

### 5-3. 재평가(다음 회차) 호출
```python
from outcome_tracker import compare_outcomes
from bottleneck_detector import compute_time_of_day_benchmark_with_sample_size

def handle_reassessment(pre_findings, pre_pos_data, post_pos_data, selected_allocation, loan_amount):
    time_benchmark, sample_size = compute_time_of_day_benchmark_with_sample_size()
    result = compare_outcomes(
        pre_findings=pre_findings,
        pre_pos_data=pre_pos_data,
        post_pos_data=post_pos_data,
        time_benchmark=time_benchmark,
        time_benchmark_sample_size=sample_size,
        selected_allocation=selected_allocation,
        loan_amount=loan_amount,
        breakeven_additional_revenue_target=abs(pre_pos_data.get("prior_remaining_cash", 0)) / 0.58,
    )
    # result["next_round_pos_data_snapshot"]을 다음 run_simulation() 호출의 pos_data로 그대로 재사용
    return result
```

### 5-4. 백엔드가 미리 챙겨야 할 것

| 항목 | 왜 필요한지 |
|---|---|
| `ai/.env`에 `ANTHROPIC_API_KEY`, `SBIZ_SERVICE_KEY`, `SEOUL_API_KEY` | LLM 호출 + (배치 재실행 시) 공공데이터 API |
| `ai/raw_data/` 안의 사전 계산 파일들 (`segment_benchmark_table_v2.json`, `trade_area_clusters.json`, `seoul_cafe_sales_full.json`) | 서버 최초 배포 시 1회 미리 만들어서 같이 배포해야 함 (매 요청마다 다시 계산 안 함) |
| Python 패키지 설치 | `requirements.txt`로 `requests`, `python-dotenv` 등 명시해서 백엔드 배포 환경에도 설치 |

### 5-5. 주의할 점 (동기 호출이라 생기는 이슈)

`run_simulation()` 안에서 **시나리오 3개마다 LLM API를 순차 호출**한다 (`llm_explainer.py`). 이게 네트워크 호출이라, **한 번의 시뮬레이션 요청에 몇 초 정도 지연이 생길 수 있다.** 백엔드에서:
- 동기 요청/응답 구조면, 타임아웃을 넉넉히 잡아둘 것 (예: 30초 이상)
- 필요하면 백엔드 쪽에서 비동기 처리(백그라운드 작업 + 폴링)로 감싸는 것도 고려 가능 — 이건 AI 파트가 아니라 백엔드 설계 영역

### 5-6. 만약 나중에 서버 분리가 필요해지면
`api_server.py`(FastAPI)가 이미 만들어져 있으니, "같은 레포 direct import" 방식에서 "별도 서버 + HTTP" 방식으로 전환하고 싶어지면 그걸 그대로 띄우기만 하면 된다 (지금은 안 쓰지만 옵션으로 남겨둠).

---

## 6. 다음 할 일 (남은 것)

1. `api_schema.py`의 `draftReasons` 구조화 — `allocation_draft_generator.py`가 자유문장 대신 구조화된 (병목,카테고리) 리스트를 반환하도록 확장
2. 온라인 채널 병목의 실제 필드명·임계값을 실제 이지샵 자료구조 확인 후 재조정
3. 백엔드와 실제로 위 5번 방식으로 연결 테스트