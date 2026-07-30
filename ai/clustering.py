"""
상권 소비패턴 클러스터링 (clustering.py) — 진짜 비지도학습

지금까지 classify_and_find_codes.py는 "상권명에 '대학'이 들어있으면 대학가"처럼
사람이 정한 키워드 규칙으로 상권을 분류했다. 이건 AI가 아니라 문자열 매칭이다.

이 스크립트는 다르다: 상권명을 아예 보지 않는다. 대신 실제 매출 데이터의
"시간대별/요일별 소비 패턴"만 갖고 K-means로 비슷한 소비패턴을 가진 상권끼리
AI가 스스로 그룹을 찾아내게 한다. 결과 클러스터에 이름을 붙이는 건 사람이 하지만,
"어느 상권이 어느 그룹인지"는 전적으로 데이터가 결정한다.

입력: raw_data/seoul_cafe_sales_full.json (또는 seoul_cafe_sales.json)
출력: raw_data/trade_area_clusters.json
"""

import os
import json
from collections import defaultdict

TIME_BUCKETS = ["00_06", "06_11", "11_14", "14_17", "17_21", "21_24"]
WEEKDAYS = ["MON", "TUES", "WED", "THUR", "FRI", "SAT", "SUN"]

RAW_DATA_CANDIDATES = [
    "./raw_data/seoul_cafe_sales_full.json",
    "./raw_data/seoul_cafe_sales.json",
]


# ─────────────────────────────────────────────
# 1) 상권별 소비패턴 벡터 만들기 (여러 분기 평균)
# ─────────────────────────────────────────────
def build_trade_area_features():
    raw_path = next((p for p in RAW_DATA_CANDIDATES if os.path.exists(p)), None)
    if not raw_path:
        raise FileNotFoundError("카페 매출 원본 데이터가 없습니다.")

    with open(raw_path, "r", encoding="utf-8") as f:
        rows = json.load(f)

    # 상권코드별로 여러 분기 데이터를 모음
    by_trdar = defaultdict(list)
    for row in rows:
        by_trdar[row["TRDAR_CD"]].append(row)

    trdar_names = {}
    features = {}

    for trdar_cd, entries in by_trdar.items():
        trdar_names[trdar_cd] = entries[0].get("TRDAR_CD_NM", trdar_cd)

        # 여러 분기 평균 -> 시간대 비중 6개 + 요일 비중 7개 = 13차원 벡터
        time_shares = {b: [] for b in TIME_BUCKETS}
        weekday_shares = {d: [] for d in WEEKDAYS}
        revenues = []

        for row in entries:
            total = row.get("THSMON_SELNG_AMT", 0)
            if not total:
                continue
            revenues.append(total)
            for b in TIME_BUCKETS:
                time_shares[b].append(row.get(f"TMZON_{b}_SELNG_AMT", 0) / total)
            for d in WEEKDAYS:
                weekday_shares[d].append(row.get(f"{d}_SELNG_AMT", 0) / total)

        if not revenues:
            continue

        vector = (
            [sum(time_shares[b]) / len(time_shares[b]) for b in TIME_BUCKETS]
            + [sum(weekday_shares[d]) / len(weekday_shares[d]) for d in WEEKDAYS]
        )
        avg_revenue = sum(revenues) / len(revenues)

        features[trdar_cd] = {"vector": vector, "avg_revenue": avg_revenue}

    return features, trdar_names


# ─────────────────────────────────────────────
# 2) K-means 클러스터링 + 적정 k 탐색
# ─────────────────────────────────────────────
def run_clustering(features: dict, k_range=range(3, 7)):
    try:
        import numpy as np
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import silhouette_score
    except ImportError:
        raise SystemExit("pip install scikit-learn numpy --break-system-packages 먼저 실행하세요.")

    trdar_codes = list(features.keys())
    X = np.array([features[t]["vector"] for t in trdar_codes])

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    print(f"클러스터링 대상 상권 수: {len(trdar_codes)}개, 특성 차원: {X.shape[1]}")

    best_k, best_score, best_model = None, -1, None
    print("\n적정 k(그룹 수) 탐색 중 (실루엣 스코어, 높을수록 좋음)...")
    for k in k_range:
        model = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = model.fit_predict(X_scaled)
        score = silhouette_score(X_scaled, labels)
        print(f"  k={k}: silhouette={score:.3f}")
        if score > best_score:
            best_k, best_score, best_model = k, score, model

    print(f"\n선택된 k = {best_k} (silhouette={best_score:.3f})")

    labels = best_model.predict(X_scaled)
    return trdar_codes, labels, best_model, scaler, best_k


# ─────────────────────────────────────────────
# 3) 클러스터 프로파일 해석 (사람이 이름 붙이는 건 여기서만)
# ─────────────────────────────────────────────
def describe_clusters(trdar_codes, labels, features, trdar_names, k):
    from collections import defaultdict as dd

    cluster_members = dd(list)
    for trdar_cd, label in zip(trdar_codes, labels):
        cluster_members[label].append(trdar_cd)

    print("\n" + "=" * 70)
    print("클러스터별 프로파일 (AI가 데이터만으로 찾아낸 그룹)")
    print("=" * 70)

    result = {}
    for cluster_id in range(k):
        members = cluster_members[cluster_id]
        vectors = [features[t]["vector"] for t in members]
        avg_vector = [sum(col) / len(col) for col in zip(*vectors)]

        time_part = avg_vector[:6]
        weekday_part = avg_vector[6:]

        dominant_time = TIME_BUCKETS[time_part.index(max(time_part))]
        dominant_weekday = WEEKDAYS[weekday_part.index(max(weekday_part))]
        avg_rev = sum(features[t]["avg_revenue"] for t in members) / len(members)

        example_names = [trdar_names[t] for t in members[:5]]

        print(f"\n[클러스터 {cluster_id}] 상권 {len(members)}개")
        print(f"  가장 비중 높은 시간대: {dominant_time}시 ({max(time_part)*100:.1f}%)")
        print(f"  가장 비중 높은 요일: {dominant_weekday} ({max(weekday_part)*100:.1f}%)")
        print(f"  평균 분기매출: {avg_rev:,.0f}원")
        print(f"  대표 상권 예시: {', '.join(example_names)}")

        result[cluster_id] = {
            "member_count": len(members),
            "dominant_time_bucket": dominant_time,
            "dominant_weekday": dominant_weekday,
            "avg_quarterly_revenue": round(avg_rev),
            "example_trade_areas": example_names,
            "member_trdar_codes": members,
            # 병목 진단(bottleneck_detector.py)에서 '이 사용자와 비슷한 클러스터의
            # 시간대별/요일별 평균'을 벤치마크로 쓰기 위해 전체 벡터를 그대로 저장
            "avg_time_of_day_shares": dict(zip(TIME_BUCKETS, time_part)),
            "avg_weekday_shares": dict(zip(WEEKDAYS, weekday_part)),
            "full_avg_vector": avg_vector,  # [시간대 6개 + 요일 7개] 순서 그대로
        }

    return result


if __name__ == "__main__":
    print("1) 상권별 소비패턴 벡터 생성 중...")
    features, trdar_names = build_trade_area_features()
    print(f"   {len(features)}개 상권 벡터 생성 완료")

    print("\n2) K-means 클러스터링...")
    trdar_codes, labels, model, scaler, k = run_clustering(features)

    print("\n3) 클러스터 해석...")
    cluster_profiles = describe_clusters(trdar_codes, labels, features, trdar_names, k)

    output = {
        "k": k,
        "cluster_profiles": cluster_profiles,
        "trdar_to_cluster": {t: int(l) for t, l in zip(trdar_codes, labels)},
    }
    os.makedirs("./raw_data", exist_ok=True)
    with open("./raw_data/trade_area_clusters.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("\n결과를 raw_data/trade_area_clusters.json 에 저장했습니다.")