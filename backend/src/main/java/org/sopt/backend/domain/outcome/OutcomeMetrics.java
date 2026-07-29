// 직접 입력한 집행 후 핵심 사업 지표를 저장하는 값 객체
package org.sopt.backend.domain.outcome;

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
public class OutcomeMetrics {

    @Column(name = "monthly_sales_amount")
    private Long monthlySalesAmount;

    @Column(name = "operating_profit_amount")
    private Long operatingProfitAmount;

    @Column(name = "online_order_ratio", precision = 7, scale = 3)
    private BigDecimal onlineOrderRatio;

    @Column(name = "cash_after_repayment_amount")
    private Long cashAfterRepaymentAmount;
}
