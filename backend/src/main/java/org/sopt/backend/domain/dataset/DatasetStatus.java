// 데이터셋 업로드와 파싱 및 정규화 진행 상태를 정의하는 열거형
package org.sopt.backend.domain.dataset;

public enum DatasetStatus {
    UPLOADED,
    PARSING,
    NORMALIZING,
    READY,
    NEEDS_REUPLOAD,
    FAILED
}
