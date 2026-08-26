"""Visualizações simples pra conferir os dados da pipeline antes de ir pro Power BI.

Roda direto no VS Code (clique em "Run" ou F5) — abre as janelas interativas do
matplotlib e também salva PNGs em visualizacoes/, pra dar uma olhada sem precisar
rodar de novo.
"""

from __future__ import annotations

import os

import matplotlib.pyplot as plt
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(HERE, "data")
OUT_DIR = os.path.join(HERE, "visualizacoes")

SETOR_CORES = {
    "bancos": "#4C72B0",
    "varejo": "#DD8452",
    "commodities": "#55A868",
    "utilities": "#C44E52",
    "industria": "#8172B2",
    "financeiro_diversificado": "#937860",
}


def cores_por_setor(setores: pd.Series) -> list[str]:
    return [SETOR_CORES.get(s, "#888888") for s in setores]


def grafico_pl_por_ticker(fund: pd.DataFrame) -> None:
    fund = fund.dropna(subset=["p_l"]).sort_values("p_l")
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(fund["ticker"], fund["p_l"], color=cores_por_setor(fund["setor"]))
    ax.set_xlabel("P/L")
    ax.set_title("P/L por ativo")
    ax.axvline(fund["p_l"].median(), color="black", linestyle="--", linewidth=1, label="mediana")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "pl_por_ticker.png"), dpi=150)


def grafico_roe_por_ticker(fund: pd.DataFrame) -> None:
    fund = fund.dropna(subset=["roe"]).sort_values("roe")
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(fund["ticker"], fund["roe"], color=cores_por_setor(fund["setor"]))
    ax.set_xlabel("ROE (%)")
    ax.set_title("ROE por ativo")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "roe_por_ticker.png"), dpi=150)


def grafico_dispersao_roe_dy(fund: pd.DataFrame) -> None:
    fund = fund.dropna(subset=["roe", "dividend_yield", "market_cap"])
    fig, ax = plt.subplots(figsize=(8, 6))
    tamanhos = (fund["market_cap"] / fund["market_cap"].max()) * 800 + 30
    for setor, grupo in fund.groupby("setor"):
        idx = grupo.index
        ax.scatter(
            grupo["roe"],
            grupo["dividend_yield"],
            s=tamanhos.loc[idx],
            color=SETOR_CORES.get(setor, "#888888"),
            alpha=0.75,
            edgecolors="white",
            linewidths=0.8,
            label=setor,
        )
    for _, row in fund.iterrows():
        ax.annotate(row["ticker"], (row["roe"], row["dividend_yield"]), fontsize=8, xytext=(4, 4), textcoords="offset points")
    ax.set_xlabel("ROE (%)")
    ax.set_ylabel("Dividend Yield (%)")
    ax.set_title("ROE x Dividend Yield (tamanho = market cap)")
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "roe_vs_dividend_yield.png"), dpi=150)


def grafico_precos_normalizados(quotes: pd.DataFrame, setor: str = "bancos") -> None:
    sub = quotes[quotes["setor"] == setor].copy()
    fig, ax = plt.subplots(figsize=(10, 6))
    for ticker, grupo in sub.groupby("ticker"):
        grupo = grupo.sort_values("data")
        base = grupo["fechamento"].iloc[0]
        normalizado = grupo["fechamento"] / base * 100
        ax.plot(grupo["data"], normalizado, label=ticker, linewidth=1.6)
    ax.axhline(100, color="black", linestyle="--", linewidth=1, alpha=0.5)
    ax.set_ylabel("Preço normalizado (base 100 = início do período)")
    ax.set_title(f"Evolução de preço — setor {setor}")
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, f"precos_normalizados_{setor}.png"), dpi=150)


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    fund = pd.read_csv(os.path.join(DATA_DIR, "fundamentals_latest.csv"))
    quotes = pd.read_csv(os.path.join(DATA_DIR, "quotes_history.csv"), parse_dates=["data"])

    grafico_pl_por_ticker(fund)
    grafico_roe_por_ticker(fund)
    grafico_dispersao_roe_dy(fund)
    grafico_precos_normalizados(quotes, setor="bancos")

    print(f"[visualize] PNGs salvos em {OUT_DIR}")
    plt.show()


if __name__ == "__main__":
    main()
