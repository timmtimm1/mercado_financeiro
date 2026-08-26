"""Normaliza os dados extraídos e calcula campos derivados para o painel."""

from __future__ import annotations

import pandas as pd


def transform_quotes(quotes: pd.DataFrame) -> pd.DataFrame:
    quotes = quotes.copy()
    quotes["data"] = pd.to_datetime(quotes["data"]).dt.date
    quotes = quotes.sort_values(["ticker", "data"])
    # retorno diário, útil pra qualquer visual de performance no painel
    quotes["retorno_diario"] = quotes.groupby("ticker")["fechamento"].pct_change()
    return quotes.dropna(subset=["fechamento"])


def transform_fundamentals(fundamentals: pd.DataFrame) -> pd.DataFrame:
    fundamentals = fundamentals.copy()
    # yfinance retorna roe/margem como proporção (0.05); padroniza pra percentual (5.0).
    # dividend_yield já vem em percentual (2.26 = 2.26%) nesta versão da lib — não reescalar.
    for col in ("roe", "margem_liquida"):
        fundamentals[col] = fundamentals[col] * 100

    # média setorial, pra comparação "ativo vs. setor" no painel
    setor_medias = fundamentals.groupby("setor")[["p_l", "roe", "dividend_yield"]].transform("mean")
    fundamentals["p_l_vs_setor"] = fundamentals["p_l"] - setor_medias["p_l"]
    fundamentals["roe_vs_setor"] = fundamentals["roe"] - setor_medias["roe"]
    fundamentals["dividend_yield_vs_setor"] = (
        fundamentals["dividend_yield"] - setor_medias["dividend_yield"]
    )
    return fundamentals
