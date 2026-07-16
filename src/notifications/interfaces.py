from typing import Protocol


class EmailSenderInterface(Protocol):
    async def send_activation_email(
        self,
        recipient: str,
        activation_link: str,
    ) -> None: ...

    async def send_password_reset_email(
        self,
        recipient: str,
        reset_link: str,
    ) -> None: ...
