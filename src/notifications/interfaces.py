from datetime import datetime
from decimal import Decimal
from typing import Protocol


class EmailSenderInterface(Protocol):
    async def send_activation_email(
        self,
        recipient: str,
        activation_link: str,
    ) -> None:
        ...

    async def send_password_reset_email(
        self,
        recipient: str,
        reset_link: str,
    ) -> None:
        ...

    async def send_payment_confirmation_email(
        self,
        recipient: str,
        order_id: int,
        movie_names: list[str],
        total_amount: Decimal,
        currency: str,
        payment_date: datetime,
    ) -> None:
        ...
