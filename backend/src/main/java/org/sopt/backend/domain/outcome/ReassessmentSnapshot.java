// 집행 후 최신 사업 상태와 해결·잔존·신규 병목을 저장하는 재평가 엔티티
package org.sopt.backend.domain.outcome;

import jakarta.persistence.CollectionTable;
import jakarta.persistence.Column;
import jakarta.persistence.ElementCollection;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.util.HashSet;
import java.util.Objects;
import java.util.Set;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.sopt.backend.domain.business.BusinessSnapshot;

@Getter
@Entity
@Table(name = "reassessment_snapshots")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class ReassessmentSnapshot {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "latest_business_snapshot_id", nullable = false)
    private BusinessSnapshot latestBusinessSnapshot;

    @ElementCollection(fetch = FetchType.LAZY)
    @CollectionTable(
            name = "reassessment_resolved_bottlenecks",
            joinColumns = @JoinColumn(name = "reassessment_snapshot_id")
    )
    @Column(name = "bottleneck_type", nullable = false, length = 100)
    private Set<String> resolvedBottleneckTypes = new HashSet<>();

    @ElementCollection(fetch = FetchType.LAZY)
    @CollectionTable(
            name = "reassessment_remaining_bottlenecks",
            joinColumns = @JoinColumn(name = "reassessment_snapshot_id")
    )
    @Column(name = "bottleneck_type", nullable = false, length = 100)
    private Set<String> remainingBottleneckTypes = new HashSet<>();

    @ElementCollection(fetch = FetchType.LAZY)
    @CollectionTable(
            name = "reassessment_new_bottlenecks",
            joinColumns = @JoinColumn(name = "reassessment_snapshot_id")
    )
    @Column(name = "bottleneck_type", nullable = false, length = 100)
    private Set<String> newBottleneckTypes = new HashSet<>();

    private ReassessmentSnapshot(
            BusinessSnapshot latestBusinessSnapshot,
            Set<String> resolvedBottleneckTypes,
            Set<String> remainingBottleneckTypes,
            Set<String> newBottleneckTypes
    ) {
        this.latestBusinessSnapshot = Objects.requireNonNull(latestBusinessSnapshot);
        this.resolvedBottleneckTypes.addAll(
                Objects.requireNonNull(resolvedBottleneckTypes)
        );
        this.remainingBottleneckTypes.addAll(
                Objects.requireNonNull(remainingBottleneckTypes)
        );
        this.newBottleneckTypes.addAll(Objects.requireNonNull(newBottleneckTypes));
    }

    public static ReassessmentSnapshot create(
            BusinessSnapshot latestBusinessSnapshot,
            Set<String> resolvedBottleneckTypes,
            Set<String> remainingBottleneckTypes,
            Set<String> newBottleneckTypes
    ) {
        return new ReassessmentSnapshot(
                latestBusinessSnapshot,
                resolvedBottleneckTypes,
                remainingBottleneckTypes,
                newBottleneckTypes
        );
    }
}
