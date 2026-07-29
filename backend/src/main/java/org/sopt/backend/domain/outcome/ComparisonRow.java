// 예상값과 실제값을 비교한 한 개 지표 행을 저장하는 값 객체
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
public class ComparisonRow {

    @Column(name = "metric_name", nullable = false, length = 150)
    private String metricName;

    @Column(name = "scb_area", length = 150)
    private String scbArea;

    @Column(name = "predicted_value", length = 100)
    private String predictedValue;

    @Column(name = "actual_value", length = 100)
    private String actualValue;

    @Column(name = "external_factor", length = 1000)
    private String externalFactor;

    @Column(name = "comparison_status", length = 50)
    private String status;
}
