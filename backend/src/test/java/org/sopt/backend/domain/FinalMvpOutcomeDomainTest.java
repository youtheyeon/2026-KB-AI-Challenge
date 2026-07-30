// 최종 MVP의 실제·Mock 집행과 목표 조건 대비 관측 결과를 검증하는 테스트
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
import org.sopt.backend.domain.execution.Execution;
import org.sopt.backend.domain.execution.ExecutionAllocation;
import org.sopt.backend.domain.execution.ExecutionType;
import org.sopt.backend.domain.outcome.ComparisonRow;
import org.sopt.backend.domain.outcome.OutcomeComparison;
import org.sopt.backend.domain.outcome.OutcomeData;
import org.sopt.backend.domain.outcome.OutcomeDataStatus;
import org.sopt.backend.domain.outcome.OutcomeStatus;
import org.sopt.backend.domain.outcome.ReassessmentSnapshot;
import org.sopt.backend.domain.simulation.AllocationCategory;
import org.sopt.backend.domain.simulation.LoanCondition;
import org.sopt.backend.domain.simulation.RepaymentType;
import org.sopt.backend.domain.simulation.Simulation;
import org.sopt.backend.domain.source.DataSourceType;
import org.sopt.backend.domain.user.User;

class FinalMvpOutcomeDomainTest {

    @Test
    void Mock_집행과_목표_조건_대비_관측_결과를_저장한다() {
        Fixture fixture = createFixture();
        Execution execution = Execution.create(
                fixture.simulation(),
                ExecutionType.MOCK,
                LocalDate.of(2026, 8, 1),
                List.of(
                        ExecutionAllocation.create(
                                AllocationCategory.MARKETING_ONLINE,
                                6_000_000L
                        ),
                        ExecutionAllocation.create(
                                AllocationCategory.EQUIPMENT_INTERIOR,
                                4_000_000L
                        ),
                        ExecutionAllocation.create(
                                AllocationCategory.LABOR,
                                3_000_000L
                        ),
                        ExecutionAllocation.create(
                                AllocationCategory.INVENTORY,
                                2_000_000L
                        )
                ),
                0L
        );
        OutcomeData outcomeData = OutcomeData.create(
                fixture.simulation(),
                fixture.dataset(),
                fixture.latestSnapshot(),
                DataSourceType.SYNTHETIC_SALES,
                LocalDate.of(2026, 10, 31),
                OutcomeDataStatus.READY
        );
        ReassessmentSnapshot reassessment = ReassessmentSnapshot.create(
                fixture.latestSnapshot(),
                Set.of("TIME_OF_DAY_WEAKNESS"),
                Set.of("HIGH_MATERIAL_COST"),
                Set.of("PLATFORM_FEE_BURDEN")
        );
        OutcomeComparison comparison = OutcomeComparison.complete(
                fixture.simulation(),
                execution,
                outcomeData,
                List.of(new ComparisonRow(
                        "BREAK_EVEN_ADDITIONAL_REVENUE",
                        "월 추가 매출 1380000원 이상",
                        "월 추가 매출 1520000원",
                        "140000원",
                        "CONDITION_MET",
                        "계절성과 상권 변화가 함께 영향을 줄 수 있습니다."
                )),
                reassessment
        );

        assertEquals(ExecutionType.MOCK, execution.getExecutionType());
        assertEquals(15_000_000L, execution.getTotalExecutedAmount());
        assertEquals("월 추가 매출 1380000원 이상", comparison.getComparisonRows()
                .getFirst()
                .getTargetCondition());
        assertEquals("월 추가 매출 1520000원", comparison.getComparisonRows()
                .getFirst()
                .getObservedValue());
        assertEquals(OutcomeStatus.COMPLETED, comparison.getStatus());
        assertEquals(
                Set.of("TIME_OF_DAY_WEAKNESS"),
                comparison.getReassessmentSnapshot().getResolvedBottleneckTypes()
        );
        assertEquals(
                fixture.latestSnapshot(),
                outcomeData.getObservedBusinessSnapshot()
        );
    }

    @Test
    void 실제_집행_배분과_미사용_금액은_대출금액과_일치해야_한다() {
        Fixture fixture = createFixture();

        assertThrows(
                IllegalArgumentException.class,
                () -> Execution.create(
                        fixture.simulation(),
                        ExecutionType.CUSTOM,
                        LocalDate.of(2026, 8, 1),
                        List.of(ExecutionAllocation.create(
                                AllocationCategory.MARKETING_ONLINE,
                                10_000_000L
                        )),
                        0L
                )
        );
    }

    private Fixture createFixture() {
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
        BusinessSnapshot baselineSnapshot = BusinessSnapshot.create(
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
        BusinessSnapshot latestSnapshot = BusinessSnapshot.create(
                business,
                dataset,
                LocalDate.of(2026, 10, 31),
                "business-snapshot-v2",
                19_520_000L,
                16_100_000L,
                500_000L,
                new BigDecimal("0.43"),
                15_300L,
                1_276,
                new BigDecimal("0.22"),
                3,
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
                baselineSnapshot,
                publicDataSnapshot,
                "diagnosis-v3",
                "benchmark-2026-07-v2"
        );
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
        return new Fixture(simulation, dataset, latestSnapshot);
    }

    private record Fixture(
            Simulation simulation,
            Dataset dataset,
            BusinessSnapshot latestSnapshot
    ) {
    }
}
