// 시뮬레이션의 예측과 실제 사업 성과를 비교한 결과를 저장하는 엔티티
package org.sopt.backend.domain.outcome;

import jakarta.persistence.CollectionTable;
import jakarta.persistence.Column;
import jakarta.persistence.ElementCollection;
import jakarta.persistence.Embedded;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.OneToOne;
import jakarta.persistence.OrderColumn;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.sopt.backend.domain.common.BaseTimeEntity;
import org.sopt.backend.domain.diagnosis.Bottleneck;
import org.sopt.backend.domain.execution.Execution;
import org.sopt.backend.domain.simulation.Simulation;

@Getter
@Entity
@Table(
        name = "outcomes",
        uniqueConstraints = {
            @UniqueConstraint(
                    name = "uk_outcome_simulation",
                    columnNames = "simulation_id"
            ),
            @UniqueConstraint(
                    name = "uk_outcome_execution",
                    columnNames = "execution_id"
            ),
            @UniqueConstraint(
                    name = "uk_outcome_data",
                    columnNames = "outcome_data_id"
            )
        }
)
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Outcome extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @OneToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "simulation_id", nullable = false, unique = true)
    private Simulation simulation;

    @OneToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "execution_id", nullable = false, unique = true)
    private Execution execution;

    @OneToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "outcome_data_id", nullable = false, unique = true)
    private OutcomeData outcomeData;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private OutcomeStatus status;

    @Embedded
    private OutcomeSummary summary;

    @ElementCollection(fetch = FetchType.LAZY)
    @CollectionTable(
            name = "outcome_monthly_sales_amounts",
            joinColumns = @JoinColumn(name = "outcome_id")
    )
    @OrderColumn(name = "metric_order")
    @Column(name = "monthly_sales_amount", nullable = false)
    private List<Long> monthlySalesAmounts = new ArrayList<>();

    @ElementCollection(fetch = FetchType.LAZY)
    @CollectionTable(
            name = "outcome_online_order_ratios",
            joinColumns = @JoinColumn(name = "outcome_id")
    )
    @OrderColumn(name = "metric_order")
    @Column(name = "online_order_ratio", nullable = false, precision = 7, scale = 3)
    private List<BigDecimal> onlineOrderRatios = new ArrayList<>();

    @ElementCollection(fetch = FetchType.LAZY)
    @CollectionTable(
            name = "outcome_comparison_rows",
            joinColumns = @JoinColumn(name = "outcome_id")
    )
    @OrderColumn(name = "row_order")
    private List<ComparisonRow> comparisonRows = new ArrayList<>();

    @Embedded
    private OutcomeReevaluation reevaluation;

    @ElementCollection(fetch = FetchType.LAZY)
    @CollectionTable(
            name = "outcome_new_bottlenecks",
            joinColumns = @JoinColumn(name = "outcome_id")
    )
    @OrderColumn(name = "bottleneck_order")
    private List<Bottleneck> newBottlenecks = new ArrayList<>();

    private Outcome(
            Simulation simulation,
            Execution execution,
            OutcomeData outcomeData,
            OutcomeSummary summary,
            OutcomeTrends trends,
            List<ComparisonRow> comparisonRows,
            OutcomeReevaluation reevaluation,
            List<Bottleneck> newBottlenecks
    ) {
        if (execution.getSimulation() != simulation
                || outcomeData.getSimulation() != simulation) {
            throw new IllegalArgumentException(
                    "집행 내역과 결과 데이터는 같은 시뮬레이션에 속해야 합니다."
            );
        }
        this.simulation = Objects.requireNonNull(simulation);
        this.execution = Objects.requireNonNull(execution);
        this.outcomeData = Objects.requireNonNull(outcomeData);
        this.status = OutcomeStatus.COMPLETED;
        this.summary = Objects.requireNonNull(summary);
        this.monthlySalesAmounts.addAll(trends.getMonthlySalesAmounts());
        this.onlineOrderRatios.addAll(trends.getOnlineOrderRatios());
        this.comparisonRows.addAll(Objects.requireNonNull(comparisonRows));
        this.reevaluation = Objects.requireNonNull(reevaluation);
        this.newBottlenecks.addAll(Objects.requireNonNull(newBottlenecks));
    }

    public static Outcome complete(
            Simulation simulation,
            Execution execution,
            OutcomeData outcomeData,
            OutcomeSummary summary,
            OutcomeTrends trends,
            List<ComparisonRow> comparisonRows,
            OutcomeReevaluation reevaluation,
            List<Bottleneck> newBottlenecks
    ) {
        return new Outcome(
                simulation,
                execution,
                outcomeData,
                summary,
                Objects.requireNonNull(trends),
                comparisonRows,
                reevaluation,
                newBottlenecks
        );
    }
}
