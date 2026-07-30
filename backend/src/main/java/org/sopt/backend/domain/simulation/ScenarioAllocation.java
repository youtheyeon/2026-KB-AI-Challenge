// 고정 시나리오의 카테고리별 배분 비율과 금액을 저장하는 하위 엔티티
package org.sopt.backend.domain.simulation;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
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
        name = "scenario_allocations",
        uniqueConstraints = @UniqueConstraint(
                name = "uk_scenario_allocation_category",
                columnNames = {"scenario_id", "category"}
        )
)
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class ScenarioAllocation {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 50)
    private AllocationCategory category;

    @Column(nullable = false, precision = 7, scale = 4)
    private BigDecimal ratio;

    @Column(nullable = false)
    private Long amount;

    private ScenarioAllocation(
            AllocationCategory category,
            BigDecimal ratio,
            Long amount
    ) {
        this.category = Objects.requireNonNull(category);
        this.ratio = Objects.requireNonNull(ratio);
        this.amount = Objects.requireNonNull(amount);
        if (ratio.signum() < 0) {
            throw new IllegalArgumentException("배분 비율은 음수일 수 없습니다.");
        }
        if (amount < 0L) {
            throw new IllegalArgumentException("배분 금액은 음수일 수 없습니다.");
        }
    }

    public static ScenarioAllocation create(
            AllocationCategory category,
            BigDecimal ratio,
            Long amount
    ) {
        return new ScenarioAllocation(category, ratio, amount);
    }
}
