# FastAPI 애플리케이션을 생성하고 API 라우터를 조립하는 진입점
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes.businesses import router as businesses_router
from app.api.routes.datasets import router as datasets_router
from app.api.routes.health import router as health_router
from app.api.routes.simulations import router as simulations_router
from app.core.config import settings
from app.core.errors import ApiError

app = FastAPI(title=settings.app_name)


@app.exception_handler(ApiError)
async def handle_api_error(_: Request, error: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"error": {"code": error.code, "message": error.message}},
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_: Request, __: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "요청 값이 유효하지 않습니다.",
            }
        },
    )


app.include_router(health_router)
app.include_router(businesses_router)
app.include_router(datasets_router)
app.include_router(simulations_router)
