# FastAPI 애플리케이션을 생성하고 API 라우터를 조립하는 진입점
from fastapi import FastAPI

from app.api.routes.businesses import router as businesses_router
from app.api.routes.datasets import router as datasets_router
from app.api.routes.health import router as health_router
from app.core.config import settings

app = FastAPI(title=settings.app_name)
app.include_router(health_router)
app.include_router(businesses_router)
app.include_router(datasets_router)
