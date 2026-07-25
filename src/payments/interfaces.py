from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StripeCheckoutSession:
    id: str
    url: str


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
    def construct_webhook_event(
        self,
        *,
        payload: bytes,
        signature: str,
    ) -> Mapping[str, Any]:
       ...
