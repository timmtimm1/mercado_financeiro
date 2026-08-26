"""Análise aprofundada de um ticker: Análise Horizontal, margens, ROI/RSPL,
endividamento e liquidez — framework do Assaf Neto (Cap. 7, 8, 11, 13).

Uso:
    python indicadores.py TAEE11.SA
"""

from __future__ import annotations

import os
import sys

import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(HERE, "visualizacoes")

LINHAS_INC = [
    "Total Revenue",
    "Cost Of Revenue",
    "Gross Profit",
    "Interest Expense",
    "Interest Income",
    "Net Income",
]
LINHAS_BS = [
    "Total Assets",
    "Current Assets",
    "Current Liabilities",
    "Total Debt",
    "Stockholders Equity",
]


def coletar(ticker: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    t = yf.Ticker(ticker)
    inc = t.income_stmt.loc[[l for l in LINHAS_INC if l in t.income_stmt.index]].dropna(axis=1, how="all")
    bs = t.balance_sheet.loc[[l for l in LINHAS_BS if l in t.balance_sheet.index]].dropna(axis=1, how="all")
    # ordena do mais antigo pro mais recente (esquerda -> direita), mais natural pra AH
    inc = inc[sorted(inc.columns)]
    bs = bs[sorted(bs.columns)]
    return inc, bs


def calcular_indicadores(inc: pd.DataFrame, bs: pd.DataFrame) -> pd.DataFrame:
    anos = [c.year for c in inc.columns]
    linhas = {}

    receita = inc.loc["Total Revenue"]
    cpv = inc.loc["Cost Of Revenue"]
    lucro_bruto = inc.loc["Gross Profit"]
    desp_fin = inc.loc["Interest Expense"]
    lucro_liquido = inc.loc["Net Income"]

    # Análise Horizontal — números-índice, base = primeiro ano disponível (Cap. 7)
    linhas["AH Receita Líquida"] = (receita / receita.iloc[0] * 100).values
    linhas["AH Custo (CPV)"] = (cpv / cpv.iloc[0] * 100).values
    linhas["AH Lucro Líquido"] = (lucro_liquido / lucro_liquido.iloc[0] * 100).values

    # Margens (Cap. 7 / 13)
    linhas["Margem Bruta %"] = (lucro_bruto / receita * 100).values
    linhas["Margem Líquida %"] = (lucro_liquido / receita * 100).values

    # ROI / RSPL — usa Lucro Operacional Genuíno = Lucro Líquido + Despesas Financeiras (Cap. 2, 13)
    pl = bs.loc["Stockholders Equity"]
    divida = bs.loc["Total Debt"]
    # income_stmt e balance_sheet podem ter datas-limite de exercício levemente diferentes;
    # casa por ano, não por data exata
    pl_por_ano = pd.Series(pl.values, index=[c.year for c in pl.index])
    divida_por_ano = pd.Series(divida.values, index=[c.year for c in divida.index])
    investimento = pl_por_ano.reindex(anos) + divida_por_ano.reindex(anos)
    nopat = (lucro_liquido.values + desp_fin.values)
    linhas["ROI %"] = nopat / investimento.values * 100
    linhas["RSPL %"] = lucro_liquido.values / pl_por_ano.reindex(anos).values * 100

    # Endividamento e liquidez (Cap. 9, 11)
    ativo_total = bs.loc["Total Assets"]
    ativo_circ = bs.loc["Current Assets"]
    passivo_circ = bs.loc["Current Liabilities"]
    ativo_total_por_ano = pd.Series(ativo_total.values, index=[c.year for c in ativo_total.index]).reindex(anos)
    ativo_circ_por_ano = pd.Series(ativo_circ.values, index=[c.year for c in ativo_circ.index]).reindex(anos)
    passivo_circ_por_ano = pd.Series(passivo_circ.values, index=[c.year for c in passivo_circ.index]).reindex(anos)

    linhas["Dívida/PL"] = divida_por_ano.reindex(anos).values / pl_por_ano.reindex(anos).values
    linhas["Passivo Total/Ativo %"] = (
        (ativo_total_por_ano.values - pl_por_ano.reindex(anos).values) / ativo_total_por_ano.values * 100
    )
    linhas["Liquidez Corrente"] = ativo_circ_por_ano.values / passivo_circ_por_ano.values

    return pd.DataFrame(linhas, index=anos).T


def renderizar(ticker: str) -> tuple[str, pd.DataFrame, dict]:
    inc, bs = coletar(ticker)
    ind = calcular_indicadores(inc, bs)
    anos = ind.columns.tolist()

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))

    ax1 = axes[0]
    for linha, cor in [("AH Receita Líquida", "#4C72B0"), ("AH Custo (CPV)", "#C44E52"), ("AH Lucro Líquido", "#55A868")]:
        ax1.plot(anos, ind.loc[linha], marker="o", label=linha.replace("AH ", ""), color=cor, linewidth=2)
    ax1.axhline(100, color="black", linestyle="--", linewidth=1, alpha=0.4)
    ax1.set_title("Análise Horizontal (base 100 = primeiro ano)")
    ax1.set_ylabel("Índice")
    ax1.set_xticks(anos)
    ax1.legend(fontsize=9)
    ax1.grid(alpha=0.25)

    ax2 = axes[1]
    ax2.plot(anos, ind.loc["Margem Bruta %"], marker="o", label="Margem Bruta", color="#4C72B0", linewidth=2)
    ax2.plot(anos, ind.loc["Margem Líquida %"], marker="o", label="Margem Líquida", color="#DD8452", linewidth=2)
    ax2.plot(anos, ind.loc["ROI %"], marker="s", label="ROI", color="#55A868", linewidth=2, linestyle="--")
    ax2.plot(anos, ind.loc["RSPL %"], marker="s", label="RSPL", color="#8172B2", linewidth=2, linestyle="--")
    ax2.set_title("Margens e Retorno (%)")
    ax2.set_ylabel("%")
    ax2.set_xticks(anos)
    ax2.legend(fontsize=9)
    ax2.grid(alpha=0.25)

    fig.suptitle(f"Análise Aprofundada — {ticker}", fontsize=14, weight="bold")
    fig.tight_layout()
    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, f"indicadores_{ticker.replace('.SA', '').lower()}.png")
    fig.savefig(out_path, dpi=170, bbox_inches="tight")
    plt.close(fig)

    contexto = {}
    try:
        info = yf.Ticker(ticker).info
        contexto = {
            "dividend_yield": info.get("dividendYield"),
            "p_l": info.get("trailingPE"),
            "beta": info.get("beta"),
        }
    except Exception:
        pass

    return out_path, ind, contexto


if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else input("Ticker da B3 (ex: TAEE11.SA): ").strip()
    if not ticker.upper().endswith(".SA"):
        ticker += ".SA"
    caminho, ind, ctx = renderizar(ticker)
    pd.set_option("display.float_format", lambda x: f"{x:,.2f}")
    pd.set_option("display.width", 160)
    print(ind)
    print(ctx)
    print(f"\nSalvo em {caminho}")
