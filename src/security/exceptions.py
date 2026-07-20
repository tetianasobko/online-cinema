class InvalidTokenError(Exception):
    """Raised when a JWT cannot be decoded or verified."""


class TokenExpiredError(InvalidTokenError):
    """Raised when a JWT has expired."""
