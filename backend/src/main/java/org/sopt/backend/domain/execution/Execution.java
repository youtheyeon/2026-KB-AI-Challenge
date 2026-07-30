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
import jakarta.persistence.Transient;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.sopt.backend.domain.common.BaseTimeEntity;
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

    @Enumerated(EnumType.STRING)
    @Column(name = "execution_type", nullable = false, length = 30)
    private ExecutionType executionType;

    @Transient
    private ExecutionMode executionMode;

    @Column(name = "executed_at", nullable = false)
    private LocalDate executedAt;

    @OneToMany(cascade = CascadeType.ALL, orphanRemoval = true)
    @JoinColumn(name = "execution_id", nullable = false)
    @OrderColumn(name = "allocation_order")
    private List<ExecutionAllocation> allocations = new ArrayList<>();

    @Transient
    private List<ExecutionItem> items = new ArrayList<>();

    @Column(name = "unused_amount", nullable = false)
    private Long unusedAmount;

    @Column(name = "total_executed_amount", nullable = false)
    private Long totalExecutedAmount;

    private Execution(
            Simulation simulation,
            ExecutionType executionType,
            LocalDate executedAt,
            List<ExecutionAllocation> allocations,
            Long unusedAmount
    ) {
        this.simulation = Objects.requireNonNull(simulation);
        this.executionType = Objects.requireNonNull(executionType);
        this.executedAt = Objects.requireNonNull(executedAt);
        this.unusedAmount = unusedAmount == null ? 0L : unusedAmount;
        if (this.unusedAmount < 0L) {
            throw new IllegalArgumentException("미사용 금액은 음수일 수 없습니다.");
        }
        this.allocations.addAll(Objects.requireNonNull(allocations));
        long allocationTotal = this.allocations.stream()
                .mapToLong(ExecutionAllocation::getAmount)
                .sum();
        long loanAmount = simulation.getLoanCondition().getAmount();
        if (allocationTotal + this.unusedAmount != loanAmount) {
            throw new IllegalArgumentException("집행 금액 합계가 대출금액과 일치해야 합니다.");
        }
        this.totalExecutedAmount = allocationTotal;
    }

    private Execution(
            Simulation simulation,
            ExecutionMode executionMode,
            LocalDate executedAt,
            List<ExecutionItem> items,
            Long unusedAmount
    ) {
        this.simulation = Objects.requireNonNull(simulation);
        this.executionMode = Objects.requireNonNull(executionMode);
        this.executionType = switch (executionMode) {
            case SAME_AS_A, SAME_AS_B, SAME_AS_C -> ExecutionType.EXACT_SELECTED;
            case MIXED -> ExecutionType.MIXED;
            case CUSTOM -> ExecutionType.CUSTOM;
        };
        this.executedAt = Objects.requireNonNull(executedAt);
        this.unusedAmount = unusedAmount == null ? 0L : unusedAmount;
        if (items != null) {
            this.items.addAll(items);
        }

        long itemTotal = this.items.stream()
                .mapToLong(ExecutionItem::getAmount)
                .sum();
        long loanAmount = simulation.getLoanCondition().getLoanAmount();
        if (executionMode == ExecutionMode.MIXED || executionMode == ExecutionMode.CUSTOM) {
            if (itemTotal + this.unusedAmount != loanAmount) {
                throw new IllegalArgumentException("집행 금액 합계가 대출금액과 일치해야 합니다.");
            }
            this.totalExecutedAmount = itemTotal;
        } else {
            this.totalExecutedAmount = loanAmount - this.unusedAmount;
        }
    }

    public static Execution create(
            Simulation simulation,
            ExecutionType executionType,
            LocalDate executedAt,
            List<ExecutionAllocation> allocations,
            Long unusedAmount
    ) {
        return new Execution(
                simulation,
                executionType,
                executedAt,
                allocations,
                unusedAmount
        );
    }

    public static Execution create(
            Simulation simulation,
            ExecutionMode executionMode,
            LocalDate executedAt,
            List<ExecutionItem> items,
            Long unusedAmount
    ) {
        return new Execution(
                simulation,
                executionMode,
                executedAt,
                items,
                unusedAmount
        );
    }
}
