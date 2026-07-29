// 시뮬레이션 생성부터 집행 후 결과 비교까지의 도메인 동작을 검증하는 테스트
package org.sopt.backend.domain;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.sopt.backend.domain.business.Business;
import org.sopt.backend.domain.business.Industry;
import org.sopt.backend.domain.business.SalesChannel;
import org.sopt.backend.domain.dataset.Dataset;
import org.sopt.backend.domain.diagnosis.Bottleneck;
import org.sopt.backend.domain.diagnosis.Diagnosis;
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
import org.sopt.backend.domain.outcome.OutcomeStatus;
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

class SimulationOutcomeDomainTest {

    @Test
    void 선택과_집행과_결과를_하나의_시뮬레이션에_연결한다() {
        Business business = createBusiness();
        Diagnosis diagnosis = Diagnosis.start(business, Dataset.create(business));
        LoanCondition loanCondition = new LoanCondition(
                30_000_000L,
                5_000_000L,
                0L,
                new BigDecimal("4.5"),
                36,
                0,
                RepaymentType.EQUAL_PAYMENT,
                890_000L
        );
        Simulation simulation = Simulation.create(
                business,
                diagnosis,
                loanCondition,
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
                List.of(new AllocationItem(
                        "복합 투자",
                        30_000_000L,
                        "MIXED"
                ))
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
        OutcomeMetrics outcomeMetrics = new OutcomeMetrics(
                32_100_000L,
                3_520_000L,
                new BigDecimal("13"),
                1_980_000L
        );
        OutcomeData outcomeData = OutcomeData.create(
                simulation,
                OutcomeSourceType.MANUAL_INPUT,
                null,
                outcomeMetrics,
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
                        List.of(30_000_000L, 30_500_000L, 32_000_000L, 34_000_000L),
                        List.of(
                                new BigDecimal("9"),
                                new BigDecimal("10"),
                                new BigDecimal("12"),
                                new BigDecimal("13")
                        )
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

        assertEquals(3, simulation.getPlans().size());
        assertEquals(PlanCode.B, selection.getSelectedPlan().getPlanCode());
        assertEquals(30_000_000L, execution.getTotalExecutedAmount());
        assertEquals(outcomeMetrics, outcomeData.getMetrics());
        assertEquals(OutcomeStatus.COMPLETED, outcome.getStatus());
        assertEquals(execution, outcome.getExecution());
        assertEquals(outcomeData, outcome.getOutcomeData());
        assertEquals(4, outcome.getMonthlySalesAmounts().size());
        assertEquals(1, outcome.getComparisonRows().size());
        assertEquals(1, outcome.getNewBottlenecks().size());
    }

    @Test
    void 같은_시뮬레이션에_동일한_배분안_코드를_추가할_수_없다() {
        Business business = createBusiness();
        Simulation simulation = Simulation.create(
                business,
                Diagnosis.start(business, Dataset.create(business)),
                new LoanCondition(
                        30_000_000L,
                        null,
                        null,
                        new BigDecimal("4.5"),
                        36,
                        null,
                        RepaymentType.EQUAL_PAYMENT,
                        890_000L
                ),
                3
        );
        simulation.addPlan(
                PlanCode.A,
                "고객 수요 확대형",
                "첫 번째 안",
                30_000_000L,
                List.of()
        );

        assertThrows(
                IllegalArgumentException.class,
                () -> simulation.addPlan(
                        PlanCode.A,
                        "고객 수요 확대형",
                        "중복 안",
                        30_000_000L,
                        List.of()
                )
        );
    }

    @Test
    void 맞춤_집행_금액과_미사용_금액은_대출금과_일치해야_한다() {
        Business business = createBusiness();
        Simulation simulation = Simulation.create(
                business,
                Diagnosis.start(business, Dataset.create(business)),
                new LoanCondition(
                        30_000_000L,
                        null,
                        null,
                        new BigDecimal("4.5"),
                        36,
                        null,
                        RepaymentType.EQUAL_PAYMENT,
                        890_000L
                ),
                3
        );

        assertThrows(
                IllegalArgumentException.class,
                () -> Execution.create(
                        simulation,
                        ExecutionMode.CUSTOM,
                        LocalDate.of(2026, 8, 1),
                        List.of(new ExecutionItem("설비", 10_000_000L)),
                        0L
                )
        );
    }

    private Business createBusiness() {
        return Business.create(
                User.create("owner@example.com", "홍길동"),
                "마포 한식당",
                "서울 마포구",
                Industry.RESTAURANT,
                2,
                Set.of(SalesChannel.OFFLINE)
        );
    }
}
