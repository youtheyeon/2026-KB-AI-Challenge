"""
2단계 스크립트: 
  1) 소상공인시장진흥공단 API에서 '카페/커피전문점'의 정확한 업종코드를 자동으로 찾아서 사용
  2) 서울시 상권분석서비스 데이터의 상권명(TRDAR_CD_NM)을 보고
     오피스/주거/대학가/관광지/기타 로 자동 분류하는 규칙 적용

실행 전 준비물은 이전 스크립트(fetch_benchmark_data.py)와 동일합니다.
같은 폴더의 .env를 그대로 사용합니다.
"""

import os
import re
import json
import requests
from dotenv import load_dotenv

load_dotenv()

SBIZ_SERVICE_KEY = os.getenv("SBIZ_SERVICE_KEY")
SEOUL_API_KEY = os.getenv("SEOUL_API_KEY")


# ─────────────────────────────────────────────
# 1) 소상공인시장진흥공단: 카페/커피전문점 업종코드 자동 조회
# ─────────────────────────────────────────────
def find_cafe_upjong_codes():
    """
    대분류(I2: 음식) -> 중분류 -> 소분류를 순서대로 훑어서
    이름에 '카페' 또는 '커피'가 들어간 소분류 코드를 전부 찾아 반환한다.
    """
    base_url = "https://apis.data.go.kr/B553077/api/open/sdsc2"

    # 1) 대분류 목록에서 '음식'(주로 I 계열) 코드를 확인
    large_resp = requests.get(
        f"{base_url}/largeUpjongList",
        params={"serviceKey": SBIZ_SERVICE_KEY, "type": "json"},
        timeout=10,
    )
    large_resp.raise_for_status()
    large_items = large_resp.json().get("body", {}).get("items", [])

    food_large = [i for i in large_items if "음식" in i.get("indsLclsNm", "")]
    print(f"[대분류] '음식' 관련: {[i.get('indsLclsNm') for i in food_large]}")

    cafe_codes = []

    for large in food_large:
        lcls_cd = large["indsLclsCd"]

        # 2) 중분류 조회
        mid_resp = requests.get(
            f"{base_url}/middleUpjongList",
            params={"serviceKey": SBIZ_SERVICE_KEY, "indsLclsCd": lcls_cd, "type": "json"},
            timeout=10,
        )
        mid_resp.raise_for_status()
        mid_items = mid_resp.json().get("body", {}).get("items", [])

        for mid in mid_items:
            mcls_cd = mid["indsMclsCd"]
            mcls_nm = mid["indsMclsNm"]

            # 3) 소분류 조회
            small_resp = requests.get(
                f"{base_url}/smallUpjongList",
                params={
                    "serviceKey": SBIZ_SERVICE_KEY,
                    "indsLclsCd": lcls_cd,
                    "indsMclsCd": mcls_cd,
                    "type": "json",
                },
                timeout=10,
            )
            small_resp.raise_for_status()
            small_items = small_resp.json().get("body", {}).get("items", [])

            for small in small_items:
                name = small.get("indsSclsNm", "")
                if "카페" in name or "커피" in name:
                    cafe_codes.append(
                        {
                            "indsLclsCd": lcls_cd,
                            "indsMclsCd": mcls_cd,
                            "indsMclsNm": mcls_nm,
                            "indsSclsCd": small["indsSclsCd"],
                            "indsSclsNm": name,
                        }
                    )

    print(f"\n찾은 카페/커피 소분류 코드: {len(cafe_codes)}건")
    for c in cafe_codes:
        print(f"  - {c['indsSclsCd']} : {c['indsSclsNm']} (중분류: {c['indsMclsNm']})")

    return cafe_codes


def fetch_stores_by_upjong(small_cls_cd: str, signgu_cd: str = "11680", num_of_rows: int = 50):
    """찾은 소분류 코드로 실제 카페 업소 목록을 조회한다."""
    base_url = "https://apis.data.go.kr/B553077/api/open/sdsc2"
    resp = requests.get(
        f"{base_url}/storeListInUpjong",
        params={
            "serviceKey": SBIZ_SERVICE_KEY,
            "divId": "indsSclsCd",
            "key": small_cls_cd,
            "signguCd": signgu_cd,
            "numOfRows": num_of_rows,
            "pageNo": 1,
            "type": "json",
        },
        timeout=10,
    )
    resp.raise_for_status()
    items = resp.json().get("body", {}).get("items", [])
    print(f"\n[강남구 기준 카페 업소] {len(items)}건 조회됨")
    for item in items[:5]:
        print(f"  - {item.get('bizesNm')} | {item.get('rdnmAdr')}")
    return items


# ─────────────────────────────────────────────
# 2) 상권 유형 분류 규칙 (오피스 / 주거 / 대학가 / 관광지 / 기타)
# ─────────────────────────────────────────────
# 키워드 기반 규칙. TRDAR_CD_NM(상권명)에 특정 단어가 있으면 해당 유형으로 분류.
# 우선순위: 위에서부터 먼저 매칭되는 규칙이 적용됨.
TRADE_AREA_RULES = [
    ("university", ["대학교", "대학", "캠퍼스", "고등학교", "중학교", "초등학교"]),
    ("office", ["오피스", "테헤란", "센터", "빌딩", "사무소", "본사", "공사", "청사", "세무서", "구청"]),
    ("residential", ["아파트", "주민센터", "동주민센터", "빌라", "래미안", "자이", "힐사이드"]),
    ("tourist", ["역사", "고궁", "궁", "미술관", "박물관", "케이블카", "관광", "터널", "산책로", "카페거리"]),
    ("transit", ["역 ", "역사문화공원", "터미널"]),  # 지하철역 출구 등은 별도 태그
]


def classify_trade_area(trdar_cd_nm: str, trdar_se_cd: str) -> dict:
    """
    상권명과 서울시 자체 상권구분코드(TRDAR_SE_CD)를 함께 활용해
    우리 시나리오의 상권 유형으로 분류한다.

    TRDAR_SE_CD 자체도 유용한 신호임:
      A: 골목상권, D: 발달상권, R: 전통시장, U: 관광특구
    이건 '상권 활력도/규모' 축이고,
    아래 키워드 매칭은 '용도(오피스/주거/대학가 등)' 축이라 서로 보완적으로 사용.
    """
    matched_type = "other"
    for category, keywords in TRADE_AREA_RULES:
        if any(kw in trdar_cd_nm for kw in keywords):
            matched_type = category
            break

    return {
        "trade_area_name": trdar_cd_nm,
        "trade_area_vitality": trdar_se_cd,  # A/D/R/U — 서울시 자체 분류
        "trade_area_usage_type": matched_type,  # 우리가 정의한 용도 분류
    }


def classify_all_cafe_sales(cafe_sales_rows: list) -> list:
    """서울시 카페 매출 데이터 전체에 상권 유형 태그를 붙인다."""
    classified = []
    for row in cafe_sales_rows:
        tag = classify_trade_area(row["TRDAR_CD_NM"], row["TRDAR_SE_CD"])
        row_with_tag = {**row, **tag}
        classified.append(row_with_tag)
    return classified


# ─────────────────────────────────────────────
# 실행
# ─────────────────────────────────────────────
if __name__ == "__main__":
    if not SBIZ_SERVICE_KEY or not SEOUL_API_KEY:
        raise SystemExit("인증키가 없습니다. .env 파일을 확인하세요.")

    print("=" * 60)
    print("STEP 1: 카페/커피전문점 업종코드 자동 탐색")
    print("=" * 60)
    cafe_codes = find_cafe_upjong_codes()

    if cafe_codes:
        first_code = cafe_codes[0]["indsSclsCd"]
        fetch_stores_by_upjong(first_code)

    print("\n" + "=" * 60)
    print("STEP 2: 상권 유형 분류 테스트 (이전 단계에서 받은 서울시 데이터 활용)")
    print("=" * 60)
    # 이전에 저장해둔 raw_data/seoul_cafe_sales.json이 있다면 그걸 불러와서 분류
    seoul_data_path = "./raw_data/seoul_cafe_sales.json"
    if os.path.exists(seoul_data_path):
        with open(seoul_data_path, "r", encoding="utf-8") as f:
            cafe_sales_rows = json.load(f)

        classified = classify_all_cafe_sales(cafe_sales_rows)

        # 유형별 개수 확인
        from collections import Counter
        type_counts = Counter(row["trade_area_usage_type"] for row in classified)
        print("\n상권 유형별 분류 결과:")
        for t, count in type_counts.items():
            print(f"  {t}: {count}건")

        print("\n샘플 5건:")
        for row in classified[:5]:
            print(
                f"  - {row['trade_area_name']} → "
                f"용도: {row['trade_area_usage_type']}, "
                f"활력도구분: {row['trade_area_vitality']}, "
                f"매출: {int(row['THSMON_SELNG_AMT']):,}원"
            )

        # 분류 결과 저장
        with open("./raw_data/seoul_cafe_sales_classified.json", "w", encoding="utf-8") as f:
            json.dump(classified, f, ensure_ascii=False, indent=2)
        print("\n분류 결과를 raw_data/seoul_cafe_sales_classified.json 에 저장했습니다.")
    else:
        print(f"\n{seoul_data_path} 파일이 없습니다. 먼저 fetch_benchmark_data.py를 실행해 데이터를 저장하세요.")