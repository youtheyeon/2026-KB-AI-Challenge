// 현재 사업지표와 비교 기준 및 출처를 함께 저장하는 진단 값 객체
package org.sopt.backend.domain.diagnosis;

import jakarta.persistence.Column;
import jakarta.persistence.Embeddable;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import java.math.BigDecimal;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.sopt.backend.domain.source.DataSourceType;

@Getter
@Embeddable
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class DiagnosisMetric {

    @Column(name = "metric_code", nullable = false, length = 100)
    private String metricCode;

    @Column(name = "current_value", nullable = false, precision = 19, scale = 4)
    private BigDecimal currentValue;

    @Enumerated(EnumType.STRING)
    @Column(name = "current_source_type", nullable = false, length = 50)
    private DataSourceType currentSourceType;

    @Column(name = "comparison_value", nullable = false, precision = 19, scale = 4)
    private BigDecimal comparisonValue;

    @Enumerated(EnumType.STRING)
    @Column(name = "comparison_source_type", nullable = false, length = 50)
    private DataSourceType comparisonSourceType;

    @Column(name = "difference_value", nullable = false, precision = 19, scale = 4)
    private BigDecimal differenceValue;

    @Column(name = "metric_unit", nullable = false, length = 50)
    private String unit;

    @Column(name = "metric_benchmark_version", length = 100)
    private String benchmarkVersion;

    public DiagnosisMetric(
            String metricCode,
            BigDecimal currentValue,
            DataSourceType currentSourceType,
            BigDecimal comparisonValue,
            DataSourceType comparisonSourceType,
            BigDecimal differenceValue,
            String unit,
            String benchmarkVersion
    ) {
        this.metricCode = java.util.Objects.requireNonNull(metricCode);
        this.currentValue = java.util.Objects.requireNonNull(currentValue);
        this.currentSourceType = java.util.Objects.requireNonNull(currentSourceType);
        this.comparisonValue = java.util.Objects.requireNonNull(comparisonValue);
        this.comparisonSourceType = java.util.Objects.requireNonNull(
                comparisonSourceType
        );
        this.differenceValue = java.util.Objects.requireNonNull(differenceValue);
        this.unit = java.util.Objects.requireNonNull(unit);
        this.benchmarkVersion = benchmarkVersion;
    }
}
