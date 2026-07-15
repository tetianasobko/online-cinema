import os

from security.interfaces import JWTAuthManagerInterface
from security.token_manager import JWTAuthManager


def get_jwt_auth_manager() -> JWTAuthManagerInterface:
    """Create a JWT manager using environment configuration."""
    return JWTAuthManager(
        secret_key_access=os.getenv(
            "JWT_ACCESS_SECRET",
            "change-this-access-secret",
        ),
        secret_key_refresh=os.getenv(
            "JWT_REFRESH_SECRET",
            "change-this-refresh-secret",
        ),
        algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
    )
