// 진단과 대출 조건을 기준으로 생성한 자금 배분 시뮬레이션 엔티티
package org.sopt.backend.domain.simulation;

import jakarta.persistence.CascadeType;
import jakarta.persistence.Column;
import jakarta.persistence.Embedded;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.OneToMany;
import jakarta.persistence.Table;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.sopt.backend.domain.business.Business;
import org.sopt.backend.domain.common.BaseTimeEntity;
import org.sopt.backend.domain.diagnosis.Diagnosis;

@Getter
@Entity
@Table(name = "simulations")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Simulation extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "business_id", nullable = false)
    private Business business;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "diagnosis_id", nullable = false)
    private Diagnosis diagnosis;

    @Embedded
    private LoanCondition loanCondition;

    @Column(name = "prediction_months", nullable = false)
    private Integer predictionMonths;

    @OneToMany(
            mappedBy = "simulation",
            cascade = CascadeType.ALL,
            orphanRemoval = true
    )
    private List<AllocationPlan> plans = new ArrayList<>();

    private Simulation(
            Business business,
            Diagnosis diagnosis,
            LoanCondition loanCondition,
            Integer predictionMonths
    ) {
        this.business = Objects.requireNonNull(business);
        this.diagnosis = Objects.requireNonNull(diagnosis);
        this.loanCondition = Objects.requireNonNull(loanCondition);
        this.predictionMonths = Objects.requireNonNull(predictionMonths);
    }

    public static Simulation create(
            Business business,
            Diagnosis diagnosis,
            LoanCondition loanCondition,
            Integer predictionMonths
    ) {
        return new Simulation(business, diagnosis, loanCondition, predictionMonths);
    }

    public AllocationPlan addPlan(
            PlanCode planCode,
            String planType,
            String title,
            Long totalAmount,
            List<AllocationItem> items
    ) {
        boolean duplicate = plans.stream()
                .anyMatch(plan -> plan.getPlanCode() == planCode);
        if (duplicate) {
            throw new IllegalArgumentException("동일한 배분안 코드는 한 번만 등록할 수 있습니다.");
        }

        AllocationPlan plan = new AllocationPlan(
                this,
                planCode,
                planType,
                title,
                totalAmount,
                items
        );
        plans.add(plan);
        return plan;
    }
}
