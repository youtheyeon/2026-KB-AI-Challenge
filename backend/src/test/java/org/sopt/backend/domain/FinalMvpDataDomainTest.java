// 최종 MVP의 사업 프로필과 정규화 데이터 모델 동작을 검증하는 테스트
package org.sopt.backend.domain;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalTime;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.sopt.backend.domain.business.Business;
import org.sopt.backend.domain.dataset.Dataset;
import org.sopt.backend.domain.dataset.DatasetFile;
import org.sopt.backend.domain.dataset.DatasetFileType;
import org.sopt.backend.domain.dataset.DatasetFormat;
import org.sopt.backend.domain.dataset.DatasetStatus;
import org.sopt.backend.domain.dataset.ExpenseCategory;
import org.sopt.backend.domain.dataset.NormalizedExpense;
import org.sopt.backend.domain.dataset.NormalizedOnlineSale;
import org.sopt.backend.domain.dataset.NormalizedSale;
import org.sopt.backend.domain.dataset.OnlineSalesReconciliationType;
import org.sopt.backend.domain.source.DataSourceType;
import org.sopt.backend.domain.user.User;

class FinalMvpDataDomainTest {

    @Test
    void 최종_MVP_사업_프로필을_저장한다() {
        User user = User.create("owner@example.com", "홍길동");

        Business business = Business.create(
                user,
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
                new BigDecimal("7.5"),
                new BigDecimal("0.82"),
                null
        );

        assertEquals("서울특별시 서대문구 연희동", business.getRoadAddress());
        assertEquals("CAFE_BAKERY", business.getIndustryCode());
        assertEquals("UNIVERSITY", business.getTradeAreaUsageType());
        assertEquals(18, business.getSeatCount());
        assertEquals(Set.of("OFFLINE", "TAKEOUT"), business.getPrimarySalesChannels());
    }

    @Test
    void 필수_파일과_선택_온라인_파일을_구분하고_READY까지_전이한다() {
        Dataset dataset = Dataset.create(createBusiness(), "dataset-v1");
        DatasetFile salesFile = dataset.addFile(
                DatasetFileType.SALES,
                "easypos_sales_sample.xlsx",
                DatasetFormat.EASYPOS_SALES,
                DataSourceType.SYNTHETIC_SALES
        );
        dataset.addFile(
                DatasetFileType.EXPENSE,
                "easyshop_expense_ledger_sample.xlsx",
                DatasetFormat.EASYSHOP_EXPENSE_LEDGER,
                DataSourceType.SYNTHETIC_EXPENSE
        );

        assertEquals(DatasetStatus.UPLOADED, dataset.getStatus());
        assertFalse(dataset.isOnlineSalesAvailable());

        dataset.addFile(
                DatasetFileType.ONLINE_SALES,
                "easyshop_online_sales_sample.xlsx",
                DatasetFormat.EASYSHOP_ONLINE_SALES,
                DataSourceType.SYNTHETIC_ONLINE_SALES
        );
        dataset.startParsing();
        dataset.startNormalizing();
        dataset.markReady();

        assertEquals(DatasetStatus.READY, dataset.getStatus());
        assertTrue(dataset.isOnlineSalesAvailable());
        assertEquals(DatasetFormat.EASYPOS_SALES, salesFile.getDetectedFormat());
    }

    @Test
    void 정규화_데이터는_원본_파일과_출처를_보존한다() {
        Dataset dataset = Dataset.create(createBusiness(), "dataset-v1");
        DatasetFile salesFile = dataset.addFile(
                DatasetFileType.SALES,
                "sales.xlsx",
                DatasetFormat.EASYPOS_SALES,
                DataSourceType.SYNTHETIC_SALES
        );
        DatasetFile expenseFile = dataset.addFile(
                DatasetFileType.EXPENSE,
                "expense.xlsx",
                DatasetFormat.EASYSHOP_EXPENSE_LEDGER,
                DataSourceType.SYNTHETIC_EXPENSE
        );
        DatasetFile onlineFile = dataset.addFile(
                DatasetFileType.ONLINE_SALES,
                "online.xlsx",
                DatasetFormat.EASYSHOP_ONLINE_SALES,
                DataSourceType.SYNTHETIC_ONLINE_SALES
        );

        NormalizedSale sale = NormalizedSale.create(
                dataset,
                salesFile,
                LocalDate.of(2026, 7, 1),
                LocalTime.of(18, 30),
                "R-001",
                "POS-1",
                20_000L,
                1_000L,
                0L,
                19_000L,
                "CARD",
                "COMPLETED"
        );
        NormalizedExpense expense = NormalizedExpense.create(
                dataset,
                expenseFile,
                LocalDate.of(2026, 7, 1),
                "원재료상사",
                "원두 구입",
                ExpenseCategory.MATERIAL,
                90_000L,
                9_000L,
                0L,
                99_000L,
                "CARD",
                "CARD_RECEIPT"
        );
        NormalizedOnlineSale onlineSale = NormalizedOnlineSale.create(
                dataset,
                onlineFile,
                LocalDate.of(2026, 7, 1),
                "DELIVERY_PLATFORM",
                "DELIVERY",
                3,
                60_000L,
                3_000L,
                0L,
                57_000L,
                6_000L,
                1_500L,
                2_000L,
                47_500L,
                LocalDate.of(2026, 7, 3),
                "COMPLETED",
                OnlineSalesReconciliationType.INCLUDED_IN_POS_TOTAL
        );

        assertEquals(DataSourceType.SYNTHETIC_SALES, sale.getSourceFile().getSourceType());
        assertEquals(ExpenseCategory.MATERIAL, expense.getExpenseCategory());
        assertEquals(
                OnlineSalesReconciliationType.INCLUDED_IN_POS_TOTAL,
                onlineSale.getReconciliationType()
        );
        assertFalse(onlineSale.shouldAddToTotalSales());
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
                Set.of("OFFLINE"),
                null,
                null,
                null,
                null
        );
    }
}
