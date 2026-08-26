"""Orquestra extract -> transform -> load. Rodado localmente ou pelo GitHub Actions."""

from __future__ import annotations

import os

from extract import extract_fundamentals, extract_quotes, load_tickers
from transform import transform_fundamentals, transform_quotes

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(HERE, "config", "tickers.yaml")
DATA_DIR = os.path.join(HERE, "data")


def run() -> None:
    specs = load_tickers(CONFIG_PATH)
    print(f"[pipeline] {len(specs)} tickers configurados")

    print("[pipeline] extraindo cotações (1 ano de histórico)...")
    quotes = transform_quotes(extract_quotes(specs))
    quotes_path = os.path.join(DATA_DIR, "quotes_history.csv")
    quotes.to_csv(quotes_path, index=False)
    print(f"[pipeline] {len(quotes)} linhas -> {quotes_path}")

    print("[pipeline] extraindo fundamentos...")
    fundamentals = transform_fundamentals(extract_fundamentals(specs))
    fundamentals_path = os.path.join(DATA_DIR, "fundamentals_latest.csv")
    fundamentals.to_csv(fundamentals_path, index=False)
    print(f"[pipeline] {len(fundamentals)} linhas -> {fundamentals_path}")


if __name__ == "__main__":
    run()
