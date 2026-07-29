// 시뮬레이션 생성 시점의 대출 조건을 저장하는 값 객체
package org.sopt.backend.domain.simulation;

import jakarta.persistence.Column;
import jakarta.persistence.Embeddable;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import java.math.BigDecimal;
import lombok.AccessLevel;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@Embeddable
@AllArgsConstructor
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class LoanCondition {

    @Column(name = "loan_amount", nullable = false)
    private Long loanAmount;

    @Column(name = "own_capital_amount")
    private Long ownCapitalAmount;

    @Column(name = "existing_monthly_repayment_amount")
    private Long existingMonthlyRepaymentAmount;

    @Column(name = "interest_rate", nullable = false, precision = 7, scale = 3)
    private BigDecimal interestRate;

    @Column(name = "repayment_period_months", nullable = false)
    private Integer repaymentPeriodMonths;

    @Column(name = "grace_period_months")
    private Integer gracePeriodMonths;

    @Enumerated(EnumType.STRING)
    @Column(name = "repayment_type", nullable = false, length = 30)
    private RepaymentType repaymentType;

    @Column(name = "monthly_repayment_amount", nullable = false)
    private Long monthlyRepaymentAmount;
}
