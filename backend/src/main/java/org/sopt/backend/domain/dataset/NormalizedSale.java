// 이지포스형 매출자료를 표준 필드로 정규화해 저장하는 엔티티
package org.sopt.backend.domain.dataset;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.LocalDate;
import java.time.LocalTime;
import java.util.Objects;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@Entity
@Table(name = "normalized_sales")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class NormalizedSale {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "dataset_id", nullable = false)
    private Dataset dataset;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "source_file_id", nullable = false)
    private DatasetFile sourceFile;

    @Column(name = "business_date", nullable = false)
    private LocalDate businessDate;

    @Column(name = "transaction_time")
    private LocalTime transactionTime;

    @Column(name = "receipt_number", length = 100)
    private String receiptNumber;

    @Column(name = "pos_number", length = 100)
    private String posNumber;

    @Column(name = "gross_sales", nullable = false)
    private Long grossSales;

    @Column(name = "discount_amount", nullable = false)
    private Long discountAmount;

    @Column(name = "refund_amount", nullable = false)
    private Long refundAmount;

    @Column(name = "net_sales", nullable = false)
    private Long netSales;

    @Column(name = "payment_method", length = 100)
    private String paymentMethod;

    @Column(name = "transaction_status", nullable = false, length = 100)
    private String transactionStatus;

    private NormalizedSale(
            Dataset dataset,
            DatasetFile sourceFile,
            LocalDate businessDate,
            LocalTime transactionTime,
            String receiptNumber,
            String posNumber,
            Long grossSales,
            Long discountAmount,
            Long refundAmount,
            Long netSales,
            String paymentMethod,
            String transactionStatus
    ) {
        this.dataset = Objects.requireNonNull(dataset);
        this.sourceFile = Objects.requireNonNull(sourceFile);
        if (!dataset.containsFile(sourceFile)) {
            throw new IllegalArgumentException(
                    "원본 파일은 정규화 행과 같은 데이터셋에 속해야 합니다."
            );
        }
        if (sourceFile.getFileType() != DatasetFileType.SALES) {
            throw new IllegalArgumentException(
                    "매출 정규화 행은 매출 파일을 원본으로 사용해야 합니다."
            );
        }
        this.businessDate = Objects.requireNonNull(businessDate);
        this.transactionTime = transactionTime;
        this.receiptNumber = receiptNumber;
        this.posNumber = posNumber;
        this.grossSales = Objects.requireNonNull(grossSales);
        this.discountAmount = Objects.requireNonNull(discountAmount);
        this.refundAmount = Objects.requireNonNull(refundAmount);
        this.netSales = Objects.requireNonNull(netSales);
        this.paymentMethod = paymentMethod;
        this.transactionStatus = Objects.requireNonNull(transactionStatus);
    }

    public static NormalizedSale create(
            Dataset dataset,
            DatasetFile sourceFile,
            LocalDate businessDate,
            LocalTime transactionTime,
            String receiptNumber,
            String posNumber,
            Long grossSales,
            Long discountAmount,
            Long refundAmount,
            Long netSales,
            String paymentMethod,
            String transactionStatus
    ) {
        return new NormalizedSale(
                dataset,
                sourceFile,
                businessDate,
                transactionTime,
                receiptNumber,
                posNumber,
                grossSales,
                discountAmount,
                refundAmount,
                netSales,
                paymentMethod,
                transactionStatus
        );
    }
}
