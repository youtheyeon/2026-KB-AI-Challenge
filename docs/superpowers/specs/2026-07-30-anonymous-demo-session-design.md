# 익명 데모 세션 설계

## 목표

로그인 없이 즉시 사용하는 시연 환경에서 브라우저 세션별 사업 데이터가 섞이지 않도록 익명 세션 경계를 만든다.

## 확정 설계

- 이메일 기반 `User` 엔티티를 제거한다.
- `DemoSession`은 브라우저에 전달할 추측하기 어려운 UUID를 기본키로 사용한다.
- `Business.user_id`를 제거하고 필수 `demo_session_id` 외래키를 추가한다.
- 세션은 `ACTIVE`, `EXPIRED` 상태와 마지막 접근 시각, 만료 시각을 보존한다.
- 세션 만료는 접근 차단 기준이며 이번 엔티티 작업에서 데이터 자동 삭제는 수행하지 않는다.
- 쿠키는 후속 API 작업에서 `HttpOnly`, `SameSite=Lax`, 운영 환경 `Secure`로 발급한다.

## 데이터 관계

`DemoSession 1:N Business` 관계를 사용한다. 한 시연 세션에서 여러 사업장을 만들 수 있지만 다른 세션의 사업장은 UUID 쿠키 없이는 조회하지 않는다.

## 마이그레이션

후속 Alembic 마이그레이션에서 `demo_sessions`를 생성하고 기존 사업장마다 만료된 임시 세션을 만든다. 이후 `businesses.user_id`와 `users` 테이블을 제거한다. 롤백 시 `users` 구조와 nullable `user_id`를 복원하되 삭제된 이메일 데이터는 복원하지 않는다.

## 제외 범위

- 로그인과 회원가입.
- Supabase Auth와 RLS.
- 쿠키 발급 미들웨어와 API 조회 필터.
- 만료 세션 자동 정리 작업.

## 검증

- `User`와 이메일 컬럼이 메타데이터에서 제거되는지 확인한다.
- `DemoSession` UUID, 상태, 접근·만료 시각과 사업장 관계를 확인한다.
- PostgreSQL에서 전체 24개 테이블과 Alembic upgrade, downgrade, re-upgrade를 확인한다.
