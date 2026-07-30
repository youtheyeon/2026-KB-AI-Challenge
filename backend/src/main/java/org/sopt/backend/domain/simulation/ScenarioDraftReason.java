// 병목과 배분 카테고리를 연결한 시나리오 생성 근거를 저장하는 값 객체
package org.sopt.backend.domain.simulation;

import jakarta.persistence.Column;
import jakarta.persistence.Embeddable;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import lombok.AccessLevel;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@Embeddable
@AllArgsConstructor
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class ScenarioDraftReason {

    @Column(name = "bottleneck_type", nullable = false, length = 100)
    private String bottleneckType;

    @Enumerated(EnumType.STRING)
    @Column(name = "related_category", nullable = false, length = 50)
    private AllocationCategory relatedCategory;

    @Column(nullable = false, length = 1000)
    private String description;
}
