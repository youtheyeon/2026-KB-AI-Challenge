"""
카페 벤치마크 데이터 수집 테스트 스크립트

목적: 두 개의 공공 API를 실제로 호출해서 응답이 정상적으로 오는지 확인하고,
      카페(커피-음료) 업종 데이터만 필터링해서 눈으로 확인해본다.

실행 전 준비:
    1. pip install requests python-dotenv
    2. .env.example을 .env로 복사하고 실제 인증키 채워넣기
    3. python fetch_benchmark_data.py 실행

주의: 이 스크립트는 이 환경(샌드박스)에서는 실행이 안 됩니다.
      네트워크 제한 때문에 정부 API 서버 접속이 막혀있어요.
      본인 컴퓨터(로컬)에서 실행하세요.
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

SBIZ_SERVICE_KEY = os.getenv("SBIZ_SERVICE_KEY")
SEOUL_API_KEY = os.getenv("SEOUL_API_KEY")

# 커피-음료 업종 코드 (서울시 상권분석서비스 응답 예시에서 확인됨)
CAFE_SVC_INDUTY_CD = "CS100010"


# ─────────────────────────────────────────────
# 1. 소상공인시장진흥공단 상가(상권)정보 API — 카페 위치/밀도 데이터
# ─────────────────────────────────────────────
def fetch_sbiz_store_list(signgu_cd: str = "11680", num_of_rows: int = 20):
    """
    특정 시군구(기본값: 서울 강남구 11680) 내 상가업소 목록을 조회한다.
    이후 업종명으로 카페만 필터링해서 사용한다.
    """
    url = "https://apis.data.go.kr/B553077/api/open/sdsc2/storeListInDong"
    params = {
        "serviceKey": SBIZ_SERVICE_KEY,
        "divId": "signguCd",
        "key": signgu_cd,
        "numOfRows": num_of_rows,
        "pageNo": 1,
        "type": "json",
    }

    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    total_count = data.get("body", {}).get("totalCount")
    items = data.get("body", {}).get("items", [])

    print(f"[소상공인시장진흥공단] 전체 업소 수: {total_count}")
    print(f"[소상공인시장진흥공단] 받아온 샘플 수: {len(items)}")

    # 업종명에 '카페' 또는 '커피'가 포함된 업소만 필터링해서 확인
    cafe_items = [
        item for item in items
        if "카페" in item.get("indsSclsNm", "") or "커피" in item.get("indsSclsNm", "")
    ]
    print(f"[소상공인시장진흥공단] 그 중 카페/커피 관련 업소: {len(cafe_items)}건")
    for item in cafe_items[:5]:
        print(f"  - {item.get('bizesNm')} | {item.get('indsSclsNm')} | {item.get('rdnmAdr')}")

    return items


# ─────────────────────────────────────────────
# 2. 서울시 상권분석서비스(추정매출-상권) API — 카페 매출 데이터
# ─────────────────────────────────────────────
def fetch_seoul_cafe_sales(start_index: int = 1, end_index: int = 100, yyqu_cd: str = None):
    """
    서울시 상권분석서비스 추정매출 데이터를 받아온 뒤,
    커피-음료(CS100010) 업종만 클라이언트 사이드에서 필터링한다.
    """
    base_url = f"http://openapi.seoul.go.kr:8088/{SEOUL_API_KEY}/json/VwsmTrdarSelngQq/{start_index}/{end_index}"
    if yyqu_cd:
        base_url += f"/{yyqu_cd}"

    resp = requests.get(base_url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    rows = data.get("VwsmTrdarSelngQq", {}).get("row", [])
    total_count = data.get("VwsmTrdarSelngQq", {}).get("list_total_count")

    print(f"\n[서울시 상권분석서비스] 전체 데이터 건수: {total_count}")
    print(f"[서울시 상권분석서비스] 받아온 샘플 수: {len(rows)}")

    cafe_rows = [row for row in rows if row.get("SVC_INDUTY_CD") == CAFE_SVC_INDUTY_CD]
    print(f"[서울시 상권분석서비스] 그 중 카페(커피-음료) 데이터: {len(cafe_rows)}건")

    for row in cafe_rows[:5]:
        print(
            f"  - {row.get('TRDAR_CD_NM')} ({row.get('TRDAR_SE_CD_NM')}) "
            f"| 분기: {row.get('STDR_YYQU_CD')} "
            f"| 매출액: {int(row.get('THSMON_SELNG_AMT', 0)):,}원 "
            f"| 매출건수: {row.get('THSMON_SELNG_CO')}건"
        )

    return cafe_rows


# ─────────────────────────────────────────────
# 3. 두 데이터를 합쳐서 저장 (다음 단계: 세그먼트 통계 계산의 재료)
# ─────────────────────────────────────────────
def save_raw_data(store_items, cafe_sales_rows, out_dir="./raw_data"):
    os.makedirs(out_dir, exist_ok=True)

    with open(os.path.join(out_dir, "sbiz_stores.json"), "w", encoding="utf-8") as f:
        json.dump(store_items, f, ensure_ascii=False, indent=2)

    with open(os.path.join(out_dir, "seoul_cafe_sales.json"), "w", encoding="utf-8") as f:
        json.dump(cafe_sales_rows, f, ensure_ascii=False, indent=2)

    print(f"\n원본 데이터를 {out_dir}/ 에 저장했습니다.")


if __name__ == "__main__":
    if not SBIZ_SERVICE_KEY or not SEOUL_API_KEY:
        raise SystemExit(
            "인증키가 없습니다. .env 파일에 SBIZ_SERVICE_KEY, SEOUL_API_KEY를 채워넣으세요."
        )

    print("=" * 60)
    print("1단계: 소상공인시장진흥공단 상가(상권)정보 API 호출 테스트")
    print("=" * 60)
    store_items = fetch_sbiz_store_list()

    print("\n" + "=" * 60)
    print("2단계: 서울시 상권분석서비스(추정매출-상권) API 호출 테스트")
    print("=" * 60)
    cafe_sales_rows = fetch_seoul_cafe_sales(start_index=1, end_index=1000, yyqu_cd="20241")

    save_raw_data(store_items, cafe_sales_rows)