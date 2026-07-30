# 사업 데이터 파일 업로드와 데이터셋 처리 상태 조회를 제공하는 라우터
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.routes.businesses import get_db
from app.domain.business import Business
from app.domain.dataset import Dataset, DatasetFile
from app.domain.enums import DatasetFileType, DatasetFormat, DatasetStatus
from app.services.dataset_import import (
    WorkbookProcessingError,
    analyze_workbook,
    normalize_rows,
)

router = APIRouter(tags=["datasets"])


class DatasetUploadResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    dataset_id: int = Field(alias="datasetId")
    status: DatasetStatus


class DatasetFileStatusResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    file_type: DatasetFileType = Field(alias="fileType")
    original_filename: str = Field(alias="originalFilename")
    detected_format: DatasetFormat = Field(alias="detectedFormat")
    column_mapping: dict[str, str] = Field(alias="columnMapping")
    missing_columns: list[str] = Field(alias="missingColumns")
    mapping_confidence: float = Field(alias="mappingConfidence")
    row_count: int = Field(alias="rowCount")


class DatasetStatusResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    dataset_id: int = Field(alias="datasetId")
    business_id: int = Field(alias="businessId")
    status: DatasetStatus
    files: list[DatasetFileStatusResponse]


@router.post(
    "/api/businesses/{business_id}/datasets",
    response_model=DatasetUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_dataset(
    business_id: int,
    sales_file: Annotated[UploadFile, File(alias="salesFile")],
    expense_file: Annotated[UploadFile, File(alias="expenseFile")],
    database: Annotated[Session, Depends(get_db)],
    demo_session_cookie: str | None = Cookie(default=None, alias="demo_session_id"),
    online_sales_file: Annotated[UploadFile | None, File(alias="onlineSalesFile")] = None,
) -> DatasetUploadResponse:
    uploads = [
        (DatasetFileType.SALE, sales_file),
        (DatasetFileType.EXPENSE, expense_file),
    ]
    if online_sales_file is not None:
        uploads.append((DatasetFileType.ONLINE_SALE, online_sales_file))
    _validate_xlsx_filenames(uploads)

    with database.begin():
        business = _get_owned_business(database, business_id, demo_session_cookie)
        dataset = Dataset(
            business=business,
            status=DatasetStatus.UPLOADED,
            dataset_version="v1",
        )
        database.add(dataset)
        database.flush()
        dataset_id = dataset.id
        if dataset_id is None:
            raise RuntimeError("데이터셋 ID가 생성되지 않았습니다.")

        dataset_files = [
            DatasetFile(
                dataset=dataset,
                file_type=file_type,
                original_filename=upload.filename or "",
                storage_path=None,
                detected_format=DatasetFormat.UNKNOWN,
                file_metadata={},
            )
            for file_type, upload in uploads
        ]
        for dataset_file in dataset_files:
            database.add(dataset_file)
        database.flush()
        dataset.status = DatasetStatus.PARSING

        parsed_files = []
        processing_file: DatasetFile | None = None
        try:
            for (file_type, upload), dataset_file in zip(
                uploads,
                dataset_files,
                strict=True,
            ):
                processing_file = dataset_file
                parsed = analyze_workbook(await upload.read(), file_type)
                dataset_file.detected_format = parsed.detected_format
                dataset_file.file_metadata = {
                    "columnMapping": parsed.column_mapping,
                    "missingColumns": parsed.missing_columns,
                    "mappingConfidence": parsed.mapping_confidence,
                    "rowCount": len(parsed.rows),
                }
                parsed_files.append((parsed, dataset_file))

            if any(parsed.missing_columns for parsed, _ in parsed_files):
                dataset.status = DatasetStatus.NEEDS_REUPLOAD
            else:
                dataset.status = DatasetStatus.NORMALIZING
                normalized_rows = []
                for parsed, dataset_file in parsed_files:
                    processing_file = dataset_file
                    normalized_rows.extend(
                        normalize_rows(parsed, dataset_id, _require_file_id(dataset_file))
                    )
                for row in normalized_rows:
                    database.add(row)
                dataset.status = DatasetStatus.READY
        except WorkbookProcessingError as error:
            dataset.status = DatasetStatus.FAILED
            if processing_file is not None:
                processing_file.file_metadata = {
                    **(processing_file.file_metadata or {}),
                    "columnMapping": {},
                    "missingColumns": [],
                    "mappingConfidence": 0.0,
                    "rowCount": 0,
                    "error": str(error),
                }

    return DatasetUploadResponse(
        dataset_id=dataset_id,
        status=DatasetStatus.UPLOADED,
    )


@router.get(
    "/api/datasets/{dataset_id}",
    response_model=DatasetStatusResponse,
)
def get_dataset_status(
    dataset_id: int,
    database: Annotated[Session, Depends(get_db)],
    demo_session_cookie: str | None = Cookie(default=None, alias="demo_session_id"),
) -> DatasetStatusResponse:
    dataset = database.get(Dataset, dataset_id)
    session_id = _parse_session_id(demo_session_cookie)
    if (
        dataset is None
        or dataset.business is None
        or session_id is None
        or dataset.business.demo_session_id != session_id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    file_order = {
        DatasetFileType.SALE: 0,
        DatasetFileType.EXPENSE: 1,
        DatasetFileType.ONLINE_SALE: 2,
    }
    files = [
        _file_status(dataset_file)
        for dataset_file in sorted(
            dataset.files,
            key=lambda item: file_order[item.file_type],
        )
    ]
    if dataset.id is None or dataset.business.id is None:
        raise RuntimeError("저장된 데이터셋 식별자가 없습니다.")
    return DatasetStatusResponse(
        dataset_id=dataset.id,
        business_id=dataset.business.id,
        status=dataset.status,
        files=files,
    )


def _get_owned_business(
    database: Session,
    business_id: int,
    session_cookie: str | None,
) -> Business:
    business = database.get(Business, business_id)
    session_id = _parse_session_id(session_cookie)
    if business is None or session_id is None or business.demo_session_id != session_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return business


def _parse_session_id(session_cookie: str | None) -> UUID | None:
    try:
        return UUID(session_cookie) if session_cookie else None
    except ValueError:
        return None


def _validate_xlsx_filenames(
    uploads: list[tuple[DatasetFileType, UploadFile]],
) -> None:
    if any(
        not upload.filename or not upload.filename.lower().endswith(".xlsx")
        for _, upload in uploads
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=".xlsx 파일만 업로드할 수 있습니다.",
        )


def _require_file_id(dataset_file: DatasetFile) -> int:
    if dataset_file.id is None:
        raise RuntimeError("데이터셋 파일 ID가 생성되지 않았습니다.")
    return dataset_file.id


def _file_status(dataset_file: DatasetFile) -> DatasetFileStatusResponse:
    metadata = dataset_file.file_metadata or {}
    return DatasetFileStatusResponse(
        file_type=dataset_file.file_type,
        original_filename=dataset_file.original_filename,
        detected_format=dataset_file.detected_format,
        column_mapping=metadata.get("columnMapping", {}),
        missing_columns=metadata.get("missingColumns", []),
        mapping_confidence=metadata.get("mappingConfidence", 0.0),
        row_count=metadata.get("rowCount", 0),
    )
