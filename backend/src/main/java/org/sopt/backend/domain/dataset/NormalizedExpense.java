// 이지샵형 비용장부를 표준 필드로 정규화해 저장하는 엔티티
package org.sopt.backend.domain.dataset;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.LocalDate;
import java.util.Objects;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@Entity
@Table(name = "normalized_expenses")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class NormalizedExpense {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "dataset_id", nullable = false)
    private Dataset dataset;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "source_file_id", nullable = false)
    private DatasetFile sourceFile;

    @Column(name = "transaction_date", nullable = false)
    private LocalDate transactionDate;

    @Column(length = 200)
    private String counterparty;

    @Column(length = 500)
    private String description;

    @Enumerated(EnumType.STRING)
    @Column(name = "expense_category", nullable = false, length = 50)
    private ExpenseCategory expenseCategory;

    @Column(name = "supply_amount")
    private Long supplyAmount;

    @Column(name = "vat_amount")
    private Long vatAmount;

    @Column(name = "tax_exempt_amount")
    private Long taxExemptAmount;

    @Column(name = "total_amount", nullable = false)
    private Long totalAmount;

    @Column(name = "payment_method", length = 100)
    private String paymentMethod;

    @Column(name = "evidence_type", length = 100)
    private String evidenceType;

    private NormalizedExpense(
            Dataset dataset,
            DatasetFile sourceFile,
            LocalDate transactionDate,
            String counterparty,
            String description,
            ExpenseCategory expenseCategory,
            Long supplyAmount,
            Long vatAmount,
            Long taxExemptAmount,
            Long totalAmount,
            String paymentMethod,
            String evidenceType
    ) {
        this.dataset = Objects.requireNonNull(dataset);
        this.sourceFile = Objects.requireNonNull(sourceFile);
        this.transactionDate = Objects.requireNonNull(transactionDate);
        this.counterparty = counterparty;
        this.description = description;
        this.expenseCategory = Objects.requireNonNull(expenseCategory);
        this.supplyAmount = supplyAmount;
        this.vatAmount = vatAmount;
        this.taxExemptAmount = taxExemptAmount;
        this.totalAmount = Objects.requireNonNull(totalAmount);
        this.paymentMethod = paymentMethod;
        this.evidenceType = evidenceType;
    }

    public static NormalizedExpense create(
            Dataset dataset,
            DatasetFile sourceFile,
            LocalDate transactionDate,
            String counterparty,
            String description,
            ExpenseCategory expenseCategory,
            Long supplyAmount,
            Long vatAmount,
            Long taxExemptAmount,
            Long totalAmount,
            String paymentMethod,
            String evidenceType
    ) {
        return new NormalizedExpense(
                dataset,
                sourceFile,
                transactionDate,
                counterparty,
                description,
                expenseCategory,
                supplyAmount,
                vatAmount,
                taxExemptAmount,
                totalAmount,
                paymentMethod,
                evidenceType
        );
    }
}
