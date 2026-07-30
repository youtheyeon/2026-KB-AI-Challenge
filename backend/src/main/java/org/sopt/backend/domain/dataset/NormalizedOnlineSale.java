// 선택 온라인 주문·정산 자료를 중복 합산 기준과 함께 저장하는 엔티티
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
import java.time.LocalDate;
import java.util.Objects;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@Entity
@Table(name = "normalized_online_sales")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class NormalizedOnlineSale {

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

    @Column(name = "sales_channel", nullable = false, length = 100)
    private String salesChannel;

    @Column(name = "order_type", length = 100)
    private String orderType;

    @Column(name = "order_count", nullable = false)
    private Integer orderCount;

    @Column(name = "gross_order_amount", nullable = false)
    private Long grossOrderAmount;

    @Column(name = "discount_amount")
    private Long discountAmount;

    @Column(name = "refund_amount")
    private Long refundAmount;

    @Column(name = "net_sales_amount", nullable = false)
    private Long netSalesAmount;

    @Column(name = "platform_fee_amount")
    private Long platformFeeAmount;

    @Column(name = "payment_fee_amount")
    private Long paymentFeeAmount;

    @Column(name = "merchant_delivery_fee")
    private Long merchantDeliveryFee;

    @Column(name = "settlement_amount")
    private Long settlementAmount;

    @Column(name = "settlement_date")
    private LocalDate settlementDate;

    @Column(name = "settlement_status", length = 100)
    private String settlementStatus;

    @Enumerated(EnumType.STRING)
    @Column(name = "reconciliation_type", nullable = false, length = 40)
    private OnlineSalesReconciliationType reconciliationType;

    private NormalizedOnlineSale(
            Dataset dataset,
            DatasetFile sourceFile,
            LocalDate businessDate,
            String salesChannel,
            String orderType,
            Integer orderCount,
            Long grossOrderAmount,
            Long discountAmount,
            Long refundAmount,
            Long netSalesAmount,
            Long platformFeeAmount,
            Long paymentFeeAmount,
            Long merchantDeliveryFee,
            Long settlementAmount,
            LocalDate settlementDate,
            String settlementStatus,
            OnlineSalesReconciliationType reconciliationType
    ) {
        this.dataset = Objects.requireNonNull(dataset);
        this.sourceFile = Objects.requireNonNull(sourceFile);
        if (!dataset.containsFile(sourceFile)) {
            throw new IllegalArgumentException(
                    "원본 파일은 정규화 행과 같은 데이터셋에 속해야 합니다."
            );
        }
        if (sourceFile.getFileType() != DatasetFileType.ONLINE_SALES) {
            throw new IllegalArgumentException(
                    "온라인 매출 정규화 행은 온라인 매출 파일을 원본으로 사용해야 합니다."
            );
        }
        this.businessDate = Objects.requireNonNull(businessDate);
        this.salesChannel = Objects.requireNonNull(salesChannel);
        this.orderType = orderType;
        this.orderCount = Objects.requireNonNull(orderCount);
        this.grossOrderAmount = Objects.requireNonNull(grossOrderAmount);
        this.discountAmount = discountAmount;
        this.refundAmount = refundAmount;
        this.netSalesAmount = Objects.requireNonNull(netSalesAmount);
        this.platformFeeAmount = platformFeeAmount;
        this.paymentFeeAmount = paymentFeeAmount;
        this.merchantDeliveryFee = merchantDeliveryFee;
        this.settlementAmount = settlementAmount;
        this.settlementDate = settlementDate;
        this.settlementStatus = settlementStatus;
        this.reconciliationType = Objects.requireNonNull(reconciliationType);
    }

    public static NormalizedOnlineSale create(
            Dataset dataset,
            DatasetFile sourceFile,
            LocalDate businessDate,
            String salesChannel,
            String orderType,
            Integer orderCount,
            Long grossOrderAmount,
            Long discountAmount,
            Long refundAmount,
            Long netSalesAmount,
            Long platformFeeAmount,
            Long paymentFeeAmount,
            Long merchantDeliveryFee,
            Long settlementAmount,
            LocalDate settlementDate,
            String settlementStatus,
            OnlineSalesReconciliationType reconciliationType
    ) {
        return new NormalizedOnlineSale(
                dataset,
                sourceFile,
                businessDate,
                salesChannel,
                orderType,
                orderCount,
                grossOrderAmount,
                discountAmount,
                refundAmount,
                netSalesAmount,
                platformFeeAmount,
                paymentFeeAmount,
                merchantDeliveryFee,
                settlementAmount,
                settlementDate,
                settlementStatus,
                reconciliationType
        );
    }

    public boolean shouldAddToTotalSales() {
        return reconciliationType == OnlineSalesReconciliationType.SEPARATE_FROM_POS_TOTAL;
    }
}
