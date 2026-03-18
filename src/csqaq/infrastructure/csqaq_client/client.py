import asyncio
import logging
import time

import httpx

from .errors import (
    CSQAQAuthError,
    CSQAQClientError,
    CSQAQRateLimitError,
    CSQAQServerError,
    CSQAQValidationError,
)

logger = logging.getLogger(__name__)

# Errors that should NOT be retried
_NO_RETRY_CODES = {401, 403, 422}

# Errors that SHOULD be retried
_RETRY_CODES = {429, 500, 502, 503, 504}


class CSQAQClient:
    """Async HTTP client for CSQAQ API with rate limiting and retry."""

    def __init__(
        self,
        base_url: str,
        api_token: str,
        rate_limit: float = 1.0,
        max_retries: int = 3,
        timeout: float = 30.0,
    ):
        self._base_url = base_url.rstrip("/")
        self._api_token = api_token
        self._max_retries = max_retries
        self._min_interval = 1.0 / rate_limit
        self._last_request_time = 0.0
        self._lock = asyncio.Lock()
        self._http = httpx.AsyncClient(
            timeout=timeout,
            headers={"ApiToken": api_token, "Content-Type": "application/json"},
        )

    async def _wait_for_rate_limit(self) -> None:
        """Token bucket: ensure minimum interval between requests."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            self._last_request_time = time.monotonic()

    async def post(self, path: str, json: dict, priority: int = 0) -> dict:
        """Send POST request with rate limiting and retry.

        Args:
            path: API endpoint path (e.g. "/info/good")
            json: Request body
            priority: Request priority (0=interactive, 1=alert, 2=background)

        Returns:
            The 'data' field from the API response.

        Raises:
            CSQAQAuthError: 401/403
            CSQAQValidationError: 422
            CSQAQRateLimitError: 429 after retries exhausted
            CSQAQServerError: 5xx after retries exhausted
        """
        url = f"{self._base_url}{path}"
        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            await self._wait_for_rate_limit()
            try:
                response = await self._http.post(url, json=json)
            except httpx.TransportError as e:
                last_error = CSQAQClientError(f"Network error: {e}")
                if attempt < self._max_retries:
                    await self._backoff(attempt)
                    continue
                raise last_error from e

            if response.status_code == 200:
                body = response.json()
                return body.get("data", body)

            # Non-retryable errors
            if response.status_code in (401, 403):
                raise CSQAQAuthError(
                    f"Authentication failed: {response.text}",
                    status_code=response.status_code,
                )
            if response.status_code == 422:
                raise CSQAQValidationError(
                    f"Validation error: {response.text}",
                    status_code=422,
                )

            # Retryable errors
            if response.status_code in _RETRY_CODES:
                last_error = (
                    CSQAQRateLimitError("Rate limited", status_code=429)
                    if response.status_code == 429
                    else CSQAQServerError(
                        f"Server error {response.status_code}: {response.text}",
                        status_code=response.status_code,
                    )
                )
                if attempt < self._max_retries:
                    logger.warning(
                        "CSQAQ API %s returned %d, retry %d/%d",
                        path, response.status_code, attempt + 1, self._max_retries,
                    )
                    await self._backoff(attempt)
                    continue

            # Unknown status code
            if last_error is None:
                last_error = CSQAQClientError(
                    f"Unexpected status {response.status_code}: {response.text}",
                    status_code=response.status_code,
                )
            break

        raise last_error  # type: ignore[misc]

    async def _backoff(self, attempt: int) -> None:
        delay = min(2**attempt * 0.5, 10.0)
        await asyncio.sleep(delay)

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    def __del__(self) -> None:
        if not self._http.is_closed:
            try:
                import asyncio
                loop = asyncio.get_running_loop()
                loop.create_task(self._http.aclose())
            except RuntimeError:
                pass
