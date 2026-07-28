from collections.abc import Mapping, Sequence
from typing import Any, cast

import stripe

from payments.exceptions import (
    InvalidWebhookPayloadError,
    InvalidWebhookSignatureError,
    StripeCheckoutError,
    StripeRefundError,
)
from payments.interfaces import (
    StripeCheckoutSession,
    StripeGatewayInterface,
    StripeRefund,
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

    async def retrieve_checkout_session(
        self,
        session_id: str,
    ) -> Mapping[str, Any]:
        try:
            session = (
                await self._client.v1.checkout.sessions.retrieve_async(
                    session_id
                )
            )
        except stripe.StripeError as error:
            raise StripeCheckoutError(
                "Stripe could not retrieve the Checkout Session."
            ) from error
        return cast(Mapping[str, Any], session)

    async def expire_checkout_session(
        self,
        session_id: str,
    ) -> Mapping[str, Any]:
        try:
            session = await self._client.v1.checkout.sessions.expire_async(
                session_id
            )
        except stripe.StripeError as error:
            raise StripeCheckoutError(
                "Stripe could not cancel the Checkout Session."
            ) from error
        return cast(Mapping[str, Any], session)

    async def create_refund(
        self,
        checkout_session_id: str,
    ) -> StripeRefund:
        session = await self.retrieve_checkout_session(
            checkout_session_id
        )
        payment_intent = session.get("payment_intent")
        if isinstance(payment_intent, str):
            payment_intent_id = payment_intent
        elif isinstance(payment_intent, Mapping):
            payment_intent_id = payment_intent.get("id")
        else:
            payment_intent_id = None

        if not isinstance(payment_intent_id, str) or not payment_intent_id:
            raise StripeRefundError(
                "The Checkout Session has no refundable PaymentIntent."
            )

        refund_params: Any = {
            "payment_intent": payment_intent_id,
            "reason": "requested_by_customer",
            "metadata": {
                "checkout_session_id": checkout_session_id,
            },
        }
        try:
            refund = await self._client.v1.refunds.create_async(
                refund_params
            )
        except stripe.StripeError as error:
            raise StripeRefundError(
                "Stripe could not refund the payment."
            ) from error

        return StripeRefund(id=refund.id, status=refund.status)

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
