from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class StripeCheckoutSession:
    id: str
    url: str


@dataclass(frozen=True)
class StripeRefund:
    id: str
    status: str | None


@dataclass(frozen=True)
class PaymentEmailConfirmation:
    recipient: str
    order_id: int
    movie_names: tuple[str, ...]
    total_amount: Decimal
    currency: str
    payment_date: datetime


@dataclass(frozen=True)
class WebhookProcessingResult:
    payment_id: int | None
    processed: bool
    created: bool
    email_confirmation: PaymentEmailConfirmation | None = None


class StripeGatewayInterface(ABC):
    @abstractmethod
    async def create_checkout_session(
        self,
        *,
        line_items: Sequence[Mapping[str, Any]],
        success_url: str,
        cancel_url: str,
        metadata: Mapping[str, str],
    ) -> StripeCheckoutSession:
        ...

    @abstractmethod
    async def retrieve_checkout_session(
        self,
        session_id: str,
    ) -> Mapping[str, Any]:
        ...

    @abstractmethod
    async def expire_checkout_session(
        self,
        session_id: str,
    ) -> Mapping[str, Any]:
        ...

    @abstractmethod
    async def create_refund(
        self,
        checkout_session_id: str,
    ) -> StripeRefund:
        ...

    @abstractmethod
    def construct_webhook_event(
        self,
        *,
        payload: bytes,
        signature: str,
    ) -> Mapping[str, Any]:
        ...
