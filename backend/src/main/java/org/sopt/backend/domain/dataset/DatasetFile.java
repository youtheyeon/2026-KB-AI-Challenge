// 데이터셋에 업로드된 개별 파일의 분석 정보를 저장하는 하위 엔티티
package org.sopt.backend.domain.dataset;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import java.util.Objects;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@Entity
@Table(
        name = "dataset_files",
        uniqueConstraints = @UniqueConstraint(
                name = "uk_dataset_file_type",
                columnNames = {"dataset_id", "file_type"}
        )
)
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class DatasetFile {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Enumerated(EnumType.STRING)
    @Column(name = "file_type", nullable = false, length = 20)
    private DatasetFileType fileType;

    @Column(name = "file_name", nullable = false, length = 255)
    private String fileName;

    @Column(name = "row_count")
    private Integer rowCount;

    DatasetFile(DatasetFileType fileType, String fileName) {
        this.fileType = Objects.requireNonNull(fileType);
        this.fileName = Objects.requireNonNull(fileName);
    }

    public void updateRowCount(Integer rowCount) {
        this.rowCount = rowCount;
    }
}
