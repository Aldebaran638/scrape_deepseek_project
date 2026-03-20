from __future__ import annotations

import argparse
import os
from typing import Any

from deepseek_module import DeepSeekConfig, run_deepseek
from scrapling_modules.sulwhasoo_scrapling_module import scrape_url as scrape_sulwhasoo
from scrapling_modules.thesaemcosmetic_scrapling_module import scrape_url as scrape_thesaem_detail
import json

def build_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run scrape + DeepSeek workflow and print model output."
    )
    parser.add_argument("--sulwhasoo-url", required=True, help="Target URL for sulwhasoo scraper.")
    parser.add_argument("--thesaem-url", required=True, help="Target URL for thesaem detail_infor scraper.")
    parser.add_argument("--prompt", default="deepseek_prompt.md", help="Prompt markdown file path.")
    parser.add_argument("--base-url", default=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
    parser.add_argument("--model", default=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))
    parser.add_argument("--api-key", default=os.getenv("DEEPSEEK_API_KEY", ""))
    parser.add_argument("--container-selector", default=".prd-price-wrap.color-chip-none")
    parser.add_argument("--detail-container-selector", default=".detail_infor")
    parser.add_argument("--timeout", type=int, default=60, help="DeepSeek timeout (seconds).")
    return parser.parse_args()


def main() -> None:
    args = build_args()
    if not args.api_key:
        raise ValueError("Missing DeepSeek API key. Use --api-key or set DEEPSEEK_API_KEY.")

    modules: dict[str, Any] = {}
    scraped_data: dict[str, Any] = {
        "urls": {
            "sulwhasoo": args.sulwhasoo_url,
            "thesaem_detail_infor": args.thesaem_url,
        },
        "modules": modules,
    }

    try:
        sulwhasoo_data = scrape_sulwhasoo(args.sulwhasoo_url, container_selector=args.container_selector)
        modules["sulwhasoo"] = sulwhasoo_data
    except Exception as exc:
        modules["sulwhasoo"] = {"error": str(exc)}

    try:
        thesaem_data = scrape_thesaem_detail(args.thesaem_url, container_selector=args.detail_container_selector)
        modules["thesaem_detail_infor"] = thesaem_data
    except Exception as exc:
        modules["thesaem_detail_infor"] = {"error": str(exc)}

    with open("result.json", "w", encoding="utf-8") as f:
        json.dump(scraped_data, f, ensure_ascii=False, indent=2)
    # # AI总结 
    # print("AI model is thinking...")
    # cfg = DeepSeekConfig(
    #     api_key=args.api_key,
    #     base_url=args.base_url,
    #     model=args.model,
    #     timeout=args.timeout,
    # )
    # llm_output = run_deepseek(
    #     input_data=scraped_data,
    #     prompt_md_path=args.prompt,
    #     config=cfg,
    # )
    # print(llm_output)


if __name__ == "__main__":
    main()
