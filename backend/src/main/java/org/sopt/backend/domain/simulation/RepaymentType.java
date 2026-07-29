// API 명세에서 허용하는 대출 상환 방식을 정의하는 열거형
package org.sopt.backend.domain.simulation;

public enum RepaymentType {
    EQUAL_PAYMENT,
    EQUAL_PRINCIPAL,
    BULLET
}
