// 집행 결과를 반영해 갱신한 사업 상태를 저장하는 값 객체
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
public class OutcomeReevaluation {

    @Column(name = "reevaluated_monthly_sales_amount")
    private Long monthlySalesAmount;

    @Column(name = "reevaluated_operating_profit_amount")
    private Long operatingProfitAmount;

    @Column(name = "reevaluated_cash_after_repayment_amount")
    private Long cashAfterRepaymentAmount;

    @Column(name = "reevaluated_online_order_ratio", precision = 7, scale = 3)
    private BigDecimal onlineOrderRatio;
}
