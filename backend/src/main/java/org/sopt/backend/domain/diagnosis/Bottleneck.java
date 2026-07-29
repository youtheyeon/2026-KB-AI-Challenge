// 진단과 결과 비교에서 발견한 병목 내용을 저장하는 값 객체
package org.sopt.backend.domain.diagnosis;

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
public class Bottleneck {

    @Column(name = "bottleneck_code", length = 100)
    private String code;

    @Column(name = "bottleneck_title", nullable = false, length = 200)
    private String title;

    @Column(length = 30)
    private String priority;

    @Column(length = 30)
    private String confidence;

    @Column(length = 1000)
    private String evidence;

    @Column(length = 1000)
    private String description;
}
