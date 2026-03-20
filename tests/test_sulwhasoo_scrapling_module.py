from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# Ensure project root is importable when this test file is run directly.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scrapling_modules import sulwhasoo_scrapling_module as scrapling_module


class _FakeResult:
    def __init__(self, values):
        self._values = values

    def getall(self):
        return self._values


class _FakeBlock:
    def css(self, selector: str):
        mapping = {
            "::text": [" 150,000 ", "원", " ", "20g "],
            "[data-price]::attr(data-price)": ["150,000"],
            "[data-sapcd]::text": ["20g"],
        }
        return _FakeResult(mapping.get(selector, []))


class _FakeCssCall:
    def __init__(self, first):
        self.first = first


class _FakePage:
    def __init__(self, block=None):
        self._block = block

    def css(self, selector: str):
        if selector in (scrapling_module.DEFAULT_CONTAINER, ".prd-price-wrap"):
            return _FakeCssCall(self._block)
        return _FakeCssCall(None)


class TestScraplingModule(unittest.TestCase):
    def test_normalize_texts(self):
        values = ["  a   b ", "", " \n ", " c "]
        self.assertEqual(scrapling_module.normalize_texts(values), ["a b", "c"])

    def test_extract_from_page_success(self):
        page = _FakePage(block=_FakeBlock())
        data = scrapling_module.extract_from_page(page)
        self.assertEqual(data["all_texts"], ["150,000", "원", "20g"])
        self.assertEqual(data["price_candidates"], ["150,000"])
        self.assertEqual(data["amount_candidates"], ["20g"])

    @patch("scrapling_modules.sulwhasoo_scrapling_module.extract_from_page")
    @patch("scrapling_modules.sulwhasoo_scrapling_module.DynamicFetcher.fetch")
    def test_scrape_url_dynamic_success(self, mock_fetch, mock_extract):
        mock_fetch.return_value = object()
        mock_extract.return_value = {"all_texts": ["ok"], "joined_text": "ok", "price_candidates": [], "amount_candidates": []}
        data = scrapling_module.scrape_url("https://example.com")
        self.assertEqual(data["source"], "DynamicFetcher")
        self.assertEqual(data["dynamic_error"], "")


if __name__ == "__main__":
    unittest.main()
