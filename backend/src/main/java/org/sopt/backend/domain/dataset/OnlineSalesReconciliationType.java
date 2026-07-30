// 온라인 매출이 POS 전체 매출에 포함되는지 구분하는 열거형
package org.sopt.backend.domain.dataset;

public enum OnlineSalesReconciliationType {
    INCLUDED_IN_POS_TOTAL,
    SEPARATE_FROM_POS_TOTAL
}
