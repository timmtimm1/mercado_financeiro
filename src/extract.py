"""Puxa cotação e fundamentos da B3 via yfinance para os tickers configurados."""

from __future__ import annotations

import time
from dataclasses import dataclass

import pandas as pd
import yaml
import yfinance as yf


@dataclass
class TickerSpec:
    ticker: str
    setor: str


def load_tickers(config_path: str) -> list[TickerSpec]:
    with open(config_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return [
        TickerSpec(ticker=ticker, setor=setor)
        for setor, tickers in raw.items()
        for ticker in tickers
    ]


def extract_quotes(specs: list[TickerSpec], period: str = "1y") -> pd.DataFrame:
    """Histórico de preço de fechamento por ticker."""
    frames = []
    for spec in specs:
        hist = yf.Ticker(spec.ticker).history(period=period)
        if hist.empty:
            print(f"[extract] aviso: sem histórico para {spec.ticker}")
            continue
        hist = hist.reset_index()[["Date", "Close", "Volume"]]
        hist["ticker"] = spec.ticker
        hist["setor"] = spec.setor
        frames.append(hist)
        time.sleep(0.3)  # não martelar a API
    if not frames:
        return pd.DataFrame(columns=["Date", "Close", "Volume", "ticker", "setor"])
    return pd.concat(frames, ignore_index=True).rename(
        columns={"Date": "data", "Close": "fechamento", "Volume": "volume"}
    )


def extract_fundamentals(specs: list[TickerSpec]) -> pd.DataFrame:
    """Snapshot atual de fundamentos por ticker (uma linha por ativo)."""
    rows = []
    for spec in specs:
        info = yf.Ticker(spec.ticker).info
        rows.append(
            {
                "ticker": spec.ticker,
                "setor": spec.setor,
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
        time.sleep(0.3)
    return pd.DataFrame(rows)
