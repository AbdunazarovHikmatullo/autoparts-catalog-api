"""Модели каталога: бренды, категории, автомобили и запчасти."""

from decimal import Decimal

from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, Numeric, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

# Таблица связи «многие-ко-многим»: какая запчасть подходит к какому автомобилю
part_vehicle = Table(
    "part_vehicle",
    Base.metadata,
    Column("part_id", ForeignKey("parts.id", ondelete="CASCADE"), primary_key=True),
    Column("vehicle_id", ForeignKey("vehicles.id", ondelete="CASCADE"), primary_key=True),
)


class Brand(TimestampMixin, Base):
    """Производитель запчастей (Bosch, Mann-Filter, Brembo и т.д.)."""

    __tablename__ = "brands"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    country: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)

    parts: Mapped[list["Part"]] = relationship(back_populates="brand")


class Category(TimestampMixin, Base):
    """Категория запчастей (фильтры, тормозная система, подвеска...)."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)

    parts: Mapped[list["Part"]] = relationship(back_populates="category")


class Vehicle(TimestampMixin, Base):
    """Модель автомобиля для проверки совместимости запчастей."""

    __tablename__ = "vehicles"
    __table_args__ = (CheckConstraint("year_from <= year_to", name="year_range"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    make: Mapped[str] = mapped_column(String(100), index=True)  # марка
    model: Mapped[str] = mapped_column(String(100))  # модель
    year_from: Mapped[int] = mapped_column(Integer)
    year_to: Mapped[int] = mapped_column(Integer)
    engine: Mapped[str | None] = mapped_column(String(100))

    parts: Mapped[list["Part"]] = relationship(secondary=part_vehicle, back_populates="vehicles")


class Part(TimestampMixin, Base):
    """Автозапчасть в каталоге."""

    __tablename__ = "parts"
    __table_args__ = (
        CheckConstraint("price >= 0", name="price_non_negative"),
        CheckConstraint("quantity >= 0", name="quantity_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # артикул
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    quantity: Mapped[int] = mapped_column(Integer, default=0)  # остаток на складе

    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id", ondelete="RESTRICT"), index=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )

    # selectin — связанные объекты подгружаются отдельным запросом, это безопасно для async
    brand: Mapped[Brand] = relationship(back_populates="parts", lazy="selectin")
    category: Mapped[Category] = relationship(back_populates="parts", lazy="selectin")
    vehicles: Mapped[list[Vehicle]] = relationship(
        secondary=part_vehicle, back_populates="parts", lazy="selectin"
    )

    @property
    def in_stock(self) -> bool:
        """Есть ли запчасть в наличии."""
        return self.quantity > 0
