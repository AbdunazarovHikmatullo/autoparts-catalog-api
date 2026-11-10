"""Импорт всех моделей — нужен Alembic для автогенерации миграций."""

from app.models.catalog import Brand, Category, Part, Vehicle, part_vehicle
from app.models.user import User

__all__ = ["Brand", "Category", "Part", "Vehicle", "part_vehicle", "User"]
