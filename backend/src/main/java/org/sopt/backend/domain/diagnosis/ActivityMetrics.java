// 진단 결과의 사업 활동 지표를 저장하는 값 객체
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
public class ActivityMetrics {

    @Column(name = "monthly_order_count")
    private Integer monthlyOrderCount;

    @Column(name = "online_sales_ratio", precision = 7, scale = 3)
    private BigDecimal onlineSalesRatio;

    @Column(name = "diagnosed_employee_count")
    private Integer employeeCount;
}
