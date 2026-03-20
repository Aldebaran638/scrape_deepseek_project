from __future__ import annotations

"""
Sulwhasoo 抓取模块。

目标：
1. 抓取商品价格/容量信息所在区域（默认 `.prd-price-wrap.color-chip-none`）。
2. 优先使用 DynamicFetcher（支持动态渲染），失败后回退到 Fetcher（静态请求）。
3. 返回统一结构，便于 main.py 汇总与后续模型处理。

返回结构：
- url: 当前抓取地址
- source: 实际使用的抓取器（DynamicFetcher 或 Fetcher (fallback)）
- dynamic_error: 动态抓取失败时的错误信息，成功时为空字符串
- all_texts: 容器内清洗后的文本列表
- joined_text: all_texts 的拼接文本（" | " 分隔）
- price_candidates: 从 data-price 属性提取的价格候选
- amount_candidates: 从 data-sapcd 节点提取的容量候选
"""

import re
from typing import Any, Iterable

from scrapling.fetchers import Fetcher

# 注意：不能在 fallback 类里直接引用 `except ... as import_exc` 变量。
# Python 会在 except 块结束后清理该变量，导致后续访问时报 NameError。
_dynamic_import_error = ""
try:
    from scrapling.fetchers import DynamicFetcher
except Exception as import_exc:
    _dynamic_import_error = str(import_exc)

    class DynamicFetcher:  # type: ignore[no-redef]
        """当 DynamicFetcher 依赖不可用时的占位回退类。"""

        @staticmethod
        def fetch(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError(f"Dynamic fetcher is unavailable: {_dynamic_import_error}")


DEFAULT_CONTAINER = ".prd-price-wrap.color-chip-none"


def normalize_texts(texts: Iterable[str]) -> list[str]:
    """压缩空白并过滤空字符串，保持原始顺序。"""
    result: list[str] = []
    for t in texts:
        t = re.sub(r"\s+", " ", t).strip()
        if t:
            result.append(t)
    return result


def extract_from_page(page: Any, container_selector: str = DEFAULT_CONTAINER) -> dict[str, list[str] | str]:
    """
    从目标容器提取文本与候选字段。

    回退策略：
    - 先使用 `container_selector`
    - 若未命中，再尝试 `.prd-price-wrap`
    """
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
    """
    抓取 URL 并输出结构化结果。

    执行流程：
    1. 先尝试 DynamicFetcher.fetch(...)
    2. 若抛异常，则改用 Fetcher.get(...) 并记录 dynamic_error
    """
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
