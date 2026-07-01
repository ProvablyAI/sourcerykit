import asyncio
from typing import Any
from urllib.parse import urlparse

from sourcerykit.config import get_settings
from sourcerykit.db._engine import get_engine
from sourcerykit.db._trusted_endpoints import (
    delete_trusted_endpoint,
    select_active_trusted_endpoints,
    select_trusted_endpoint_prefix,
)
from sourcerykit.db._trusted_endpoints import (
    insert_trusted_endpoint as db_insert_trusted_endpoint,
)
from sourcerykit.errors import SourceryKitStorageError, SourceryKitTrustError
from sourcerykit.logger import get_logger
from sourcerykit.schemas.handoff import HandoffPayload
from sourcerykit.utils.validation import validate_length

_log = get_logger(__name__)


def sanitize_and_extract_trusted_url(raw_url: str) -> str:
    """
    Parses a raw URL string and extracts only the scheme and netloc (domain).
    """
    clean_url = raw_url.strip()
    if not clean_url.startswith(("http://", "https://")):
        clean_url = "https://" + clean_url

    parsed = urlparse(clean_url)

    if not parsed.netloc:
        _log.warning("sanitize_url_invalid", raw_url=raw_url)
        raise SourceryKitTrustError("Invalid URL structure: Could not determine the host domain.")

    normalized_path = parsed.path.rstrip("/")

    return f"{parsed.scheme}://{parsed.netloc}{normalized_path}"


async def is_endpoint_trusted(url: str) -> bool:
    """
    Validates if a given URL is registered as an active trusted endpoint
    for the current organization.
    """
    # Sanitize input to isolate the scheme + netloc
    parsed_url = sanitize_and_extract_trusted_url(url)

    org_id = get_settings().org_id
    engine = get_engine()

    # Build SELECT statement
    stmt = select_trusted_endpoint_prefix(org_id, parsed_url)

    # Execute
    try:
        async with engine.connect() as conn:
            result = await conn.execute(stmt)
            return bool(result.scalar())
    except Exception as e:
        _log.error("is_endpoint_trusted_db_error", url=url, error=str(e))
        raise SourceryKitStorageError("Failed to query trusted endpoints") from e


async def insert_trusted_endpoint(*, url: str, display_label: str | None = None) -> None:
    """Insert an active trusted endpoint for the configured org, ignoring conflicts."""

    # Sanitize the URL string
    clean_url = sanitize_and_extract_trusted_url(url)

    # Validate optional display label length against DB column size
    validate_length("display_label", display_label, max_len=255, allow_none=True)

    org_id = get_settings().org_id
    engine = get_engine()

    # Insert statement
    stmt = db_insert_trusted_endpoint(org_id, clean_url, display_label)

    try:
        async with engine.begin() as conn:
            await conn.execute(stmt)
        _log.info("trusted_endpoint_inserted", url=clean_url)
    except Exception as e:
        _log.error("insert_trusted_endpoint_db_error", url=clean_url, error=str(e))
        raise SourceryKitStorageError("Failed to insert trusted endpoint") from e


async def list_all_trusted_endpoints_detailed() -> list[dict[str, Any]]:
    """
    Return all active trusted endpoints formatted with metadata and risk tracking.
    """
    org_id = get_settings().org_id
    engine = get_engine()

    # Compile the SELECT statement
    stmt = select_active_trusted_endpoints(org_id)

    # Execute
    try:
        async with engine.connect() as conn:
            result = await conn.execute(stmt)
            rows = result.fetchall()
    except Exception as e:
        _log.error("list_trusted_endpoints_db_error", error=str(e))
        raise SourceryKitStorageError("Failed to list trusted endpoints") from e

    detailed_list = []
    for row in rows:
        detailed_list.append(
            {
                "url": row.normalized_url,
                "label": row.display_label or row.normalized_url,
                "policy_version": row.policy_version or "v1",
                "created_by": row.created_by or "system",
                "category": "custom",
                "risk_level": "unknown",
                "description": f"Managed endpoint enforced under policy {row.policy_version}",
            }
        )

    return detailed_list


async def list_all_trusted_endpoints() -> list[str]:
    """
    Return all active trusted endpoints urls.
    """

    urls = await list_all_trusted_endpoints_detailed()
    return [ep["url"] for ep in urls]


async def remove_trusted_endpoint(*, url: str) -> None:
    """Remove an active trusted endpoint for the configured org."""

    # Sanitize the URL string
    clean_url = sanitize_and_extract_trusted_url(url)

    org_id = get_settings().org_id
    engine = get_engine()

    if not await is_endpoint_trusted(clean_url):
        raise SourceryKitTrustError(f"Endpoint '{clean_url}' is not trusted")

    # Remove statement
    stmt = delete_trusted_endpoint(org_id, clean_url)

    try:
        async with engine.begin() as conn:
            await conn.execute(stmt)
        _log.info("remove_endpoint_removed", url=clean_url)
    except Exception as e:
        _log.error("remove_trusted_endpoint_db_error", url=clean_url, error=str(e))
        raise SourceryKitStorageError("Failed to remove trusted endpoint") from e


async def verify_claim_endpoints(
    payload: HandoffPayload,
) -> None:
    """
    Validates that all URLs within the payload claims are authorized prefixes.

    Raises:
        ValueError: If one or more endpoint URLs fail the authorization guard.
    """

    # Extract and clean unique claim URLs
    claim_urls = {claim.request_payload["url"].strip() for claim in payload.claims if claim.request_payload.get("url")}

    if not claim_urls:
        return

    # Check authorization for all URLs
    results = await asyncio.gather(*(is_endpoint_trusted(url) for url in claim_urls))

    # Filter out the failures
    untrusted_found = [url for url, is_authorized in zip(claim_urls, results) if not is_authorized]

    # Raise an exception if any unauthorized endpoints were caught
    if untrusted_found:
        _log.warning("trust_gate_failed", untrusted_urls=untrusted_found)
        raise SourceryKitTrustError(f"handoff has untrusted endpoints: {', '.join(untrusted_found)}")

    _log.info("trust_gate_passed", url_count=len(claim_urls))
