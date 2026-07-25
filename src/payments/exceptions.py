class StripeGatewayError(Exception):
    """Base exception for Stripe gateway failures."""


class StripeCheckoutError(StripeGatewayError):
    """Raised when Stripe cannot create a Checkout Session."""


class InvalidWebhookPayloadError(StripeGatewayError):
    """Raised when a Stripe webhook payload is invalid."""


class InvalidWebhookSignatureError(StripeGatewayError):
    """Raised when a Stripe webhook signature cannot be verified."""
