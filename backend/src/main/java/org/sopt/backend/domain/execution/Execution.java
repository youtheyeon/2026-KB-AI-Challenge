// 시뮬레이션에 대한 실제 자금 집행 내역을 저장하는 엔티티
package org.sopt.backend.domain.execution;

import jakarta.persistence.Column;
import jakarta.persistence.CascadeType;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.OneToOne;
import jakarta.persistence.OneToMany;
import jakarta.persistence.OrderColumn;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.EnumSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.sopt.backend.domain.common.BaseTimeEntity;
import org.sopt.backend.domain.selection.ScenarioSelection;
import org.sopt.backend.domain.simulation.AllocationCategory;
import org.sopt.backend.domain.simulation.Simulation;

@Getter
@Entity
@Table(
        name = "executions",
        uniqueConstraints = @UniqueConstraint(
                name = "uk_execution_simulation",
                columnNames = "simulation_id"
        )
)
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Execution extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @OneToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "simulation_id", nullable = false, unique = true)
    private Simulation simulation;

    @OneToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "scenario_selection_id", nullable = false, unique = true)
    private ScenarioSelection scenarioSelection;

    @Enumerated(EnumType.STRING)
    @Column(name = "execution_type", nullable = false, length = 30)
    private ExecutionType executionType;

    @Column(name = "executed_at", nullable = false)
    private LocalDate executedAt;

    @OneToMany(cascade = CascadeType.ALL, orphanRemoval = true)
    @JoinColumn(name = "execution_id", nullable = false)
    @OrderColumn(name = "allocation_order")
    private List<ExecutionAllocation> allocations = new ArrayList<>();

    @Column(name = "unused_amount", nullable = false)
    private Long unusedAmount;

    @Column(name = "total_executed_amount", nullable = false)
    private Long totalExecutedAmount;

    private Execution(
            Simulation simulation,
            ScenarioSelection scenarioSelection,
            ExecutionType executionType,
            LocalDate executedAt,
            List<ExecutionAllocation> allocations,
            Long unusedAmount
    ) {
        this.simulation = Objects.requireNonNull(simulation);
        this.scenarioSelection = Objects.requireNonNull(scenarioSelection);
        if (scenarioSelection.getSimulation() != simulation) {
            throw new IllegalArgumentException(
                    "집행은 같은 시뮬레이션의 선택 내역을 참조해야 합니다."
            );
        }
        this.executionType = Objects.requireNonNull(executionType);
        this.executedAt = Objects.requireNonNull(executedAt);
        this.unusedAmount = unusedAmount == null ? 0L : unusedAmount;
        if (this.unusedAmount < 0L) {
            throw new IllegalArgumentException("미사용 금액은 음수일 수 없습니다.");
        }
        this.allocations.addAll(Objects.requireNonNull(allocations));
        Set<AllocationCategory> categories = EnumSet.noneOf(
                AllocationCategory.class
        );
        boolean hasDuplicateCategory = this.allocations.stream()
                .map(ExecutionAllocation::getCategory)
                .anyMatch(category -> !categories.add(category));
        if (hasDuplicateCategory) {
            throw new IllegalArgumentException(
                    "집행 배분 카테고리는 중복될 수 없습니다."
            );
        }
        long allocationTotal = this.allocations.stream()
                .mapToLong(ExecutionAllocation::getAmount)
                .sum();
        long loanAmount = simulation.getLoanCondition().getAmount();
        if (allocationTotal + this.unusedAmount != loanAmount) {
            throw new IllegalArgumentException("집행 금액 합계가 대출금액과 일치해야 합니다.");
        }
        this.totalExecutedAmount = allocationTotal;
    }

    public static Execution create(
            Simulation simulation,
            ScenarioSelection scenarioSelection,
            ExecutionType executionType,
            LocalDate executedAt,
            List<ExecutionAllocation> allocations,
            Long unusedAmount
    ) {
        return new Execution(
                simulation,
                scenarioSelection,
                executionType,
                executedAt,
                allocations,
                unusedAmount
        );
    }

    public List<ExecutionAllocation> getAllocations() {
        return List.copyOf(allocations);
    }

}
