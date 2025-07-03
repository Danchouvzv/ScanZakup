"""
Asynchronous Goszakup API Client

FAANG-grade implementation with rate limiting, retries, and comprehensive error handling.
"""

import asyncio
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, AsyncGenerator
from urllib.parse import urljoin, urlencode

import aiohttp
import structlog
from aiohttp import ClientTimeout, ClientSession

from app.core.config import settings
from app.goszakup_client.exceptions import (
    GoszakupAPIError,
    GoszakupRateLimitError,
    GoszakupAuthError,
    GoszakupTimeoutError,
    GoszakupServerError,
    GoszakupValidationError,
)

logger = structlog.get_logger()


class RateLimiter:
    """Rate limiter using token bucket algorithm."""
    
    def __init__(self, rate: int = 5, per: int = 1):
        """
        Initialize rate limiter.
        
        Args:
            rate: Number of requests allowed
            per: Time period in seconds
        """
        self.rate = rate
        self.per = per
        self.tokens = rate
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire a token, waiting if necessary."""
        async with self._lock:
            now = time.monotonic()
            time_passed = now - self.last_update
            self.last_update = now
            
            # Add tokens based on time passed
            tokens_to_add = time_passed * (self.rate / self.per)
            self.tokens = min(self.rate, self.tokens + tokens_to_add)
            
            if self.tokens >= 1:
                self.tokens -= 1
                return
            
            # Wait until we can get a token
            wait_time = (1 - self.tokens) * (self.per / self.rate)
            await asyncio.sleep(wait_time)
            self.tokens = 0


class GoszakupClient:
    """
    Asynchronous Goszakup API client.
    
    Features:
    - Rate limiting with exponential backoff
    - Automatic retries with circuit breaker
    - Comprehensive error handling
    - Both REST v2 and GraphQL v3 support
    - Request/response logging
    - Caching support
    """
    
    def __init__(
        self,
        token: str = None,
        base_url: str = None,
        graphql_url: str = None,
        rate_limit: int = None,
        timeout: int = None,
        max_retries: int = None,
        session: ClientSession = None,
    ):
        """
        Initialize Goszakup API client.
        
        Args:
            token: API authentication token
            base_url: Base URL for REST API
            graphql_url: GraphQL endpoint URL
            rate_limit: Requests per second limit
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
            session: Existing aiohttp session (optional)
        """
        self.token = token or settings.GOSZAKUP_API_TOKEN
        self.base_url = base_url or settings.GOSZAKUP_API_BASE_URL
        self.graphql_url = graphql_url or settings.GOSZAKUP_GRAPHQL_URL
        self.timeout = timeout or settings.GOSZAKUP_TIMEOUT
        self.max_retries = max_retries or settings.GOSZAKUP_MAX_RETRIES
        
        # Rate limiting
        rate_limit = rate_limit or settings.GOSZAKUP_RATE_LIMIT
        self.rate_limiter = RateLimiter(rate=rate_limit, per=1)
        
        # Session management
        self._session = session
        self._session_created = False
        
        # Circuit breaker state
        self._circuit_open = False
        self._circuit_failures = 0
        self._circuit_last_failure = None
        self._circuit_timeout = 60  # seconds
        
        # Request cache
        self._cache: Dict[str, tuple] = {}
        self._cache_ttl = settings.CACHE_TTL_SECONDS if settings.ENABLE_CACHING else 0
    
    @property
    def session(self) -> ClientSession:
        """Get or create HTTP session."""
        if self._session is None:
            timeout = ClientTimeout(total=self.timeout)
            headers = {
                "Authorization": f"Bearer {self.token}",
                "User-Agent": f"ScanZakup/{settings.APP_VERSION}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            
            self._session = ClientSession(
                timeout=timeout,
                headers=headers,
                connector=aiohttp.TCPConnector(limit=20, ttl_dns_cache=300),
            )
            self._session_created = True
        
        return self._session
    
    async def close(self):
        """Close HTTP session."""
        if self._session and self._session_created:
            await self._session.close()
            self._session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    def _get_cache_key(self, url: str, params: dict = None) -> str:
        """Generate cache key for request."""
        key_data = f"{url}:{params or {}}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _is_cache_valid(self, timestamp: datetime) -> bool:
        """Check if cached data is still valid."""
        if self._cache_ttl <= 0:
            return False
        return (datetime.utcnow() - timestamp).total_seconds() < self._cache_ttl
    
    async def _check_circuit_breaker(self):
        """Check circuit breaker state."""
        if not self._circuit_open:
            return
        
        # Check if circuit should be closed
        if (
            self._circuit_last_failure
            and (time.monotonic() - self._circuit_last_failure) > self._circuit_timeout
        ):
            self._circuit_open = False
            self._circuit_failures = 0
            logger.info("Circuit breaker closed, resuming requests")
        else:
            raise GoszakupAPIError("Circuit breaker is open, requests blocked")
    
    def _record_failure(self):
        """Record circuit breaker failure."""
        self._circuit_failures += 1
        self._circuit_last_failure = time.monotonic()
        
        if self._circuit_failures >= 5:  # Open circuit after 5 failures
            self._circuit_open = True
            logger.warning("Circuit breaker opened due to failures")
    
    def _record_success(self):
        """Record circuit breaker success."""
        if self._circuit_failures > 0:
            self._circuit_failures = max(0, self._circuit_failures - 1)
    
    async def _make_request(
        self,
        method: str,
        url: str,
        params: dict = None,
        data: dict = None,
        headers: dict = None,
    ) -> dict:
        """
        Make HTTP request with rate limiting and error handling.
        
        Args:
            method: HTTP method
            url: Request URL
            params: Query parameters
            data: Request body data
            headers: Additional headers
            
        Returns:
            Response data as dictionary
            
        Raises:
            Various GoszakupAPIError subclasses
        """
        await self._check_circuit_breaker()
        
        # Check cache
        cache_key = self._get_cache_key(url, params)
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if self._is_cache_valid(cached_time):
                logger.debug("Cache hit", url=url, cache_key=cache_key)
                return cached_data
        
        # Rate limiting
        await self.rate_limiter.acquire()
        
        # Prepare request
        full_url = urljoin(self.base_url, url) if not url.startswith("http") else url
        request_headers = headers or {}
        
        start_time = time.monotonic()
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(
                    "Making API request",
                    method=method,
                    url=full_url,
                    params=params,
                    attempt=attempt + 1,
                )
                
                async with self.session.request(
                    method=method,
                    url=full_url,
                    params=params,
                    json=data,
                    headers=request_headers,
                ) as response:
                    response_time = int((time.monotonic() - start_time) * 1000)
                    
                    # Handle different response codes
                    if response.status == 200:
                        response_data = await response.json()
                        
                        # Cache successful response
                        if self._cache_ttl > 0:
                            self._cache[cache_key] = (response_data, datetime.utcnow())
                        
                        self._record_success()
                        
                        logger.info(
                            "API request successful",
                            url=full_url,
                            status=response.status,
                            response_time_ms=response_time,
                        )
                        
                        return response_data
                    
                    elif response.status == 401:
                        raise GoszakupAuthError("Invalid or expired token")
                    
                    elif response.status == 429:
                        retry_after = int(response.headers.get("Retry-After", 60))
                        if attempt < self.max_retries:
                            logger.warning(
                                "Rate limit hit, waiting",
                                retry_after=retry_after,
                                attempt=attempt + 1,
                            )
                            await asyncio.sleep(retry_after)
                            continue
                        else:
                            raise GoszakupRateLimitError(retry_after=retry_after)
                    
                    elif 500 <= response.status < 600:
                        error_text = await response.text()
                        if attempt < self.max_retries:
                            wait_time = 2 ** attempt  # Exponential backoff
                            logger.warning(
                                "Server error, retrying",
                                status=response.status,
                                wait_time=wait_time,
                                attempt=attempt + 1,
                            )
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            raise GoszakupServerError(
                                f"Server error: {error_text}",
                                status_code=response.status
                            )
                    
                    else:
                        error_text = await response.text()
                        raise GoszakupAPIError(
                            f"HTTP {response.status}: {error_text}",
                            status_code=response.status
                        )
            
            except asyncio.TimeoutError:
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt
                    logger.warning(
                        "Request timeout, retrying",
                        wait_time=wait_time,
                        attempt=attempt + 1,
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    self._record_failure()
                    raise GoszakupTimeoutError()
            
            except Exception as e:
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt
                    logger.warning(
                        "Request failed, retrying",
                        error=str(e),
                        wait_time=wait_time,
                        attempt=attempt + 1,
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    self._record_failure()
                    raise GoszakupAPIError(f"Request failed: {str(e)}")
        
        # This should never be reached
        self._record_failure()
        raise GoszakupAPIError("Max retries exceeded")
    
    # REST API methods
    
    async def trd_buy(self, **filters) -> List[dict]:
        """
        Get procurement announcements (trd_buy).
        
        Args:
            **filters: Query filters (bin, year, product_name, etc.)
            
        Returns:
            List of procurement announcements
        """
        return await self._paginated_request("trd_buy", **filters)
    
    async def lots(self, trd_buy_id: int = None, **filters) -> List[dict]:
        """
        Get procurement lots.
        
        Args:
            trd_buy_id: Parent procurement ID
            **filters: Additional filters
            
        Returns:
            List of lots
        """
        if trd_buy_id:
            filters["trd_buy_id"] = trd_buy_id
        return await self._paginated_request("lot", **filters)
    
    async def contracts(self, **filters) -> List[dict]:
        """
        Get contracts.
        
        Args:
            **filters: Query filters
            
        Returns:
            List of contracts
        """
        return await self._paginated_request("contract", **filters)
    
    async def participants(self, **filters) -> List[dict]:
        """
        Get participants.
        
        Args:
            **filters: Query filters
            
        Returns:
            List of participants
        """
        return await self._paginated_request("participant", **filters)
    
    async def _paginated_request(self, endpoint: str, **params) -> List[dict]:
        """
        Make paginated request to REST API.
        
        Args:
            endpoint: API endpoint name
            **params: Query parameters
            
        Returns:
            List of all items from paginated response
        """
        all_items = []
        page = 1
        limit = 100  # Maximum allowed by API
        
        while True:
            params.update({"page": page, "limit": limit})
            
            response = await self._make_request("GET", endpoint, params=params)
            
            items = response.get("items", [])
            if not items:
                break
            
            all_items.extend(items)
            
            # Check if there are more pages
            total = response.get("total", 0)
            if len(all_items) >= total or len(items) < limit:
                break
            
            page += 1
        
        logger.info(
            "Paginated request completed",
            endpoint=endpoint,
            total_items=len(all_items),
            pages=page,
        )
        
        return all_items
    
    # GraphQL methods
    
    async def graphql(self, query: str, variables: dict = None) -> dict:
        """
        Execute GraphQL query.
        
        Args:
            query: GraphQL query string
            variables: Query variables
            
        Returns:
            GraphQL response data
        """
        data = {"query": query}
        if variables:
            data["variables"] = variables
        
        response = await self._make_request(
            "POST",
            self.graphql_url,
            data=data,
        )
        
        if "errors" in response:
            errors = response["errors"]
            error_messages = [error.get("message", str(error)) for error in errors]
            raise GoszakupValidationError(
                f"GraphQL errors: {', '.join(error_messages)}",
                errors=errors
            )
        
        return response.get("data", {})
    
    # Utility methods
    
    async def health_check(self) -> dict:
        """
        Check API health.
        
        Returns:
            Health status information
        """
        try:
            response = await self._make_request("GET", "trd_buy", params={"limit": 1})
            return {
                "status": "healthy",
                "api_accessible": True,
                "total_records": response.get("total", 0),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "api_accessible": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
    
    async def get_statistics(self) -> dict:
        """
        Get basic API statistics.
        
        Returns:
            Statistics about available data
        """
        stats = {}
        
        try:
            # Get total counts for main entities
            endpoints = ["trd_buy", "lot", "contract", "participant"]
            
            for endpoint in endpoints:
                response = await self._make_request(
                    "GET", 
                    endpoint, 
                    params={"limit": 1}
                )
                stats[f"total_{endpoint}"] = response.get("total", 0)
            
            stats["timestamp"] = datetime.utcnow().isoformat()
            stats["status"] = "success"
            
        except Exception as e:
            stats["status"] = "error"
            stats["error"] = str(e)
        
        return stats 