import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base


class PaymentStatusEnum(str, enum.Enum):
    SUCCESSFUL = "successful"
    CANCELED = "canceled"
    REFUNDED = "refunded"


class PaymentModel(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    status: Mapped[PaymentStatusEnum] = mapped_column(
        Enum(
            PaymentStatusEnum,
            values_callable=lambda enum_class: [
                member.value for member in enum_class
            ],
            native_enum=False,
            length=50,
        ),
        default=PaymentStatusEnum.SUCCESSFUL,
        server_default=PaymentStatusEnum.SUCCESSFUL.value,
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2),
        nullable=False,
    )
    external_payment_id: Mapped[str | None] = mapped_column(String(255))

    user: Mapped["UserModel"] = relationship(back_populates="payments")
    order: Mapped["OrderModel"] = relationship(back_populates="payments")
    items: Mapped[list["PaymentItemModel"]] = relationship(
        back_populates="payment",
        cascade="all, delete-orphan",
    )


class PaymentItemModel(Base):
    __tablename__ = "payment_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    payment_id: Mapped[int] = mapped_column(
        ForeignKey("payments.id"),
        nullable=False,
    )
    order_item_id: Mapped[int] = mapped_column(
        ForeignKey("order_items.id"),
        nullable=False,
    )
    price_at_payment: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2),
        nullable=False,
    )

    payment: Mapped["PaymentModel"] = relationship(back_populates="items")
    order_item: Mapped["OrderItemModel"] = relationship(
        back_populates="payment_items"
    )
