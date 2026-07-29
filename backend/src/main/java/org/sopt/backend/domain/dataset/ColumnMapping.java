// 원본 파일 컬럼과 표준 필드의 매핑 정보를 저장하는 하위 엔티티
package org.sopt.backend.domain.dataset;

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
import jakarta.persistence.UniqueConstraint;
import java.math.BigDecimal;
import java.util.Objects;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@Entity
@Table(
        name = "column_mappings",
        uniqueConstraints = @UniqueConstraint(
                name = "uk_dataset_mapping_source",
                columnNames = {"dataset_id", "file_type", "source_column"}
        )
)
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class ColumnMapping {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "dataset_id", nullable = false)
    private Dataset dataset;

    @Enumerated(EnumType.STRING)
    @Column(name = "file_type", nullable = false, length = 20)
    private DatasetFileType fileType;

    @Column(name = "source_column", nullable = false, length = 150)
    private String sourceColumn;

    @Column(name = "target_field", nullable = false, length = 150)
    private String targetField;

    @Column(precision = 5, scale = 4)
    private BigDecimal confidence;

    @Column(nullable = false)
    private boolean confirmed;

    ColumnMapping(
            Dataset dataset,
            DatasetFileType fileType,
            String sourceColumn,
            String targetField,
            BigDecimal confidence
    ) {
        this.dataset = Objects.requireNonNull(dataset);
        this.fileType = Objects.requireNonNull(fileType);
        this.sourceColumn = Objects.requireNonNull(sourceColumn);
        this.targetField = Objects.requireNonNull(targetField);
        this.confidence = confidence;
    }

    void confirm() {
        this.confirmed = true;
    }
}
