# Anonymous Demo Session Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 이메일 사용자를 제거하고 로그인 없는 시연 브라우저를 UUID 기반 `DemoSession`으로 구분한다.

**Architecture:** `DemoSession`이 익명 세션 수명과 UUID 식별자를 보존하고 `Business`가 필수 외래키로 세션에 속한다. 기존 `User`는 제거하며 쿠키 발급과 API 필터는 후속 작업으로 분리한다.

**Tech Stack:** Python 3.13, SQLAlchemy 2, Alembic, PostgreSQL 15+, pytest, Ruff, uv.

## Global Constraints

- 작업 브랜치는 `feat/16`이다.
- `checklist.md`와 `context-notes.md`는 만들지 않는다.
- 새 Python 소스 파일 첫 줄에는 역할을 설명하는 한국어 주석을 작성한다.
- `DemoSession.id`는 PostgreSQL UUID이며 나머지 도메인 기본키는 기존 BIGINT를 유지한다.
- Supabase Auth, RLS, 로그인과 쿠키 API는 이번 작업에서 제외한다.
- 구현은 실패 테스트를 먼저 확인하는 TDD 순서를 따른다.

---

### Task 1: User를 DemoSession으로 교체

**Files:**
- Create: `backend/app/domain/demo_session.py`
- Delete: `backend/app/domain/user.py`
- Modify: `backend/app/domain/enums.py`
- Modify: `backend/app/domain/business.py`
- Modify: `backend/app/domain/__init__.py`
- Modify: `backend/tests/domain/test_business_data.py`

**Interfaces:**
- Produces: `DemoSession(id: UUID, last_accessed_at: datetime, expires_at: datetime, status: DemoSessionStatus)`.
- Produces: `Business.demo_session_id: UUID`, `Business.demo_session: DemoSession`.

- [ ] **Step 1: 실패 테스트 작성**

```python
def test_demo_session_uses_uuid_and_owns_businesses() -> None:
    session = DemoSession(expires_at=datetime(2026, 8, 1, tzinfo=timezone.utc))
    business = Business(name="Y카페", region="서울", industry="카페")
    session.businesses.append(business)

    assert isinstance(DemoSession.__table__.c.id.type, UUID)
    assert business.demo_session is session
    assert not hasattr(Business, "user_id")
```

- [ ] **Step 2: RED 확인**

Run: `uv run pytest tests/domain/test_business_data.py -q`

Expected: `DemoSession` 모듈 부재 또는 기존 `Business.user_id` 존재로 실패한다.

- [ ] **Step 3: 최소 모델 구현**

```python
class DemoSession(TimestampMixin, Base):
    __tablename__ = "demo_sessions"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    last_accessed_at = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at = mapped_column(DateTime(timezone=True), nullable=False)
    status = mapped_column(string_enum(DemoSessionStatus, "demo_session_status", 20))
    businesses = relationship(back_populates="demo_session")
```

`Business.user_id`와 `Business.user`를 제거하고 필수 `demo_session_id` UUID 외래키 및 `demo_session` 관계로 교체한다. 패키지 공개 목록에서 `User`를 제거하고 `DemoSession`을 추가한다.

- [ ] **Step 4: GREEN 확인**

Run: `uv run pytest tests/domain/test_business_data.py -q`

Expected: 모든 사업 데이터 도메인 테스트가 통과한다.

- [ ] **Step 5: 커밋**

```bash
git add backend/app/domain backend/tests/domain/test_business_data.py
git commit -m "feat: 익명 데모 세션 엔티티 추가"
```

### Task 2: 후속 PostgreSQL 마이그레이션

**Files:**
- Create: `backend/alembic/versions/20260730_0002_replace_user_with_demo_session.py`
- Modify: `backend/tests/integration/test_domain_persistence.py`
- Modify: `backend/tests/integration/test_alembic_migration.py`

**Interfaces:**
- Consumes: Task 1의 `DemoSession`과 `Business.demo_session_id`.
- Produces: `demo_sessions` 테이블과 `businesses.demo_session_id` 외래키.

- [ ] **Step 1: 마이그레이션 실패 테스트 작성**

```python
run_alembic("upgrade head")
tables = set(inspect(engine).get_table_names())
assert "demo_sessions" in tables
assert "users" not in tables
assert "demo_session_id" in {
    column["name"] for column in inspect(engine).get_columns("businesses")
}
```

- [ ] **Step 2: RED 확인**

Run: `uv run pytest tests/integration/test_alembic_migration.py -q`

Expected: 기존 마이그레이션에 `users`만 존재해 실패한다.

- [ ] **Step 3: 후속 마이그레이션 구현**

`demo_sessions` 생성, `businesses.demo_session_id` 추가, 기존 사업장용 만료 세션 생성, UUID 외래키 적용, `user_id`와 `users` 제거 순서로 upgrade를 작성한다. downgrade는 `users`, 이메일 인덱스, nullable `user_id`를 복원한 후 데모 세션 구조를 제거한다.

- [ ] **Step 4: 전체 검증**

Run: `uv run pytest -q`

Run: `uv run alembic -c alembic.ini check`

Run: `uv run ruff check .`

Run: `uv run ruff format --check .`

Run: `git diff --check`

Expected: 테스트와 정적 검사가 모두 통과하고 Alembic 스키마 차이가 없다.

- [ ] **Step 5: 커밋**

```bash
git add backend/alembic/versions backend/tests/integration
git commit -m "feat: 데모 세션 마이그레이션 추가"
```
