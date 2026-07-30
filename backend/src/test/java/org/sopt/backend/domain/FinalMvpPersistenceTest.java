// 최종 MVP 전체 도메인 그래프와 데이터베이스 제약조건을 검증하는 영속성 테스트
package org.sopt.backend.domain;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalTime;
import java.util.List;
import java.util.Set;
import org.hibernate.exception.ConstraintViolationException;
import org.junit.jupiter.api.Test;
import org.sopt.backend.domain.business.Business;
import org.sopt.backend.domain.business.BusinessSnapshot;
import org.sopt.backend.domain.business.PublicDataSnapshot;
import org.sopt.backend.domain.dataset.Dataset;
import org.sopt.backend.domain.dataset.DatasetFile;
import org.sopt.backend.domain.dataset.DatasetFileType;
import org.sopt.backend.domain.dataset.DatasetFormat;
import org.sopt.backend.domain.dataset.ExpenseCategory;
import org.sopt.backend.domain.dataset.NormalizedExpense;
import org.sopt.backend.domain.dataset.NormalizedOnlineSale;
import org.sopt.backend.domain.dataset.NormalizedSale;
import org.sopt.backend.domain.dataset.OnlineSalesReconciliationType;
import org.sopt.backend.domain.diagnosis.Bottleneck;
import org.sopt.backend.domain.diagnosis.BottleneckSeverity;
import org.sopt.backend.domain.diagnosis.Diagnosis;
import org.sopt.backend.domain.diagnosis.DiagnosisMetric;
import org.sopt.backend.domain.execution.Execution;
import org.sopt.backend.domain.execution.ExecutionAllocation;
import org.sopt.backend.domain.execution.ExecutionType;
import org.sopt.backend.domain.outcome.ComparisonRow;
import org.sopt.backend.domain.outcome.ComparisonResultStatus;
import org.sopt.backend.domain.outcome.OutcomeComparison;
import org.sopt.backend.domain.outcome.OutcomeData;
import org.sopt.backend.domain.outcome.OutcomeDataStatus;
import org.sopt.backend.domain.outcome.ReassessmentSnapshot;
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
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.transaction.annotation.Transactional;

@SpringBootTest
@Transactional
class FinalMvpPersistenceTest {

    @PersistenceContext
    private EntityManager entityManager;

    @Test
    void 최종_MVP_전체_그래프를_저장하고_재조회한다() {
        User user = User.create("owner@example.com", "홍길동");
        Business business = createBusiness(user);
        Dataset dataset = Dataset.create(business, "dataset-v2");
        DatasetFile salesFile = dataset.addFile(
                DatasetFileType.SALES,
                "sales.xlsx",
                DatasetFormat.EASYPOS_SALES,
                DataSourceType.SYNTHETIC_SALES
        );
        DatasetFile expenseFile = dataset.addFile(
                DatasetFileType.EXPENSE,
                "expense.xlsx",
                DatasetFormat.EASYSHOP_EXPENSE_LEDGER,
                DataSourceType.SYNTHETIC_EXPENSE
        );
        DatasetFile onlineFile = dataset.addFile(
                DatasetFileType.ONLINE_SALES,
                "online.xlsx",
                DatasetFormat.EASYSHOP_ONLINE_SALES,
                DataSourceType.SYNTHETIC_ONLINE_SALES
        );
        dataset.startParsing();
        dataset.startNormalizing();
        dataset.markReady();

        entityManager.persist(user);
        entityManager.persist(business);
        entityManager.persist(dataset);
        entityManager.persist(NormalizedSale.create(
                dataset,
                salesFile,
                LocalDate.of(2026, 7, 1),
                LocalTime.of(18, 30),
                "R-001",
                "POS-1",
                20_000L,
                1_000L,
                0L,
                19_000L,
                "CARD",
                "COMPLETED"
        ));
        entityManager.persist(NormalizedExpense.create(
                dataset,
                expenseFile,
                LocalDate.of(2026, 7, 1),
                "원재료상사",
                "원두 구입",
                ExpenseCategory.MATERIAL,
                90_000L,
                9_000L,
                0L,
                99_000L,
                "CARD",
                "CARD_RECEIPT"
        ));
        entityManager.persist(NormalizedOnlineSale.create(
                dataset,
                onlineFile,
                LocalDate.of(2026, 7, 1),
                "DELIVERY_PLATFORM",
                "DELIVERY",
                3,
                60_000L,
                3_000L,
                0L,
                57_000L,
                6_000L,
                1_500L,
                2_000L,
                47_500L,
                LocalDate.of(2026, 7, 3),
                "COMPLETED",
                OnlineSalesReconciliationType.INCLUDED_IN_POS_TOTAL
        ));

        BusinessSnapshot baselineSnapshot = createSnapshot(
                business,
                dataset,
                LocalDate.of(2026, 7, 1),
                "business-snapshot-v1",
                18_000_000L
        );
        PublicDataSnapshot publicDataSnapshot = PublicDataSnapshot.create(
                business,
                LocalDate.of(2026, 6, 30),
                "서울시 상권분석서비스",
                "public-data-2026-06",
                "서울특별시 서대문구 연희동"
        );
        entityManager.persist(baselineSnapshot);
        entityManager.persist(publicDataSnapshot);

        Diagnosis diagnosis = Diagnosis.start(
                business,
                dataset,
                baselineSnapshot,
                publicDataSnapshot,
                "diagnosis-v3",
                "benchmark-2026-07-v2"
        );
        diagnosis.complete(
                List.of(new DiagnosisMetric(
                        "EVENING_SALES_SHARE",
                        new BigDecimal("0.12"),
                        DataSourceType.SYNTHETIC_SALES,
                        new BigDecimal("0.24"),
                        DataSourceType.BENCHMARK,
                        new BigDecimal("-0.12"),
                        "RATIO",
                        "benchmark-2026-07-v2"
                )),
                List.of(Bottleneck.create(
                        "TIME_OF_DAY_WEAKNESS",
                        "저녁 시간대 매출 비중이 비교값보다 낮습니다.",
                        BottleneckSeverity.CLEAR,
                        DataSourceType.BENCHMARK,
                        "서울시 카페 시간대별 추정매출",
                        Set.of(AllocationCategory.MARKETING_ONLINE)
                ))
        );
        entityManager.persist(diagnosis);

        Simulation simulation = Simulation.create(
                business,
                dataset,
                diagnosis,
                baselineSnapshot,
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
        Scenario scenarioA = addScenario(
                simulation,
                ScenarioCode.A,
                "BOTTLENECK_FOCUSED",
                List.of("EVENING_REVENUE", "ORDER_COUNT")
        );
        addScenario(
                simulation,
                ScenarioCode.B,
                "DIAGNOSIS_PROPORTIONAL",
                List.of("MATERIAL_COST_RATE")
        );
        addScenario(
                simulation,
                ScenarioCode.C,
                "EVEN_DISTRIBUTION",
                List.of("MONTHLY_NET_SALES")
        );
        entityManager.persist(simulation);

        ScenarioSelection selection = ScenarioSelection.create(simulation, scenarioA);
        Execution execution = Execution.create(
                simulation,
                selection,
                ExecutionType.MOCK,
                LocalDate.of(2026, 8, 1),
                executionAllocations(),
                0L
        );
        entityManager.persist(selection);
        entityManager.persist(execution);

        Dataset outcomeDataset = Dataset.create(business, "outcome-dataset-v1");
        entityManager.persist(outcomeDataset);
        BusinessSnapshot latestSnapshot = createSnapshot(
                business,
                outcomeDataset,
                LocalDate.of(2026, 10, 31),
                "business-snapshot-v2",
                19_520_000L
        );
        entityManager.persist(latestSnapshot);
        OutcomeData outcomeData = OutcomeData.create(
                simulation,
                outcomeDataset,
                latestSnapshot,
                DataSourceType.SYNTHETIC_SALES,
                LocalDate.of(2026, 10, 31),
                OutcomeDataStatus.READY
        );
        entityManager.persist(outcomeData);
        OutcomeComparison comparison = OutcomeComparison.complete(
                simulation,
                execution,
                outcomeData,
                List.of(new ComparisonRow(
                        "BREAK_EVEN_ADDITIONAL_REVENUE",
                        "월 추가 매출 1380000원 이상",
                        "월 추가 매출 1520000원",
                        "140000원",
                        ComparisonResultStatus.CONDITION_MET,
                        "계절성과 상권 변화가 함께 영향을 줄 수 있습니다."
                )),
                ReassessmentSnapshot.create(
                        latestSnapshot,
                        Set.of("TIME_OF_DAY_WEAKNESS"),
                        Set.of("HIGH_MATERIAL_COST"),
                        Set.of("PLATFORM_FEE_BURDEN")
                )
        );
        entityManager.persist(comparison);
        entityManager.flush();

        Long comparisonId = comparison.getId();
        entityManager.clear();

        OutcomeComparison saved = entityManager.find(
                OutcomeComparison.class,
                comparisonId
        );

        assertNotNull(saved.getCreatedAt());
        assertEquals(3, saved.getSimulation().getScenarios().size());
        assertEquals(4, saved.getExecution().getAllocations().size());
        assertEquals(
                "월 추가 매출 1380000원 이상",
                saved.getComparisonRows().getFirst().getTargetCondition()
        );
        assertEquals(
                Set.of("TIME_OF_DAY_WEAKNESS"),
                saved.getReassessmentSnapshot().getResolvedBottleneckTypes()
        );
        assertEquals(
                "allocation-v4",
                saved.getSimulation().getAllocationGeneratorVersion()
        );
    }

    @Test
    void 사용자_이메일은_중복될_수_없다() {
        entityManager.persist(User.create("duplicate@example.com", "홍길동"));
        entityManager.flush();

        assertThrows(
                ConstraintViolationException.class,
                () -> entityManager.persist(User.create(
                        "duplicate@example.com",
                        "김국민"
                ))
        );
    }

    private Business createBusiness(User user) {
        return Business.create(
                user,
                "연희동 Y카페",
                "서울특별시 서대문구 연희동",
                "CAFE_BAKERY",
                "UNIVERSITY",
                "OVER_3_YEARS",
                "SEAT_AND_TAKEOUT",
                2,
                "TEN_TO_TWENTY_MILLION",
                Set.of("OFFLINE", "TAKEOUT"),
                18,
                new BigDecimal("7.5"),
                new BigDecimal("0.82"),
                null
        );
    }

    private BusinessSnapshot createSnapshot(
            Business business,
            Dataset dataset,
            LocalDate referenceDate,
            String version,
            Long monthlySales
    ) {
        return BusinessSnapshot.create(
                business,
                dataset,
                referenceDate,
                version,
                monthlySales,
                15_500_000L,
                500_000L,
                new BigDecimal("0.42"),
                15_000L,
                1_200,
                new BigDecimal("0.18"),
                2,
                DataSourceType.CALCULATED
        );
    }

    private Scenario addScenario(
            Simulation simulation,
            ScenarioCode code,
            String strategyType,
            List<String> targetMetrics
    ) {
        return simulation.addScenario(
                code,
                strategyType,
                code.name() + " 시나리오",
                scenarioAllocations(),
                List.of(new ScenarioDraftReason(
                        "TIME_OF_DAY_WEAKNESS",
                        AllocationCategory.MARKETING_ONLINE,
                        "진단 병목에 대응하는 방향입니다."
                )),
                ScenarioFinancialResult.create(
                        446_204L,
                        290_000L,
                        -154_000L,
                        1_380_000L,
                        184,
                        null,
                        "UNAVAILABLE",
                        "검증된 추가 순현금 가정이 없습니다.",
                        RiskLevel.MEDIUM,
                        List.of("현재 상태 유지 시 월 잔여 현금이 음수입니다.")
                ),
                targetMetrics
        );
    }

    private List<ScenarioAllocation> scenarioAllocations() {
        return List.of(
                ScenarioAllocation.create(
                        AllocationCategory.MARKETING_ONLINE,
                        new BigDecimal("0.25"),
                        3_750_000L
                ),
                ScenarioAllocation.create(
                        AllocationCategory.EQUIPMENT_INTERIOR,
                        new BigDecimal("0.25"),
                        3_750_000L
                ),
                ScenarioAllocation.create(
                        AllocationCategory.LABOR,
                        new BigDecimal("0.25"),
                        3_750_000L
                ),
                ScenarioAllocation.create(
                        AllocationCategory.INVENTORY,
                        new BigDecimal("0.25"),
                        3_750_000L
                )
        );
    }

    private List<ExecutionAllocation> executionAllocations() {
        return List.of(
                ExecutionAllocation.create(
                        AllocationCategory.MARKETING_ONLINE,
                        6_000_000L
                ),
                ExecutionAllocation.create(
                        AllocationCategory.EQUIPMENT_INTERIOR,
                        4_000_000L
                ),
                ExecutionAllocation.create(AllocationCategory.LABOR, 3_000_000L),
                ExecutionAllocation.create(AllocationCategory.INVENTORY, 2_000_000L)
        );
    }
}
