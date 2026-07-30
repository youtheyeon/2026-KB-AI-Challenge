// 최종 MVP의 사업 스냅샷과 근거 기반 병목 진단을 검증하는 테스트
package org.sopt.backend.domain;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.sopt.backend.domain.business.Business;
import org.sopt.backend.domain.business.BusinessSnapshot;
import org.sopt.backend.domain.business.PublicDataSnapshot;
import org.sopt.backend.domain.dataset.Dataset;
import org.sopt.backend.domain.diagnosis.Bottleneck;
import org.sopt.backend.domain.diagnosis.BottleneckSeverity;
import org.sopt.backend.domain.diagnosis.Diagnosis;
import org.sopt.backend.domain.diagnosis.DiagnosisMetric;
import org.sopt.backend.domain.diagnosis.DiagnosisStatus;
import org.sopt.backend.domain.simulation.AllocationCategory;
import org.sopt.backend.domain.source.DataSourceType;
import org.sopt.backend.domain.user.User;

class FinalMvpDiagnosisDomainTest {

    @Test
    void 시뮬레이션에_사용할_사업_상태와_공공데이터를_스냅샷으로_보존한다() {
        Business business = createBusiness();
        Dataset dataset = Dataset.create(business, "dataset-v2");
        BusinessSnapshot businessSnapshot = BusinessSnapshot.create(
                business,
                dataset,
                LocalDate.of(2026, 7, 1),
                "business-snapshot-v1",
                18_000_000L,
                15_500_000L,
                500_000L,
                new BigDecimal("0.42"),
                15_000L,
                1_200,
                new BigDecimal("0.18"),
                2,
                DataSourceType.CALCULATED
        );
        PublicDataSnapshot publicDataSnapshot = PublicDataSnapshot.create(
                business,
                LocalDate.of(2026, 6, 30),
                "서울시 상권분석서비스",
                "public-data-2026-06",
                "서울특별시 서대문구 연희동"
        );

        assertEquals("dataset-v2", businessSnapshot.getDataset().getDatasetVersion());
        assertEquals(18_000_000L, businessSnapshot.getMonthlyNetSalesAmount());
        assertEquals(
                LocalDate.of(2026, 6, 30),
                publicDataSnapshot.getReferenceDate()
        );
        assertEquals(DataSourceType.PUBLIC_DATA, publicDataSnapshot.getSourceType());
    }

    @Test
    void 진단은_현재값과_비교값의_출처와_병목_근거를_저장한다() {
        Business business = createBusiness();
        Dataset dataset = Dataset.create(business, "dataset-v2");
        BusinessSnapshot businessSnapshot = BusinessSnapshot.create(
                business,
                dataset,
                LocalDate.of(2026, 7, 1),
                "business-snapshot-v1",
                18_000_000L,
                15_500_000L,
                500_000L,
                new BigDecimal("0.42"),
                15_000L,
                1_200,
                new BigDecimal("0.18"),
                2,
                DataSourceType.CALCULATED
        );
        PublicDataSnapshot publicDataSnapshot = PublicDataSnapshot.create(
                business,
                LocalDate.of(2026, 6, 30),
                "서울시 상권분석서비스",
                "public-data-2026-06",
                "서울특별시 서대문구 연희동"
        );
        Diagnosis diagnosis = Diagnosis.start(
                business,
                dataset,
                businessSnapshot,
                publicDataSnapshot,
                "diagnosis-v3",
                "benchmark-2026-07-v2"
        );
        DiagnosisMetric eveningSalesShare = new DiagnosisMetric(
                "EVENING_SALES_SHARE",
                new BigDecimal("0.12"),
                DataSourceType.SYNTHETIC_SALES,
                new BigDecimal("0.24"),
                DataSourceType.BENCHMARK,
                new BigDecimal("-0.12"),
                "RATIO",
                "benchmark-2026-07-v2"
        );
        Bottleneck bottleneck = Bottleneck.create(
                "TIME_OF_DAY_WEAKNESS",
                "17~21시 매출 비중이 유사 카페 중앙값보다 낮습니다.",
                BottleneckSeverity.CLEAR,
                DataSourceType.BENCHMARK,
                "서울시 카페 시간대별 추정매출",
                Set.of(
                        AllocationCategory.MARKETING_ONLINE,
                        AllocationCategory.LABOR
                )
        );

        diagnosis.complete(List.of(eveningSalesShare), List.of(bottleneck));

        assertEquals(DiagnosisStatus.COMPLETED, diagnosis.getStatus());
        assertEquals("benchmark-2026-07-v2", diagnosis.getBenchmarkVersion());
        assertEquals(new BigDecimal("-0.12"), diagnosis.getMetrics().getFirst().getDifferenceValue());
        assertEquals(
                DataSourceType.SYNTHETIC_SALES,
                diagnosis.getMetrics().getFirst().getCurrentSourceType()
        );
        assertEquals(
                DataSourceType.BENCHMARK,
                diagnosis.getMetrics().getFirst().getComparisonSourceType()
        );
        assertEquals(BottleneckSeverity.CLEAR, diagnosis.getBottlenecks().getFirst().getSeverity());
        assertEquals(
                Set.of(AllocationCategory.MARKETING_ONLINE, AllocationCategory.LABOR),
                diagnosis.getBottlenecks().getFirst().getRelatedCategories()
        );
        assertThrows(
                UnsupportedOperationException.class,
                () -> diagnosis.getMetrics().clear()
        );
    }

    private Business createBusiness() {
        return Business.create(
                User.create("owner@example.com", "홍길동"),
                "연희동 Y카페",
                "서울특별시 서대문구 연희동",
                "CAFE_BAKERY",
                "UNIVERSITY",
                "OVER_3_YEARS",
                "SEAT_AND_TAKEOUT",
                2,
                "TEN_TO_TWENTY_MILLION",
                Set.of("OFFLINE", "TAKEOUT"),
                18,
                null,
                null,
                null
        );
    }
}
