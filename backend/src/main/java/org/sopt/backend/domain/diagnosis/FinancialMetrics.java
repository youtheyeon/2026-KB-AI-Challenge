// 진단 결과의 재무 지표를 저장하는 값 객체
package org.sopt.backend.domain.diagnosis;

import jakarta.persistence.Column;
import jakarta.persistence.Embeddable;
import java.math.BigDecimal;
import lombok.AccessLevel;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@Embeddable
@AllArgsConstructor
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class FinancialMetrics {

    @Column(name = "monthly_sales_amount")
    private Long monthlySalesAmount;

    @Column(name = "operating_profit_rate", precision = 7, scale = 3)
    private BigDecimal operatingProfitRate;

    @Column(name = "material_cost_rate", precision = 7, scale = 3)
    private BigDecimal materialCostRate;

    @Column(name = "cash_surplus_amount")
    private Long cashSurplusAmount;
}
