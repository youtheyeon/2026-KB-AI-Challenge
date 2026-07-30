// 결과 비교에 사용할 집행 후 사업 데이터를 저장하는 엔티티
package org.sopt.backend.domain.outcome;

import jakarta.persistence.Column;
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
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import java.time.LocalDate;
import java.util.Objects;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.sopt.backend.domain.common.BaseTimeEntity;
import org.sopt.backend.domain.business.BusinessSnapshot;
import org.sopt.backend.domain.dataset.Dataset;
import org.sopt.backend.domain.simulation.Simulation;
import org.sopt.backend.domain.source.DataSourceType;

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
    @Column(name = "source_type", nullable = false, length = 50)
    private DataSourceType dataSourceType;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "dataset_id")
    private Dataset dataset;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "observed_business_snapshot_id", nullable = false)
    private BusinessSnapshot observedBusinessSnapshot;

    @Column(name = "observed_at", nullable = false)
    private LocalDate observedAt;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private OutcomeDataStatus status;

    private OutcomeData(
            Simulation simulation,
            Dataset dataset,
            BusinessSnapshot observedBusinessSnapshot,
            DataSourceType dataSourceType,
            LocalDate observedAt,
            OutcomeDataStatus status
    ) {
        this.simulation = Objects.requireNonNull(simulation);
        this.dataset = dataset;
        this.observedBusinessSnapshot = Objects.requireNonNull(observedBusinessSnapshot);
        this.dataSourceType = Objects.requireNonNull(dataSourceType);
        this.observedAt = Objects.requireNonNull(observedAt);
        this.status = Objects.requireNonNull(status);
        if (observedBusinessSnapshot.getBusiness() != simulation.getBusiness()
                || (dataset != null && dataset.getBusiness() != simulation.getBusiness())
                || (dataset != null
                && observedBusinessSnapshot.getDataset() != dataset)) {
            throw new IllegalArgumentException(
                    "관측 데이터는 시뮬레이션과 같은 사업체와 데이터셋에 속해야 합니다."
            );
        }
    }

    public static OutcomeData create(
            Simulation simulation,
            Dataset dataset,
            BusinessSnapshot observedBusinessSnapshot,
            DataSourceType dataSourceType,
            LocalDate observedAt,
            OutcomeDataStatus status
    ) {
        return new OutcomeData(
                simulation,
                dataset,
                observedBusinessSnapshot,
                dataSourceType,
                observedAt,
                status
        );
    }
}
