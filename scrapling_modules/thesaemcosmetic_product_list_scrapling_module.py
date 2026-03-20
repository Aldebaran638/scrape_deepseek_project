from __future__ import annotations

"""
The SAEM 列表页抓取模块。

功能：
1. 输入列表页 URL（例如 `.../product/index.php?&sort=&sca=&page=3`）。
2. 从 page=3 开始递增分页抓取（tmp=3,4,5...）。
3. 在 `.wrapper ul.item-list` 下提取每个 `li a[href]`。
4. 当当前页不存在 `li a[href]` 时，停止循环。
5. 对每个商品链接调用 `thesaemcosmetic_scrapling_module.scrape_url` 抓详情。
6. 每条详情抓取之间 sleep 1.5 秒，避免请求过频。
"""

import time
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from scrapling.fetchers import Fetcher

from scrapling_modules.thesaemcosmetic_scrapling_module import scrape_url as scrape_thesaem_detail

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


DEFAULT_WRAPPER_SELECTOR = ".wrapper"
DEFAULT_LIST_SELECTOR = "ul.item-list"
DEFAULT_BASE_URL = "https://www.thesaemcosmetic.com"
DEFAULT_DELAY_SECONDS = 1.5


def _to_absolute_url(href: str, base_url: str = DEFAULT_BASE_URL) -> str:
    href = (href or "").strip()
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if not href:
        return ""
    if href.startswith("/"):
        return f"{base_url}{href}"
    return f"{base_url}/{href}"


def _extract_start_page(url: str) -> int:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    raw_page = query.get("page", ["1"])[0]
    try:
        page = int(raw_page)
        return page if page > 0 else 1
    except (TypeError, ValueError):
        return 1


def _with_page(url: str, page: int) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    query["page"] = [str(page)]
    encoded_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=encoded_query))


def _fetch_list_page(url: str) -> tuple[Any, str, str]:
    try:
        page = DynamicFetcher.fetch(url, network_idle=True, timeout=60_000, verify=False)
        return page, "DynamicFetcher", ""
    except Exception as exc:
        page = Fetcher.get(url, timeout=60, verify=False)
        return page, "Fetcher (fallback)", str(exc)


def extract_item_hrefs(
    page: Any,
    wrapper_selector: str = DEFAULT_WRAPPER_SELECTOR,
    list_selector: str = DEFAULT_LIST_SELECTOR,
) -> list[str]:
    """
    从 `.wrapper ul.item-list li a[href]` 提取并去重链接。
    若 wrapper 未命中，回退尝试直接从 `ul.item-list` 提取。
    """
    wrapper = page.css(wrapper_selector).first
    list_block = wrapper.css(list_selector).first if wrapper else page.css(list_selector).first
    if not list_block:
        return []

    hrefs = list_block.css("li a::attr(href)").getall()
    unique_hrefs: list[str] = []
    seen: set[str] = set()
    for href in hrefs:
        cleaned = (href or "").strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        unique_hrefs.append(cleaned)
    return unique_hrefs


def scrape_url(
    url: str,
    wrapper_selector: str = DEFAULT_WRAPPER_SELECTOR,
    list_selector: str = DEFAULT_LIST_SELECTOR,
    base_url: str = DEFAULT_BASE_URL,
    delay_seconds: float = DEFAULT_DELAY_SECONDS,
    max_pages: int | None = None,
) -> dict[str, Any]:
    """
    分页抓取列表并抓取每个商品详情。

    停止条件：
    - 当前页 `ul.item-list` 下不存在 `li a[href]`。
    """
    start_page = _extract_start_page(url)
    tmp = start_page
    global_index = 0
    pages_scraped = 0

    pages: list[dict[str, Any]] = []
    all_hrefs: list[str] = []
    all_products: list[dict[str, Any]] = []

    while True:
        if max_pages is not None and max_pages > 0 and pages_scraped >= max_pages:
            break

        page_url = _with_page(url, tmp)
        list_page, source, dynamic_error = _fetch_list_page(page_url)
        hrefs = extract_item_hrefs(
            list_page,
            wrapper_selector=wrapper_selector,
            list_selector=list_selector,
        )

        if not hrefs:
            break

        page_products: list[dict[str, Any]] = []
        for href in hrefs:
            global_index += 1
            item_url = _to_absolute_url(href, base_url=base_url)
            try:
                detail_data = scrape_thesaem_detail(item_url)
                item = {
                    "index": global_index,
                    "href": href,
                    "item_url": item_url,
                    "data": detail_data,
                }
            except Exception as exc:
                item = {
                    "index": global_index,
                    "href": href,
                    "item_url": item_url,
                    "error": str(exc),
                }

            page_products.append(item)
            all_products.append(item)
            all_hrefs.append(href)
            time.sleep(delay_seconds)

        pages.append(
            {
                "page": tmp,
                "url": page_url,
                "source": source,
                "dynamic_error": dynamic_error,
                "item_hrefs": hrefs,
                "item_count": len(hrefs),
                "items": page_products,
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
        "item_hrefs": all_hrefs,
        "item_count": len(all_hrefs),
        "items": all_products,
    }
