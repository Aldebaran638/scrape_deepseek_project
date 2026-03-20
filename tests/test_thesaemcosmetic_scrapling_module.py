from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# Ensure project root is importable when this test file is run directly.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scrapling_modules import thesaemcosmetic_scrapling_module as target_module


class _FakeCssCall:
    def __init__(self, first):
        self.first = first


class _FakeContainer:
    def __init__(self, html: str):
        self.html = html


class _FakePage:
    def __init__(self, container=None):
        self._container = container

    def css(self, selector: str):
        if selector == target_module.DEFAULT_CONTAINER:
            return _FakeCssCall(self._container)
        return _FakeCssCall(None)


DETAIL_INFOR_HTML = """
<div class="detail_infor">
  <span>상품정보고시</span>
  <table>
    <tbody>
      <tr><th>용량/중량</th><td>4.5g</td></tr>
      <tr><th>제품 주요 사양</th><td>모든 피부용</td></tr>
      <tr><th>사용상주의사항</th><td><ul><li>직사광선을 피하세요</li><li>어린이 손이 닿지 않는 곳에 보관</li></ul></td></tr>
    </tbody>
  </table>
</div>
"""


class TestThesaemcosmeticScraplingModule(unittest.TestCase):
    def test_extract_from_page_success(self):
        page = _FakePage(_FakeContainer(DETAIL_INFOR_HTML))
        data = target_module.extract_from_page(page)

        self.assertEqual(data["title"], "상품정보고시")
        self.assertEqual(data["field_count"], 3)
        self.assertEqual(data["field_map"]["용량/중량"], "4.5g")
        self.assertIn("사용상주의사항", data["field_map"])
        self.assertTrue(data["joined_text"])

    def test_extract_from_page_no_container(self):
        page = _FakePage(None)
        data = target_module.extract_from_page(page)
        self.assertEqual(data["field_count"], 0)
        self.assertEqual(data["fields"], [])
        self.assertEqual(data["joined_text"], "")

    @patch("scrapling_modules.thesaemcosmetic_scrapling_module.extract_from_page")
    @patch("scrapling_modules.thesaemcosmetic_scrapling_module.DynamicFetcher.fetch")
    def test_scrape_url_dynamic_success(self, mock_fetch, mock_extract):
        mock_fetch.return_value = object()
        mock_extract.return_value = {
            "title": "상품정보고시",
            "fields": [],
            "field_map": {},
            "all_texts": [],
            "joined_text": "",
            "field_count": 0,
        }

        data = target_module.scrape_url("https://example.com")
        self.assertEqual(data["source"], "DynamicFetcher")
        self.assertEqual(data["dynamic_error"], "")


if __name__ == "__main__":
    unittest.main()

