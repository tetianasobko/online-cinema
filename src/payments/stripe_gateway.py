from collections.abc import Mapping, Sequence
from typing import Any, cast

import stripe

from payments.exceptions import (
    InvalidWebhookPayloadError,
    InvalidWebhookSignatureError,
    StripeCheckoutError,
)
from payments.interfaces import (
    StripeCheckoutSession,
    StripeGatewayInterface,
)


class StripeGateway(StripeGatewayInterface):
    def __init__(
        self,
        secret_key: str,
        webhook_secret: str,
    ) -> None:
        self._client = stripe.StripeClient(secret_key)
        self._webhook_secret = webhook_secret

    async def create_checkout_session(
        self,
        *,
        line_items: Sequence[Mapping[str, Any]],
        success_url: str,
        cancel_url: str,
        metadata: Mapping[str, str],
    ) -> StripeCheckoutSession:
        checkout_params: Any = {
            "mode": "payment",
            "line_items": [dict(item) for item in line_items],
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": dict(metadata),
        }
        try:
            session = await self._client.v1.checkout.sessions.create_async(
                checkout_params
            )
        except stripe.StripeError as error:
            raise StripeCheckoutError(
                "Stripe could not create the Checkout Session."
            ) from error

        if session.url is None:
            raise StripeCheckoutError(
                "Stripe returned a Checkout Session without a URL."
            )

        return StripeCheckoutSession(id=session.id, url=session.url)

    def construct_webhook_event(
        self,
        *,
        payload: bytes,
        signature: str,
    ) -> Mapping[str, Any]:
        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                self._webhook_secret,
            )
        except ValueError as error:
            raise InvalidWebhookPayloadError(
                "Invalid Stripe webhook payload."
            ) from error
        except stripe.SignatureVerificationError as error:
            raise InvalidWebhookSignatureError(
                "Invalid Stripe webhook signature."
            ) from error

        return cast(Mapping[str, Any], event)
