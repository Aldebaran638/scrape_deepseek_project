from __future__ import annotations

"""
本模块用于抓取并结构化解析商品页面中 `class="detail_infor"` 区域的表格信息。

适用页面特征（与根目录 test.html 一致）：
1. 页面存在一个信息容器：`<div class="detail_infor"> ... </div>`。
2. 容器内通常包含一个标题（如“상품정보고시”）和一个 `<table>`。
3. 表格通常由多行 `<tr>` 组成，每行是 “字段名(th) + 字段值(td)” 的键值结构。
4. 某些字段值较长，可能包含 `<br>`、`<ul>`、多行文本等复杂内容。

设计目标：
1. 对外参数风格与现有 scrapling 模块一致：
   - `extract_from_page(page, container_selector=...)`
   - `scrape_url(url, container_selector=...)`
2. 返回稳定、可程序消费的结构化结果（字段列表 + 字段映射 + 纯文本汇总）。
3. 对动态抓取失败场景提供自动回退（DynamicFetcher -> Fetcher）。
4. 尽量清洗浏览器翻译插件注入节点，减少噪声文本对解析结果的污染。
"""

import re
from typing import Any, Iterable

from lxml import html as lxml_html
from scrapling.fetchers import Fetcher

try:
    from scrapling.fetchers import DynamicFetcher
except Exception as import_exc:
    class DynamicFetcher:  # type: ignore[no-redef]
        """当动态抓取依赖不可用时的占位回退类。"""

        @staticmethod
        def fetch(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError(f"Dynamic fetcher is unavailable: {import_exc}")


DEFAULT_CONTAINER = ".detail_infor"


def normalize_texts(texts: Iterable[str]) -> list[str]:
    """统一清洗文本：压缩空白、去掉空字符串，保留原有语义顺序。"""
    result: list[str] = []
    for t in texts:
        cleaned = re.sub(r"\s+", " ", t).strip()
        if cleaned:
            result.append(cleaned)
    return result


def _normalize_cell_text(raw_text: str) -> str:
    """对单个单元格文本进行标准化，确保结果适合入库或后续模型处理。"""
    return re.sub(r"\s+", " ", raw_text).strip()


def _extract_container_html(container: Any) -> str:
    """
    从 scrapling 节点对象中提取 HTML 字符串。

    兼容性说明：
    - 不同解析器对象可用属性不一致，因此按常见顺序尝试多个入口。
    - 若无法直接获取，最后回退到 `str(container)`。
    """
    for attr in ("html", "markup"):
        value = getattr(container, attr, None)
        if isinstance(value, str) and value.strip():
            return value

    if hasattr(container, "get"):
        try:
            value = container.get()
            if isinstance(value, str) and value.strip():
                return value
        except Exception:
            pass

    text = str(container)
    return text if isinstance(text, str) else ""


def _remove_noise_nodes(root: Any) -> None:
    """
    删除常见噪声节点，降低解析污染风险。

    主要处理两类噪声：
    1. 浏览器翻译插件注入节点（class 包含 immersive-translate-*）。
    2. 脚本与样式节点（script/style）。
    """
    for node in root.xpath(".//*[contains(@class, 'immersive-translate-')]"):
        parent = node.getparent()
        if parent is not None:
            parent.remove(node)

    for node in root.xpath(".//script | .//style"):
        parent = node.getparent()
        if parent is not None:
            parent.remove(node)


def extract_from_page(page: Any, container_selector: str = DEFAULT_CONTAINER) -> dict[str, Any]:
    """
    从页面对象中提取 `detail_infor` 区域并结构化输出表格数据。

    返回字段说明：
    - `title`: 区块标题（例如 상품정보고시）
    - `fields`: 有序字段列表，每项包含 index/label/value/value_lines
    - `field_map`: 字段字典（label -> value）
    - `all_texts`: 扁平化文本列表（用于快速检索或拼接）
    - `joined_text`: `all_texts` 的拼接字符串（分隔符 ` | `）
    - `field_count`: 解析到的字段数量
    """
    block = page.css(container_selector).first
    if not block:
        return {
            "title": "",
            "fields": [],
            "field_map": {},
            "all_texts": [],
            "joined_text": "",
            "field_count": 0,
        }

    container_html = _extract_container_html(block)
    if not container_html.strip():
        return {
            "title": "",
            "fields": [],
            "field_map": {},
            "all_texts": [],
            "joined_text": "",
            "field_count": 0,
        }

    root = lxml_html.fromstring(container_html)
    _remove_noise_nodes(root)

    title = _normalize_cell_text(" ".join(root.xpath(".//span[1]//text()")))
    rows = root.xpath(".//table//tr")

    fields: list[dict[str, Any]] = []
    field_map: dict[str, str] = {}
    all_texts: list[str] = [title] if title else []

    for idx, row in enumerate(rows, start=1):
        label_raw = " ".join(row.xpath("./th[1]//text()"))
        value_node = row.xpath("./td[1]")
        value_raw = " ".join(value_node[0].xpath(".//text()")) if value_node else ""

        label = _normalize_cell_text(label_raw)
        value = _normalize_cell_text(value_raw)
        if not label and not value:
            continue

        value_lines = normalize_texts(re.split(r"(?:\r?\n|<br\s*/?>)", value))
        if not value_lines and value:
            value_lines = [value]

        fields.append(
            {
                "index": idx,
                "label": label,
                "value": value,
                "value_lines": value_lines,
            }
        )

        if label:
            field_map[label] = value
            all_texts.append(label)
        if value:
            all_texts.append(value)

    normalized_texts = normalize_texts(all_texts)
    return {
        "title": title,
        "fields": fields,
        "field_map": field_map,
        "all_texts": normalized_texts,
        "joined_text": " | ".join(normalized_texts),
        "field_count": len(fields),
    }


def scrape_url(url: str, container_selector: str = DEFAULT_CONTAINER) -> dict[str, Any]:
    """
    抓取 URL 并解析 detail_infor 表格。

    参数风格与原 scrapling 模块一致：
    - `url`: 待抓取页面地址
    - `container_selector`: 信息容器选择器，默认 `.detail_infor`
    """
    try:
        page = DynamicFetcher.fetch(url, network_idle=True, timeout=60_000, verify=False)
        source = "DynamicFetcher"
        dynamic_error = ""
    except Exception as exc:
        page = Fetcher.get(url, timeout=60, verify=False)
        source = "Fetcher (fallback)"
        dynamic_error = str(exc)

    data = extract_from_page(page, container_selector=container_selector)
    return {
        "url": url,
        "source": source,
        "dynamic_error": dynamic_error,
        **data,
    }

