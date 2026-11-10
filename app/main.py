"""Точка входа приложения FastAPI."""

from fastapi import FastAPI

from app.api.routers import auth, brands, categories, health, parts, vehicles
from app.core.config import settings


def create_app() -> FastAPI:
    """Фабрика приложения — удобно для тестов и разных конфигураций."""
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="REST API каталога автозапчастей: бренды, категории, автомобили и запчасти "
        "с поиском, фильтрами, пагинацией и JWT-аутентификацией.",
    )
    app.include_router(health.router)
    for module in (auth, brands, categories, vehicles, parts):
        app.include_router(module.router, prefix=settings.api_prefix)
    return app


app = create_app()
