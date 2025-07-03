"""
Goszakup API Client Package

Async client for interacting with Goszakup Open Data API (v2/v3).
"""

from app.goszakup_client.client import GoszakupClient
from app.goszakup_client.exceptions import (
    GoszakupAPIError,
    GoszakupRateLimitError,
    GoszakupAuthError,
    GoszakupTimeoutError,
)

__all__ = [
    "GoszakupClient",
    "GoszakupAPIError",
    "GoszakupRateLimitError",
    "GoszakupAuthError", 
    "GoszakupTimeoutError",
] 