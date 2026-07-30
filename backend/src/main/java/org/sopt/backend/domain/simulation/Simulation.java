// 진단과 대출 조건을 기준으로 생성한 자금 배분 시뮬레이션 엔티티
package org.sopt.backend.domain.simulation;

import jakarta.persistence.CascadeType;
import jakarta.persistence.Column;
import jakarta.persistence.Embedded;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.OneToMany;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import jakarta.persistence.Transient;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.EnumSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.sopt.backend.domain.business.Business;
import org.sopt.backend.domain.business.BusinessSnapshot;
import org.sopt.backend.domain.common.BaseTimeEntity;
import org.sopt.backend.domain.dataset.Dataset;
import org.sopt.backend.domain.diagnosis.Diagnosis;

@Getter
@Entity
@Table(name = "simulations")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Simulation extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "business_id", nullable = false)
    private Business business;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "diagnosis_id", nullable = false)
    private Diagnosis diagnosis;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "dataset_id")
    private Dataset dataset;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "business_snapshot_id")
    private BusinessSnapshot businessSnapshot;

    @Embedded
    private LoanCondition loanCondition;

    @Transient
    private Integer predictionMonths;

    @Column(nullable = false, length = 30)
    private String status;

    @Column(name = "allocation_generator_version", nullable = false, length = 100)
    private String allocationGeneratorVersion;

    @Column(name = "calculation_version", nullable = false, length = 100)
    private String calculationVersion;

    @Column(name = "prompt_version", nullable = false, length = 100)
    private String promptVersion;

    @Column(name = "public_data_reference_date", nullable = false)
    private LocalDate publicDataReferenceDate;

    @OneToMany(cascade = CascadeType.ALL, orphanRemoval = true)
    @JoinColumn(name = "simulation_id", nullable = false)
    private List<Scenario> scenarios = new ArrayList<>();

    @Transient
    private List<AllocationPlan> plans = new ArrayList<>();

    private Simulation(
            Business business,
            Diagnosis diagnosis,
            LoanCondition loanCondition,
            Integer predictionMonths
    ) {
        this.business = Objects.requireNonNull(business);
        this.diagnosis = Objects.requireNonNull(diagnosis);
        this.loanCondition = Objects.requireNonNull(loanCondition);
        this.predictionMonths = Objects.requireNonNull(predictionMonths);
        this.status = "LEGACY";
        this.allocationGeneratorVersion = "legacy";
        this.calculationVersion = "legacy";
        this.promptVersion = "legacy";
        this.publicDataReferenceDate = LocalDate.of(1970, 1, 1);
    }

    private Simulation(
            Business business,
            Dataset dataset,
            Diagnosis diagnosis,
            BusinessSnapshot businessSnapshot,
            LoanCondition loanCondition,
            String allocationGeneratorVersion,
            String calculationVersion,
            String promptVersion,
            LocalDate publicDataReferenceDate
    ) {
        this.business = Objects.requireNonNull(business);
        this.dataset = Objects.requireNonNull(dataset);
        this.diagnosis = Objects.requireNonNull(diagnosis);
        this.businessSnapshot = Objects.requireNonNull(businessSnapshot);
        this.loanCondition = Objects.requireNonNull(loanCondition);
        this.status = "CREATING";
        this.allocationGeneratorVersion = Objects.requireNonNull(allocationGeneratorVersion);
        this.calculationVersion = Objects.requireNonNull(calculationVersion);
        this.promptVersion = Objects.requireNonNull(promptVersion);
        this.publicDataReferenceDate = Objects.requireNonNull(publicDataReferenceDate);
    }

    public static Simulation create(
            Business business,
            Diagnosis diagnosis,
            LoanCondition loanCondition,
            Integer predictionMonths
    ) {
        return new Simulation(business, diagnosis, loanCondition, predictionMonths);
    }

    public static Simulation create(
            Business business,
            Dataset dataset,
            Diagnosis diagnosis,
            BusinessSnapshot businessSnapshot,
            LoanCondition loanCondition,
            String allocationGeneratorVersion,
            String calculationVersion,
            String promptVersion,
            LocalDate publicDataReferenceDate
    ) {
        return new Simulation(
                business,
                dataset,
                diagnosis,
                businessSnapshot,
                loanCondition,
                allocationGeneratorVersion,
                calculationVersion,
                promptVersion,
                publicDataReferenceDate
        );
    }

    public Scenario addScenario(
            ScenarioCode scenarioCode,
            String strategyType,
            String title,
            List<ScenarioAllocation> allocations,
            List<ScenarioDraftReason> draftReasons,
            ScenarioFinancialResult financialResult,
            List<String> targetMetrics
    ) {
        boolean duplicate = scenarios.stream()
                .anyMatch(scenario -> scenario.getScenarioCode() == scenarioCode);
        if (duplicate) {
            throw new IllegalArgumentException("동일한 시나리오 코드는 한 번만 등록할 수 있습니다.");
        }
        Scenario scenario = new Scenario(
                scenarioCode,
                strategyType,
                title,
                loanCondition.getAmount(),
                allocations,
                draftReasons,
                financialResult,
                targetMetrics
        );
        scenarios.add(scenario);
        if (scenarios.size() == ScenarioCode.values().length) {
            status = "COMPLETED";
        }
        return scenario;
    }

    public List<Scenario> getScenarios() {
        return List.copyOf(scenarios);
    }

    public AllocationPlan addPlan(
            PlanCode planCode,
            String planType,
            String title,
            Long totalAmount,
            List<AllocationItem> items
    ) {
        boolean duplicate = plans.stream()
                .anyMatch(plan -> plan.getPlanCode() == planCode);
        if (duplicate) {
            throw new IllegalArgumentException("동일한 배분안 코드는 한 번만 등록할 수 있습니다.");
        }

        AllocationPlan plan = new AllocationPlan(
                planCode,
                planType,
                title,
                totalAmount,
                items
        );
        plans.add(plan);
        return plan;
    }

    public List<AllocationPlan> getPlans() {
        return List.copyOf(plans);
    }

    @PrePersist
    @PreUpdate
    private void validatePlanSet() {
        if (!scenarios.isEmpty()) {
            Set<ScenarioCode> scenarioCodes = EnumSet.noneOf(ScenarioCode.class);
            scenarios.forEach(scenario -> scenarioCodes.add(scenario.getScenarioCode()));
            if (scenarios.size() != ScenarioCode.values().length
                    || !scenarioCodes.equals(EnumSet.allOf(ScenarioCode.class))) {
                throw new IllegalStateException("A, B, C 시나리오가 각각 하나씩 필요합니다.");
            }
            return;
        }

        Set<PlanCode> planCodes = EnumSet.noneOf(PlanCode.class);
        plans.forEach(plan -> planCodes.add(plan.getPlanCode()));
        if (plans.size() != PlanCode.values().length
                || !planCodes.equals(EnumSet.allOf(PlanCode.class))) {
            throw new IllegalStateException("A, B, C 배분안이 각각 하나씩 필요합니다.");
        }
    }
}
