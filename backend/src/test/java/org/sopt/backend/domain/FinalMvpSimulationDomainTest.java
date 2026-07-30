// 최종 MVP의 고정 A·B·C 시나리오와 조건 계산 결과를 검증하는 테스트
package org.sopt.backend.domain;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.sopt.backend.domain.business.Business;
import org.sopt.backend.domain.business.BusinessSnapshot;
import org.sopt.backend.domain.business.PublicDataSnapshot;
import org.sopt.backend.domain.dataset.Dataset;
import org.sopt.backend.domain.diagnosis.Diagnosis;
import org.sopt.backend.domain.selection.ScenarioSelection;
import org.sopt.backend.domain.simulation.AllocationCategory;
import org.sopt.backend.domain.simulation.LoanCondition;
import org.sopt.backend.domain.simulation.RepaymentType;
import org.sopt.backend.domain.simulation.RiskLevel;
import org.sopt.backend.domain.simulation.Scenario;
import org.sopt.backend.domain.simulation.ScenarioAllocation;
import org.sopt.backend.domain.simulation.ScenarioCode;
import org.sopt.backend.domain.simulation.ScenarioDraftReason;
import org.sopt.backend.domain.simulation.ScenarioFinancialResult;
import org.sopt.backend.domain.simulation.Simulation;
import org.sopt.backend.domain.source.DataSourceType;
import org.sopt.backend.domain.user.User;

class FinalMvpSimulationDomainTest {

    @Test
    void 고정_A_B_C와_조건_계산_결과를_생성한다() {
        Simulation simulation = createSimulation();

        Scenario scenarioA = simulation.addScenario(
                ScenarioCode.A,
                "BOTTLENECK_FOCUSED",
                "병목 집중형",
                allocations("0.55", "0.25", "0.10", "0.10"),
                List.of(new ScenarioDraftReason(
                        "TIME_OF_DAY_WEAKNESS",
                        AllocationCategory.MARKETING_ONLINE,
                        "저녁 시간대 매출 비중 차이에 대응하는 방향입니다."
                )),
                financialResult(),
                List.of("EVENING_REVENUE", "ORDER_COUNT", "ONLINE_SALES_SHARE")
        );
        simulation.addScenario(
                ScenarioCode.B,
                "DIAGNOSIS_PROPORTIONAL",
                "진단 비례 대응형",
                allocations("0.35", "0.25", "0.25", "0.15"),
                List.of(),
                financialResult(),
                List.of("MATERIAL_COST_RATE")
        );
        simulation.addScenario(
                ScenarioCode.C,
                "EVEN_DISTRIBUTION",
                "균등 분산형",
                allocations("0.25", "0.25", "0.25", "0.25"),
                List.of(),
                financialResult(),
                List.of("MONTHLY_NET_SALES")
        );
        ScenarioSelection selection = ScenarioSelection.create(simulation, scenarioA);

        assertEquals(3, simulation.getScenarios().size());
        assertEquals("COMPLETED", simulation.getStatus());
        assertEquals(ScenarioCode.A, selection.getSelectedScenario().getScenarioCode());
        assertEquals(
                1_380_000L,
                scenarioA.getFinancialResult().getBreakEvenAdditionalRevenue()
        );
        assertEquals(
                DataSourceType.CALCULATED,
                scenarioA.getFinancialResult().getSourceType()
        );
        assertEquals("allocation-v4", simulation.getAllocationGeneratorVersion());
        assertEquals("prompt-v2", simulation.getPromptVersion());
    }

    @Test
    void 배분은_모든_카테고리를_최소_5퍼센트_포함해야_한다() {
        Simulation simulation = createSimulation();

        assertThrows(
                IllegalArgumentException.class,
                () -> simulation.addScenario(
                        ScenarioCode.A,
                        "BOTTLENECK_FOCUSED",
                        "잘못된 안",
                        allocations("0.04", "0.46", "0.25", "0.25"),
                        List.of(),
                        financialResult(),
                        List.of()
                )
        );
    }

    @Test
    void 배분_금액_합계는_대출금액과_일치해야_한다() {
        Simulation simulation = createSimulation();
        List<ScenarioAllocation> invalidAllocations = List.of(
                ScenarioAllocation.create(
                        AllocationCategory.MARKETING_ONLINE,
                        new BigDecimal("0.25"),
                        3_000_000L
                ),
                ScenarioAllocation.create(
                        AllocationCategory.EQUIPMENT_INTERIOR,
                        new BigDecimal("0.25"),
                        3_000_000L
                ),
                ScenarioAllocation.create(
                        AllocationCategory.LABOR,
                        new BigDecimal("0.25"),
                        3_000_000L
                ),
                ScenarioAllocation.create(
                        AllocationCategory.INVENTORY,
                        new BigDecimal("0.25"),
                        3_000_000L
                )
        );

        assertThrows(
                IllegalArgumentException.class,
                () -> simulation.addScenario(
                        ScenarioCode.A,
                        "BOTTLENECK_FOCUSED",
                        "금액 불일치 안",
                        invalidAllocations,
                        List.of(),
                        financialResult(),
                        List.of()
                )
        );
    }

    private Simulation createSimulation() {
        Business business = Business.create(
                User.create("owner@example.com", "홍길동"),
                "연희동 Y카페",
                "서울특별시 서대문구 연희동",
                "CAFE_BAKERY",
                "UNIVERSITY",
                "OVER_3_YEARS",
                "SEAT_AND_TAKEOUT",
                2,
                "TEN_TO_TWENTY_MILLION",
                Set.of("OFFLINE"),
                18,
                null,
                null,
                null
        );
        Dataset dataset = Dataset.create(business, "dataset-v2");
        BusinessSnapshot businessSnapshot = BusinessSnapshot.create(
                business,
                dataset,
                LocalDate.of(2026, 7, 1),
                "business-snapshot-v1",
                18_000_000L,
                15_500_000L,
                500_000L,
                new BigDecimal("0.42"),
                15_000L,
                1_200,
                new BigDecimal("0.18"),
                2,
                DataSourceType.CALCULATED
        );
        PublicDataSnapshot publicDataSnapshot = PublicDataSnapshot.create(
                business,
                LocalDate.of(2026, 6, 30),
                "서울시 상권분석서비스",
                "public-data-2026-06",
                "서울특별시 서대문구 연희동"
        );
        Diagnosis diagnosis = Diagnosis.start(
                business,
                dataset,
                businessSnapshot,
                publicDataSnapshot,
                "diagnosis-v3",
                "benchmark-2026-07-v2"
        );

        return Simulation.create(
                business,
                dataset,
                diagnosis,
                businessSnapshot,
                new LoanCondition(
                        15_000_000L,
                        new BigDecimal("0.045"),
                        36,
                        0,
                        RepaymentType.EQUAL_PAYMENT
                ),
                "allocation-v4",
                "calculation-v5",
                "prompt-v2",
                LocalDate.of(2026, 6, 30)
        );
    }

    private List<ScenarioAllocation> allocations(
            String marketingRatio,
            String equipmentRatio,
            String laborRatio,
            String inventoryRatio
    ) {
        return List.of(
                allocation(AllocationCategory.MARKETING_ONLINE, marketingRatio),
                allocation(AllocationCategory.EQUIPMENT_INTERIOR, equipmentRatio),
                allocation(AllocationCategory.LABOR, laborRatio),
                allocation(AllocationCategory.INVENTORY, inventoryRatio)
        );
    }

    private ScenarioAllocation allocation(
            AllocationCategory category,
            String ratio
    ) {
        BigDecimal decimalRatio = new BigDecimal(ratio);
        return ScenarioAllocation.create(
                category,
                decimalRatio,
                decimalRatio.multiply(new BigDecimal("15000000")).longValueExact()
        );
    }

    private ScenarioFinancialResult financialResult() {
        return ScenarioFinancialResult.create(
                446_204L,
                290_000L,
                -154_000L,
                1_380_000L,
                184,
                null,
                "UNAVAILABLE",
                "추가 순현금에 대한 검증된 가정이 없습니다.",
                RiskLevel.MEDIUM,
                List.of(
                        "현재 상태 유지 시 월 잔여 현금이 음수입니다.",
                        "추가 매출이 있어야 현금흐름이 0 이상이 됩니다."
                )
        );
    }
}
