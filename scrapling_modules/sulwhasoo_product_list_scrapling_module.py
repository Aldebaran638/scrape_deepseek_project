from __future__ import annotations

"""
Scrape Sulwhasoo list pages and then scrape each product detail page.

Workflow:
1. Start from input URL such as `.../skincare.html?page=3`.
2. Keep increasing page index (`tmp = 3, 4, 5, ...`).
3. For each page, find `.product-list-wrap` and extract `li a[href]`.
4. If current page has no `li a[href]`, stop the pagination loop.
5. Otherwise scrape all product detail pages and sleep 1.5s per product.
"""

import time
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from scrapling.fetchers import Fetcher

from scrapling_modules.sulwhasoo_scrapling_module import scrape_url as scrape_sulwhasoo_detail

_dynamic_import_error = ""
try:
    from scrapling.fetchers import DynamicFetcher
except Exception as import_exc:
    _dynamic_import_error = str(import_exc)

    class DynamicFetcher:  # type: ignore[no-redef]
        """Fallback shim when dynamic fetch dependencies are unavailable."""

        @staticmethod
        def fetch(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError(f"Dynamic fetcher is unavailable: {_dynamic_import_error}")


DEFAULT_CONTAINER = ".product-list-wrap"
DEFAULT_BASE_URL = "https://www.sulwhasoo.com"
DEFAULT_DELAY_SECONDS = 1.5


def _to_absolute_product_url(href: str, base_url: str = DEFAULT_BASE_URL) -> str:
    href = (href or "").strip()
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if not href:
        return ""
    if href.startswith("/"):
        return f"{base_url}{href}"
    return f"{base_url}/{href}"


def extract_product_hrefs(page: Any, container_selector: str = DEFAULT_CONTAINER) -> list[str]:
    """Extract unique href values from `.product-list-wrap li a`."""
    container = page.css(container_selector).first
    if not container:
        return []

    hrefs = container.css("li a::attr(href)").getall()
    unique_hrefs: list[str] = []
    seen: set[str] = set()
    for href in hrefs:
        cleaned = (href or "").strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        unique_hrefs.append(cleaned)
    return unique_hrefs


def _with_page(url: str, page: int) -> str:
    """Return URL with query parameter `page=<page>`."""
    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    query["page"] = [str(page)]
    encoded_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=encoded_query))


def _extract_start_page(url: str) -> int:
    """Read start page from URL query `page`. Default to 1."""
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    raw = query.get("page", ["1"])[0]
    try:
        page = int(raw)
        return page if page > 0 else 1
    except (TypeError, ValueError):
        return 1


def _fetch_list_page(url: str) -> tuple[Any, str, str]:
    """
    Fetch list page using dynamic fetch first, static fetch as fallback.

    Returns: (page_obj, source, dynamic_error)
    """
    try:
        page = DynamicFetcher.fetch(url, network_idle=True, timeout=60_000, verify=False)
        return page, "DynamicFetcher", ""
    except Exception as exc:
        page = Fetcher.get(url, timeout=60, verify=False)
        return page, "Fetcher (fallback)", str(exc)


def scrape_url(
    url: str,
    container_selector: str = DEFAULT_CONTAINER,
    base_url: str = DEFAULT_BASE_URL,
    delay_seconds: float = DEFAULT_DELAY_SECONDS,
    max_pages: int | None = None,
) -> dict[str, Any]:
    """
    Scrape a Sulwhasoo product list page, then scrape each product detail page.

    Returns:
    - url: list page URL
    - source: fetch source for list page (`DynamicFetcher` or `Fetcher (fallback)`)
    - dynamic_error: list page dynamic fetch error, if any
    - product_hrefs: extracted href list from `.product-list-wrap li a`
    - product_count: number of extracted links
    - products: per-product scrape results
    """
    start_page = _extract_start_page(url)
    tmp = start_page
    global_index = 0
    pages_scraped = 0

    all_product_hrefs: list[str] = []
    all_products: list[dict[str, Any]] = []
    pages: list[dict[str, Any]] = []

    while True:
        if max_pages is not None and max_pages > 0 and pages_scraped >= max_pages:
            break

        page_url = _with_page(url, tmp)
        page_obj, source, dynamic_error = _fetch_list_page(page_url)
        product_hrefs = extract_product_hrefs(page_obj, container_selector=container_selector)

        # Stop condition: no li/a href found in this page.
        if not product_hrefs:
            break

        page_products: list[dict[str, Any]] = []
        for href in product_hrefs:
            global_index += 1
            product_url = _to_absolute_product_url(href, base_url=base_url)
            try:
                product_data = scrape_sulwhasoo_detail(product_url)
                item = {
                    "index": global_index,
                    "href": href,
                    "product_url": product_url,
                    "data": product_data,
                }
            except Exception as exc:
                item = {
                    "index": global_index,
                    "href": href,
                    "product_url": product_url,
                    "error": str(exc),
                }

            page_products.append(item)
            all_products.append(item)
            all_product_hrefs.append(href)
            time.sleep(delay_seconds)

        pages.append(
            {
                "page": tmp,
                "url": page_url,
                "source": source,
                "dynamic_error": dynamic_error,
                "product_hrefs": product_hrefs,
                "product_count": len(product_hrefs),
                "products": page_products,
            }
        )
        pages_scraped += 1
        tmp += 1

    return {
        "url": url,
        "start_page": start_page,
        "max_pages": max_pages,
        "next_empty_page": tmp,
        "pages": pages,
        "product_hrefs": all_product_hrefs,
        "product_count": len(all_product_hrefs),
        "products": all_products,
    }
