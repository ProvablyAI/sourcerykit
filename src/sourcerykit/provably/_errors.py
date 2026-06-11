from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx

from sourcerykit.errors import SourceryKitError
from sourcerykit.logger import get_logger

_log = get_logger(__name__)


class ProvablyError(SourceryKitError):
    """Base exception for all SourceryKit Provably errors."""

    pass


class ProvablyAPIError(ProvablyError):
    """Raised when the Provably API returns a 4xx or 5xx response."""

    def __init__(self, message: str, status_code: int | None = None, response_body: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class ProvablyConnectionError(ProvablyError):
    """Raised when the Provably API is unreachable (Network/Timeout)."""

    pass


class ProvablyDataError(ProvablyError):
    """Raised when the API response is malformed or invalid."""

    pass


@asynccontextmanager
async def provably_error_handler(service: str) -> AsyncIterator[None]:
    """
    Standardizes error handling and logging across service methods.

    Args:
        service: A slug representing the operation.
    """
    service_name = service.replace("_", " ")
    try:
        yield
    except httpx.HTTPStatusError as e:
        # Log API failures
        _log.error(
            f"provably_api_rejected_{service}",
            status_code=e.response.status_code,
            path=str(e.request.url),
            response=e.response.text[:500],
        )
        raise ProvablyAPIError(
            message=f"Provably API rejected {service_name}: {e.response.text}",
            status_code=e.response.status_code,
            response_body=e.response.text,
        ) from e

    except (ValueError, TypeError, KeyError) as e:
        # Log data corruption or unexpected schema changes
        _log.error(f"provably_data_invalid_{service}", error=str(e))
        raise ProvablyDataError(f"Provably API returned invalid data for {service_name}: {e}") from e

    except httpx.RequestError as e:
        # Log network-level failures
        _log.error(f"provably_network_unreachable_{service}", error=str(e))
        raise ProvablyConnectionError(f"Could not reach Provably API to perform {service_name}.") from e

    except Exception as e:
        _log.error(f"provably_unexpected_error_{service}", error=str(e))
        raise ProvablyError(f"Unexpected error during {service_name}: {e}") from e
