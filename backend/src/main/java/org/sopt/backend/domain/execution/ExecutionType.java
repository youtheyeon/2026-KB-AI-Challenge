// 선택안과 구분해 실제 또는 Mock 집행 방식을 정의하는 열거형
package org.sopt.backend.domain.execution;

public enum ExecutionType {
    EXACT_SELECTED,
    MODIFIED,
    MIXED,
    CUSTOM,
    MOCK
}
