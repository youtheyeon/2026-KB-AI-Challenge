// 진단에 사용한 상권 공공데이터의 기준일과 버전을 이력으로 저장하는 엔티티
package org.sopt.backend.domain.business;

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
import jakarta.persistence.Table;
import java.time.LocalDate;
import java.util.Objects;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.sopt.backend.domain.common.BaseTimeEntity;
import org.sopt.backend.domain.source.DataSourceType;

@Getter
@Entity
@Table(name = "public_data_snapshots")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class PublicDataSnapshot extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "business_id", nullable = false)
    private Business business;

    @Column(name = "reference_date", nullable = false)
    private LocalDate referenceDate;

    @Column(name = "source_name", nullable = false, length = 200)
    private String sourceName;

    @Column(name = "snapshot_version", nullable = false, length = 100)
    private String snapshotVersion;

    @Column(name = "reference_area", nullable = false, length = 255)
    private String referenceArea;

    @Enumerated(EnumType.STRING)
    @Column(name = "source_type", nullable = false, length = 50)
    private DataSourceType sourceType;

    private PublicDataSnapshot(
            Business business,
            LocalDate referenceDate,
            String sourceName,
            String snapshotVersion,
            String referenceArea
    ) {
        this.business = Objects.requireNonNull(business);
        this.referenceDate = Objects.requireNonNull(referenceDate);
        this.sourceName = Objects.requireNonNull(sourceName);
        this.snapshotVersion = Objects.requireNonNull(snapshotVersion);
        this.referenceArea = Objects.requireNonNull(referenceArea);
        this.sourceType = DataSourceType.PUBLIC_DATA;
    }

    public static PublicDataSnapshot create(
            Business business,
            LocalDate referenceDate,
            String sourceName,
            String snapshotVersion,
            String referenceArea
    ) {
        return new PublicDataSnapshot(
                business,
                referenceDate,
                sourceName,
                snapshotVersion,
                referenceArea
        );
    }
}
