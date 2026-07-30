// 진단 병목에 대응하는 수정 불가능한 하나의 자금 배분 시나리오를 저장하는 엔티티
package org.sopt.backend.domain.simulation;

import jakarta.persistence.CascadeType;
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
import jakarta.persistence.OneToMany;
import jakarta.persistence.OneToOne;
import jakarta.persistence.OrderColumn;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.EnumSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@Entity
@Table(
        name = "scenarios",
        uniqueConstraints = @UniqueConstraint(
                name = "uk_simulation_scenario_code",
                columnNames = {"simulation_id", "scenario_code"}
        )
)
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Scenario {

    private static final BigDecimal MINIMUM_RATIO = new BigDecimal("0.05");
    private static final BigDecimal TOTAL_RATIO = BigDecimal.ONE;

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Enumerated(EnumType.STRING)
    @Column(name = "scenario_code", nullable = false, length = 5)
    private ScenarioCode scenarioCode;

    @Column(name = "strategy_type", nullable = false, length = 100)
    private String strategyType;

    @Column(nullable = false, length = 255)
    private String title;

    @Column(name = "total_amount", nullable = false)
    private Long totalAmount;

    @OneToMany(cascade = CascadeType.ALL, orphanRemoval = true)
    @JoinColumn(name = "scenario_id", nullable = false)
    @OrderColumn(name = "allocation_order")
    private List<ScenarioAllocation> allocations = new ArrayList<>();

    @ElementCollection(fetch = FetchType.LAZY)
    @CollectionTable(
            name = "scenario_draft_reasons",
            joinColumns = @JoinColumn(name = "scenario_id")
    )
    @OrderColumn(name = "reason_order")
    private List<ScenarioDraftReason> draftReasons = new ArrayList<>();

    @OneToOne(cascade = CascadeType.ALL, orphanRemoval = true, optional = false)
    @JoinColumn(name = "financial_result_id", nullable = false, unique = true)
    private ScenarioFinancialResult financialResult;

    @ElementCollection(fetch = FetchType.LAZY)
    @CollectionTable(
            name = "scenario_target_metrics",
            joinColumns = @JoinColumn(name = "scenario_id")
    )
    @OrderColumn(name = "metric_order")
    @Column(name = "target_metric", nullable = false, length = 100)
    private List<String> targetMetrics = new ArrayList<>();

    Scenario(
            ScenarioCode scenarioCode,
            String strategyType,
            String title,
            Long totalAmount,
            List<ScenarioAllocation> allocations,
            List<ScenarioDraftReason> draftReasons,
            ScenarioFinancialResult financialResult,
            List<String> targetMetrics
    ) {
        this.scenarioCode = Objects.requireNonNull(scenarioCode);
        this.strategyType = Objects.requireNonNull(strategyType);
        this.title = Objects.requireNonNull(title);
        this.totalAmount = Objects.requireNonNull(totalAmount);
        validateAllocations(allocations, totalAmount);
        this.allocations.addAll(allocations);
        requireNotEmpty(draftReasons, "시나리오 생성 근거가 필요합니다.");
        this.draftReasons.addAll(draftReasons);
        this.financialResult = Objects.requireNonNull(financialResult);
        requireNotEmpty(targetMetrics, "시나리오 목표 확인지표가 필요합니다.");
        this.targetMetrics.addAll(targetMetrics);
    }

    private void validateAllocations(
            List<ScenarioAllocation> allocations,
            Long expectedTotalAmount
    ) {
        Objects.requireNonNull(allocations);
        Set<AllocationCategory> categories = EnumSet.noneOf(AllocationCategory.class);
        BigDecimal ratioTotal = BigDecimal.ZERO;
        long amountTotal = 0L;

        for (ScenarioAllocation allocation : allocations) {
            if (!categories.add(allocation.getCategory())) {
                throw new IllegalArgumentException("배분 카테고리는 중복될 수 없습니다.");
            }
            if (allocation.getRatio().compareTo(MINIMUM_RATIO) < 0) {
                throw new IllegalArgumentException("각 카테고리 비율은 5% 이상이어야 합니다.");
            }
            ratioTotal = ratioTotal.add(allocation.getRatio());
            amountTotal = Math.addExact(amountTotal, allocation.getAmount());
        }

        if (!categories.equals(EnumSet.allOf(AllocationCategory.class))) {
            throw new IllegalArgumentException("모든 배분 카테고리가 필요합니다.");
        }
        if (ratioTotal.compareTo(TOTAL_RATIO) != 0) {
            throw new IllegalArgumentException("배분 비율 합계는 100%여야 합니다.");
        }
        if (amountTotal != expectedTotalAmount) {
            throw new IllegalArgumentException("배분 금액 합계는 대출금액과 같아야 합니다.");
        }
    }

    private void requireNotEmpty(List<?> values, String message) {
        if (Objects.requireNonNull(values).isEmpty()) {
            throw new IllegalArgumentException(message);
        }
    }

    public List<ScenarioAllocation> getAllocations() {
        return List.copyOf(allocations);
    }

    public List<ScenarioDraftReason> getDraftReasons() {
        return List.copyOf(draftReasons);
    }

    public List<String> getTargetMetrics() {
        return List.copyOf(targetMetrics);
    }
}
