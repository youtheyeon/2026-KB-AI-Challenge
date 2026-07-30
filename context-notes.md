# 이슈 1 컨텍스트 노트

## 2026-07-31

- 이슈 1만 `feat/28` 브랜치에서 구현하며 이슈 2는 후속 작업으로 남긴다.
- 현재 작업 트리의 `.gitignore` 수정과 `docs/project-proposal-plan.md`는 사용자 변경이므로 건드리지 않는다.
- 기존 `Business`는 필수 `demo_session_id` 외래키를 가지므로 사업자 등록 API가 데모 세션을 먼저 해석하거나 생성해야 한다.
- 쿠키가 없거나 세션이 만료되었으면 새 `DemoSession`을 생성하고, 유효한 쿠키가 있으면 기존 세션을 재사용한다.
- 외부 API 필드는 camelCase를 사용하고 SQLAlchemy 모델 필드는 기존 snake_case를 유지한다.
- 이메일 로그인, Supabase Auth, 데이터 업로드와 컬럼 매핑은 이번 범위에 포함하지 않는다.
- 새 동작은 실패 테스트를 먼저 작성하고 RED를 확인한 뒤 최소 구현한다.
- 시스템에 `uv` 실행 파일이 없지만 `backend/.venv`에 pytest와 Ruff가 준비되어 있다.
- 기준 검증은 `.venv/bin/pytest -q`에서 33개 통과, 3개 스킵이며 Ruff 검사도 통과했다.
- 데모 세션 쿠키 이름은 `demo_session_id`, 신규 세션 유효 기간은 24시간으로 정했다.
- `BACKEND_ENVIRONMENT=production`에서만 쿠키의 `Secure` 속성을 활성화한다.
- `employeeCount`와 `primarySalesChannels`는 각각 `0`과 빈 배열을 기본값으로 사용한다.
- 저장소 문자열·정수 한계를 요청 스키마에 반영하고 공백 정규화를 길이 검증 전에 수행한다.
- 미존재 UUID와 비활성 세션 분기를 API 테스트로 보호한다.
- 실제 PostgreSQL 성공·롤백 통합 테스트를 추가했지만 현재 `TEST_DATABASE_URL`이 없어 실행은 스킵됐다.
- 작업 단위 리뷰에서 `aa3688c..3a44bcb` 범위의 Critical과 Important 항목이 모두 해소됐다.
- 사용자의 요청에 따라 추가 서브 에이전트 검토 없이 최종 검증을 직접 수행했다.
- 최종 검증에서 `.venv/bin/pytest -q`는 51개 통과와 5개 스킵, Ruff 검사와 포맷 검사는 통과했다.
- OpenAPI에서 `POST /api/businesses`의 `201` 응답과 camelCase 요청 필드를 확인했다.

## 이슈 2 — 2026-07-31

- 이슈 #29만 `feat/29` 브랜치에서 구현하고 `PATCH /api/datasets/{datasetId}/mapping`은 제외한다.
- 작업 트리의 `.gitignore` 수정과 `docs/project-proposal-plan.md`는 사용자 변경이므로 건드리지 않는다.
- Notion 원본 페이지는 연결 권한에서 `NOT_FOUND`였으며 GitHub 이슈 #29의 계약을 기준으로 구현한다.
- 매출과 비용 xlsx는 필수이고 온라인 매출 xlsx는 선택으로 처리한다.
- 원본 파일은 영구 저장하지 않고 `DatasetFile.storage_path`를 비워 둔다.
- 자동 컬럼 매핑, 누락 컬럼, 신뢰도, 행 수는 기존 `DatasetFile.file_metadata` JSONB에 저장한다.
- 새 테이블이나 컬럼 없이 기존 `Dataset`, `DatasetFile`, 정규화 모델을 사용한다.
- 업로드 요청 안에서 파싱과 정규화를 수행하고 접수 응답은 `202`, 상태 조회는 최종 처리 상태를 반환한다.
- 매출은 영업일자와 순매출, 비용은 거래일자·비용항목·합계금액, 온라인 매출은 영업일자와 매출금액을 필수 매핑으로 본다.
- 누락 필수 컬럼은 `needs_reupload`, 손상된 xlsx나 행 변환 실패는 `failed`로 저장한다.
- 상권 파일 파트는 받지 않으며 외부 공공데이터 클라이언트가 없는 현재 범위에서는 사업자의 지역 정보를 훼손하지 않는다.
- `python-multipart 0.0.32`, `openpyxl 3.1.5`를 추가하고 `uv.lock`을 갱신했다.
- 지원 헤더가 일부 또는 전부 누락된 정상 xlsx는 `needs_reupload`, 압축 구조가 손상된 파일은 `failed`로 구분한다.
- 빠른 API 테스트에서 필수·선택 파일, 정규화, 메타데이터, 실패 상태, 세션 격리를 검증한다.
- PostgreSQL 통합 테스트는 JSONB 메타데이터와 세 정규화 테이블 저장, 파일 insert 실패 시 롤백을 검증하도록 작성했다.
- 현재 `TEST_DATABASE_URL`과 Docker 실행 파일이 없고 로컬 55432 포트 연결도 거부돼 PostgreSQL 테스트 7건은 스킵된다.
- 최종 전 검증에서 전체 테스트는 61개 통과와 7개 스킵이며 Ruff 검사와 multipart OpenAPI 계약 확인은 통과했다.
- 구현 변경은 `30657c4` 커밋으로 분리했다.

## 이슈 3 — 2026-07-31

- `POST /api/businesses/{businessId}/diagnoses`와 `GET /api/diagnoses/{diagnosisId}`를 구현한다.
- 실행 API는 FastAPI `BackgroundTasks`로 `202/RUNNING`을 반환하고 요청 세션과 분리된 DB 세션에서 `COMPLETED` 또는 `FAILED`로 전이한다.
- 진단 요청 중 공공 API를 호출하지 않고 `ai/raw_data/seoul_cafe_sales_full.json`의 최신 분기에서 만든 고정 벤치마크를 사용한다.
- 최신 분기는 `20242`, 표본은 326개 상권, 월매출 중앙값은 94,283,406원, 월주문 중앙값은 11,729건이다.
- 공공데이터 캐시에 유동인구가 없으므로 `floatingPopulationGrowthRate`는 추정하지 않고 `null`로 반환한다.
- 월별 지표는 데이터셋의 가장 최신 매출 연월을 기준으로 매출·비용·온라인 자료를 동일 기간에서 집계한다.
- 온라인 자료가 없으면 온라인 매출 비중은 `null`이고 온라인 관련 병목을 만들지 않는다.
- 기존 `BusinessSnapshot`, `PublicDataSnapshot`, `Diagnosis`, `DiagnosisMetric`, `Bottleneck`을 사용하며 스키마 마이그레이션은 추가하지 않는다.
- 요청 검증 실패는 진단 실행 경로에서만 `400`으로 변환하고 기존 API의 `422` 계약은 유지한다.
- 현재 `develop`의 `.gitignore` 수정과 `docs/project-proposal-plan.md`는 사용자 변경이므로 `/tmp/kb-ai-business-diagnosis-api` 격리 워크트리에서 작업한다.
- 구현 전 기준 검증은 전체 테스트 61개 통과·7개 스킵, Ruff 검사 통과다.
- 새 동작은 실패 테스트를 먼저 실행해 RED를 확인한 뒤 최소 구현한다.
- 순수 분석 서비스의 RED는 모듈 부재로 확인했고 구현 후 테스트 6개와 대상 Ruff 검사가 통과했다.
- 벤치마크는 최신 분기 326건의 단순 중앙값을 Python `statistics.median`으로 계산해 94,283,406원으로 고정했다.
- 최신 월 집계와 백그라운드 상태 전이의 RED를 확인했고 구현 후 서비스 테스트 총 10개와 대상 Ruff 검사가 통과했다.
- 백그라운드 작업은 요청 세션을 재사용하지 않으며 실패 시 계산 트랜잭션을 롤백하고 진단 상태만 `FAILED`로 갱신한다.
- 진단 라우터의 RED는 모듈 부재로 확인했고 구현 후 API 테스트 7개와 대상 Ruff 검사가 통과했다.
- 진단 요청의 400 오류 변환은 전용 `APIRoute`에만 적용해 기존 API의 FastAPI 422 계약은 유지한다.
- PostgreSQL 통합 테스트는 실제 스냅샷·지표·병목 영속화를 검증하며 `TEST_DATABASE_URL`이 없는 현재 환경에서는 1개가 안전하게 스킵됐다.
- 운영 Supabase 연결은 테스트에 사용하지 않았고 스키마나 데이터를 변경하지 않았다.
- `BackgroundTasks`는 프로세스 재시작 시 실행 중인 작업을 복구하지 못하므로 단일 EC2용 초기 구현으로 문서화했다.
- 단위·통합 테스트의 같은 파일명이 pytest 수집 충돌을 일으켜 통합 테스트를 `test_diagnosis_persistence.py`로 변경했고 대상 테스트 7개 통과·1개 스킵으로 회귀를 확인했다.
- 최종 검증은 전체 테스트 78개 통과·8개 스킵, Ruff 검사·포맷 검사·OpenAPI 진단 계약·`git diff --check` 통과다.
- 독립 코드 리뷰에서 파괴적 테스트 DB 오지정, 빈 매출의 동기 실패, 일부 정산 집계 왜곡, 만료 세션 재사용, 스냅샷·작업 동시성 문제가 병합 차단 항목으로 확인됐다.
- 통합 테스트는 `ALLOW_DESTRUCTIVE_TEST_DATABASE_RESET=1`과 `_test`로 끝나는 DB명을 모두 요구하며, 더미 `postgres` DB명으로 실행했을 때 연결 전에 차단되는 것을 확인했다.
- 빈 매출 데이터셋은 0원 입력 스냅샷과 `RUNNING` 진단을 먼저 저장하고 기존의 엄격한 분석 수집기가 백그라운드에서 `FAILED`로 전이시킨다.
- 정산액이 누락된 온라인 행이 하나라도 있으면 정산율 관련 입력을 `null`로 두어 모집단이 다른 비율을 계산하지 않는다.
- 진단 소유권은 쿠키 UUID뿐 아니라 세션의 `ACTIVE` 상태와 만료 시각까지 검증한다.
- POST는 데이터셋 행을, 백그라운드 작업은 진단 행을 잠그며 이미 종료된 진단은 재계산하거나 실패 상태로 덮어쓰지 않는다.
- 리뷰 수정 후 전체 테스트 89개 통과·9개 스킵, Ruff 검사·포맷 검사·OpenAPI 계약·`git diff --check`가 통과했다.
- 독립 재검토에서 남은 Critical·Important 항목과 새 병합 차단 항목이 없음을 확인했다.
