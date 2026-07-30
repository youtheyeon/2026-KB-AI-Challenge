"""
최종 벤치마크 테이블 생성 스크립트

이전 단계들의 문제를 한 번에 해결한다:
  1) 데이터 양 확장 - 여러 분기 x 페이징으로 카페 데이터를 더 많이 수집
  2) 평균 대신 중앙값(median) 사용 - 소수의 초대형 카페에 흔들리지 않게
  3) 세그먼트를 2축으로 분리 - 용도(오피스/대학가 등) x 상권 규모(소/중/대)
     -> "대학가의 큰 상권" vs "오피스의 큰 상권"처럼 공정한 비교가 되도록

기존 raw_data/ 안의 파일들은 건드리지 않는다. 이 스크립트는 별도 파일로 저장한다.

실행 전 준비: 이전 스크립트들과 동일 (.env에 SEOUL_API_KEY 필요)

주의: 서울시 API는 일일 호출 제한이 있을 수 있으니,
      QUARTERS와 MAX_PAGES_PER_QUARTER 값을 무리하게 늘리지 마세요.
"""

import os
import json
import time
import statistics
import requests
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

SEOUL_API_KEY = os.getenv("SEOUL_API_KEY")
CAFE_SVC_INDUTY_CD = "CS100010"

# ── 설정값 (필요하면 조정) ──
QUARTERS = ["20233", "20234", "20241", "20242"]  # 수집할 분기 (최근 4개 분기)
ROWS_PER_PAGE = 1000          # 한 번에 받을 최대 행 수 (API 한계)
MAX_PAGES_PER_QUARTER = 5     # 분기당 최대 페이지 수 (5 * 1000 = 5000행까지)

RAW_OUT_PATH = "./raw_data/seoul_cafe_sales_full.json"
SEGMENT_OUT_PATH = "./raw_data/segment_benchmark_table_v2.json"


# ─────────────────────────────────────────────
# 1) 여러 분기 x 페이징으로 데이터 수집
# ─────────────────────────────────────────────
def fetch_quarter_data(yyqu_cd: str) -> list:
    """특정 분기의 카페 데이터를 페이징하며 전부 받아온다."""
    all_cafe_rows = []
    start = 1

    for page in range(MAX_PAGES_PER_QUARTER):
        end = start + ROWS_PER_PAGE - 1
        url = f"http://openapi.seoul.go.kr:8088/{SEOUL_API_KEY}/json/VwsmTrdarSelngQq/{start}/{end}/{yyqu_cd}"

        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        body = data.get("VwsmTrdarSelngQq", {})
        rows = body.get("row", [])
        total_count = body.get("list_total_count", 0)

        if not rows:
            break

        cafe_rows = [r for r in rows if r.get("SVC_INDUTY_CD") == CAFE_SVC_INDUTY_CD]
        all_cafe_rows.extend(cafe_rows)

        print(f"  [{yyqu_cd}] {start}~{end} 조회 -> 카페 {len(cafe_rows)}건 (전체 {total_count}건 중)")

        if end >= total_count:
            break

        start += ROWS_PER_PAGE
        time.sleep(0.2)  # API 과호출 방지용 짧은 대기

    return all_cafe_rows


def fetch_all_quarters() -> list:
    all_rows = []
    for yyqu in QUARTERS:
        print(f"\n분기 {yyqu} 수집 시작...")
        rows = fetch_quarter_data(yyqu)
        all_rows.extend(rows)
        print(f"  -> {yyqu} 총 카페 데이터: {len(rows)}건")
    return all_rows


# ─────────────────────────────────────────────
# 2) 상권 유형 분류 (지난번 개선 버전 그대로 사용)
# ─────────────────────────────────────────────
TRADE_AREA_RULES = [
    ("university", ["대학교", "대학", "캠퍼스", "고등학교", "중학교", "초등학교", "숙대", "홍대", "국대", "외대", "여대"]),
    ("office", ["오피스", "테헤란", "센터", "빌딩", "사무소", "본사", "공사", "청사", "세무서", "구청", "주민센터", "안전센터", "교통공사"]),
    ("residential", ["아파트", "빌라", "래미안", "자이", "힐사이드", "코아루"]),
    ("tourist", ["역사", "고궁", "궁", "미술관", "박물관", "케이블카", "관광", "터널", "산책로", "카페거리", "예술마을", "성지"]),
]
TRANSIT_KEYWORDS = ["역", "터미널"]


def classify_usage_type(trdar_cd_nm: str) -> str:
    for category, keywords in TRADE_AREA_RULES:
        if any(kw in trdar_cd_nm for kw in keywords):
            return category
    return "other"


# ─────────────────────────────────────────────
# 3) 상권 규모 분류 (두 번째 축) - 매출건수 기준 3분위
# ─────────────────────────────────────────────
def assign_scale_tier(rows: list) -> list:
    """
    전체 데이터의 매출건수(THSMON_SELNG_CO) 분포를 보고
    소(low) / 중(medium) / 대(high) 3구간으로 나눈다.
    """
    counts = sorted(r["THSMON_SELNG_CO"] for r in rows)
    n = len(counts)
    p33 = counts[int(n * 0.33)]
    p66 = counts[int(n * 0.66)]

    for r in rows:
        c = r["THSMON_SELNG_CO"]
        if c <= p33:
            r["scale_tier"] = "small"
        elif c <= p66:
            r["scale_tier"] = "medium"
        else:
            r["scale_tier"] = "large"

    print(f"\n상권 규모 분위 기준: 33백분위={p33}건, 66백분위={p66}건")
    return rows


def reclassify_all(raw_rows: list) -> list:
    for row in raw_rows:
        row["trade_area_usage_type"] = classify_usage_type(row["TRDAR_CD_NM"])
        row["is_transit_adjacent"] = any(kw in row["TRDAR_CD_NM"] for kw in TRANSIT_KEYWORDS)
    raw_rows = assign_scale_tier(raw_rows)
    return raw_rows


# ─────────────────────────────────────────────
# 4) 2축(용도 x 규모) 세그먼트 통계 - 중앙값 기반
# ─────────────────────────────────────────────
MIN_SAMPLE_SIZE = 5  # 이보다 표본이 적으면 상위 카테고리로 fallback


def compute_segment_stats_v2(classified_rows: list) -> dict:
    groups = defaultdict(list)
    for row in classified_rows:
        key = f"{row['trade_area_usage_type']}__{row['scale_tier']}"
        groups[key].append(row)

    # fallback용: 용도별 전체(규모 무시) 통계도 같이 계산
    usage_only_groups = defaultdict(list)
    for row in classified_rows:
        usage_only_groups[row["trade_area_usage_type"]].append(row)

    def calc_stats(rows):
        amounts = [r["THSMON_SELNG_AMT"] for r in rows]
        counts = [r["THSMON_SELNG_CO"] for r in rows]
        return {
            "sample_size": len(rows),
            "median_monthly_sales_amt": round(statistics.median(amounts)),
            "p25_monthly_sales_amt": round(statistics.quantiles(amounts, n=4)[0]) if len(amounts) >= 4 else None,
            "p75_monthly_sales_amt": round(statistics.quantiles(amounts, n=4)[2]) if len(amounts) >= 4 else None,
            "median_monthly_sales_count": round(statistics.median(counts)),
        }

    segment_stats = {}
    for key, rows in groups.items():
        usage_type, scale_tier = key.split("__")
        if len(rows) >= MIN_SAMPLE_SIZE:
            stats = calc_stats(rows)
            stats["fallback_used"] = False
        else:
            # 표본 부족 -> 용도 전체(규모 무시) 통계로 대체
            fallback_rows = usage_only_groups[usage_type]
            stats = calc_stats(fallback_rows)
            stats["fallback_used"] = True
            stats["fallback_reason"] = f"세그먼트 표본 {len(rows)}개 < 최소기준 {MIN_SAMPLE_SIZE}개"

        segment_stats[key] = stats

    return segment_stats


def print_segment_comparison_v2(stats: dict):
    print("\n" + "=" * 80)
    print("세그먼트별(용도 x 규모) 카페 매출 중앙값 비교")
    print("=" * 80)

    for key in sorted(stats.keys()):
        s = stats[key]
        usage_type, scale_tier = key.split("__")
        fallback_note = " [fallback: 표본부족으로 용도 전체값 사용]" if s.get("fallback_used") else ""
        print(f"\n[{usage_type} / {scale_tier}] (표본 {s['sample_size']}개){fallback_note}")
        print(f"  매출 중앙값: {s['median_monthly_sales_amt']:,}원")
        if s.get("p25_monthly_sales_amt") is not None:
            print(f"  IQR(25~75%): {s['p25_monthly_sales_amt']:,}원 ~ {s['p75_monthly_sales_amt']:,}원")
        print(f"  매출건수 중앙값: {s['median_monthly_sales_count']:,}건")

    print("\n" + "-" * 80)
    print("같은 규모(scale_tier) 안에서 용도별 격차를 비교해보세요.")
    print("예: large 규모 안에서 university vs office 중앙값 차이가 뚜렷하면,")
    print("    이제야 '용도' 자체가 매출에 미치는 영향을 공정하게 비교한 것입니다.")
    print("=" * 80)


# ─────────────────────────────────────────────
# 실행
# ─────────────────────────────────────────────
if __name__ == "__main__":
    if not SEOUL_API_KEY:
        raise SystemExit(".env 파일에 SEOUL_API_KEY가 없습니다.")

    os.makedirs("./raw_data", exist_ok=True)

    print("=" * 80)
    print(f"데이터 수집 시작: {len(QUARTERS)}개 분기 x 최대 {MAX_PAGES_PER_QUARTER}페이지")
    print("=" * 80)

    all_raw_rows = fetch_all_quarters()
    print(f"\n총 수집된 카페 데이터: {len(all_raw_rows)}건")

    with open(RAW_OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_raw_rows, f, ensure_ascii=False, indent=2)
    print(f"원본 데이터를 {RAW_OUT_PATH} 에 저장했습니다.")

    print("\n분류 및 세그먼트 계산 중...")
    classified = reclassify_all(all_raw_rows)

    stats = compute_segment_stats_v2(classified)
    print_segment_comparison_v2(stats)

    with open(SEGMENT_OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"\n최종 세그먼트 벤치마크 테이블을 {SEGMENT_OUT_PATH} 에 저장했습니다.")
    print("이제 이 파일이 예측 엔진(predict_metrics)의 실제 입력 재료가 됩니다.")