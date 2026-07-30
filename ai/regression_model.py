"""
회귀모델: 시장 신호(유동인구, 신생매장 비율) -> 매출 성장률 예측

목적: "배분안 -> 매출변화"는 데이터가 없어 못 만들지만,
     "관찰 가능한 시장 신호 -> 매출 성장률"은 우리가 가진 실제 데이터로 진짜 학습 가능하다.

X1: 유동인구/생활인구 변화율 (마케팅·온라인 배분의 대리 근거)
X2: 신생매장 비율 (설비·인테리어 배분의 대리 근거)
Y : 다음 분기 매출 성장률

주의: 아래 API 응답 필드명은 실제 서울시 API 문서를 받아본 뒤 확인/수정이 필요할 수 있음.
      (점포-상권, 길단위인구-상권 API는 이번에 신규 신청하는 것이라 필드명이 100% 확정은 아님)
"""

import os
import json
import time
import requests
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

SEOUL_API_KEY = os.getenv("SEOUL_API_KEY")
QUARTERS = ["20233", "20234", "20241", "20242"]  # 기존 매출 데이터와 동일한 분기로 맞춤
ROWS_PER_PAGE = 1000
MAX_PAGES = 5


# ─────────────────────────────────────────────
# 1) 신규 데이터 수집: 점포-상권 (개폐업/업력 근거)
# ─────────────────────────────────────────────
CAFE_SVC_INDUTY_CD = "CS100010"  # 커피-음료 (기존 매출 데이터와 동일 기준)


def fetch_store_data(yyqu_cd: str) -> list:
    """점포-상권 API. 카페(CS100010) 업종만 클라이언트 사이드에서 필터링한다."""
    all_rows = []
    start = 1
    service_name = "VwsmTrdarStorQq"

    for page in range(MAX_PAGES):
        end = start + ROWS_PER_PAGE - 1
        url = f"http://openapi.seoul.go.kr:8088/{SEOUL_API_KEY}/json/{service_name}/{start}/{end}/{yyqu_cd}"
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        body = data.get(service_name, {})
        rows = body.get("row", [])
        total_count = body.get("list_total_count", 0)

        if not rows:
            print(f"  [경고] {yyqu_cd} 응답에 row가 없음. 응답 원문 일부: {json.dumps(data, ensure_ascii=False)[:300]}")
            break

        cafe_rows = [r for r in rows if r.get("SVC_INDUTY_CD") == CAFE_SVC_INDUTY_CD]
        all_rows.extend(cafe_rows)
        print(f"  [{yyqu_cd}] 점포 데이터 {start}~{end} -> 카페 {len(cafe_rows)}건 (전체 {total_count}건 중, 이 페이지 {len(rows)}건)")

        if end >= total_count:
            break
        start += ROWS_PER_PAGE
        time.sleep(0.2)

    return all_rows


# ─────────────────────────────────────────────
# 2) 신규 데이터 수집: 길단위인구 (유동인구 근거)
# ─────────────────────────────────────────────
def fetch_population_data(yyqu_cd: str) -> list:
    """길단위인구-상권 API. 업종 구분이 없는 상권 단위 데이터라 필터링 없이 그대로 사용."""
    all_rows = []
    start = 1
    service_name = "VwsmTrdarFlpopQq"

    for page in range(MAX_PAGES):
        end = start + ROWS_PER_PAGE - 1
        url = f"http://openapi.seoul.go.kr:8088/{SEOUL_API_KEY}/json/{service_name}/{start}/{end}/{yyqu_cd}"
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        body = data.get(service_name, {})
        rows = body.get("row", [])
        total_count = body.get("list_total_count", 0)

        if not rows:
            print(f"  [경고] {yyqu_cd} 응답에 row가 없음. 응답 원문 일부: {json.dumps(data, ensure_ascii=False)[:300]}")
            break

        all_rows.extend(rows)
        print(f"  [{yyqu_cd}] 유동인구 데이터 {start}~{end} -> {len(rows)}건 (전체 {total_count}건 중)")

        if end >= total_count:
            break
        start += ROWS_PER_PAGE
        time.sleep(0.2)

    return all_rows


# ─────────────────────────────────────────────
# 3) 기존 매출 데이터 로드 (이미 있음)
# ─────────────────────────────────────────────
def load_existing_sales_data() -> list:
    candidates = ["./raw_data/seoul_cafe_sales_full.json", "./raw_data/seoul_cafe_sales.json"]
    path = next((p for p in candidates if os.path.exists(p)), None)
    if not path:
        raise FileNotFoundError("기존 매출 데이터가 없습니다.")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────────────────────────
# 4) 데이터셋 조인: (상권코드, 분기) 기준으로 X1, X2, Y 만들기
# ─────────────────────────────────────────────
def build_regression_dataset(sales_rows, store_rows, population_rows):
    """
    X1 = 유동인구 (TOT_FLPOP_CO, 상권 단위 -- 업종 구분 없음)
    X2 = 개업률 (OPBIZ_RT, 카페 업종만 필터링된 점포 데이터 -- API가 이미 %로 계산해서 줌)
    Y  = 다음 분기 매출 성장률
    """
    # 상권코드+분기 -> 매출 (카페 업종만, 기존 로직 그대로)
    sales_by_key = {}
    for row in sales_rows:
        key = (row["TRDAR_CD"], row["STDR_YYQU_CD"])
        sales_by_key[key] = row.get("THSMON_SELNG_AMT", 0)

    # 상권코드+분기 -> 유동인구 (업종 구분 없이 상권 단위로 그대로 조인)
    population_by_key = {}
    for row in population_rows:
        key = (row.get("TRDAR_CD"), row.get("STDR_YYQU_CD"))
        population_by_key[key] = row.get("TOT_FLPOP_CO")

    # 상권코드+분기 -> 카페 업종 개업률 (API가 이미 %로 제공)
    new_store_ratio_by_key = {}
    for row in store_rows:
        key = (row.get("TRDAR_CD"), row.get("STDR_YYQU_CD"))
        new_store_ratio_by_key[key] = row.get("OPBIZ_RT")

    sorted_quarters = sorted(QUARTERS)
    dataset = []
    trdar_codes = {row["TRDAR_CD"] for row in sales_rows}

    for trdar_cd in trdar_codes:
        for i in range(len(sorted_quarters) - 1):
            q_now, q_next = sorted_quarters[i], sorted_quarters[i + 1]
            key_now = (trdar_cd, q_now)
            key_next = (trdar_cd, q_next)

            sales_now = sales_by_key.get(key_now)
            sales_next = sales_by_key.get(key_next)
            if not sales_now or not sales_next:
                continue

            growth_rate = (sales_next - sales_now) / sales_now

            x1 = population_by_key.get(key_now)
            x2 = new_store_ratio_by_key.get(key_now)
            if x1 is None or x2 is None:
                continue

            dataset.append({"trdar_cd": trdar_cd, "quarter": q_now,
                             "flpop": x1, "opbiz_rt": x2, "growth_rate": growth_rate})

    return dataset


# ─────────────────────────────────────────────
# 5) 회귀분석
# ─────────────────────────────────────────────
def trim_outliers(dataset, lower_pct=5, upper_pct=95):
    """growth_rate 상하위 % 극단값을 제거한다 (분기 성장률 특성상 노이즈가 매우 큼)."""
    import numpy as np
    rates = np.array([d["growth_rate"] for d in dataset])
    lo, hi = np.percentile(rates, [lower_pct, upper_pct])
    trimmed = [d for d in dataset if lo <= d["growth_rate"] <= hi]
    print(f"극단값 제거: {len(dataset)}건 -> {len(trimmed)}건 (growth_rate {lo:.2f} ~ {hi:.2f} 범위만 사용)")
    return trimmed


def fit_regression(dataset):
    try:
        import numpy as np
        from sklearn.linear_model import LinearRegression
        from sklearn.metrics import r2_score
    except ImportError:
        raise SystemExit("pip install scikit-learn numpy --break-system-packages 먼저 실행하세요.")

    if len(dataset) < 10:
        print(f"\n[경고] 표본이 {len(dataset)}개뿐입니다. 회귀분석 결과 신뢰도가 낮을 수 있습니다.")

    X = np.array([[d["flpop"], d["opbiz_rt"]] for d in dataset])
    y = np.array([d["growth_rate"] for d in dataset])

    model = LinearRegression()
    model.fit(X, y)
    pred = model.predict(X)
    r2 = r2_score(y, pred)

    # 표준화(z-score) 계수도 같이 계산 -> 두 변수의 스케일이 완전히 달라서
    # (유동인구는 수만 단위, 개업률은 0~100 단위) 원 단위 계수만 보면 오해하기 쉬움
    X_std = (X - X.mean(axis=0)) / X.std(axis=0)
    model_std = LinearRegression()
    model_std.fit(X_std, y)

    print(f"\n표본 수: {len(dataset)}개")
    print(f"R^2 (설명력): {r2:.3f}")
    print(f"[원 단위] 유동인구 계수: {model.coef_[0]:.10f} / 개업률 계수: {model.coef_[1]:.6f}")
    print(f"[표준화 계수, 서로 비교 가능] 유동인구: {model_std.coef_[0]:.4f} / 개업률: {model_std.coef_[1]:.4f}")
    print(f"절편: {model.intercept_:.6f}")

    return model, r2


if __name__ == "__main__":
    if not SEOUL_API_KEY:
        raise SystemExit(".env에 SEOUL_API_KEY가 없습니다.")

    dataset_cache_path = "./raw_data/regression_dataset.json"

    if os.path.exists(dataset_cache_path):
        print(f"캐시된 데이터셋 발견: {dataset_cache_path} -> API 재호출 없이 바로 사용")
        with open(dataset_cache_path, "r", encoding="utf-8") as f:
            dataset = json.load(f)
    else:
        print("1) 기존 매출 데이터 로드...")
        sales_rows = load_existing_sales_data()
        print(f"   {len(sales_rows)}건 로드")

        print("\n2) 점포(개폐업) 데이터 수집 중...")
        store_rows = []
        for q in QUARTERS:
            store_rows.extend(fetch_store_data(q))

        print("\n3) 유동인구 데이터 수집 중...")
        population_rows = []
        for q in QUARTERS:
            population_rows.extend(fetch_population_data(q))

        print("\n4) 데이터셋 조인 중...")
        dataset = build_regression_dataset(sales_rows, store_rows, population_rows)
        print(f"   최종 학습 데이터: {len(dataset)}건")

        os.makedirs("./raw_data", exist_ok=True)
        with open(dataset_cache_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)

    if len(dataset) >= 5:
        print("\n5) 극단값 제거 후 회귀분석 실행...")
        trimmed_dataset = trim_outliers(dataset, lower_pct=5, upper_pct=95)
        fit_regression(trimmed_dataset)
    else:
        print("\n[중단] 학습 가능한 데이터가 너무 적습니다. 필드명 매핑을 확인하세요.")