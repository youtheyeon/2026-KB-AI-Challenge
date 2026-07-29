// 사업 정보부터 진단 완료까지의 도메인 모델 동작을 검증하는 테스트
package org.sopt.backend.domain;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.sopt.backend.domain.business.Business;
import org.sopt.backend.domain.business.Industry;
import org.sopt.backend.domain.business.SalesChannel;
import org.sopt.backend.domain.dataset.Dataset;
import org.sopt.backend.domain.dataset.DatasetFileType;
import org.sopt.backend.domain.dataset.DatasetStatus;
import org.sopt.backend.domain.diagnosis.ActivityMetrics;
import org.sopt.backend.domain.diagnosis.Bottleneck;
import org.sopt.backend.domain.diagnosis.CommercialMetrics;
import org.sopt.backend.domain.diagnosis.Diagnosis;
import org.sopt.backend.domain.diagnosis.DiagnosisStatus;
import org.sopt.backend.domain.diagnosis.FinancialMetrics;
import org.sopt.backend.domain.user.User;

class BusinessDiagnosisDomainTest {

    @Test
    void 사업체와_데이터셋을_소유자에게_연결한다() {
        User user = User.create("owner@example.com", "홍길동");
        Business business = Business.create(
                user,
                "마포 한식당",
                "서울 마포구",
                Industry.RESTAURANT,
                2,
                Set.of(SalesChannel.OFFLINE, SalesChannel.DELIVERY_PLATFORM)
        );

        Dataset dataset = Dataset.create(business);
        dataset.addFile(DatasetFileType.SALES, "sales.xlsx");
        dataset.addFile(DatasetFileType.COST, "cost.xlsx");
        dataset.addAutoMapping(
                DatasetFileType.SALES,
                "결제금액",
                "salesAmount",
                new BigDecimal("0.93")
        );

        LocalDateTime confirmedAt = LocalDateTime.of(2026, 7, 29, 3, 25);
        dataset.confirmMappings(confirmedAt);

        assertEquals(user, business.getUser());
        assertEquals(business, dataset.getBusiness());
        assertEquals(2, dataset.getFiles().size());
        assertEquals(DatasetStatus.MAPPING_CONFIRMED, dataset.getStatus());
        assertEquals(confirmedAt, dataset.getConfirmedAt());
        assertTrue(dataset.getColumnMappings().getFirst().isConfirmed());
    }

    @Test
    void 진단을_완료하면_지표와_병목을_보관한다() {
        User user = User.create("owner@example.com", "홍길동");
        Business business = Business.create(
                user,
                "마포 한식당",
                "서울 마포구",
                Industry.RESTAURANT,
                2,
                Set.of(SalesChannel.OFFLINE)
        );
        Dataset dataset = Dataset.create(business);
        Diagnosis diagnosis = Diagnosis.start(business, dataset);

        FinancialMetrics financialMetrics = new FinancialMetrics(
                30_000_000L,
                new BigDecimal("11"),
                new BigDecimal("40"),
                1_800_000L
        );
        ActivityMetrics activityMetrics = new ActivityMetrics(
                420,
                new BigDecimal("9"),
                2
        );
        CommercialMetrics commercialMetrics = new CommercialMetrics(
                new BigDecimal("3.2"),
                new BigDecimal("-8")
        );
        Bottleneck bottleneck = new Bottleneck(
                "CHANNEL_CONCENTRATION",
                "판매 채널 편중",
                "HIGH",
                "MEDIUM",
                "온라인 주문 비중 9%, 비교군 28%.",
                null
        );

        diagnosis.complete(
                financialMetrics,
                activityMetrics,
                commercialMetrics,
                List.of(bottleneck)
        );

        assertEquals(DiagnosisStatus.COMPLETED, diagnosis.getStatus());
        assertEquals(financialMetrics, diagnosis.getFinancialMetrics());
        assertEquals(activityMetrics, diagnosis.getActivityMetrics());
        assertEquals(commercialMetrics, diagnosis.getCommercialMetrics());
        assertEquals(List.of(bottleneck), diagnosis.getBottlenecks());
    }
}
