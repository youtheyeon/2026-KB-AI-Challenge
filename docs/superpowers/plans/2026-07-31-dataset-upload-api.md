# 사업 데이터 업로드 및 상태 조회 API 구현 계획

## 목표

현재 데모 세션이 소유한 사업자에 매출·비용·온라인 매출 xlsx를 업로드하고, 자동 컬럼 매핑과 정규화 결과를 저장한 뒤 데이터셋 처리 상태를 조회할 수 있게 한다.

## 범위

- `POST /api/businesses/{businessId}/datasets`
- `GET /api/datasets/{datasetId}`
- 매출·비용 필수, 온라인 매출 선택 multipart 계약
- xlsx 헤더 탐지와 알려진 한글·영문 헤더 자동 매핑
- 파일별 원본 파일명, 감지 형식, 매핑, 누락 컬럼, 신뢰도 저장
- 기존 정규화 매출·비용·온라인 매출 모델에 행 저장
- 세션 소유권이 다른 리소스의 `404` 처리
- `uploaded`, `parsing`, `normalizing`, `ready`, `needs_reupload`, `failed` 상태 사용

## 제외 범위

- `PATCH /api/datasets/{datasetId}/mapping`
- 원본 파일 영구 보관
- 백그라운드 작업 큐
- 외부 공공데이터 공급자 연동
- CSV 및 xls 지원

## 구현 순서

1. `python-multipart`, `openpyxl` 의존성을 추가한다.
2. multipart 계약, 필수 파일, 확장자, 세션 격리, 상태 조회 테스트를 먼저 작성하고 실패를 확인한다.
3. 파일별 지원 헤더와 필수 표준 컬럼을 상수로 정의한다.
4. xlsx에서 헤더 행을 찾고 표준 컬럼 매핑, 누락 컬럼, 신뢰도를 계산한다.
5. 기존 `DatasetFile.file_metadata`에 분석 결과를 저장한다.
6. 유효한 행을 기존 정규화 모델로 변환해 저장한다.
7. 업로드와 상태 조회 라우터를 애플리케이션에 등록한다.
8. 실제 PostgreSQL 성공과 롤백 경로를 통합 테스트로 검증한다.
9. 전체 pytest, Ruff, OpenAPI 계약을 확인한다.

## API 계약

### 업로드

- multipart 파트는 `salesFile`, `expenseFile`, `onlineSalesFile`을 사용한다.
- 성공적인 접수는 `202 Accepted`와 `datasetId`, `status: uploaded`를 반환한다.
- `.xlsx` 이외 파일은 `400 Bad Request`로 거절한다.
- 쿠키가 없거나 사업자가 현재 데모 세션 소유가 아니면 `404 Not Found`를 반환한다.

### 상태 조회

- `datasetId`, `businessId`, `status`, `files`를 반환한다.
- 파일 항목은 `fileType`, `originalFilename`, `detectedFormat`, `columnMapping`, `missingColumns`, `mappingConfidence`, `rowCount`를 포함한다.
- 파일 매핑에 필수 컬럼이 빠지면 데이터셋은 `needs_reupload`가 된다.
- xlsx 파싱 또는 행 정규화가 실패하면 데이터셋은 `failed`가 된다.

## 완료 조건

- 온라인 매출 파일 없이도 매출·비용 파일만으로 `ready` 상태가 된다.
- 세 파일이 모두 유효하면 각 정규화 테이블에 행이 저장된다.
- 다른 데모 세션의 사업자와 데이터셋은 `404`로 숨긴다.
- 원본 파일 바이트나 저장 경로를 DB에 남기지 않는다.
- 전체 pytest와 Ruff 검사, OpenAPI 계약 확인이 통과한다.
