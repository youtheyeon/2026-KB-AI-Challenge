// 사용자가 소유한 사업체의 기본 정보를 저장하는 엔티티
package org.sopt.backend.domain.business;

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
import java.math.BigDecimal;
import java.util.HashSet;
import java.util.Objects;
import java.util.Set;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.sopt.backend.domain.common.BaseTimeEntity;
import org.sopt.backend.domain.user.User;

@Getter
@Entity
@Table(name = "businesses")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Business extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Column(name = "business_name", nullable = false, length = 150)
    private String businessName;

    @Column(name = "road_address", nullable = false, length = 255)
    private String roadAddress;

    @Column(name = "industry_code", nullable = false, length = 100)
    private String industryCode;

    @Column(name = "trade_area_usage_type", nullable = false, length = 100)
    private String tradeAreaUsageType;

    @Column(name = "business_age", nullable = false, length = 100)
    private String businessAge;

    @Column(name = "store_type", nullable = false, length = 100)
    private String storeType;

    @Column(name = "employee_count", nullable = false)
    private Integer employeeCount;

    @Column(name = "monthly_revenue_band", nullable = false, length = 100)
    private String monthlyRevenueBand;

    @ElementCollection(fetch = FetchType.LAZY)
    @CollectionTable(
            name = "business_sales_channels",
            joinColumns = @JoinColumn(name = "business_id")
    )
    @Column(name = "sales_channel", nullable = false, length = 100)
    private Set<String> primarySalesChannels = new HashSet<>();

    @Column(name = "seat_count")
    private Integer seatCount;

    @Column(name = "average_wait_time_minutes", precision = 7, scale = 2)
    private BigDecimal averageWaitTimeMinutes;

    @Column(name = "peak_hour_utilization_rate", precision = 7, scale = 4)
    private BigDecimal peakHourUtilizationRate;

    @Column(name = "repeat_customer_rate", precision = 7, scale = 4)
    private BigDecimal repeatCustomerRate;

    private Business(
            User user,
            String businessName,
            String roadAddress,
            String industryCode,
            String tradeAreaUsageType,
            String businessAge,
            String storeType,
            Integer employeeCount,
            String monthlyRevenueBand,
            Set<String> primarySalesChannels,
            Integer seatCount,
            BigDecimal averageWaitTimeMinutes,
            BigDecimal peakHourUtilizationRate,
            BigDecimal repeatCustomerRate
    ) {
        this.user = Objects.requireNonNull(user);
        this.businessName = Objects.requireNonNull(businessName);
        this.roadAddress = Objects.requireNonNull(roadAddress);
        this.industryCode = Objects.requireNonNull(industryCode);
        this.tradeAreaUsageType = Objects.requireNonNull(tradeAreaUsageType);
        this.businessAge = Objects.requireNonNull(businessAge);
        this.storeType = Objects.requireNonNull(storeType);
        this.employeeCount = Objects.requireNonNull(employeeCount);
        this.monthlyRevenueBand = Objects.requireNonNull(monthlyRevenueBand);
        this.primarySalesChannels.addAll(Objects.requireNonNull(primarySalesChannels));
        this.seatCount = seatCount;
        this.averageWaitTimeMinutes = averageWaitTimeMinutes;
        this.peakHourUtilizationRate = peakHourUtilizationRate;
        this.repeatCustomerRate = repeatCustomerRate;
    }

    public static Business create(
            User user,
            String businessName,
            String roadAddress,
            String industryCode,
            String tradeAreaUsageType,
            String businessAge,
            String storeType,
            Integer employeeCount,
            String monthlyRevenueBand,
            Set<String> primarySalesChannels,
            Integer seatCount,
            BigDecimal averageWaitTimeMinutes,
            BigDecimal peakHourUtilizationRate,
            BigDecimal repeatCustomerRate
    ) {
        return new Business(
                user,
                businessName,
                roadAddress,
                industryCode,
                tradeAreaUsageType,
                businessAge,
                storeType,
                employeeCount,
                monthlyRevenueBand,
                primarySalesChannels,
                seatCount,
                averageWaitTimeMinutes,
                peakHourUtilizationRate,
                repeatCustomerRate
        );
    }

    public static Business create(
            User user,
            String businessName,
            String region,
            Industry industry,
            Integer employeeCount,
            Set<SalesChannel> salesChannels
    ) {
        return create(
                user,
                businessName,
                region,
                industry.name(),
                "UNSPECIFIED",
                "UNSPECIFIED",
                "UNSPECIFIED",
                employeeCount,
                "UNSPECIFIED",
                salesChannels.stream().map(Enum::name).collect(java.util.stream.Collectors.toSet()),
                null,
                null,
                null,
                null
        );
    }
}
