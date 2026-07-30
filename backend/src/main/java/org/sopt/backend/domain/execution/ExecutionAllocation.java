// 실제 또는 Mock 집행의 카테고리별 사용 금액을 저장하는 하위 엔티티
package org.sopt.backend.domain.execution;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.util.Objects;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.sopt.backend.domain.simulation.AllocationCategory;

@Getter
@Entity
@Table(name = "execution_allocations")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class ExecutionAllocation {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 50)
    private AllocationCategory category;

    @Column(nullable = false)
    private Long amount;

    private ExecutionAllocation(AllocationCategory category, Long amount) {
        this.category = Objects.requireNonNull(category);
        this.amount = Objects.requireNonNull(amount);
        if (amount < 0L) {
            throw new IllegalArgumentException("집행 금액은 음수일 수 없습니다.");
        }
    }

    public static ExecutionAllocation create(
            AllocationCategory category,
            Long amount
    ) {
        return new ExecutionAllocation(category, amount);
    }
}
