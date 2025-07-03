"""
Custom exceptions for Goszakup API client.
"""


class GoszakupAPIError(Exception):
    """Base exception for Goszakup API errors."""
    
    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(self.message)


class GoszakupRateLimitError(GoszakupAPIError):
    """Raised when API rate limit is exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = None):
        self.retry_after = retry_after
        super().__init__(message, status_code=429)


class GoszakupAuthError(GoszakupAPIError):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)


class GoszakupTimeoutError(GoszakupAPIError):
    """Raised when request times out."""
    
    def __init__(self, message: str = "Request timeout"):
        super().__init__(message)


class GoszakupServerError(GoszakupAPIError):
    """Raised when server returns 5xx error."""
    
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message, status_code=status_code)


class GoszakupValidationError(GoszakupAPIError):
    """Raised when request validation fails."""
    
    def __init__(self, message: str, errors: list = None):
        self.errors = errors or []
        super().__init__(message, status_code=400) 