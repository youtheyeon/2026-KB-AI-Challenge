"""
cluster_benchmark.py — 클러스터링 결과를 병목 진단에 실제로 연결

역할: 사용자의 시간대별/요일별 매출 비중을 보고, clustering.py가 찾아낸
     3개 그룹 중 가장 비슷한 그룹(클러스터)에 배정한다.
     그다음 "전체 카페 평균"이 아니라 "그 클러스터의 평균"을 벤치마크로 제공한다.

이렇게 하면 병목 진단이 "1,300여 개 카페 전체 평균과 비교"에서
"AI가 비지도학습으로 찾아낸, 나와 소비패턴이 가장 비슷한 상권군과 비교"로 바뀐다.
"""

import json
import os

TIME_BUCKETS = ["00_06", "06_11", "11_14", "14_17", "17_21", "21_24"]
WEEKDAYS = ["MON", "TUES", "WED", "THUR", "FRI", "SAT", "SUN"]

CLUSTER_FILE_PATH = "./raw_data/trade_area_clusters.json"


def load_clusters() -> dict:
    if not os.path.exists(CLUSTER_FILE_PATH):
        raise FileNotFoundError(f"{CLUSTER_FILE_PATH}가 없습니다. clustering.py를 먼저 실행하세요.")
    with open(CLUSTER_FILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_user_vector(pos_data: dict) -> list:
    """사용자 POS 데이터를 클러스터와 동일한 13차원 벡터(시간대6 + 요일7 비중)로 변환."""
    revenue = pos_data["monthly_revenue"]
    time_vec = [
        pos_data["time_of_day_sales"].get(f"TMZON_{b}_SELNG_AMT", 0) / revenue if revenue else 0
        for b in TIME_BUCKETS
    ]
    weekday_vec = [
        pos_data["weekday_sales"].get(f"{d}_SELNG_AMT", 0) / revenue if revenue else 0
        for d in WEEKDAYS
    ]
    return time_vec + weekday_vec


def _euclidean_distance(v1: list, v2: list) -> float:
    return sum((a - b) ** 2 for a, b in zip(v1, v2)) ** 0.5


def assign_user_cluster(pos_data: dict) -> dict:
    """
    사용자를 가장 가까운 클러스터에 배정하고,
    그 클러스터의 시간대별 벤치마크 + 메타정보를 반환한다.
    """
    clusters = load_clusters()
    user_vector = _build_user_vector(pos_data)

    best_cluster_id, best_distance = None, float("inf")
    for cluster_id_str, profile in clusters["cluster_profiles"].items():
        distance = _euclidean_distance(user_vector, profile["full_avg_vector"])
        if distance < best_distance:
            best_distance = distance
            best_cluster_id = cluster_id_str

    assigned_profile = clusters["cluster_profiles"][best_cluster_id]

    return {
        "cluster_id": int(best_cluster_id),
        "cluster_member_count": assigned_profile["member_count"],
        "cluster_dominant_time": assigned_profile["dominant_time_bucket"],
        "cluster_dominant_weekday": assigned_profile["dominant_weekday"],
        "cluster_example_trade_areas": assigned_profile["example_trade_areas"],
        "time_of_day_benchmark": assigned_profile["avg_time_of_day_shares"],
        "distance_to_cluster_center": round(best_distance, 4),
    }


if __name__ == "__main__":
    from mock_pos_data import generate_mock_pos_data

    for scenario in ["normal", "evening_weak", "multi_bottleneck"]:
        pos_data = generate_mock_pos_data(scenario=scenario, monthly_revenue=7_500_000)
        result = assign_user_cluster(pos_data)

        print(f"\n[{scenario}] -> 클러스터 {result['cluster_id']} 배정 "
              f"(구성원 {result['cluster_member_count']}개 상권, 거리 {result['distance_to_cluster_center']})")
        print(f"  이 클러스터 특징: {result['cluster_dominant_time']}시 강세, {result['cluster_dominant_weekday']}요일 강세")
        print(f"  대표 상권: {', '.join(result['cluster_example_trade_areas'][:3])}")
        print(f"  이 클러스터의 시간대별 벤치마크: "
              f"{ {k: f'{v*100:.1f}%' for k, v in result['time_of_day_benchmark'].items()} }")