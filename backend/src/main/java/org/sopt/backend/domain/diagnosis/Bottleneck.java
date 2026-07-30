// 진단과 결과 비교에서 발견한 병목 내용을 저장하는 값 객체
package org.sopt.backend.domain.diagnosis;

import jakarta.persistence.Column;
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
import jakarta.persistence.Table;
import java.util.HashSet;
import java.util.Objects;
import java.util.Set;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.sopt.backend.domain.simulation.AllocationCategory;
import org.sopt.backend.domain.source.DataSourceType;

@Getter
@Entity
@Table(name = "bottlenecks")
@NoArgsConstructor(access = lombok.AccessLevel.PROTECTED)
public class Bottleneck {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "bottleneck_type", nullable = false, length = 100)
    private String bottleneckType;

    @Column(nullable = false, length = 1000)
    private String detail;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private BottleneckSeverity severity;

    @Enumerated(EnumType.STRING)
    @Column(name = "evidence_source_type", nullable = false, length = 50)
    private DataSourceType evidenceSourceType;

    @Column(name = "evidence_description", nullable = false, length = 1000)
    private String evidenceDescription;

    @ElementCollection(fetch = FetchType.LAZY)
    @CollectionTable(
            name = "bottleneck_related_categories",
            joinColumns = @JoinColumn(name = "bottleneck_id")
    )
    @Enumerated(EnumType.STRING)
    @Column(name = "allocation_category", nullable = false, length = 50)
    private Set<AllocationCategory> relatedCategories = new HashSet<>();

    private Bottleneck(
            String bottleneckType,
            String detail,
            BottleneckSeverity severity,
            DataSourceType evidenceSourceType,
            String evidenceDescription,
            Set<AllocationCategory> relatedCategories
    ) {
        this.bottleneckType = Objects.requireNonNull(bottleneckType);
        this.detail = Objects.requireNonNull(detail);
        this.severity = Objects.requireNonNull(severity);
        this.evidenceSourceType = Objects.requireNonNull(evidenceSourceType);
        this.evidenceDescription = Objects.requireNonNull(evidenceDescription);
        this.relatedCategories.addAll(Objects.requireNonNull(relatedCategories));
    }

    public Bottleneck(
            String code,
            String title,
            String priority,
            String confidence,
            String evidence,
            String description
    ) {
        this(
                code == null ? "UNSPECIFIED" : code,
                description == null ? title : description,
                BottleneckSeverity.CLEAR,
                DataSourceType.DOMAIN_ASSUMPTION,
                evidence == null ? "근거 미지정" : evidence,
                Set.of()
        );
    }

    public static Bottleneck create(
            String bottleneckType,
            String detail,
            BottleneckSeverity severity,
            DataSourceType evidenceSourceType,
            String evidenceDescription,
            Set<AllocationCategory> relatedCategories
    ) {
        return new Bottleneck(
                bottleneckType,
                detail,
                severity,
                evidenceSourceType,
                evidenceDescription,
                relatedCategories
        );
    }

    public String getTitle() {
        return detail;
    }
}
