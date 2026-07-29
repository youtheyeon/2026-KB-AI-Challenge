// 사용자가 시뮬레이션에서 최종 선택한 자금 배분안을 저장하는 엔티티
package org.sopt.backend.domain.selection;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.OneToOne;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import java.time.LocalDate;
import java.util.Objects;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.sopt.backend.domain.common.BaseTimeEntity;
import org.sopt.backend.domain.simulation.AllocationPlan;
import org.sopt.backend.domain.simulation.Simulation;

@Getter
@Entity
@Table(
        name = "plan_selections",
        uniqueConstraints = @UniqueConstraint(
                name = "uk_plan_selection_simulation",
                columnNames = "simulation_id"
        )
)
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class PlanSelection extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @OneToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "simulation_id", nullable = false, unique = true)
    private Simulation simulation;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "selected_plan_id", nullable = false)
    private AllocationPlan selectedPlan;

    @Column(length = 1000)
    private String memo;

    @Column(name = "verification_available_date", nullable = false)
    private LocalDate verificationAvailableDate;

    private PlanSelection(
            Simulation simulation,
            AllocationPlan selectedPlan,
            String memo,
            LocalDate verificationAvailableDate
    ) {
        if (!simulation.getPlans().contains(selectedPlan)) {
            throw new IllegalArgumentException("선택한 배분안은 같은 시뮬레이션에 속해야 합니다.");
        }
        this.simulation = Objects.requireNonNull(simulation);
        this.selectedPlan = Objects.requireNonNull(selectedPlan);
        this.memo = memo;
        this.verificationAvailableDate = Objects.requireNonNull(verificationAvailableDate);
    }

    public static PlanSelection create(
            Simulation simulation,
            AllocationPlan selectedPlan,
            String memo,
            LocalDate verificationAvailableDate
    ) {
        return new PlanSelection(
                simulation,
                selectedPlan,
                memo,
                verificationAvailableDate
        );
    }
}
