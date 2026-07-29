// 데이터셋을 분석한 사업 지표와 병목 결과를 저장하는 엔티티
package org.sopt.backend.domain.diagnosis;

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
import jakarta.persistence.ManyToOne;
import jakarta.persistence.OrderColumn;
import jakarta.persistence.Table;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.sopt.backend.domain.business.Business;
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

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private DiagnosisStatus status;

    @Embedded
    private FinancialMetrics financialMetrics;

    @Embedded
    private ActivityMetrics activityMetrics;

    @Embedded
    private CommercialMetrics commercialMetrics;

    @ElementCollection(fetch = FetchType.LAZY)
    @CollectionTable(
            name = "diagnosis_bottlenecks",
            joinColumns = @JoinColumn(name = "diagnosis_id")
    )
    @OrderColumn(name = "bottleneck_order")
    private List<Bottleneck> bottlenecks = new ArrayList<>();

    private Diagnosis(Business business, Dataset dataset) {
        this.business = Objects.requireNonNull(business);
        this.dataset = Objects.requireNonNull(dataset);
        this.status = DiagnosisStatus.RUNNING;
    }

    public static Diagnosis start(Business business, Dataset dataset) {
        return new Diagnosis(business, dataset);
    }

    public void complete(
            FinancialMetrics financialMetrics,
            ActivityMetrics activityMetrics,
            CommercialMetrics commercialMetrics,
            List<Bottleneck> bottlenecks
    ) {
        this.financialMetrics = Objects.requireNonNull(financialMetrics);
        this.activityMetrics = Objects.requireNonNull(activityMetrics);
        this.commercialMetrics = Objects.requireNonNull(commercialMetrics);
        this.bottlenecks.clear();
        this.bottlenecks.addAll(Objects.requireNonNull(bottlenecks));
        this.status = DiagnosisStatus.COMPLETED;
    }
}
