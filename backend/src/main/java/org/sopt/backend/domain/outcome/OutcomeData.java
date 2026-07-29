// 결과 비교에 사용할 집행 후 사업 데이터를 저장하는 엔티티
package org.sopt.backend.domain.outcome;

import jakarta.persistence.Embedded;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.OneToOne;
import jakarta.persistence.Column;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import java.util.Objects;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.sopt.backend.domain.common.BaseTimeEntity;
import org.sopt.backend.domain.dataset.Dataset;
import org.sopt.backend.domain.simulation.Simulation;

@Getter
@Entity
@Table(
        name = "outcome_data",
        uniqueConstraints = @UniqueConstraint(
                name = "uk_outcome_data_simulation",
                columnNames = "simulation_id"
        )
)
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class OutcomeData extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @OneToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "simulation_id", nullable = false, unique = true)
    private Simulation simulation;

    @Enumerated(EnumType.STRING)
    @Column(name = "source_type", nullable = false, length = 20)
    private OutcomeSourceType sourceType;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "dataset_id")
    private Dataset dataset;

    @Embedded
    private OutcomeMetrics metrics;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private OutcomeDataStatus status;

    private OutcomeData(
            Simulation simulation,
            OutcomeSourceType sourceType,
            Dataset dataset,
            OutcomeMetrics metrics,
            OutcomeDataStatus status
    ) {
        this.simulation = Objects.requireNonNull(simulation);
        this.sourceType = Objects.requireNonNull(sourceType);
        this.dataset = dataset;
        this.metrics = metrics;
        this.status = Objects.requireNonNull(status);
    }

    public static OutcomeData create(
            Simulation simulation,
            OutcomeSourceType sourceType,
            Dataset dataset,
            OutcomeMetrics metrics,
            OutcomeDataStatus status
    ) {
        return new OutcomeData(simulation, sourceType, dataset, metrics, status);
    }
}
