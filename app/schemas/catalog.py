"""Pydantic-схемы каталога: создание, частичное обновление и чтение."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Бренды ----------
class BrandBase(BaseModel):
    name: str = Field(min_length=1, max_length=100, examples=["Bosch"])
    country: str | None = Field(default=None, max_length=100, examples=["Германия"])
    description: str | None = None


class BrandCreate(BrandBase):
    pass


class BrandUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    description: str | None = None


class BrandRead(BrandBase, ORMModel):
    id: int


# ---------- Категории ----------
class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=100, examples=["Тормозная система"])
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$", examples=["brakes"])
    description: str | None = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    slug: str | None = Field(default=None, min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: str | None = None


class CategoryRead(CategoryBase, ORMModel):
    id: int


# ---------- Автомобили ----------
class VehicleBase(BaseModel):
    make: str = Field(min_length=1, max_length=100, examples=["Toyota"])
    model: str = Field(min_length=1, max_length=100, examples=["Camry"])
    year_from: int = Field(ge=1950, le=2100, examples=[2017])
    year_to: int = Field(ge=1950, le=2100, examples=[2023])
    engine: str | None = Field(default=None, max_length=100, examples=["2.5 A25A-FKS"])

    @model_validator(mode="after")
    def check_years(self):
        """Год начала выпуска не может быть больше года окончания."""
        if self.year_from > self.year_to:
            raise ValueError("year_from не может быть больше year_to")
        return self


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(BaseModel):
    make: str | None = Field(default=None, min_length=1, max_length=100)
    model: str | None = Field(default=None, min_length=1, max_length=100)
    year_from: int | None = Field(default=None, ge=1950, le=2100)
    year_to: int | None = Field(default=None, ge=1950, le=2100)
    engine: str | None = Field(default=None, max_length=100)


class VehicleRead(VehicleBase, ORMModel):
    id: int


# ---------- Запчасти ----------
class PartBase(BaseModel):
    sku: str = Field(min_length=1, max_length=64, examples=["BOSCH-0986494524"])
    name: str = Field(min_length=1, max_length=255, examples=["Тормозные колодки передние"])
    description: str | None = None
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2, examples=["3490.00"])
    quantity: int = Field(default=0, ge=0, examples=[12])
    brand_id: int
    category_id: int


class PartCreate(PartBase):
    vehicle_ids: list[int] = Field(default_factory=list, description="Совместимые автомобили")


class PartUpdate(BaseModel):
    sku: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    quantity: int | None = Field(default=None, ge=0)
    brand_id: int | None = None
    category_id: int | None = None
    vehicle_ids: list[int] | None = None


class PartRead(ORMModel):
    id: int
    sku: str
    name: str
    description: str | None
    price: Decimal
    quantity: int
    in_stock: bool
    brand: BrandRead
    category: CategoryRead
    vehicles: list[VehicleRead]
    created_at: datetime
    updated_at: datetime

    @field_serializer("price")
    def serialize_price(self, value: Decimal) -> float:
        """Отдаём цену числом, а не строкой — так удобнее фронтенду."""
        return float(value)
