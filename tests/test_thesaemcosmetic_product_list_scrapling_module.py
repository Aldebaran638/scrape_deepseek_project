from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import call, patch

# Ensure project root is importable when this test file is run directly.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scrapling_modules import thesaemcosmetic_product_list_scrapling_module as target_module


class _FakeResult:
    def __init__(self, values):
        self._values = values

    def getall(self):
        return self._values


class _FakeListBlock:
    def __init__(self, hrefs):
        self._hrefs = hrefs

    def css(self, selector: str):
        if selector == "li a::attr(href)":
            return _FakeResult(self._hrefs)
        return _FakeResult([])


class _FakeWrapper:
    def __init__(self, list_block=None):
        self._list_block = list_block

    def css(self, selector: str):
        if selector == target_module.DEFAULT_LIST_SELECTOR:
            return _FakeCssCall(self._list_block)
        return _FakeCssCall(None)


class _FakeCssCall:
    def __init__(self, first):
        self.first = first


class _FakePage:
    def __init__(self, wrapper=None, list_block=None):
        self._wrapper = wrapper
        self._list_block = list_block

    def css(self, selector: str):
        if selector == target_module.DEFAULT_WRAPPER_SELECTOR:
            return _FakeCssCall(self._wrapper)
        if selector == target_module.DEFAULT_LIST_SELECTOR:
            return _FakeCssCall(self._list_block)
        return _FakeCssCall(None)


class TestThesaemcosmeticProductListScraplingModule(unittest.TestCase):
    def test_extract_start_page_and_with_page(self):
        url = "https://www.thesaemcosmetic.com/product/index.php?&sort=&sca=&page=3"
        self.assertEqual(target_module._extract_start_page(url), 3)
        self.assertEqual(
            target_module._with_page(url, 4),
            "https://www.thesaemcosmetic.com/product/index.php?sort=&sca=&page=4",
        )

    def test_extract_item_hrefs_from_wrapper(self):
        list_block = _FakeListBlock(
            [
                "https://www.thesaemcosmetic.com/product/item.php?it_id=1773133732",
                " https://www.thesaemcosmetic.com/product/item.php?it_id=1773133732 ",
                "",
                "https://www.thesaemcosmetic.com/product/item.php?it_id=1234567890",
            ]
        )
        wrapper = _FakeWrapper(list_block=list_block)
        page = _FakePage(wrapper=wrapper)

        hrefs = target_module.extract_item_hrefs(page)
        self.assertEqual(
            hrefs,
            [
                "https://www.thesaemcosmetic.com/product/item.php?it_id=1773133732",
                "https://www.thesaemcosmetic.com/product/item.php?it_id=1234567890",
            ],
        )

    def test_extract_item_hrefs_fallback_to_list(self):
        list_block = _FakeListBlock(["/product/item.php?it_id=1"])
        page = _FakePage(wrapper=None, list_block=list_block)
        hrefs = target_module.extract_item_hrefs(page)
        self.assertEqual(hrefs, ["/product/item.php?it_id=1"])

    @patch("scrapling_modules.thesaemcosmetic_product_list_scrapling_module.time.sleep")
    @patch("scrapling_modules.thesaemcosmetic_product_list_scrapling_module.scrape_thesaem_detail")
    @patch("scrapling_modules.thesaemcosmetic_product_list_scrapling_module._fetch_list_page")
    def test_scrape_url_pagination_until_empty(self, mock_fetch_page, mock_detail, mock_sleep):
        page_3 = _FakePage(wrapper=_FakeWrapper(_FakeListBlock(["/product/item.php?it_id=1"])))
        page_4 = _FakePage(wrapper=_FakeWrapper(_FakeListBlock(["/product/item.php?it_id=2"])))
        page_5 = _FakePage(wrapper=_FakeWrapper(_FakeListBlock([])))
        mock_fetch_page.side_effect = [
            (page_3, "DynamicFetcher", ""),
            (page_4, "Fetcher (fallback)", "dynamic failed"),
            (page_5, "DynamicFetcher", ""),
        ]
        mock_detail.side_effect = [{"joined_text": "p1"}, {"joined_text": "p2"}]

        start_url = "https://www.thesaemcosmetic.com/product/index.php?&sort=&sca=&page=3"
        data = target_module.scrape_url(start_url)

        self.assertEqual(data["start_page"], 3)
        self.assertEqual(data["next_empty_page"], 5)
        self.assertEqual(data["item_count"], 2)
        self.assertEqual(len(data["pages"]), 2)
        self.assertEqual(data["pages"][0]["page"], 3)
        self.assertEqual(data["pages"][1]["page"], 4)
        mock_fetch_page.assert_has_calls(
            [
                call("https://www.thesaemcosmetic.com/product/index.php?sort=&sca=&page=3"),
                call("https://www.thesaemcosmetic.com/product/index.php?sort=&sca=&page=4"),
                call("https://www.thesaemcosmetic.com/product/index.php?sort=&sca=&page=5"),
            ]
        )
        mock_detail.assert_has_calls(
            [
                call("https://www.thesaemcosmetic.com/product/item.php?it_id=1"),
                call("https://www.thesaemcosmetic.com/product/item.php?it_id=2"),
            ]
        )
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_has_calls([call(1.5), call(1.5)])

    @patch("scrapling_modules.thesaemcosmetic_product_list_scrapling_module.time.sleep")
    @patch("scrapling_modules.thesaemcosmetic_product_list_scrapling_module.scrape_thesaem_detail")
    @patch("scrapling_modules.thesaemcosmetic_product_list_scrapling_module._fetch_list_page")
    def test_scrape_url_item_error_keeps_loop_running(self, mock_fetch_page, mock_detail, mock_sleep):
        page_1 = _FakePage(wrapper=_FakeWrapper(_FakeListBlock(["/product/item.php?it_id=1", "/product/item.php?it_id=2"])))
        empty_page = _FakePage(wrapper=_FakeWrapper(_FakeListBlock([])))
        mock_fetch_page.side_effect = [
            (page_1, "DynamicFetcher", ""),
            (empty_page, "DynamicFetcher", ""),
        ]
        mock_detail.side_effect = [RuntimeError("detail failed"), {"joined_text": "ok"}]

        data = target_module.scrape_url("https://www.thesaemcosmetic.com/product/index.php?&sort=&sca=&page=1")
        self.assertEqual(data["item_count"], 2)
        self.assertIn("error", data["items"][0])
        self.assertEqual(data["items"][1]["data"]["joined_text"], "ok")
        self.assertEqual(mock_sleep.call_count, 2)

    @patch("scrapling_modules.thesaemcosmetic_product_list_scrapling_module.time.sleep")
    @patch("scrapling_modules.thesaemcosmetic_product_list_scrapling_module.scrape_thesaem_detail")
    @patch("scrapling_modules.thesaemcosmetic_product_list_scrapling_module._fetch_list_page")
    def test_scrape_url_respects_max_pages(self, mock_fetch_page, mock_detail, mock_sleep):
        page_3 = _FakePage(wrapper=_FakeWrapper(_FakeListBlock(["/product/item.php?it_id=1"])))
        page_4 = _FakePage(wrapper=_FakeWrapper(_FakeListBlock(["/product/item.php?it_id=2"])))
        mock_fetch_page.side_effect = [
            (page_3, "DynamicFetcher", ""),
            (page_4, "DynamicFetcher", ""),
        ]
        mock_detail.side_effect = [{"joined_text": "a"}, {"joined_text": "b"}]

        data = target_module.scrape_url(
            "https://www.thesaemcosmetic.com/product/index.php?&sort=&sca=&page=3",
            max_pages=1,
        )

        self.assertEqual(data["max_pages"], 1)
        self.assertEqual(data["item_count"], 1)
        self.assertEqual(data["next_empty_page"], 4)
        self.assertEqual(len(data["pages"]), 1)
        self.assertEqual(mock_fetch_page.call_count, 1)
        mock_detail.assert_called_once_with("https://www.thesaemcosmetic.com/product/item.php?it_id=1")
        mock_sleep.assert_called_once_with(1.5)


if __name__ == "__main__":
    unittest.main()
