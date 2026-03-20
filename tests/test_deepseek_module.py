from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root is importable when this test file is run directly.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import deepseek_module


class TestDeepSeekModule(unittest.TestCase):
    @patch("deepseek_module.requests.post")
    def test_run_deepseek_success(self, mock_post):
        with tempfile.TemporaryDirectory() as td:
            prompt_path = Path(td) / "prompt.md"
            prompt_path.write_text("system prompt", encoding="utf-8")

            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
            mock_post.return_value = resp

            cfg = deepseek_module.DeepSeekConfig(api_key="k")
            out = deepseek_module.run_deepseek({"x": 1}, prompt_path, cfg)
            self.assertEqual(out, "ok")

    @patch("deepseek_module.requests.post")
    def test_run_deepseek_http_error(self, mock_post):
        with tempfile.TemporaryDirectory() as td:
            prompt_path = Path(td) / "prompt.md"
            prompt_path.write_text("system prompt", encoding="utf-8")

            resp = MagicMock()
            resp.status_code = 401
            resp.text = "unauthorized"
            mock_post.return_value = resp

            cfg = deepseek_module.DeepSeekConfig(api_key="k")
            with self.assertRaises(RuntimeError):
                deepseek_module.run_deepseek("x", prompt_path, cfg)


if __name__ == "__main__":
    unittest.main()
