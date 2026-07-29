// 결과 비교 화면의 월별 지표 추이를 전달하는 값 객체
package org.sopt.backend.domain.outcome;

import java.math.BigDecimal;
import java.util.List;
import lombok.Getter;

@Getter
public class OutcomeTrends {

    private final List<Long> monthlySalesAmounts;
    private final List<BigDecimal> onlineOrderRatios;

    public OutcomeTrends(
            List<Long> monthlySalesAmounts,
            List<BigDecimal> onlineOrderRatios
    ) {
        this.monthlySalesAmounts = List.copyOf(monthlySalesAmounts);
        this.onlineOrderRatios = List.copyOf(onlineOrderRatios);
    }
}
