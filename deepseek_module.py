from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests


@dataclass
class DeepSeekConfig:
    api_key: str
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    timeout: int = 60


def _load_prompt_md(prompt_md_path: str | Path) -> str:
    path = Path(prompt_md_path)
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def _normalize_input(input_data: Any) -> str:
    if isinstance(input_data, str):
        return input_data
    return json.dumps(input_data, ensure_ascii=False, indent=2)


def run_deepseek(
    input_data: Any,
    prompt_md_path: str | Path,
    config: DeepSeekConfig,
    stream: bool = False,
) -> str:
    system_prompt = _load_prompt_md(prompt_md_path)
    user_payload = _normalize_input(input_data)

    url = f"{config.base_url.rstrip('/')}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.api_key}",
    }
    body = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_payload},
        ],
        "stream": stream,
    }

    response = requests.post(url, headers=headers, json=body, timeout=config.timeout)
    if response.status_code >= 400:
        raise RuntimeError(f"DeepSeek API error {response.status_code}: {response.text}")

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected DeepSeek response format: {data}") from exc

