"""Orquestra extract -> transform -> load. Rodado localmente ou pelo GitHub Actions.

Uso:
    python pipeline.py                       # usa config/tickers_ativos.txt (universo
                                              # filtrado por liquidez, ~150 tickers) ou
                                              # cai pra config/tickers.yaml se aquele
                                              # arquivo ainda não existir
    python pipeline.py PETR4.SA VALE3.SA      # roda só os papéis escolhidos (consulta avulsa)

Uma seleção avulsa NUNCA sobrescreve o dataset canônico (data/quotes_history.csv e
data/fundamentals_latest.csv, usados pelo painel) — vai pra data/consulta_*.csv.

Não depende de Postgres em nenhum momento — é por isso que dá pra rodar no GitHub
Actions sem acesso ao seu banco local. Setor de cada ativo vem direto do yfinance
(info['sector']), não de uma classificação manual.
"""

from __future__ import annotations

import os
import sys

from extract import extrair_tudo, resolve_tickers
from transform import transform_fundamentals, transform_quotes

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(HERE, "config", "tickers.yaml")
ATIVOS_PATH = os.path.join(HERE, "config", "tickers_ativos.txt")
DATA_DIR = os.path.join(HERE, "data")


def run(escolhidos: list[str] | None = None) -> None:
    tickers = resolve_tickers(CONFIG_PATH, ATIVOS_PATH, escolhidos)
    avulso = bool(escolhidos)
    prefixo = "consulta_" if avulso else ""
    fonte = "consulta avulsa" if avulso else ("universo filtrado" if os.path.exists(ATIVOS_PATH) else "config/tickers.yaml")

    print(f"[pipeline] {len(tickers)} tickers ({fonte})")

    quotes_raw, fundamentals_raw = extrair_tudo(tickers)

    quotes = transform_quotes(quotes_raw)
    quotes_path = os.path.join(DATA_DIR, f"{prefixo}quotes_history.csv")
    quotes.to_csv(quotes_path, index=False)
    print(f"[pipeline] {len(quotes)} linhas -> {quotes_path}")

    fundamentals = transform_fundamentals(fundamentals_raw)
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
