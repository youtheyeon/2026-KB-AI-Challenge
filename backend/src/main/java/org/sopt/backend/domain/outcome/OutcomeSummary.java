// 예측 대비 실제 결과의 핵심 상태를 저장하는 값 객체
package org.sopt.backend.domain.outcome;

import jakarta.persistence.Column;
import jakarta.persistence.Embeddable;
import lombok.AccessLevel;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@Embeddable
@AllArgsConstructor
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class OutcomeSummary {

    @Column(name = "sales_growth_status", length = 50)
    private String salesGrowthStatus;

    @Column(name = "online_ratio_status", length = 50)
    private String onlineRatioStatus;

    @Column(name = "cash_after_repayment_status", length = 50)
    private String cashAfterRepaymentStatus;
}
