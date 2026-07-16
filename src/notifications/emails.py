from email.message import EmailMessage

import aiosmtplib
from fastapi import Depends

from config import Settings, get_settings
from notifications.interfaces import EmailSenderInterface


class SMTPEmailSender:
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


def get_email_sender(
    settings: Settings = Depends(get_settings),
) -> EmailSenderInterface:
    return SMTPEmailSender(settings)
