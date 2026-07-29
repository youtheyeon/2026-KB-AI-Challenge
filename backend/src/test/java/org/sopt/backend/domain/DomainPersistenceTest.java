// 전체 도메인 그래프와 데이터베이스 제약조건의 영속성 매핑을 검증하는 테스트
package org.sopt.backend.domain;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Set;
import org.hibernate.exception.ConstraintViolationException;
import org.junit.jupiter.api.Test;
import org.sopt.backend.domain.business.Business;
import org.sopt.backend.domain.business.Industry;
import org.sopt.backend.domain.business.SalesChannel;
import org.sopt.backend.domain.dataset.Dataset;
import org.sopt.backend.domain.dataset.DatasetFileType;
import org.sopt.backend.domain.diagnosis.ActivityMetrics;
import org.sopt.backend.domain.diagnosis.Bottleneck;
import org.sopt.backend.domain.diagnosis.CommercialMetrics;
import org.sopt.backend.domain.diagnosis.Diagnosis;
import org.sopt.backend.domain.diagnosis.FinancialMetrics;
import org.sopt.backend.domain.execution.Execution;
import org.sopt.backend.domain.execution.ExecutionItem;
import org.sopt.backend.domain.execution.ExecutionMode;
import org.sopt.backend.domain.outcome.ComparisonRow;
import org.sopt.backend.domain.outcome.Outcome;
import org.sopt.backend.domain.outcome.OutcomeData;
import org.sopt.backend.domain.outcome.OutcomeDataStatus;
import org.sopt.backend.domain.outcome.OutcomeMetrics;
import org.sopt.backend.domain.outcome.OutcomeReevaluation;
import org.sopt.backend.domain.outcome.OutcomeSourceType;
import org.sopt.backend.domain.outcome.OutcomeSummary;
import org.sopt.backend.domain.outcome.OutcomeTrends;
import org.sopt.backend.domain.selection.PlanSelection;
import org.sopt.backend.domain.simulation.AllocationItem;
import org.sopt.backend.domain.simulation.AllocationPlan;
import org.sopt.backend.domain.simulation.LoanCondition;
import org.sopt.backend.domain.simulation.PlanCode;
import org.sopt.backend.domain.simulation.RepaymentType;
import org.sopt.backend.domain.simulation.Simulation;
import org.sopt.backend.domain.user.User;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.transaction.annotation.Transactional;

@SpringBootTest
@Transactional
class DomainPersistenceTest {

    @PersistenceContext
    private EntityManager entityManager;

    @Test
    void 전체_도메인_그래프를_저장하고_조회한다() {
        User user = User.create("owner@example.com", "홍길동");
        Business business = Business.create(
                user,
                "마포 한식당",
                "서울 마포구",
                Industry.RESTAURANT,
                2,
                Set.of(SalesChannel.OFFLINE, SalesChannel.DELIVERY_PLATFORM)
        );
        Dataset dataset = Dataset.create(business);
        dataset.addFile(DatasetFileType.SALES, "sales.xlsx");
        dataset.addFile(DatasetFileType.COST, "cost.xlsx");
        dataset.addAutoMapping(
                DatasetFileType.SALES,
                "결제금액",
                "salesAmount",
                new BigDecimal("0.93")
        );
        dataset.confirmMappings(LocalDateTime.of(2026, 7, 29, 3, 25));

        Diagnosis diagnosis = Diagnosis.start(business, dataset);
        diagnosis.complete(
                new FinancialMetrics(
                        30_000_000L,
                        new BigDecimal("11"),
                        new BigDecimal("40"),
                        1_800_000L
                ),
                new ActivityMetrics(420, new BigDecimal("9"), 2),
                new CommercialMetrics(
                        new BigDecimal("3.2"),
                        new BigDecimal("-8")
                ),
                List.of(
                        new Bottleneck(
                                "CHANNEL_CONCENTRATION",
                                "판매 채널 편중",
                                "HIGH",
                                "MEDIUM",
                                "온라인 주문 비중 9%, 비교군 28%.",
                                null
                        ),
                        new Bottleneck(
                                "MATERIAL_COST",
                                "원가율 상승",
                                "MEDIUM",
                                "HIGH",
                                "재료비 비중 40%, 비교군 34%.",
                                null
                        )
                )
        );

        Simulation simulation = Simulation.create(
                business,
                diagnosis,
                new LoanCondition(
                        30_000_000L,
                        5_000_000L,
                        0L,
                        new BigDecimal("4.5"),
                        36,
                        0,
                        RepaymentType.EQUAL_PAYMENT,
                        890_000L
                ),
                3
        );
        simulation.addPlan(
                PlanCode.A,
                "고객 수요 확대형",
                "광고·마케팅 + 온라인 채널 구축",
                30_000_000L,
                List.of(new AllocationItem(
                        "SNS·온라인 광고",
                        30_000_000L,
                        "RECURRING"
                ))
        );
        AllocationPlan selectedPlan = simulation.addPlan(
                PlanCode.B,
                "운영 효율 개선형",
                "주방 설비 교체와 자동화",
                30_000_000L,
                List.of(new AllocationItem(
                        "주방 설비 교체",
                        30_000_000L,
                        "ONE_TIME"
                ))
        );
        simulation.addPlan(
                PlanCode.C,
                "혼합형",
                "채널 확장과 설비 개선",
                30_000_000L,
                List.of()
        );

        PlanSelection selection = PlanSelection.create(
                simulation,
                selectedPlan,
                "설비 교체 중심으로 집행",
                LocalDate.of(2026, 10, 29)
        );
        Execution execution = Execution.create(
                simulation,
                ExecutionMode.CUSTOM,
                LocalDate.of(2026, 8, 1),
                List.of(
                        new ExecutionItem("주방 설비 교체", 17_000_000L),
                        new ExecutionItem("마케팅", 5_000_000L),
                        new ExecutionItem("운영자금", 8_000_000L)
                ),
                0L
        );
        OutcomeData outcomeData = OutcomeData.create(
                simulation,
                OutcomeSourceType.MANUAL_INPUT,
                null,
                new OutcomeMetrics(
                        32_100_000L,
                        3_520_000L,
                        new BigDecimal("13"),
                        1_980_000L
                ),
                OutcomeDataStatus.READY
        );
        Outcome outcome = Outcome.complete(
                simulation,
                execution,
                outcomeData,
                new OutcomeSummary(
                        "ABOVE_EXPECTED",
                        "WITHIN_RANGE",
                        "BELOW_EXPECTED"
                ),
                new OutcomeTrends(
                        List.of(30_000_000L, 32_100_000L),
                        List.of(new BigDecimal("9"), new BigDecimal("13"))
                ),
                List.of(new ComparisonRow(
                        "매출 성장률",
                        "매출 상세분석",
                        "4~7%",
                        "+7.0%",
                        "상권 유동인구 +4%.",
                        "ABOVE_EXPECTED"
                )),
                new OutcomeReevaluation(
                        32_100_000L,
                        3_520_000L,
                        1_980_000L,
                        new BigDecimal("13")
                ),
                List.of(new Bottleneck(
                        null,
                        "원가율 상승",
                        null,
                        null,
                        null,
                        "원재료 가격 상승으로 원가율 목표를 달성하지 못했습니다."
                ))
        );

        entityManager.persist(user);
        entityManager.persist(business);
        entityManager.persist(dataset);
        entityManager.persist(diagnosis);
        entityManager.persist(simulation);
        entityManager.persist(selection);
        entityManager.persist(execution);
        entityManager.persist(outcomeData);
        entityManager.persist(outcome);
        entityManager.flush();

        Long outcomeId = outcome.getId();
        entityManager.clear();

        Outcome savedOutcome = entityManager.find(Outcome.class, outcomeId);

        assertNotNull(savedOutcome.getCreatedAt());
        assertEquals(3, savedOutcome.getSimulation().getPlans().size());
        assertEquals(3, savedOutcome.getExecution().getItems().size());
        assertEquals(
                List.of("판매 채널 편중", "원가율 상승"),
                savedOutcome.getSimulation()
                        .getDiagnosis()
                        .getBottlenecks()
                        .stream()
                        .map(Bottleneck::getTitle)
                        .toList()
        );
        assertEquals(
                List.of(30_000_000L, 32_100_000L),
                savedOutcome.getMonthlySalesAmounts()
        );
        assertEquals(1, savedOutcome.getComparisonRows().size());
        assertEquals("원가율 상승", savedOutcome.getNewBottlenecks().getFirst().getTitle());
        assertEquals(
                "CUSTOM",
                entityManager.createNativeQuery(
                        "SELECT execution_mode FROM executions WHERE id = :id",
                        String.class
                )
                        .setParameter("id", execution.getId())
                        .getSingleResult()
        );
    }

    @Test
    void 사용자_이메일은_중복될_수_없다() {
        entityManager.persist(User.create("owner@example.com", "홍길동"));
        entityManager.flush();

        assertThrows(
                ConstraintViolationException.class,
                () -> entityManager.persist(User.create("owner@example.com", "김국민"))
        );
    }

    @Test
    void 배분안_코드는_시뮬레이션_안에서_중복될_수_없다() {
        Simulation simulation = persistMinimalSimulation("plan");

        assertThrows(
                ConstraintViolationException.class,
                () -> entityManager.createNativeQuery("""
                                INSERT INTO allocation_plans (
                                    simulation_id,
                                    plan_code,
                                    plan_type,
                                    title,
                                    total_amount
                                ) VALUES (:simulationId, 'A', '중복 유형', '중복 안', 30000000)
                                """)
                        .setParameter("simulationId", simulation.getId())
                        .executeUpdate()
        );
    }

    @Test
    void 데이터셋의_파일_유형은_중복될_수_없다() {
        Dataset dataset = persistMinimalDataset("file");

        assertThrows(
                ConstraintViolationException.class,
                () -> entityManager.createNativeQuery("""
                                INSERT INTO dataset_files (
                                    dataset_id,
                                    file_type,
                                    file_name
                                ) VALUES (:datasetId, 'SALES', 'duplicate.xlsx')
                                """)
                        .setParameter("datasetId", dataset.getId())
                        .executeUpdate()
        );
    }

    @Test
    void 데이터셋의_원본_컬럼_매핑은_중복될_수_없다() {
        Dataset dataset = persistMinimalDataset("mapping");

        assertThrows(
                ConstraintViolationException.class,
                () -> entityManager.createNativeQuery("""
                                INSERT INTO column_mappings (
                                    dataset_id,
                                    file_type,
                                    source_column,
                                    target_field,
                                    confirmed
                                ) VALUES (
                                    :datasetId,
                                    'SALES',
                                    '결제금액',
                                    'duplicateTarget',
                                    false
                                )
                                """)
                        .setParameter("datasetId", dataset.getId())
                        .executeUpdate()
        );
    }

    @Test
    void 시뮬레이션은_A_B_C_배분안을_모두_가져야_저장할_수_있다() {
        User user = User.create("incomplete-plan@example.com", "홍길동");
        Business business = Business.create(
                user,
                "마포 한식당",
                "서울 마포구",
                Industry.RESTAURANT,
                null,
                Set.of(SalesChannel.OFFLINE)
        );
        Dataset dataset = Dataset.create(business);
        Diagnosis diagnosis = Diagnosis.start(business, dataset);
        Simulation simulation = Simulation.create(
                business,
                diagnosis,
                createLoanCondition(),
                3
        );
        simulation.addPlan(
                PlanCode.A,
                "고객 수요 확대형",
                "광고·마케팅 중심",
                30_000_000L,
                List.of()
        );

        entityManager.persist(user);
        entityManager.persist(business);
        entityManager.persist(dataset);
        entityManager.persist(diagnosis);

        assertThrows(IllegalStateException.class, () -> entityManager.persist(simulation));
    }

    @Test
    void 선택은_시뮬레이션마다_하나만_저장할_수_있다() {
        Simulation simulation = persistMinimalSimulation("selection");
        AllocationPlan selectedPlan = simulation.getPlans().getFirst();
        entityManager.persist(PlanSelection.create(
                simulation,
                selectedPlan,
                "첫 번째 선택",
                LocalDate.of(2026, 10, 29)
        ));
        entityManager.flush();

        assertThrows(
                ConstraintViolationException.class,
                () -> entityManager.persist(PlanSelection.create(
                        simulation,
                        selectedPlan,
                        "두 번째 선택",
                        LocalDate.of(2026, 10, 30)
                ))
        );
    }

    @Test
    void 집행은_시뮬레이션마다_하나만_저장할_수_있다() {
        Simulation simulation = persistMinimalSimulation("execution");
        entityManager.persist(createExecution(simulation));
        entityManager.flush();

        assertThrows(
                ConstraintViolationException.class,
                () -> entityManager.persist(createExecution(simulation))
        );
    }

    @Test
    void 결과_데이터는_시뮬레이션마다_하나만_저장할_수_있다() {
        Simulation simulation = persistMinimalSimulation("outcome-data");
        entityManager.persist(createOutcomeData(simulation));
        entityManager.flush();

        assertThrows(
                ConstraintViolationException.class,
                () -> entityManager.persist(createOutcomeData(simulation))
        );
    }

    @Test
    void 결과는_시뮬레이션마다_하나만_저장할_수_있다() {
        OutcomeFixture fixture = persistOutcomeFixture("outcome-simulation");

        assertThrows(
                ConstraintViolationException.class,
                () -> insertOutcome(
                        fixture.firstSimulation().getId(),
                        fixture.secondExecution().getId(),
                        fixture.secondOutcomeData().getId()
                )
        );
    }

    @Test
    void 결과에_사용한_집행은_다른_결과에서_재사용할_수_없다() {
        OutcomeFixture fixture = persistOutcomeFixture("outcome-execution");

        assertThrows(
                ConstraintViolationException.class,
                () -> insertOutcome(
                        fixture.secondSimulation().getId(),
                        fixture.firstExecution().getId(),
                        fixture.secondOutcomeData().getId()
                )
        );
    }

    @Test
    void 결과에_사용한_결과_데이터는_다른_결과에서_재사용할_수_없다() {
        OutcomeFixture fixture = persistOutcomeFixture("outcome-data-reuse");

        assertThrows(
                ConstraintViolationException.class,
                () -> insertOutcome(
                        fixture.secondSimulation().getId(),
                        fixture.secondExecution().getId(),
                        fixture.firstOutcomeData().getId()
                )
        );
    }

    private Dataset persistMinimalDataset(String emailPrefix) {
        User user = User.create(emailPrefix + "@example.com", "홍길동");
        Business business = Business.create(
                user,
                "마포 한식당",
                "서울 마포구",
                Industry.RESTAURANT,
                null,
                Set.of(SalesChannel.OFFLINE)
        );
        Dataset dataset = Dataset.create(business);
        dataset.addFile(DatasetFileType.SALES, "sales.xlsx");
        dataset.addAutoMapping(
                DatasetFileType.SALES,
                "결제금액",
                "salesAmount",
                null
        );

        entityManager.persist(user);
        entityManager.persist(business);
        entityManager.persist(dataset);
        entityManager.flush();
        return dataset;
    }

    private Simulation persistMinimalSimulation(String emailPrefix) {
        User user = User.create(emailPrefix + "@example.com", "홍길동");
        Business business = Business.create(
                user,
                "마포 한식당",
                "서울 마포구",
                Industry.RESTAURANT,
                null,
                Set.of(SalesChannel.OFFLINE)
        );
        Dataset dataset = Dataset.create(business);
        Diagnosis diagnosis = Diagnosis.start(business, dataset);
        Simulation simulation = Simulation.create(
                business,
                diagnosis,
                createLoanCondition(),
                3
        );
        simulation.addPlan(
                PlanCode.A,
                "고객 수요 확대형",
                "광고·마케팅 중심",
                30_000_000L,
                List.of()
        );
        simulation.addPlan(
                PlanCode.B,
                "운영 효율 개선형",
                "설비 개선 중심",
                30_000_000L,
                List.of()
        );
        simulation.addPlan(
                PlanCode.C,
                "혼합형",
                "채널과 설비 개선",
                30_000_000L,
                List.of()
        );

        entityManager.persist(user);
        entityManager.persist(business);
        entityManager.persist(dataset);
        entityManager.persist(diagnosis);
        entityManager.persist(simulation);
        entityManager.flush();
        return simulation;
    }

    private LoanCondition createLoanCondition() {
        return new LoanCondition(
                30_000_000L,
                null,
                null,
                new BigDecimal("4.5"),
                36,
                null,
                RepaymentType.EQUAL_PAYMENT,
                890_000L
        );
    }

    private Execution createExecution(Simulation simulation) {
        return Execution.create(
                simulation,
                ExecutionMode.SAME_AS_A,
                LocalDate.of(2026, 8, 1),
                List.of(),
                0L
        );
    }

    private OutcomeData createOutcomeData(Simulation simulation) {
        return OutcomeData.create(
                simulation,
                OutcomeSourceType.MANUAL_INPUT,
                null,
                null,
                OutcomeDataStatus.READY
        );
    }

    private Outcome createOutcome(
            Simulation simulation,
            Execution execution,
            OutcomeData outcomeData
    ) {
        return Outcome.complete(
                simulation,
                execution,
                outcomeData,
                new OutcomeSummary(null, null, null),
                new OutcomeTrends(List.of(), List.of()),
                List.of(),
                new OutcomeReevaluation(null, null, null, null),
                List.of()
        );
    }

    private OutcomeFixture persistOutcomeFixture(String emailPrefix) {
        Simulation firstSimulation = persistMinimalSimulation(emailPrefix + "-first");
        Simulation secondSimulation = persistMinimalSimulation(emailPrefix + "-second");
        Execution firstExecution = createExecution(firstSimulation);
        Execution secondExecution = createExecution(secondSimulation);
        OutcomeData firstOutcomeData = createOutcomeData(firstSimulation);
        OutcomeData secondOutcomeData = createOutcomeData(secondSimulation);

        entityManager.persist(firstExecution);
        entityManager.persist(secondExecution);
        entityManager.persist(firstOutcomeData);
        entityManager.persist(secondOutcomeData);
        entityManager.persist(createOutcome(
                firstSimulation,
                firstExecution,
                firstOutcomeData
        ));
        entityManager.flush();

        return new OutcomeFixture(
                firstSimulation,
                secondSimulation,
                firstExecution,
                secondExecution,
                firstOutcomeData,
                secondOutcomeData
        );
    }

    private void insertOutcome(
            Long simulationId,
            Long executionId,
            Long outcomeDataId
    ) {
        entityManager.createNativeQuery("""
                        INSERT INTO outcomes (
                            simulation_id,
                            execution_id,
                            outcome_data_id,
                            status,
                            created_at,
                            updated_at
                        ) VALUES (
                            :simulationId,
                            :executionId,
                            :outcomeDataId,
                            'COMPLETED',
                            CURRENT_TIMESTAMP,
                            CURRENT_TIMESTAMP
                        )
                        """)
                .setParameter("simulationId", simulationId)
                .setParameter("executionId", executionId)
                .setParameter("outcomeDataId", outcomeDataId)
                .executeUpdate();
    }

    private record OutcomeFixture(
            Simulation firstSimulation,
            Simulation secondSimulation,
            Execution firstExecution,
            Execution secondExecution,
            OutcomeData firstOutcomeData,
            OutcomeData secondOutcomeData
    ) {
    }
}
