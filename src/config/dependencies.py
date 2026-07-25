from fastapi import Depends

from config.settings import Settings
from payments.interfaces import StripeGatewayInterface
from payments.stripe_gateway import StripeGateway
from payments.stripe_service import StripePaymentService
from security.interfaces import JWTAuthManagerInterface
from security.token_manager import JWTAuthManager


def get_settings() -> Settings:
    return Settings()


def get_jwt_auth_manager(
    settings: Settings = Depends(get_settings),
) -> JWTAuthManagerInterface:
    return JWTAuthManager(
        secret_key_access=settings.SECRET_KEY_ACCESS,
        secret_key_refresh=settings.SECRET_KEY_REFRESH,
        algorithm=settings.JWT_SIGNING_ALGORITHM,
    )


def get_stripe_gateway(
    settings: Settings = Depends(get_settings),
) -> StripeGatewayInterface:
    return StripeGateway(
        secret_key=settings.STRIPE_SECRET_KEY,
        webhook_secret=settings.STRIPE_WEBHOOK_SECRET,
    )


def get_stripe_payment_service(
    gateway: StripeGatewayInterface = Depends(get_stripe_gateway),
    settings: Settings = Depends(get_settings),
) -> StripePaymentService:
    return StripePaymentService(
        gateway,
        success_url=settings.STRIPE_SUCCESS_URL,
        cancel_url=settings.STRIPE_CANCEL_URL,
        currency=settings.STRIPE_CURRENCY,
    )
