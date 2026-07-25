class StripeGatewayError(Exception):
    """Base exception for Stripe gateway failures."""


class StripeCheckoutError(StripeGatewayError):
    """Raised when Stripe cannot create a Checkout Session."""


class InvalidWebhookPayloadError(StripeGatewayError):
    """Raised when a Stripe webhook payload is invalid."""


class InvalidWebhookSignatureError(StripeGatewayError):
    """Raised when a Stripe webhook signature cannot be verified."""


class PaymentServiceError(Exception):
    """Base exception for payment workflow failures."""


class PaymentOrderNotFoundError(PaymentServiceError):
    """Raised when the user does not own the requested order."""


class OrderNotPayableError(PaymentServiceError):
    """Raised when an order cannot enter the payment flow."""


class OrderItemUnavailableError(PaymentServiceError):
    """Raised when an order item cannot be purchased."""


class InvalidWebhookEventError(PaymentServiceError):
    """Raised when a Stripe event lacks valid payment information."""


class PaymentAmountMismatchError(PaymentServiceError):
    """Raised when Stripe's amount differs from the order total."""
