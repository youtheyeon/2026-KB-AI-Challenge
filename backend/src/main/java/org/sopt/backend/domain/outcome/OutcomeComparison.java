// 선택안의 목표 조건과 집행 후 관측 결과를 비교해 저장하는 엔티티
package org.sopt.backend.domain.outcome;

import jakarta.persistence.CascadeType;
import jakarta.persistence.CollectionTable;
import jakarta.persistence.ElementCollection;
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
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.sopt.backend.domain.common.BaseTimeEntity;
import org.sopt.backend.domain.execution.Execution;
import org.sopt.backend.domain.simulation.Simulation;

@Getter
@Entity
@Table(
        name = "outcome_comparisons",
        uniqueConstraints = {
            @UniqueConstraint(
                    name = "uk_outcome_comparison_simulation",
                    columnNames = "simulation_id"
            ),
            @UniqueConstraint(
                    name = "uk_outcome_comparison_execution",
                    columnNames = "execution_id"
            ),
            @UniqueConstraint(
                    name = "uk_outcome_comparison_data",
                    columnNames = "outcome_data_id"
            )
        }
)
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class OutcomeComparison extends BaseTimeEntity {

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
    @jakarta.persistence.Column(nullable = false, length = 20)
    private OutcomeStatus status;

    @ElementCollection(fetch = FetchType.LAZY)
    @CollectionTable(
            name = "outcome_comparison_rows",
            joinColumns = @JoinColumn(name = "outcome_comparison_id")
    )
    @OrderColumn(name = "row_order")
    private List<ComparisonRow> comparisonRows = new ArrayList<>();

    @OneToOne(cascade = CascadeType.ALL, orphanRemoval = true, optional = false)
    @JoinColumn(name = "reassessment_snapshot_id", nullable = false, unique = true)
    private ReassessmentSnapshot reassessmentSnapshot;

    private OutcomeComparison(
            Simulation simulation,
            Execution execution,
            OutcomeData outcomeData,
            List<ComparisonRow> comparisonRows,
            ReassessmentSnapshot reassessmentSnapshot
    ) {
        if (execution.getSimulation() != simulation
                || outcomeData.getSimulation() != simulation) {
            throw new IllegalArgumentException(
                    "집행 내역과 관측 데이터는 같은 시뮬레이션에 속해야 합니다."
            );
        }
        this.simulation = Objects.requireNonNull(simulation);
        this.execution = Objects.requireNonNull(execution);
        this.outcomeData = Objects.requireNonNull(outcomeData);
        this.comparisonRows.addAll(Objects.requireNonNull(comparisonRows));
        this.reassessmentSnapshot = Objects.requireNonNull(reassessmentSnapshot);
        this.status = OutcomeStatus.COMPLETED;
    }

    public static OutcomeComparison complete(
            Simulation simulation,
            Execution execution,
            OutcomeData outcomeData,
            List<ComparisonRow> comparisonRows,
            ReassessmentSnapshot reassessmentSnapshot
    ) {
        return new OutcomeComparison(
                simulation,
                execution,
                outcomeData,
                comparisonRows,
                reassessmentSnapshot
        );
    }
}
