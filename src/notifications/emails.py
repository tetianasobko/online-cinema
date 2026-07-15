import os
from email.message import EmailMessage

import aiosmtplib

from notifications.interfaces import EmailSenderInterface


class SMTPEmailSender:
    async def send_activation_email(
        self,
        recipient: str,
        activation_link: str,
    ) -> None:
        message = EmailMessage()
        message["From"] = os.getenv(
            "MAIL_FROM",
            "noreply@online-cinema.local",
        )
        message["To"] = recipient
        message["Subject"] = "Activate your Online Cinema account"
        message.set_content(
            "Activate your account within 24 hours using this link:\n"
            f"{activation_link}"
        )

        await aiosmtplib.send(
            message,
            hostname=os.getenv("SMTP_HOST", "localhost"),
            port=int(os.getenv("SMTP_PORT", "1025")),
        )


def get_email_sender() -> EmailSenderInterface:
    return SMTPEmailSender()
