"""Visualizações simples pra conferir os dados da pipeline antes de ir pro painel.

Roda direto no VS Code (clique em "Run" ou F5) — abre as janelas interativas do
matplotlib e também salva PNGs em visualizacoes/, pra dar uma olhada sem precisar
rodar de novo.

Com ~150 tickers, gráfico de barra com todo mundo vira ilegível — os de P/L e ROE
mostram só os extremos (top/bottom N). Sanity-check rápido, não é o painel final
(isso é o Metabase).
"""

from __future__ import annotations

import os

import matplotlib.pyplot as plt
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(HERE, "data")
OUT_DIR = os.path.join(HERE, "visualizacoes")

# setores como o yfinance realmente classifica (GICS-like) — descobertos em
# extract.py, não uma lista curada manualmente
SETOR_CORES = {
    "Financial Services": "#4C72B0",
    "Consumer Cyclical": "#DD8452",
    "Basic Materials": "#55A868",
    "Utilities": "#C44E52",
    "Industrials": "#8172B2",
    "Real Estate": "#937860",
    "Consumer Defensive": "#DA8BC3",
    "Healthcare": "#8C8C8C",
    "Energy": "#CCB974",
    "Communication Services": "#64B5CD",
    "Technology": "#4E9A8C",
    "Desconhecido": "#B0B0B0",
}


def cores_por_setor(setores: pd.Series) -> list[str]:
    return [SETOR_CORES.get(s, "#888888") for s in setores]


def grafico_pl_por_ticker(fund: pd.DataFrame, top_n: int = 15) -> None:
    fund = fund.dropna(subset=["p_l"])
    fund = fund[fund["p_l"] > 0].sort_values("p_l")  # P/L negativo (prejuízo) distorce a escala
    extremos = pd.concat([fund.head(top_n), fund.tail(top_n)]).drop_duplicates("ticker")
    fig, ax = plt.subplots(figsize=(9, 8))
    ax.barh(extremos["ticker"], extremos["p_l"], color=cores_por_setor(extremos["setor"]))
    ax.set_xlabel("P/L")
    ax.set_title(f"P/L — {top_n} mais baratos e {top_n} mais caros (de {len(fund)} com P/L positivo)")
    ax.axvline(fund["p_l"].median(), color="black", linestyle="--", linewidth=1, label="mediana do universo")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "pl_por_ticker.png"), dpi=150)


def grafico_roe_por_ticker(fund: pd.DataFrame, top_n: int = 15) -> None:
    fund = fund.dropna(subset=["roe"]).sort_values("roe")
    extremos = pd.concat([fund.head(top_n), fund.tail(top_n)]).drop_duplicates("ticker")
    fig, ax = plt.subplots(figsize=(9, 8))
    ax.barh(extremos["ticker"], extremos["roe"], color=cores_por_setor(extremos["setor"]))
    ax.set_xlabel("ROE (%)")
    ax.set_title(f"ROE — {top_n} piores e {top_n} melhores (de {len(fund)} tickers)")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "roe_por_ticker.png"), dpi=150)


def grafico_dispersao_roe_dy(fund: pd.DataFrame, anotar_top_n: int = 12) -> None:
    fund = fund.dropna(subset=["roe", "dividend_yield", "market_cap"])
    fig, ax = plt.subplots(figsize=(9, 7))
    tamanhos = (fund["market_cap"] / fund["market_cap"].max()) * 800 + 20
    for setor, grupo in fund.groupby("setor"):
        idx = grupo.index
        ax.scatter(
            grupo["roe"],
            grupo["dividend_yield"],
            s=tamanhos.loc[idx],
            color=SETOR_CORES.get(setor, "#888888"),
            alpha=0.65,
            edgecolors="white",
            linewidths=0.6,
            label=setor,
        )
    # com ~150 pontos, anotar todo mundo vira ruído — só os maiores market caps
    destaques = fund.nlargest(anotar_top_n, "market_cap")
    for _, row in destaques.iterrows():
        ax.annotate(row["ticker"], (row["roe"], row["dividend_yield"]), fontsize=7.5, xytext=(4, 4), textcoords="offset points")
    ax.set_xlabel("ROE (%)")
    ax.set_ylabel("Dividend Yield (%)")
    ax.set_title(f"ROE × Dividend Yield — {len(fund)} tickers (tamanho = market cap; rótulos = {anotar_top_n} maiores)")
    ax.legend(loc="upper right", fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "roe_vs_dividend_yield.png"), dpi=150)


def grafico_precos_normalizados(quotes: pd.DataFrame, setor: str = "Financial Services", max_tickers: int = 12) -> None:
    sub = quotes[quotes["setor"] == setor].copy()
    tickers_incluidos = sorted(sub["ticker"].unique())[:max_tickers]
    sub = sub[sub["ticker"].isin(tickers_incluidos)]
    fig, ax = plt.subplots(figsize=(10, 6))
    for ticker, grupo in sub.groupby("ticker"):
        grupo = grupo.sort_values("data")
        base = grupo["fechamento"].iloc[0]
        normalizado = grupo["fechamento"] / base * 100
        ax.plot(grupo["data"], normalizado, label=ticker, linewidth=1.4)
    ax.axhline(100, color="black", linestyle="--", linewidth=1, alpha=0.5)
    ax.set_ylabel("Preço normalizado (base 100 = início do período)")
    ax.set_title(f"Evolução de preço — setor {setor} (até {max_tickers} tickers)")
    ax.legend(fontsize=8, ncol=2)
    fig.autofmt_xdate()
    fig.tight_layout()
    nome_arquivo = setor.lower().replace(" ", "_")
    fig.savefig(os.path.join(OUT_DIR, f"precos_normalizados_{nome_arquivo}.png"), dpi=150)


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    fund = pd.read_csv(os.path.join(DATA_DIR, "fundamentals_latest.csv"))
    quotes = pd.read_csv(os.path.join(DATA_DIR, "quotes_history.csv"), parse_dates=["data"])

    grafico_pl_por_ticker(fund)
    grafico_roe_por_ticker(fund)
    grafico_dispersao_roe_dy(fund)
    grafico_precos_normalizados(quotes, setor="Financial Services")

    print(f"[visualize] PNGs salvos em {OUT_DIR}")
    plt.show()


if __name__ == "__main__":
    main()
