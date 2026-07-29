// 시뮬레이션에서 생성한 하나의 자금 배분안을 저장하는 하위 엔티티
package org.sopt.backend.domain.simulation;

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
import jakarta.persistence.OrderColumn;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@Entity
@Table(
        name = "allocation_plans",
        uniqueConstraints = @UniqueConstraint(
                name = "uk_simulation_plan_code",
                columnNames = {"simulation_id", "plan_code"}
        )
)
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class AllocationPlan {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "simulation_id", nullable = false)
    private Simulation simulation;

    @Enumerated(EnumType.STRING)
    @Column(name = "plan_code", nullable = false, length = 5)
    private PlanCode planCode;

    @Column(name = "plan_type", nullable = false, length = 100)
    private String planType;

    @Column(nullable = false, length = 255)
    private String title;

    @Column(name = "total_amount", nullable = false)
    private Long totalAmount;

    @ElementCollection(fetch = FetchType.LAZY)
    @CollectionTable(
            name = "allocation_plan_items",
            joinColumns = @JoinColumn(name = "allocation_plan_id")
    )
    @OrderColumn(name = "item_order")
    private List<AllocationItem> items = new ArrayList<>();

    AllocationPlan(
            Simulation simulation,
            PlanCode planCode,
            String planType,
            String title,
            Long totalAmount,
            List<AllocationItem> items
    ) {
        this.simulation = Objects.requireNonNull(simulation);
        this.planCode = Objects.requireNonNull(planCode);
        this.planType = Objects.requireNonNull(planType);
        this.title = Objects.requireNonNull(title);
        this.totalAmount = Objects.requireNonNull(totalAmount);
        this.items.addAll(Objects.requireNonNull(items));
    }
}
