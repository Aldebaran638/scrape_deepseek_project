from __future__ import annotations

# 本模块用于抓取 Sulwhasoo（雪花秀）商品页面中的价格与容量相关信息。
# 说明：
# 1. 默认抓取商品价格容器（.prd-price-wrap.color-chip-none）。
# 2. 优先使用 DynamicFetcher（动态渲染）；失败后自动回退到 Fetcher（静态抓取）。
# 3. 返回结构化结果，便于后续传给下游模型或入库处理。

import re
from typing import Any, Iterable

from scrapling.fetchers import Fetcher

try:
    from scrapling.fetchers import DynamicFetcher
except Exception as import_exc:
    class DynamicFetcher:  # type: ignore[no-redef]
        """Fallback shim when optional dynamic dependencies are unavailable."""

        @staticmethod
        def fetch(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError(f"Dynamic fetcher is unavailable: {import_exc}")

DEFAULT_CONTAINER = ".prd-price-wrap.color-chip-none"


def normalize_texts(texts: Iterable[str]) -> list[str]:
    """Normalize whitespace and drop empty strings."""
    result: list[str] = []
    for t in texts:
        t = re.sub(r"\s+", " ", t).strip()
        if t:
            result.append(t)
    return result


def extract_from_page(page: Any, container_selector: str = DEFAULT_CONTAINER) -> dict[str, list[str] | str]:
    """Extract text and numeric candidates from the target container."""
    block = page.css(container_selector).first or page.css(".prd-price-wrap").first
    if not block:
        return {"all_texts": [], "joined_text": "", "price_candidates": [], "amount_candidates": []}

    all_texts = normalize_texts(block.css("::text").getall())
    price_candidates = normalize_texts(block.css("[data-price]::attr(data-price)").getall())
    amount_candidates = normalize_texts(block.css("[data-sapcd]::text").getall())

    return {
        "all_texts": all_texts,
        "joined_text": " | ".join(all_texts),
        "price_candidates": price_candidates,
        "amount_candidates": amount_candidates,
    }


def scrape_url(url: str, container_selector: str = DEFAULT_CONTAINER) -> dict[str, Any]:
    """Scrape URL and return structured extraction output."""
    try:
        page = DynamicFetcher.fetch(url, network_idle=True, timeout=60_000, verify=False)
        source = "DynamicFetcher"
        dynamic_error = ""
    except Exception as exc:
        page = Fetcher.get(url, timeout=60)
        source = "Fetcher (fallback)"
        dynamic_error = str(exc)

    data = extract_from_page(page, container_selector=container_selector)
    return {
        "url": url,
        "source": source,
        "dynamic_error": dynamic_error,
        **data,
    }
