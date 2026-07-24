import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DECIMAL,
    DateTime,
    Enum,
    ForeignKey,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base


class OrderStatusEnum(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELED = "canceled"


class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
    status: Mapped[OrderStatusEnum] = mapped_column(
        Enum(
            OrderStatusEnum,
            values_callable=lambda enum_class: [
                member.value for member in enum_class
            ],
            native_enum=False,
            length=50,
        ),
        default=OrderStatusEnum.PENDING,
        nullable=False,
    )
    total_amount: Mapped[Decimal | None] = mapped_column(
        DECIMAL(10, 2),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    user: Mapped["UserModel"] = relationship(back_populates="orders")
    items: Mapped[list["OrderItemModel"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )
    payments: Mapped[list["PaymentModel"]] = relationship(
        back_populates="order",
    )


class OrderItemModel(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"),
        nullable=False,
    )
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id"),
        nullable=False,
    )
    price_at_order: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2),
        nullable=False,
    )

    order: Mapped["OrderModel"] = relationship(back_populates="items")
    movie: Mapped["MovieModel"] = relationship(back_populates="order_items")
    payment_items: Mapped[list["PaymentItemModel"]] = relationship(
        back_populates="order_item",
    )
