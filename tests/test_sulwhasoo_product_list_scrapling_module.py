from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import call, patch

# Ensure project root is importable when this test file is run directly.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scrapling_modules import sulwhasoo_product_list_scrapling_module as target_module


class _FakeResult:
    def __init__(self, values):
        self._values = values

    def getall(self):
        return self._values


class _FakeContainer:
    def __init__(self, hrefs):
        self._hrefs = hrefs

    def css(self, selector: str):
        if selector == "li a::attr(href)":
            return _FakeResult(self._hrefs)
        return _FakeResult([])


class _FakeCssCall:
    def __init__(self, first):
        self.first = first


class _FakePage:
    def __init__(self, container=None):
        self._container = container

    def css(self, selector: str):
        if selector == target_module.DEFAULT_CONTAINER:
            return _FakeCssCall(self._container)
        return _FakeCssCall(None)


class TestSulwhasooProductListScraplingModule(unittest.TestCase):
    def test_to_absolute_product_url(self):
        self.assertEqual(
            target_module._to_absolute_product_url("/kr/ko/products/a.html"),
            "https://www.sulwhasoo.com/kr/ko/products/a.html",
        )
        self.assertEqual(
            target_module._to_absolute_product_url("kr/ko/products/b.html"),
            "https://www.sulwhasoo.com/kr/ko/products/b.html",
        )
        self.assertEqual(
            target_module._to_absolute_product_url("https://www.sulwhasoo.com/kr/ko/products/c.html"),
            "https://www.sulwhasoo.com/kr/ko/products/c.html",
        )

    def test_extract_start_page_and_with_page(self):
        url = "https://www.sulwhasoo.com/kr/ko/products/skincare/skincare.html?page=3"
        self.assertEqual(target_module._extract_start_page(url), 3)
        self.assertEqual(
            target_module._with_page(url, 4),
            "https://www.sulwhasoo.com/kr/ko/products/skincare/skincare.html?page=4",
        )
        self.assertEqual(
            target_module._extract_start_page("https://www.sulwhasoo.com/kr/ko/products/skincare/skincare.html"),
            1,
        )

    def test_extract_product_hrefs_deduplicate_and_filter_empty(self):
        page = _FakePage(
            _FakeContainer(
                [
                    " /kr/ko/products/a.html ",
                    "/kr/ko/products/a.html",
                    "",
                    "   ",
                    "/kr/ko/products/b.html",
                ]
            )
        )
        hrefs = target_module.extract_product_hrefs(page)
        self.assertEqual(hrefs, ["/kr/ko/products/a.html", "/kr/ko/products/b.html"])

    @patch("scrapling_modules.sulwhasoo_product_list_scrapling_module.time.sleep")
    @patch("scrapling_modules.sulwhasoo_product_list_scrapling_module.scrape_sulwhasoo_detail")
    @patch("scrapling_modules.sulwhasoo_product_list_scrapling_module._fetch_list_page")
    def test_scrape_url_pagination_from_page_3_until_empty(self, mock_fetch_page, mock_detail, mock_sleep):
        page_3 = _FakePage(_FakeContainer(["/kr/ko/products/a.html", "/kr/ko/products/b.html"]))
        page_4 = _FakePage(_FakeContainer(["/kr/ko/products/c.html"]))
        page_5 = _FakePage(_FakeContainer([]))  # stop condition

        mock_fetch_page.side_effect = [
            (page_3, "DynamicFetcher", ""),
            (page_4, "Fetcher (fallback)", "dynamic failed"),
            (page_5, "DynamicFetcher", ""),
        ]
        mock_detail.side_effect = [
            {"joined_text": "a"},
            {"joined_text": "b"},
            {"joined_text": "c"},
        ]

        start_url = "https://www.sulwhasoo.com/kr/ko/products/skincare/skincare.html?page=3"
        data = target_module.scrape_url(start_url)

        self.assertEqual(data["start_page"], 3)
        self.assertEqual(data["next_empty_page"], 5)
        self.assertEqual(data["product_count"], 3)
        self.assertEqual(len(data["products"]), 3)
        self.assertEqual(len(data["pages"]), 2)
        self.assertEqual(data["pages"][0]["page"], 3)
        self.assertEqual(data["pages"][1]["page"], 4)

        mock_fetch_page.assert_has_calls(
            [
                call("https://www.sulwhasoo.com/kr/ko/products/skincare/skincare.html?page=3"),
                call("https://www.sulwhasoo.com/kr/ko/products/skincare/skincare.html?page=4"),
                call("https://www.sulwhasoo.com/kr/ko/products/skincare/skincare.html?page=5"),
            ]
        )
        mock_detail.assert_has_calls(
            [
                call("https://www.sulwhasoo.com/kr/ko/products/a.html"),
                call("https://www.sulwhasoo.com/kr/ko/products/b.html"),
                call("https://www.sulwhasoo.com/kr/ko/products/c.html"),
            ]
        )
        self.assertEqual(mock_sleep.call_count, 3)
        mock_sleep.assert_has_calls([call(1.5), call(1.5), call(1.5)])

    @patch("scrapling_modules.sulwhasoo_product_list_scrapling_module.time.sleep")
    @patch("scrapling_modules.sulwhasoo_product_list_scrapling_module.scrape_sulwhasoo_detail")
    @patch("scrapling_modules.sulwhasoo_product_list_scrapling_module._fetch_list_page")
    def test_scrape_url_per_item_error_keeps_loop_running(self, mock_fetch_page, mock_detail, mock_sleep):
        page_1 = _FakePage(_FakeContainer(["/kr/ko/products/a.html", "/kr/ko/products/b.html"]))
        empty_page = _FakePage(_FakeContainer([]))
        mock_fetch_page.side_effect = [
            (page_1, "DynamicFetcher", ""),
            (empty_page, "DynamicFetcher", ""),
        ]
        mock_detail.side_effect = [RuntimeError("detail failed"), {"joined_text": "b"}]

        data = target_module.scrape_url("https://www.sulwhasoo.com/kr/ko/products/skincare/skincare.html?page=1")

        self.assertEqual(data["product_count"], 2)
        self.assertIn("error", data["products"][0])
        self.assertEqual(data["products"][1]["data"]["joined_text"], "b")
        self.assertEqual(mock_sleep.call_count, 2)

    @patch("scrapling_modules.sulwhasoo_product_list_scrapling_module.time.sleep")
    @patch("scrapling_modules.sulwhasoo_product_list_scrapling_module.scrape_sulwhasoo_detail")
    @patch("scrapling_modules.sulwhasoo_product_list_scrapling_module._fetch_list_page")
    def test_scrape_url_respects_max_pages(self, mock_fetch_page, mock_detail, mock_sleep):
        page_3 = _FakePage(_FakeContainer(["/kr/ko/products/a.html"]))
        page_4 = _FakePage(_FakeContainer(["/kr/ko/products/b.html"]))
        mock_fetch_page.side_effect = [
            (page_3, "DynamicFetcher", ""),
            (page_4, "DynamicFetcher", ""),
        ]
        mock_detail.side_effect = [{"joined_text": "a"}, {"joined_text": "b"}]

        data = target_module.scrape_url(
            "https://www.sulwhasoo.com/kr/ko/products/skincare/skincare.html?page=3",
            max_pages=1,
        )

        self.assertEqual(data["max_pages"], 1)
        self.assertEqual(data["product_count"], 1)
        self.assertEqual(data["next_empty_page"], 4)
        self.assertEqual(len(data["pages"]), 1)
        self.assertEqual(mock_fetch_page.call_count, 1)
        mock_detail.assert_called_once_with("https://www.sulwhasoo.com/kr/ko/products/a.html")
        mock_sleep.assert_called_once_with(1.5)


if __name__ == "__main__":
    unittest.main()
