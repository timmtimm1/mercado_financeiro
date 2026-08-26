"""Orquestra extract -> transform -> load. Rodado localmente ou pelo GitHub Actions.

Uso:
    python pipeline.py                       # roda os 20 tickers do config (padrão agendado)
    python pipeline.py PETR4.SA VALE3.SA      # roda só os papéis escolhidos (consulta avulsa)

Uma seleção avulsa NUNCA sobrescreve o dataset canônico (data/quotes_history.csv e
data/fundamentals_latest.csv, usados pelo painel) — vai pra data/consulta_*.csv, pra não
encolher sem querer a cobertura de setor que o dashboard depende.
"""

from __future__ import annotations

import os
import sys

from extract import extract_fundamentals, extract_quotes, resolve_tickers
from transform import transform_fundamentals, transform_quotes

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(HERE, "config", "tickers.yaml")
DATA_DIR = os.path.join(HERE, "data")


def run(escolhidos: list[str] | None = None) -> None:
    specs = resolve_tickers(CONFIG_PATH, escolhidos)
    avulso = bool(escolhidos)
    prefixo = "consulta_" if avulso else ""

    print(f"[pipeline] {len(specs)} tickers ({'consulta avulsa' if avulso else 'config completo'})")

    print("[pipeline] extraindo cotações (1 ano de histórico)...")
    quotes = transform_quotes(extract_quotes(specs))
    quotes_path = os.path.join(DATA_DIR, f"{prefixo}quotes_history.csv")
    quotes.to_csv(quotes_path, index=False)
    print(f"[pipeline] {len(quotes)} linhas -> {quotes_path}")

    print("[pipeline] extraindo fundamentos...")
    fundamentals = transform_fundamentals(extract_fundamentals(specs))
    fundamentals_path = os.path.join(DATA_DIR, f"{prefixo}fundamentals_latest.csv")
    fundamentals.to_csv(fundamentals_path, index=False)
    print(f"[pipeline] {len(fundamentals)} linhas -> {fundamentals_path}")

    if avulso:
        print(
            "\n[pipeline] consulta avulsa — o dataset principal do painel "
            "(quotes_history.csv / fundamentals_latest.csv) não foi tocado."
        )


if __name__ == "__main__":
    run(sys.argv[1:] or None)
