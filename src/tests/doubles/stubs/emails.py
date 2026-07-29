from datetime import datetime
from decimal import Decimal


class StubEmailSender:
    def __init__(self) -> None:
        self.activation_emails: list[tuple[str, str]] = []
        self.password_reset_emails: list[tuple[str, str]] = []
        self.payment_confirmation_emails: list[dict[str, object]] = []

    async def send_activation_email(
        self,
        recipient: str,
        activation_link: str,
    ) -> None:
        self.activation_emails.append((recipient, activation_link))

    async def send_password_reset_email(
        self,
        recipient: str,
        reset_link: str,
    ) -> None:
        self.password_reset_emails.append((recipient, reset_link))

    async def send_payment_confirmation_email(
        self,
        recipient: str,
        order_id: int,
        movie_names: list[str],
        total_amount: Decimal,
        currency: str,
        payment_date: datetime,
    ) -> None:
        self.payment_confirmation_emails.append(
            {
                "recipient": recipient,
                "order_id": order_id,
                "movie_names": movie_names,
                "total_amount": total_amount,
                "currency": currency,
                "payment_date": payment_date,
            }
        )
