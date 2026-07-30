// 목표 조건 대비 관측 결과의 충족 상태를 정의하는 열거형
package org.sopt.backend.domain.outcome;

public enum ComparisonResultStatus {
    CONDITION_MET,
    PARTIALLY_MET,
    NOT_MET,
    NOT_COMPARABLE
}
