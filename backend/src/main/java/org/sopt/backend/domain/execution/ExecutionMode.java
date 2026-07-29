// API 명세에서 허용하는 실제 자금 집행 방식을 정의하는 열거형
package org.sopt.backend.domain.execution;

public enum ExecutionMode {
    SAME_AS_A,
    SAME_AS_B,
    SAME_AS_C,
    MIXED,
    CUSTOM
}
