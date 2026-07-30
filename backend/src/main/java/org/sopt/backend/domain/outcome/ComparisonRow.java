// 예상값과 실제값을 비교한 한 개 지표 행을 저장하는 값 객체
package org.sopt.backend.domain.outcome;

import jakarta.persistence.Column;
import jakarta.persistence.Embeddable;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@Embeddable
@NoArgsConstructor(access = lombok.AccessLevel.PROTECTED)
public class ComparisonRow {

    @Column(name = "metric_code", nullable = false, length = 150)
    private String metricCode;

    @Column(name = "target_condition", length = 255)
    private String targetCondition;

    @Column(name = "observed_value", length = 255)
    private String observedValue;

    @Column(name = "change_value", length = 255)
    private String changeValue;

    @Column(name = "result_status", nullable = false, length = 50)
    private String resultStatus;

    @Column(name = "external_factors", length = 1000)
    private String externalFactors;

    public ComparisonRow(
            String metricCode,
            String targetCondition,
            String observedValue,
            String changeValue,
            String resultStatus,
            String externalFactors
    ) {
        this.metricCode = java.util.Objects.requireNonNull(metricCode);
        this.targetCondition = targetCondition;
        this.observedValue = observedValue;
        this.changeValue = changeValue;
        this.resultStatus = java.util.Objects.requireNonNull(resultStatus);
        this.externalFactors = externalFactors;
    }
}
