// 시뮬레이션 생성 전 사업의 재무·활동 기준값을 변경 불가능한 이력으로 저장하는 엔티티
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
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.Objects;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.sopt.backend.domain.common.BaseTimeEntity;
import org.sopt.backend.domain.dataset.Dataset;
import org.sopt.backend.domain.source.DataSourceType;

@Getter
@Entity
@Table(name = "business_snapshots")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class BusinessSnapshot extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "business_id", nullable = false)
    private Business business;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "dataset_id", nullable = false)
    private Dataset dataset;

    @Column(name = "reference_date", nullable = false)
    private LocalDate referenceDate;

    @Column(name = "snapshot_version", nullable = false, length = 100)
    private String snapshotVersion;

    @Column(name = "monthly_net_sales_amount", nullable = false)
    private Long monthlyNetSalesAmount;

    @Column(name = "monthly_expense_amount", nullable = false)
    private Long monthlyExpenseAmount;

    @Column(name = "existing_monthly_repayment_amount", nullable = false)
    private Long existingMonthlyRepaymentAmount;

    @Column(name = "contribution_margin_rate", nullable = false, precision = 7, scale = 4)
    private BigDecimal contributionMarginRate;

    @Column(name = "average_order_amount")
    private Long averageOrderAmount;

    @Column(name = "monthly_order_count")
    private Integer monthlyOrderCount;

    @Column(name = "online_sales_ratio", precision = 7, scale = 4)
    private BigDecimal onlineSalesRatio;

    @Column(name = "employee_count", nullable = false)
    private Integer employeeCount;

    @Enumerated(EnumType.STRING)
    @Column(name = "source_type", nullable = false, length = 50)
    private DataSourceType sourceType;

    private BusinessSnapshot(
            Business business,
            Dataset dataset,
            LocalDate referenceDate,
            String snapshotVersion,
            Long monthlyNetSalesAmount,
            Long monthlyExpenseAmount,
            Long existingMonthlyRepaymentAmount,
            BigDecimal contributionMarginRate,
            Long averageOrderAmount,
            Integer monthlyOrderCount,
            BigDecimal onlineSalesRatio,
            Integer employeeCount,
            DataSourceType sourceType
    ) {
        this.business = Objects.requireNonNull(business);
        this.dataset = Objects.requireNonNull(dataset);
        if (dataset.getBusiness() != business) {
            throw new IllegalArgumentException(
                    "사업 스냅샷의 데이터셋은 같은 사업체에 속해야 합니다."
            );
        }
        this.referenceDate = Objects.requireNonNull(referenceDate);
        this.snapshotVersion = Objects.requireNonNull(snapshotVersion);
        this.monthlyNetSalesAmount = Objects.requireNonNull(monthlyNetSalesAmount);
        this.monthlyExpenseAmount = Objects.requireNonNull(monthlyExpenseAmount);
        this.existingMonthlyRepaymentAmount = Objects.requireNonNull(
                existingMonthlyRepaymentAmount
        );
        this.contributionMarginRate = Objects.requireNonNull(contributionMarginRate);
        this.averageOrderAmount = averageOrderAmount;
        this.monthlyOrderCount = monthlyOrderCount;
        this.onlineSalesRatio = onlineSalesRatio;
        this.employeeCount = Objects.requireNonNull(employeeCount);
        this.sourceType = Objects.requireNonNull(sourceType);
    }

    public static BusinessSnapshot create(
            Business business,
            Dataset dataset,
            LocalDate referenceDate,
            String snapshotVersion,
            Long monthlyNetSalesAmount,
            Long monthlyExpenseAmount,
            Long existingMonthlyRepaymentAmount,
            BigDecimal contributionMarginRate,
            Long averageOrderAmount,
            Integer monthlyOrderCount,
            BigDecimal onlineSalesRatio,
            Integer employeeCount,
            DataSourceType sourceType
    ) {
        return new BusinessSnapshot(
                business,
                dataset,
                referenceDate,
                snapshotVersion,
                monthlyNetSalesAmount,
                monthlyExpenseAmount,
                existingMonthlyRepaymentAmount,
                contributionMarginRate,
                averageOrderAmount,
                monthlyOrderCount,
                onlineSalesRatio,
                employeeCount,
                sourceType
        );
    }
}
