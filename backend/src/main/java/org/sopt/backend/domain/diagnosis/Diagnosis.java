// 데이터셋을 분석한 사업 지표와 병목 결과를 저장하는 엔티티
package org.sopt.backend.domain.diagnosis;

import jakarta.persistence.CascadeType;
import jakarta.persistence.Column;
import jakarta.persistence.ElementCollection;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.OneToMany;
import jakarta.persistence.OrderColumn;
import jakarta.persistence.Table;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.sopt.backend.domain.business.Business;
import org.sopt.backend.domain.business.BusinessSnapshot;
import org.sopt.backend.domain.business.PublicDataSnapshot;
import org.sopt.backend.domain.common.BaseTimeEntity;
import org.sopt.backend.domain.dataset.Dataset;

@Getter
@Entity
@Table(name = "diagnoses")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Diagnosis extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "business_id", nullable = false)
    private Business business;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "dataset_id", nullable = false)
    private Dataset dataset;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "business_snapshot_id", nullable = false)
    private BusinessSnapshot businessSnapshot;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "public_data_snapshot_id", nullable = false)
    private PublicDataSnapshot publicDataSnapshot;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private DiagnosisStatus status;

    @ElementCollection(fetch = FetchType.LAZY)
    @jakarta.persistence.CollectionTable(
            name = "diagnosis_metrics",
            joinColumns = @JoinColumn(name = "diagnosis_id")
    )
    @OrderColumn(name = "metric_order")
    private List<DiagnosisMetric> metrics = new ArrayList<>();

    @OneToMany(cascade = CascadeType.ALL, orphanRemoval = true)
    @JoinColumn(name = "diagnosis_id", nullable = false)
    @OrderColumn(name = "bottleneck_order")
    private List<Bottleneck> bottlenecks = new ArrayList<>();

    @Column(name = "diagnosis_version", nullable = false, length = 100)
    private String diagnosisVersion;

    @Column(name = "benchmark_version", nullable = false, length = 100)
    private String benchmarkVersion;

    private Diagnosis(
            Business business,
            Dataset dataset,
            BusinessSnapshot businessSnapshot,
            PublicDataSnapshot publicDataSnapshot,
            String diagnosisVersion,
            String benchmarkVersion
    ) {
        this.business = Objects.requireNonNull(business);
        this.dataset = Objects.requireNonNull(dataset);
        this.businessSnapshot = Objects.requireNonNull(businessSnapshot);
        this.publicDataSnapshot = Objects.requireNonNull(publicDataSnapshot);
        if (dataset.getBusiness() != business
                || businessSnapshot.getBusiness() != business
                || businessSnapshot.getDataset() != dataset
                || publicDataSnapshot.getBusiness() != business) {
            throw new IllegalArgumentException(
                    "진단 입력 데이터는 모두 같은 사업체와 데이터셋에 속해야 합니다."
            );
        }
        this.diagnosisVersion = Objects.requireNonNull(diagnosisVersion);
        this.benchmarkVersion = Objects.requireNonNull(benchmarkVersion);
        this.status = DiagnosisStatus.RUNNING;
    }

    public static Diagnosis start(
            Business business,
            Dataset dataset,
            BusinessSnapshot businessSnapshot,
            PublicDataSnapshot publicDataSnapshot,
            String diagnosisVersion,
            String benchmarkVersion
    ) {
        return new Diagnosis(
                business,
                dataset,
                businessSnapshot,
                publicDataSnapshot,
                diagnosisVersion,
                benchmarkVersion
        );
    }

    public void complete(
            List<DiagnosisMetric> metrics,
            List<Bottleneck> bottlenecks
    ) {
        this.metrics.clear();
        this.metrics.addAll(Objects.requireNonNull(metrics));
        this.bottlenecks.clear();
        this.bottlenecks.addAll(Objects.requireNonNull(bottlenecks));
        this.status = DiagnosisStatus.COMPLETED;
    }

    public List<DiagnosisMetric> getMetrics() {
        return List.copyOf(metrics);
    }

    public List<Bottleneck> getBottlenecks() {
        return List.copyOf(bottlenecks);
    }
}
