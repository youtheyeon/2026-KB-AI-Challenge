// 최종 MVP의 사업 프로필과 정규화 데이터 모델 동작을 검증하는 테스트
package org.sopt.backend.domain;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
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
    void 같은_데이터셋에_동일한_파일_유형을_중복_등록할_수_없다() {
        Dataset dataset = Dataset.create(createBusiness(), "dataset-v1");
        dataset.addFile(
                DatasetFileType.SALES,
                "sales-1.xlsx",
                DatasetFormat.EASYPOS_SALES,
                DataSourceType.USER_INPUT
        );

        assertThrows(
                IllegalArgumentException.class,
                () -> dataset.addFile(
                        DatasetFileType.SALES,
                        "sales-2.xlsx",
                        DatasetFormat.EASYPOS_SALES,
                        DataSourceType.USER_INPUT
                )
        );
    }

    @Test
    void 데이터셋의_파일_목록은_외부에서_수정할_수_없다() {
        Dataset dataset = Dataset.create(createBusiness(), "dataset-v1");
        dataset.addFile(
                DatasetFileType.SALES,
                "sales.xlsx",
                DatasetFormat.EASYPOS_SALES,
                DataSourceType.USER_INPUT
        );

        assertThrows(
                UnsupportedOperationException.class,
                () -> dataset.getFiles().clear()
        );
    }

    @Test
    void 지원하지_않는_파일_형식이_있으면_재업로드가_필요하다() {
        Dataset dataset = Dataset.create(createBusiness(), "dataset-v1");
        dataset.addFile(
                DatasetFileType.SALES,
                "unknown-sales.xlsx",
                DatasetFormat.UNKNOWN,
                DataSourceType.USER_INPUT
        );
        dataset.addFile(
                DatasetFileType.EXPENSE,
                "expense.xlsx",
                DatasetFormat.EASYSHOP_EXPENSE_LEDGER,
                DataSourceType.USER_INPUT
        );

        dataset.startParsing();
        dataset.startNormalizing();
        dataset.markReady();

        assertEquals(DatasetStatus.NEEDS_REUPLOAD, dataset.getStatus());
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

    @Test
    void 다른_데이터셋의_원본_파일로_정규화_행을_생성할_수_없다() {
        Dataset sourceDataset = Dataset.create(createBusiness(), "source-v1");
        DatasetFile sourceFile = sourceDataset.addFile(
                DatasetFileType.SALES,
                "sales.xlsx",
                DatasetFormat.EASYPOS_SALES,
                DataSourceType.USER_INPUT
        );
        Dataset targetDataset = Dataset.create(createBusiness(), "target-v1");

        assertThrows(
                IllegalArgumentException.class,
                () -> NormalizedSale.create(
                        targetDataset,
                        sourceFile,
                        LocalDate.of(2026, 7, 1),
                        LocalTime.NOON,
                        "R-001",
                        "POS-1",
                        10_000L,
                        0L,
                        0L,
                        10_000L,
                        "CARD",
                        "COMPLETED"
                )
        );
    }

    @Test
    void 매출_정규화_행은_매출_파일만_원본으로_사용할_수_있다() {
        Dataset dataset = Dataset.create(createBusiness(), "dataset-v1");
        DatasetFile expenseFile = dataset.addFile(
                DatasetFileType.EXPENSE,
                "expense.xlsx",
                DatasetFormat.EASYSHOP_EXPENSE_LEDGER,
                DataSourceType.USER_INPUT
        );

        assertThrows(
                IllegalArgumentException.class,
                () -> NormalizedSale.create(
                        dataset,
                        expenseFile,
                        LocalDate.of(2026, 7, 1),
                        LocalTime.NOON,
                        "R-001",
                        "POS-1",
                        10_000L,
                        0L,
                        0L,
                        10_000L,
                        "CARD",
                        "COMPLETED"
                )
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
                Set.of("OFFLINE"),
                null,
                null,
                null,
                null
        );
    }
}
