// 매출 증가를 가정하지 않은 시나리오별 재무 조건 계산 결과를 저장하는 엔티티
package org.sopt.backend.domain.simulation;

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
import jakarta.persistence.OrderColumn;
import jakarta.persistence.Table;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.sopt.backend.domain.source.DataSourceType;

@Getter
@Entity
@Table(name = "scenario_financial_results")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class ScenarioFinancialResult {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "monthly_loan_payment", nullable = false)
    private Long monthlyLoanPayment;

    @Column(name = "monthly_recurring_cost", nullable = false)
    private Long monthlyRecurringCost;

    @Column(name = "cash_after_payment_if_current_state_maintained", nullable = false)
    private Long cashAfterPaymentIfCurrentStateMaintained;

    @Column(name = "break_even_additional_revenue", nullable = false)
    private Long breakEvenAdditionalRevenue;

    @Column(name = "required_additional_orders")
    private Integer requiredAdditionalOrders;

    @Column(name = "payback_period_months")
    private Integer paybackPeriodMonths;

    @Column(name = "payback_status", nullable = false, length = 50)
    private String paybackStatus;

    @Column(name = "payback_reason", length = 1000)
    private String paybackReason;

    @Enumerated(EnumType.STRING)
    @Column(name = "risk_level", nullable = false, length = 20)
    private RiskLevel riskLevel;

    @ElementCollection(fetch = FetchType.LAZY)
    @CollectionTable(
            name = "scenario_risk_reasons",
            joinColumns = @JoinColumn(name = "financial_result_id")
    )
    @OrderColumn(name = "reason_order")
    @Column(name = "risk_reason", nullable = false, length = 1000)
    private List<String> riskReasons = new ArrayList<>();

    @Enumerated(EnumType.STRING)
    @Column(name = "source_type", nullable = false, length = 50)
    private DataSourceType sourceType;

    private ScenarioFinancialResult(
            Long monthlyLoanPayment,
            Long monthlyRecurringCost,
            Long cashAfterPaymentIfCurrentStateMaintained,
            Long breakEvenAdditionalRevenue,
            Integer requiredAdditionalOrders,
            Integer paybackPeriodMonths,
            String paybackStatus,
            String paybackReason,
            RiskLevel riskLevel,
            List<String> riskReasons
    ) {
        this.monthlyLoanPayment = Objects.requireNonNull(monthlyLoanPayment);
        this.monthlyRecurringCost = Objects.requireNonNull(monthlyRecurringCost);
        this.cashAfterPaymentIfCurrentStateMaintained = Objects.requireNonNull(
                cashAfterPaymentIfCurrentStateMaintained
        );
        this.breakEvenAdditionalRevenue = Objects.requireNonNull(
                breakEvenAdditionalRevenue
        );
        this.requiredAdditionalOrders = requiredAdditionalOrders;
        this.paybackPeriodMonths = paybackPeriodMonths;
        this.paybackStatus = Objects.requireNonNull(paybackStatus);
        this.paybackReason = paybackReason;
        this.riskLevel = Objects.requireNonNull(riskLevel);
        this.riskReasons.addAll(Objects.requireNonNull(riskReasons));
        this.sourceType = DataSourceType.CALCULATED;
    }

    public static ScenarioFinancialResult create(
            Long monthlyLoanPayment,
            Long monthlyRecurringCost,
            Long cashAfterPaymentIfCurrentStateMaintained,
            Long breakEvenAdditionalRevenue,
            Integer requiredAdditionalOrders,
            Integer paybackPeriodMonths,
            String paybackStatus,
            String paybackReason,
            RiskLevel riskLevel,
            List<String> riskReasons
    ) {
        return new ScenarioFinancialResult(
                monthlyLoanPayment,
                monthlyRecurringCost,
                cashAfterPaymentIfCurrentStateMaintained,
                breakEvenAdditionalRevenue,
                requiredAdditionalOrders,
                paybackPeriodMonths,
                paybackStatus,
                paybackReason,
                riskLevel,
                riskReasons
        );
    }
}
