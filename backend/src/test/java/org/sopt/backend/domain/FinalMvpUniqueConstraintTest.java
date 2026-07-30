// 최종 MVP에서 시뮬레이션별 단일 기록을 보장하는 데이터베이스 제약조건 테스트
package org.sopt.backend.domain;

import static org.junit.jupiter.api.Assertions.assertThrows;

import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.Set;
import org.hibernate.exception.ConstraintViolationException;
import org.junit.jupiter.api.Test;
import org.sopt.backend.domain.business.Business;
import org.sopt.backend.domain.business.BusinessSnapshot;
import org.sopt.backend.domain.business.PublicDataSnapshot;
import org.sopt.backend.domain.dataset.Dataset;
import org.sopt.backend.domain.diagnosis.Diagnosis;
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
import org.sopt.backend.domain.simulation.ScenarioFinancialResult;
import org.sopt.backend.domain.simulation.Simulation;
import org.sopt.backend.domain.source.DataSourceType;
import org.sopt.backend.domain.user.User;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.transaction.annotation.Transactional;

@SpringBootTest
@Transactional
class FinalMvpUniqueConstraintTest {

    @PersistenceContext
    private EntityManager entityManager;

    @Test
    void 시뮬레이션마다_선택은_하나만_저장할_수_있다() {
        Fixture fixture = persistFixture("selection@example.com");

        assertThrows(
                ConstraintViolationException.class,
                () -> {
                    entityManager.persist(ScenarioSelection.create(
                            fixture.simulation(),
                            fixture.scenarioA()
                    ));
                    entityManager.flush();
                }
        );
    }

    @Test
    void 시뮬레이션마다_집행은_하나만_저장할_수_있다() {
        Fixture fixture = persistFixture("execution@example.com");
        entityManager.persist(createExecution(fixture));
        entityManager.flush();

        assertThrows(
                ConstraintViolationException.class,
                () -> {
                    entityManager.persist(createExecution(fixture));
                    entityManager.flush();
                }
        );
    }

    @Test
    void 시뮬레이션마다_관측_데이터는_하나만_저장할_수_있다() {
        Fixture fixture = persistFixture("outcome-data@example.com");
        BusinessSnapshot latestSnapshot = persistLatestSnapshot(fixture);
        entityManager.persist(createOutcomeData(fixture, latestSnapshot));
        entityManager.flush();

        assertThrows(
                ConstraintViolationException.class,
                () -> {
                    entityManager.persist(createOutcomeData(fixture, latestSnapshot));
                    entityManager.flush();
                }
        );
    }

    @Test
    void 시뮬레이션마다_결과_비교는_하나만_저장할_수_있다() {
        Fixture fixture = persistFixture("comparison@example.com");
        BusinessSnapshot latestSnapshot = persistLatestSnapshot(fixture);
        Execution execution = createExecution(fixture);
        OutcomeData outcomeData = createOutcomeData(fixture, latestSnapshot);
        entityManager.persist(execution);
        entityManager.persist(outcomeData);
        entityManager.persist(createComparison(
                fixture,
                execution,
                outcomeData,
                latestSnapshot
        ));
        entityManager.flush();

        assertThrows(
                ConstraintViolationException.class,
                () -> {
                    entityManager.persist(createComparison(
                            fixture,
                            execution,
                            outcomeData,
                            latestSnapshot
                    ));
                    entityManager.flush();
                }
        );
    }

    private Fixture persistFixture(String email) {
        User user = User.create(email, "테스트 사용자");
        Business business = Business.create(
                user,
                "테스트 카페",
                "서울특별시 중구",
                "CAFE_BAKERY",
                "OFFICE",
                "OVER_3_YEARS",
                "SEAT_AND_TAKEOUT",
                2,
                "TEN_TO_TWENTY_MILLION",
                Set.of("OFFLINE"),
                null,
                null,
                null,
                null
        );
        Dataset dataset = Dataset.create(business, "dataset-v1");
        BusinessSnapshot baselineSnapshot = BusinessSnapshot.create(
                business,
                dataset,
                LocalDate.of(2026, 7, 1),
                "snapshot-v1",
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
                "public-v1",
                "서울특별시 중구"
        );
        Diagnosis diagnosis = Diagnosis.start(
                business,
                dataset,
                baselineSnapshot,
                publicDataSnapshot,
                "diagnosis-v1",
                "benchmark-v1"
        );
        diagnosis.complete(List.of(), List.of());
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
                "allocation-v1",
                "calculation-v1",
                "prompt-v1",
                LocalDate.of(2026, 6, 30)
        );
        Scenario scenarioA = addScenario(simulation, ScenarioCode.A);
        addScenario(simulation, ScenarioCode.B);
        addScenario(simulation, ScenarioCode.C);
        ScenarioSelection selection = ScenarioSelection.create(
                simulation,
                scenarioA
        );

        entityManager.persist(user);
        entityManager.persist(business);
        entityManager.persist(dataset);
        entityManager.persist(baselineSnapshot);
        entityManager.persist(publicDataSnapshot);
        entityManager.persist(diagnosis);
        entityManager.persist(simulation);
        entityManager.persist(selection);
        entityManager.flush();

        return new Fixture(business, dataset, simulation, scenarioA, selection);
    }

    private Scenario addScenario(Simulation simulation, ScenarioCode code) {
        return simulation.addScenario(
                code,
                "EVEN_DISTRIBUTION",
                code.name() + " 시나리오",
                List.of(
                        allocation(AllocationCategory.MARKETING_ONLINE),
                        allocation(AllocationCategory.EQUIPMENT_INTERIOR),
                        allocation(AllocationCategory.LABOR),
                        allocation(AllocationCategory.INVENTORY)
                ),
                List.of(new org.sopt.backend.domain.simulation.ScenarioDraftReason(
                        "TIME_OF_DAY_WEAKNESS",
                        AllocationCategory.MARKETING_ONLINE,
                        "진단 병목에 대응하는 방향입니다."
                )),
                ScenarioFinancialResult.create(
                        446_204L,
                        0L,
                        100_000L,
                        0L,
                        0,
                        null,
                        "UNAVAILABLE",
                        "검증된 추가 순현금 가정이 없습니다.",
                        RiskLevel.LOW,
                        List.of("현재 상태 유지 시 잔여 현금이 양수입니다.")
                ),
                List.of("MONTHLY_NET_SALES")
        );
    }

    private ScenarioAllocation allocation(AllocationCategory category) {
        return ScenarioAllocation.create(
                category,
                new BigDecimal("0.25"),
                3_750_000L
        );
    }

    private Execution createExecution(Fixture fixture) {
        return Execution.create(
                fixture.simulation(),
                fixture.selection(),
                ExecutionType.MOCK,
                LocalDate.of(2026, 8, 1),
                List.of(
                        ExecutionAllocation.create(
                                AllocationCategory.MARKETING_ONLINE,
                                3_750_000L
                        ),
                        ExecutionAllocation.create(
                                AllocationCategory.EQUIPMENT_INTERIOR,
                                3_750_000L
                        ),
                        ExecutionAllocation.create(
                                AllocationCategory.LABOR,
                                3_750_000L
                        ),
                        ExecutionAllocation.create(
                                AllocationCategory.INVENTORY,
                                3_750_000L
                        )
                ),
                0L
        );
    }

    private BusinessSnapshot persistLatestSnapshot(Fixture fixture) {
        Dataset outcomeDataset = Dataset.create(
                fixture.business(),
                "outcome-dataset-v1"
        );
        entityManager.persist(outcomeDataset);
        BusinessSnapshot latestSnapshot = BusinessSnapshot.create(
                fixture.business(),
                outcomeDataset,
                LocalDate.of(2026, 10, 31),
                "snapshot-v2",
                19_000_000L,
                16_000_000L,
                500_000L,
                new BigDecimal("0.43"),
                15_200L,
                1_250,
                new BigDecimal("0.20"),
                2,
                DataSourceType.CALCULATED
        );
        entityManager.persist(latestSnapshot);
        return latestSnapshot;
    }

    private OutcomeData createOutcomeData(
            Fixture fixture,
            BusinessSnapshot latestSnapshot
    ) {
        return OutcomeData.create(
                fixture.simulation(),
                latestSnapshot.getDataset(),
                latestSnapshot,
                DataSourceType.SYNTHETIC_SALES,
                LocalDate.of(2026, 10, 31),
                OutcomeDataStatus.READY
        );
    }

    private OutcomeComparison createComparison(
            Fixture fixture,
            Execution execution,
            OutcomeData outcomeData,
            BusinessSnapshot latestSnapshot
    ) {
        return OutcomeComparison.complete(
                fixture.simulation(),
                execution,
                outcomeData,
                List.of(new ComparisonRow(
                        "BREAK_EVEN_ADDITIONAL_REVENUE",
                        "월 추가 매출 0원 이상",
                        "월 추가 매출 1원",
                        "1원",
                        ComparisonResultStatus.CONDITION_MET,
                        null
                )),
                ReassessmentSnapshot.create(
                        latestSnapshot,
                        Set.of(),
                        Set.of(),
                        Set.of()
                )
        );
    }

    private record Fixture(
            Business business,
            Dataset dataset,
            Simulation simulation,
            Scenario scenarioA,
            ScenarioSelection selection
    ) {
    }
}
