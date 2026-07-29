// 사용자가 소유한 사업체의 기본 정보를 저장하는 엔티티
package org.sopt.backend.domain.business;

import jakarta.persistence.CollectionTable;
import jakarta.persistence.Column;
import jakarta.persistence.ElementCollection;
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

    @Column(nullable = false, length = 150)
    private String region;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 30)
    private Industry industry;

    @Column(name = "employee_count")
    private Integer employeeCount;

    @ElementCollection(fetch = FetchType.LAZY)
    @CollectionTable(
            name = "business_sales_channels",
            joinColumns = @JoinColumn(name = "business_id")
    )
    @Enumerated(EnumType.STRING)
    @Column(name = "sales_channel", nullable = false, length = 30)
    private Set<SalesChannel> salesChannels = new HashSet<>();

    private Business(
            User user,
            String businessName,
            String region,
            Industry industry,
            Integer employeeCount,
            Set<SalesChannel> salesChannels
    ) {
        this.user = Objects.requireNonNull(user);
        this.businessName = Objects.requireNonNull(businessName);
        this.region = Objects.requireNonNull(region);
        this.industry = Objects.requireNonNull(industry);
        this.employeeCount = employeeCount;
        if (salesChannels != null) {
            this.salesChannels.addAll(salesChannels);
        }
    }

    public static Business create(
            User user,
            String businessName,
            String region,
            Industry industry,
            Integer employeeCount,
            Set<SalesChannel> salesChannels
    ) {
        return new Business(
                user,
                businessName,
                region,
                industry,
                employeeCount,
                salesChannels
        );
    }
}
