"""Safe product-page fetching and text extraction helpers."""

from __future__ import annotations

import ipaddress
import json
import logging
import os
import re
import socket
import time
import traceback
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from errors import AppError


logger = logging.getLogger(__name__)


MAX_TEXT_CHARS = 12_000
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
REQUEST_TIMEOUT_SECONDS = 12
MAX_REDIRECTS = 5
DEMO_PAGES_DIR = Path(__file__).resolve().parent / "demo_pages"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
)
BLOCK_MARKERS = re.compile(
    r"captcha|robot\s+check|access\s+denied",
    re.IGNORECASE,
)
REDIRECT_STATUSES = {301, 302, 303, 307, 308}
BLOCKED_STATUSES = {403, 429, 503}


def _error(code: str, message: str, status: int = 400) -> AppError:
    return AppError(code, message, status)


def _allow_local_demo(url: str) -> bool:
    parsed = urlparse(url)
    allowed = os.getenv("ALLOW_LOCAL_DEMO", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return (
        allowed
        and parsed.scheme.lower() == "http"
        and (parsed.hostname or "").lower() in {"localhost", "127.0.0.1"}
        and parsed.path.startswith("/demo/")
    )


def _local_demo_path(url: str) -> Path:
    parsed = urlparse(url)
    filename = unquote(parsed.path[len("/demo/") :])
    if (
        not filename
        or filename in {".", ".."}
        or ".." in filename
        or "/" in filename
        or "\\" in filename
        or "\x00" in filename
        or Path(filename).name != filename
    ):
        raise _error(
            "BLOCKED_URL",
            "Local demo URLs must name one existing file directly inside demo_pages.",
        )

    demo_root = DEMO_PAGES_DIR.resolve()
    candidate = (demo_root / filename).resolve()
    if candidate.parent != demo_root or not candidate.is_file():
        raise _error("FETCH_FAILED", "The requested demo page does not exist.")
    return candidate


def _resolved_addresses(hostname: str, port: int) -> set[ipaddress._BaseAddress]:
    try:
        results = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, OSError) as exc:
        raise _error(
            "BLOCKED_URL",
            "The hostname could not be resolved safely.",
        ) from exc

    addresses: set[ipaddress._BaseAddress] = set()
    for result in results:
        try:
            addresses.add(ipaddress.ip_address(result[4][0]))
        except (ValueError, IndexError):
            continue
    if not addresses:
        raise _error("BLOCKED_URL", "The hostname did not resolve to an IP address.")
    return addresses


def validate_url(url: str) -> None:
    """Validate URL syntax and reject destinations that could enable SSRF."""

    if not isinstance(url, str) or not url.strip():
        raise _error("INVALID_URL", "Please provide a valid http or https URL.")

    try:
        parsed = urlparse(url.strip())
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise _error("INVALID_URL", "Please provide a valid http or https URL.") from exc

    if parsed.scheme.lower() not in {"http", "https"} or not hostname:
        raise _error("INVALID_URL", "URL scheme must be http or https.")
    if parsed.username or parsed.password:
        raise _error("INVALID_URL", "URLs with embedded credentials are not supported.")

    if _allow_local_demo(url.strip()):
        return

    addresses = _resolved_addresses(hostname, port or (443 if parsed.scheme == "https" else 80))
    blocked = [
        address
        for address in addresses
        if address.is_loopback or address.is_private or address.is_link_local
    ]
    if blocked:
        raise _error(
            "BLOCKED_URL",
            "Requests to loopback, private, or link-local addresses are not allowed.",
        )


def contains_block_marker(text: str) -> bool:
    """Return whether a response looks like a bot-check or access-denied page."""

    return bool(BLOCK_MARKERS.search(text or ""))


def _normalise_line(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def clean_manual_text(text: str) -> str:
    """Normalise pasted product text and cap it at the scraper's text limit."""

    if not isinstance(text, str):
        return ""
    normalised = re.sub(r"\s+", " ", text).strip()
    return normalised[:MAX_TEXT_CHARS]


def _json_ld_objects(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        objects = [value]
        graph = value.get("@graph")
        if isinstance(graph, list):
            objects.extend(item for item in graph if isinstance(item, dict))
        return objects
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _is_product(item: dict[str, Any]) -> bool:
    item_type = item.get("@type", "")
    types = item_type if isinstance(item_type, list) else [item_type]
    return any(str(value).rsplit("/", 1)[-1].lower() == "product" for value in types)


def _first_value(value: Any) -> Any:
    if isinstance(value, list):
        return value[0] if value else ""
    return value


def _value_text(value: Any) -> str:
    if isinstance(value, dict):
        if "name" in value:
            return _value_text(value["name"])
        if "value" in value:
            return _value_text(value["value"])
        return ""
    return _normalise_line(value)


def _add_line(lines: list[str], line: Any) -> None:
    cleaned = _normalise_line(line)
    if cleaned and cleaned not in lines:
        lines.append(cleaned)


def extract_text_from_html(html: str) -> str:
    """Extract structured product information followed by visible page text."""

    soup = BeautifulSoup(html or "", "html.parser")
    sections: list[tuple[str, list[str]]] = []

    metadata: list[str] = []
    if soup.title:
        _add_line(metadata, f"Title: {soup.title.get_text(' ', strip=True)}")
    meta_names = {
        "og:title": "Open Graph title",
        "og:description": "Open Graph description",
        "product:price": "Product price",
        "product:price:amount": "Product price",
        "product:price:currency": "Product price currency",
    }
    for tag in soup.find_all("meta"):
        key = (tag.get("property") or tag.get("name") or "").lower()
        label = meta_names.get(key)
        content = _normalise_line(tag.get("content"))
        if label and content:
            _add_line(metadata, f"{label}: {content}")
    if metadata:
        sections.append(("Page metadata", metadata))

    json_ld_lines: list[str] = []
    for script in soup.find_all("script", attrs={"type": re.compile(r"application/ld\+json", re.I)}):
        try:
            data = json.loads(script.string or script.get_text())
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        for product in _json_ld_objects(data):
            if not _is_product(product):
                continue
            _add_line(json_ld_lines, f"Product name: {_value_text(product.get('name'))}")
            _add_line(json_ld_lines, f"Brand: {_value_text(product.get('brand'))}")
            _add_line(json_ld_lines, f"Description: {_value_text(product.get('description'))}")
            offers = _first_value(product.get("offers"))
            if isinstance(offers, dict):
                _add_line(json_ld_lines, f"Price: {_value_text(offers.get('price'))}")
                _add_line(json_ld_lines, f"Price currency: {_value_text(offers.get('priceCurrency'))}")
            properties = product.get("additionalProperty", [])
            if isinstance(properties, dict):
                properties = [properties]
            property_items = properties if isinstance(properties, list) else []
            for prop in property_items:
                if isinstance(prop, dict):
                    name = _value_text(prop.get("name"))
                    value = _value_text(prop.get("value"))
                    if name and value:
                        _add_line(json_ld_lines, f"{name}: {value}")
            rating = product.get("aggregateRating")
            if isinstance(rating, dict):
                _add_line(json_ld_lines, f"Rating: {_value_text(rating.get('ratingValue'))}")
                _add_line(json_ld_lines, f"Review count: {_value_text(rating.get('reviewCount'))}")
    if json_ld_lines:
        sections.append(("Structured product data", json_ld_lines))

    specs: list[str] = []
    for row in soup.find_all("tr"):
        cells = [_normalise_line(cell.get_text(" ", strip=True)) for cell in row.find_all(["th", "td"])]
        cells = [cell for cell in cells if cell]
        if len(cells) >= 2:
            _add_line(specs, f"{cells[0]}: {' '.join(cells[1:])}")
        elif cells:
            _add_line(specs, cells[0])
    for definition in soup.find_all("dl"):
        terms = definition.find_all("dt")
        for term in terms:
            description = term.find_next_sibling("dd")
            if description:
                _add_line(
                    specs,
                    f"{term.get_text(' ', strip=True)}: {description.get_text(' ', strip=True)}",
                )
    feature_tokens = ("feature", "spec", "detail", "bullet")
    for element in soup.find_all(True):
        identity = " ".join(
            [str(element.get("id", "")), " ".join(str(item) for item in element.get("class", []))]
        ).lower()
        if any(token in identity for token in feature_tokens):
            for item in element.find_all("li"):
                _add_line(specs, item.get_text(" ", strip=True))
    if specs:
        sections.append(("Specifications and features", specs))

    body = soup.body or soup
    for element in body.find_all(["script", "style", "noscript", "template", "nav", "footer", "header"]):
        element.decompose()
    visible: list[str] = []
    for line in body.get_text("\n", strip=True).splitlines():
        _add_line(visible, line)
    if visible:
        sections.append(("Visible page text", visible))

    output_lines: list[str] = []
    seen: set[str] = set()
    for heading, lines in sections:
        if heading not in seen:
            output_lines.append(heading)
            seen.add(heading)
        for line in lines:
            if line not in seen:
                output_lines.append(line)
                seen.add(line)

    cleaned = "\n".join(output_lines)[:MAX_TEXT_CHARS].strip()
    useful_text = " ".join(line for line in output_lines if line not in {item[0] for item in sections})
    if len(useful_text) < 200:
        raise _error(
            "NO_PRODUCT_CONTENT",
            "The page did not contain enough useful product information.",
        )
    return cleaned


def _content_length(response: requests.Response) -> int | None:
    value = response.headers.get("Content-Length")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _response_text(response: requests.Response) -> str:
    content = bytearray()
    try:
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            remaining = MAX_RESPONSE_BYTES - len(content)
            if remaining <= 0:
                break
            content.extend(chunk[:remaining])
            if len(content) >= MAX_RESPONSE_BYTES:
                break
    finally:
        response.close()
    encoding = response.encoding or "utf-8"
    return bytes(content).decode(encoding, errors="replace")


def _log_fetch_failure(
    *,
    url: str,
    final_url: str,
    status: int | str | None,
    response_size: int,
    started_at: float,
    exc: BaseException,
) -> None:
    logger.error(
        "Fetch failed url=%s final_url=%s status=%s response_size=%s elapsed_seconds=%.3f "
        "exception_type=%s exception_message=%s traceback=%s",
        url,
        final_url,
        status,
        response_size,
        time.perf_counter() - started_at,
        type(exc).__name__,
        str(exc),
        "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)).strip(),
        exc_info=(type(exc), exc, exc.__traceback__),
    )


def _log_fetch_success(
    *,
    url: str,
    final_url: str,
    status: int | str | None,
    response_size: int,
    started_at: float,
) -> None:
    logger.info(
        "Fetched url=%s final_url=%s status=%s response_size=%s elapsed_seconds=%.3f",
        url,
        final_url,
        status,
        response_size,
        time.perf_counter() - started_at,
    )


def fetch_product_text(url: str) -> tuple[str, int]:
    """Fetch and extract product text, applying URL, size, and block protections."""

    requested_url = url.strip() if isinstance(url, str) else url
    current_url = requested_url

    for redirect_number in range(MAX_REDIRECTS + 1):
        started_at = time.perf_counter()
        try:
            validate_url(current_url)
        except AppError as exc:
            _log_fetch_failure(
                url=current_url,
                final_url=current_url,
                status=None,
                response_size=0,
                started_at=started_at,
                exc=exc,
            )
            raise

        if _allow_local_demo(current_url):
            response_size = 0
            try:
                demo_path = _local_demo_path(current_url)
                html = demo_path.read_text(encoding="utf-8")
                response_size = len(html.encode("utf-8"))
                _log_fetch_success(
                    url=current_url,
                    final_url=current_url,
                    status="LOCAL_DEMO",
                    response_size=response_size,
                    started_at=started_at,
                )
                if contains_block_marker(html):
                    raise _error(
                        "PAGE_BLOCKED",
                        "This page appears to block automated access. Please paste the page text instead.",
                    )
                cleaned = extract_text_from_html(html)
                return cleaned, len(cleaned)
            except AppError as exc:
                _log_fetch_failure(
                    url=current_url,
                    final_url=current_url,
                    status="LOCAL_DEMO",
                    response_size=response_size,
                    started_at=started_at,
                    exc=exc,
                )
                raise
            except (OSError, UnicodeError) as exc:
                _log_fetch_failure(
                    url=current_url,
                    final_url=current_url,
                    status="LOCAL_DEMO",
                    response_size=0,
                    started_at=started_at,
                    exc=exc,
                )
                raise _error("FETCH_FAILED", "The product page could not be fetched.") from exc

        response: requests.Response | None = None
        try:
            response = requests.get(
                current_url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept-Language": "en-IN,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
                timeout=REQUEST_TIMEOUT_SECONDS,
                stream=True,
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            _log_fetch_failure(
                url=current_url,
                final_url=current_url,
                status=None,
                response_size=0,
                started_at=started_at,
                exc=exc,
            )
            raise _error("FETCH_FAILED", "The product page could not be fetched.") from exc

        final_url = response.url or current_url
        response_size = _content_length(response) or 0

        if response.status_code in REDIRECT_STATUSES:
            _log_fetch_success(
                url=current_url,
                final_url=final_url,
                status=response.status_code,
                response_size=response_size,
                started_at=started_at,
            )
            location = response.headers.get("Location") or response.headers.get("location")
            response.close()
            if not location or redirect_number >= MAX_REDIRECTS:
                exc = _error("FETCH_FAILED", "The product page redirected too many times.")
                _log_fetch_failure(
                    url=current_url,
                    final_url=final_url,
                    status=response.status_code,
                    response_size=response_size,
                    started_at=started_at,
                    exc=exc,
                )
                raise exc
            current_url = urljoin(current_url, location)
            continue

        if response.status_code in BLOCKED_STATUSES:
            response.close()
            exc = _error(
                "PAGE_BLOCKED",
                "This page appears to block automated access. Please paste the page text instead.",
            )
            _log_fetch_failure(
                url=current_url,
                final_url=final_url,
                status=response.status_code,
                response_size=response_size,
                started_at=started_at,
                exc=exc,
            )
            raise exc
        if response.status_code >= 400:
            response.close()
            exc = _error("FETCH_FAILED", f"The product page returned HTTP {response.status_code}.")
            _log_fetch_failure(
                url=current_url,
                final_url=final_url,
                status=response.status_code,
                response_size=response_size,
                started_at=started_at,
                exc=exc,
            )
            raise exc

        try:
            html = _response_text(response)
            response_size = len(html.encode(response.encoding or "utf-8", errors="replace"))
            _log_fetch_success(
                url=current_url,
                final_url=final_url,
                status=response.status_code,
                response_size=response_size,
                started_at=started_at,
            )
        except requests.RequestException as exc:
            _log_fetch_failure(
                url=current_url,
                final_url=final_url,
                status=response.status_code,
                response_size=response_size,
                started_at=started_at,
                exc=exc,
            )
            raise _error("FETCH_FAILED", "The product page could not be fetched.") from exc
        if contains_block_marker(html):
            exc = _error(
                "PAGE_BLOCKED",
                "This page appears to block automated access. Please paste the page text instead.",
            )
            _log_fetch_failure(
                url=current_url,
                final_url=final_url,
                status=response.status_code,
                response_size=response_size,
                started_at=started_at,
                exc=exc,
            )
            raise exc
        try:
            cleaned = extract_text_from_html(html)
        except AppError as exc:
            _log_fetch_failure(
                url=current_url,
                final_url=final_url,
                status=response.status_code,
                response_size=response_size,
                started_at=started_at,
                exc=exc,
            )
            raise
        return cleaned, len(cleaned)

    exc = _error("FETCH_FAILED", "The product page could not be fetched.")
    _log_fetch_failure(
        url=requested_url,
        final_url=current_url,
        status=None,
        response_size=0,
        started_at=time.perf_counter(),
        exc=exc,
    )
    raise exc


__all__ = [
    "clean_manual_text",
    "contains_block_marker",
    "extract_text_from_html",
    "fetch_product_text",
    "validate_url",
]
