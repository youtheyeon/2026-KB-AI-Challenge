# Domain Entities Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** API 명세의 사업 등록부터 결과 비교까지 필요한 JPA 도메인 모델과 초기 데이터베이스 스키마를 구현한다.

**Architecture:** 기능별 도메인 패키지에 외부 식별 엔티티와 부모 종속 하위 모델을 배치한다. 고정 구조는 Embeddable, 단순 반복 구조는 ElementCollection으로 저장하고 운영 스키마는 Flyway가 관리한다.

**Tech Stack:** Java 21, Spring Boot 4.1, Spring Data JPA, Hibernate, MySQL, Flyway, H2, JUnit 5.

## Global Constraints

- 모든 새 Java 소스 파일 첫 줄에 파일 역할을 설명하는 한국어 주석을 작성한다.
- 공개 setter와 Lombok `@Data`를 엔티티에 사용하지 않는다.
- API, 서비스, Repository, 인증과 실제 파일 저장은 추가하지 않는다.
- 명세에 없는 Enum 값이나 상태값을 추가하지 않는다.

---

### Task 1: 사업 정보와 진단 모델

- [ ] 모델 사용 방식을 보여주는 실패 테스트를 작성하고 실패 원인을 확인한다.
- [ ] 공통 시간 모델, 사용자, 사업체, 데이터셋, 파일, 매핑, 진단 모델을 최소 구현한다.
- [ ] 소유 하위 모델의 cascade와 값 객체 매핑 테스트를 통과시킨다.
- [ ] 변경 사항을 의미 단위로 커밋한다.

### Task 2: 시뮬레이션과 결과 모델

- [ ] 시뮬레이션부터 결과 비교까지 전체 그래프의 실패 테스트를 작성하고 실패 원인을 확인한다.
- [ ] 시뮬레이션, 배분안, 선택, 집행, 결과 데이터와 결과 모델을 최소 구현한다.
- [ ] 시뮬레이션별 단일 자원과 배분안 코드 제약 테스트를 통과시킨다.
- [ ] 변경 사항을 의미 단위로 커밋한다.

### Task 3: 스키마와 통합 검증

- [ ] Flyway 및 H2 테스트 의존성과 테스트 프로필을 추가한다.
- [ ] JPA 모델과 일치하는 `V1__create_domain_schema.sql`을 추가한다.
- [ ] Flyway 마이그레이션 후 Hibernate validate와 전체 그래프 저장 테스트를 통과시킨다.
- [ ] `./gradlew test`, `./gradlew bootJar`, `git diff --check`를 실행한다.
- [ ] 스키마와 테스트 변경 사항을 의미 단위로 커밋한다.
