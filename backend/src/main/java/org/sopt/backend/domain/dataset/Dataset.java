// 사업 분석에 사용할 업로드 파일과 컬럼 매핑 상태를 관리하는 엔티티
package org.sopt.backend.domain.dataset;

import jakarta.persistence.CascadeType;
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
import jakarta.persistence.OneToMany;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.sopt.backend.domain.business.Business;
import org.sopt.backend.domain.common.BaseTimeEntity;

@Getter
@Entity
@Table(name = "datasets")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Dataset extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "business_id", nullable = false)
    private Business business;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 30)
    private DatasetStatus status;

    @Column(name = "confirmed_at")
    private LocalDateTime confirmedAt;

    @OneToMany(
            mappedBy = "dataset",
            cascade = CascadeType.ALL,
            orphanRemoval = true
    )
    private List<DatasetFile> files = new ArrayList<>();

    @OneToMany(
            mappedBy = "dataset",
            cascade = CascadeType.ALL,
            orphanRemoval = true
    )
    private List<ColumnMapping> columnMappings = new ArrayList<>();

    private Dataset(Business business) {
        this.business = Objects.requireNonNull(business);
        this.status = DatasetStatus.ANALYZING;
    }

    public static Dataset create(Business business) {
        return new Dataset(business);
    }

    public void addFile(DatasetFileType fileType, String fileName) {
        boolean duplicate = files.stream()
                .anyMatch(file -> file.getFileType() == fileType);
        if (duplicate) {
            throw new IllegalArgumentException("동일한 파일 유형은 한 번만 등록할 수 있습니다.");
        }
        files.add(new DatasetFile(this, fileType, fileName));
    }

    public void addAutoMapping(
            DatasetFileType fileType,
            String sourceColumn,
            String targetField,
            BigDecimal confidence
    ) {
        columnMappings.add(new ColumnMapping(
                this,
                fileType,
                sourceColumn,
                targetField,
                confidence
        ));
        status = DatasetStatus.MAPPING_READY;
    }

    public void confirmMappings(LocalDateTime confirmedAt) {
        columnMappings.forEach(ColumnMapping::confirm);
        this.status = DatasetStatus.MAPPING_CONFIRMED;
        this.confirmedAt = Objects.requireNonNull(confirmedAt);
    }
}
