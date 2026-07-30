// 사용자가 고정 A·B·C 중 선택한 하나의 시나리오를 저장하는 엔티티
package org.sopt.backend.domain.selection;

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
import java.util.Objects;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.sopt.backend.domain.common.BaseTimeEntity;
import org.sopt.backend.domain.simulation.Scenario;
import org.sopt.backend.domain.simulation.Simulation;

@Getter
@Entity
@Table(
        name = "scenario_selections",
        uniqueConstraints = @UniqueConstraint(
                name = "uk_scenario_selection_simulation",
                columnNames = "simulation_id"
        )
)
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class ScenarioSelection extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @OneToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "simulation_id", nullable = false, unique = true)
    private Simulation simulation;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "selected_scenario_id", nullable = false)
    private Scenario selectedScenario;

    private ScenarioSelection(Simulation simulation, Scenario selectedScenario) {
        if (!simulation.getScenarios().contains(selectedScenario)) {
            throw new IllegalArgumentException("선택한 시나리오는 같은 시뮬레이션에 속해야 합니다.");
        }
        this.simulation = Objects.requireNonNull(simulation);
        this.selectedScenario = Objects.requireNonNull(selectedScenario);
    }

    public static ScenarioSelection create(
            Simulation simulation,
            Scenario selectedScenario
    ) {
        return new ScenarioSelection(simulation, selectedScenario);
    }
}
