// 자금 배분안의 개별 사용 항목을 저장하는 값 객체
package org.sopt.backend.domain.simulation;

import jakarta.persistence.Column;
import jakarta.persistence.Embeddable;
import lombok.AccessLevel;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@Embeddable
@AllArgsConstructor
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class AllocationItem {

    @Column(name = "item_name", nullable = false, length = 200)
    private String name;

    @Column(nullable = false)
    private Long amount;

    @Column(name = "expense_type", length = 50)
    private String expenseType;
}
