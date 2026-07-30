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
