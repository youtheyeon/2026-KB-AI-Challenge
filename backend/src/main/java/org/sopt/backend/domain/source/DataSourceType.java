// 화면에 표시하는 데이터와 계산 결과의 출처를 구분하는 열거형
package org.sopt.backend.domain.source;

public enum DataSourceType {
    PUBLIC_DATA,
    SYNTHETIC_SALES,
    SYNTHETIC_EXPENSE,
    SYNTHETIC_ONLINE_SALES,
    USER_INPUT,
    BENCHMARK,
    DOMAIN_ASSUMPTION,
    CALCULATED,
    AI_GENERATED_TEXT
}
