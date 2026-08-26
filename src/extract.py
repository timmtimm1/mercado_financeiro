"""Puxa cotação e fundamentos da B3 via yfinance para os tickers configurados.

Uma única passada por ticker (um yf.Ticker() só, não dois) — pega .info (fundamentos
+ setor real, não uma classificação manual) e .history() (cotação) juntos, e retorna
os dois DataFrames já com o mesmo setor descoberto em cada linha.
"""

from __future__ import annotations

import os
import time

import pandas as pd
import yaml
import yfinance as yf

SETOR_DESCONHECIDO = "Desconhecido"


def load_tickers_yaml(config_path: str) -> list[str]:
    """Lê a lista curada manualmente (config/tickers.yaml) — fallback de 20 tickers,
    usado só se config/tickers_ativos.txt ainda não existir."""
    with open(config_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return [ticker for tickers in raw.values() for ticker in tickers]


def load_tickers_ativos(path: str) -> list[str]:
    """Lê a lista de tickers ativos gerada por fetch_universe.py (liquidez filtrada,
    versionada no git — é essa que o GitHub Actions usa, sem depender de Postgres)."""
    with open(path, encoding="utf-8") as f:
        return [linha.strip() for linha in f if linha.strip() and not linha.startswith("#")]


def resolve_tickers(config_path: str, ativos_path: str, escolhidos: list[str] | None) -> list[str]:
    """Ordem de resolução:
    1. `escolhidos` explícito (consulta avulsa via CLI) — sempre vence.
    2. config/tickers_ativos.txt (universo filtrado por liquidez, gerado por fetch_universe.py).
    3. Fallback: config/tickers.yaml (lista curada manual de 20, se o passo 1 do
       universo — fetch_universe.py — nunca rodou ainda).
    """
    if escolhidos:
        return [t.upper() if t.upper().endswith(".SA") else t.upper() + ".SA" for t in escolhidos]

    if os.path.exists(ativos_path):
        return load_tickers_ativos(ativos_path)

    return load_tickers_yaml(config_path)


def extrair_tudo(tickers: list[str], period: str = "1y") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Uma passada por ticker: cotação (histórico) + fundamentos, com o setor
    descoberto via yfinance (info['sector']) usado consistentemente nos dois."""
    linhas_quotes = []
    linhas_fund = []

    for i, ticker in enumerate(tickers, 1):
        try:
            t = yf.Ticker(ticker)
            info = t.info
            setor = info.get("sector") or SETOR_DESCONHECIDO

            hist = t.history(period=period)
            if not hist.empty:
                h = hist.reset_index()[["Date", "Close", "Volume"]]
                h["ticker"] = ticker
                h["setor"] = setor
                linhas_quotes.append(h)

            linhas_fund.append(
                {
                    "ticker": ticker,
                    "setor": setor,
                    "nome": info.get("longName"),
                    "preco_atual": info.get("currentPrice") or info.get("regularMarketPrice"),
                    "p_l": info.get("trailingPE"),
                    "p_vp": info.get("priceToBook"),
                    "roe": info.get("returnOnEquity"),
                    "dividend_yield": info.get("dividendYield"),
                    "margem_liquida": info.get("profitMargins"),
                    "divida_patrimonio": info.get("debtToEquity"),
                    "market_cap": info.get("marketCap"),
                }
            )
        except Exception as e:
            print(f"[extract] aviso: falhou {ticker} ({e}) — pulando")

        if i % 25 == 0 or i == len(tickers):
            print(f"[extract] {i}/{len(tickers)} tickers processados")
        time.sleep(0.3)

    quotes = (
        pd.concat(linhas_quotes, ignore_index=True).rename(
            columns={"Date": "data", "Close": "fechamento", "Volume": "volume"}
        )
        if linhas_quotes
        else pd.DataFrame(columns=["data", "fechamento", "volume", "ticker", "setor"])
    )
    fundamentals = pd.DataFrame(linhas_fund)
    return quotes, fundamentals
