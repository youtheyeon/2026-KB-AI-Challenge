// 시뮬레이션 생성 시점의 대출 조건을 저장하는 값 객체
package org.sopt.backend.domain.simulation;

import jakarta.persistence.Column;
import jakarta.persistence.Embeddable;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import java.math.BigDecimal;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@Embeddable
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class LoanCondition {

    @Column(name = "loan_amount", nullable = false)
    private Long amount;

    @Column(name = "annual_interest_rate", nullable = false, precision = 7, scale = 4)
    private BigDecimal annualInterestRate;

    @Column(name = "term_months", nullable = false)
    private Integer termMonths;

    @Column(name = "grace_months", nullable = false)
    private Integer graceMonths;

    @Enumerated(EnumType.STRING)
    @Column(name = "repayment_type", nullable = false, length = 30)
    private RepaymentType repaymentType;

    public LoanCondition(
            Long amount,
            BigDecimal annualInterestRate,
            Integer termMonths,
            Integer graceMonths,
            RepaymentType repaymentType
    ) {
        this.amount = java.util.Objects.requireNonNull(amount);
        this.annualInterestRate = java.util.Objects.requireNonNull(annualInterestRate);
        this.termMonths = java.util.Objects.requireNonNull(termMonths);
        this.graceMonths = java.util.Objects.requireNonNull(graceMonths);
        this.repaymentType = java.util.Objects.requireNonNull(repaymentType);
    }

    public LoanCondition(
            Long loanAmount,
            Long ownCapitalAmount,
            Long existingMonthlyRepaymentAmount,
            BigDecimal interestRate,
            Integer repaymentPeriodMonths,
            Integer gracePeriodMonths,
            RepaymentType repaymentType,
            Long monthlyRepaymentAmount
    ) {
        this(
                loanAmount,
                interestRate,
                repaymentPeriodMonths,
                gracePeriodMonths == null ? 0 : gracePeriodMonths,
                repaymentType
        );
    }

    public Long getLoanAmount() {
        return amount;
    }
}
