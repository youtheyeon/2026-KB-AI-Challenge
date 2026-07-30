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
import org.sopt.backend.domain.source.DataSourceType;

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

    @Column(name = "dataset_version", nullable = false, length = 100)
    private String datasetVersion;

    @OneToMany(
            cascade = CascadeType.ALL,
            orphanRemoval = true
    )
    @JoinColumn(name = "dataset_id", nullable = false)
    private List<DatasetFile> files = new ArrayList<>();

    @OneToMany(
            cascade = CascadeType.ALL,
            orphanRemoval = true
    )
    @JoinColumn(name = "dataset_id", nullable = false)
    private List<ColumnMapping> columnMappings = new ArrayList<>();

    private Dataset(Business business, String datasetVersion) {
        this.business = Objects.requireNonNull(business);
        this.datasetVersion = Objects.requireNonNull(datasetVersion);
        this.status = DatasetStatus.UPLOADED;
    }

    public static Dataset create(Business business, String datasetVersion) {
        return new Dataset(business, datasetVersion);
    }

    public static Dataset create(Business business) {
        return new Dataset(business, "legacy");
    }

    public DatasetFile addFile(
            DatasetFileType fileType,
            String fileName,
            DatasetFormat detectedFormat,
            DataSourceType sourceType
    ) {
        boolean duplicate = files.stream()
                .anyMatch(file -> file.getFileType() == fileType);
        if (duplicate) {
            throw new IllegalArgumentException("동일한 파일 유형은 한 번만 등록할 수 있습니다.");
        }
        DatasetFile file = new DatasetFile(
                fileType,
                fileName,
                detectedFormat,
                sourceType
        );
        files.add(file);
        return file;
    }

    public void addFile(DatasetFileType fileType, String fileName) {
        addFile(
                fileType,
                fileName,
                DatasetFormat.UNKNOWN,
                DataSourceType.USER_INPUT
        );
    }

    public void addAutoMapping(
            DatasetFileType fileType,
            String sourceColumn,
            String targetField,
            BigDecimal confidence
    ) {
        columnMappings.add(new ColumnMapping(
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

    public void startParsing() {
        requireStatus(DatasetStatus.UPLOADED);
        status = DatasetStatus.PARSING;
    }

    public void startNormalizing() {
        requireStatus(DatasetStatus.PARSING);
        status = DatasetStatus.NORMALIZING;
    }

    public void markReady() {
        requireStatus(DatasetStatus.NORMALIZING);
        boolean hasSales = hasFile(DatasetFileType.SALES);
        boolean hasExpense = hasFile(DatasetFileType.EXPENSE)
                || hasFile(DatasetFileType.COST);
        if (!hasSales || !hasExpense) {
            throw new IllegalStateException("매출 파일과 비용 파일이 모두 필요합니다.");
        }
        status = DatasetStatus.READY;
    }

    public void markNeedsReupload() {
        status = DatasetStatus.NEEDS_REUPLOAD;
    }

    public void markFailed() {
        status = DatasetStatus.FAILED;
    }

    public boolean isOnlineSalesAvailable() {
        return hasFile(DatasetFileType.ONLINE_SALES)
                || hasFile(DatasetFileType.PLATFORM);
    }

    private boolean hasFile(DatasetFileType fileType) {
        return files.stream().anyMatch(file -> file.getFileType() == fileType);
    }

    private void requireStatus(DatasetStatus expected) {
        if (status != expected) {
            throw new IllegalStateException("데이터셋 상태 전이 순서가 올바르지 않습니다.");
        }
    }
}
