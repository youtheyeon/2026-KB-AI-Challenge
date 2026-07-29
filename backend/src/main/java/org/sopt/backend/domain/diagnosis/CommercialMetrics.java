// 진단 결과의 상권 비교 지표를 저장하는 값 객체
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
public class CommercialMetrics {

    @Column(name = "floating_population_growth_rate", precision = 7, scale = 3)
    private BigDecimal floatingPopulationGrowthRate;

    @Column(name = "sales_compared_to_peer_rate", precision = 7, scale = 3)
    private BigDecimal salesComparedToPeerRate;
}
