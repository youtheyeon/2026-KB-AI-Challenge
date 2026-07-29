// 데이터셋 분석과 매핑 진행 상태를 정의하는 열거형
package org.sopt.backend.domain.dataset;

public enum DatasetStatus {
    ANALYZING,
    MAPPING_READY,
    MAPPING_CONFIRMED,
    FAILED
}
