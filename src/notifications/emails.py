from datetime import datetime
from decimal import Decimal
from email.message import EmailMessage
from pathlib import Path

import aiosmtplib
from fastapi import Depends

from config import Settings, get_settings
from notifications.interfaces import EmailSenderInterface


class SMTPEmailSender:
    _PAYMENT_CONFIRMATION_TEMPLATE = (
        Path(__file__).parent
        / "templates"
        / "payment_confirmation.txt"
    )

    def __init__(self, settings: Settings):
        self.settings = settings

    async def send_activation_email(
        self,
        recipient: str,
        activation_link: str,
    ) -> None:
        message = EmailMessage()
        message["From"] = self.settings.EMAIL_FROM
        message["To"] = recipient
        message["Subject"] = "Activate your Online Cinema account"
        message.set_content(
            "Activate your account within 24 hours using this link:\n"
            f"{activation_link}"
        )

        await aiosmtplib.send(
            message,
            hostname=self.settings.EMAIL_HOST,
            port=self.settings.EMAIL_PORT,
        )

    async def send_password_reset_email(
        self,
        recipient: str,
        reset_link: str,
    ) -> None:
        message = EmailMessage()
        message["From"] = self.settings.EMAIL_FROM
        message["To"] = recipient
        message["Subject"] = "Reset your Online Cinema password"
        message.set_content(
            "Reset your password within 24 hours using this link:\n"
            f"{reset_link}"
        )

        await aiosmtplib.send(
            message,
            hostname=self.settings.EMAIL_HOST,
            port=self.settings.EMAIL_PORT,
        )

    async def send_payment_confirmation_email(
        self,
        recipient: str,
        order_id: int,
        movie_names: list[str],
        total_amount: Decimal,
        currency: str,
        payment_date: datetime,
    ) -> None:
        movie_list = "\n".join(
            f"- {movie_name}" for movie_name in movie_names
        )
        template = self._PAYMENT_CONFIRMATION_TEMPLATE.read_text(
            encoding="utf-8"
        )
        content = template.format(
            order_id=order_id,
            payment_date=payment_date.isoformat(),
            movie_list=movie_list,
            total_amount=f"{total_amount:.2f}",
            currency=currency.upper(),
        )

        message = EmailMessage()
        message["From"] = self.settings.EMAIL_FROM
        message["To"] = recipient
        message["Subject"] = "Your Online Cinema payment is confirmed"
        message.set_content(content)

        await aiosmtplib.send(
            message,
            hostname=self.settings.EMAIL_HOST,
            port=self.settings.EMAIL_PORT,
        )


def get_email_sender(
    settings: Settings = Depends(get_settings),
) -> EmailSenderInterface:
    return SMTPEmailSender(settings)
