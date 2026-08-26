"""Renderiza a DRE de um ticker como imagem PNG (tabela), pra ver fora do terminal.

Uso:
    python dre_report.py PETR4.SA
    python dre_report.py WEGE3.SA --trimestral
"""

from __future__ import annotations

import os
import sys

import matplotlib.pyplot as plt
import pandas as pd

from dre import montar_dre

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(HERE, "visualizacoes")

LINHAS_SEM_ESCALA = {"Lucro por Ação (diluído)"}  # não é valor monetário em milhões
LINHAS_DESTAQUE = {
    "(=) Resultado Bruto",
    "(=) Resultado Antes do IR/CSLL",
    "(=) Resultado Líquido do Exercício",
}


def _fmt(valor: float, is_av: bool, is_eps: bool) -> str:
    if pd.isna(valor):
        return "-"
    if is_av:
        return f"{valor:.1f}%"
    if is_eps:
        return f"{valor:.2f}"
    return f"{valor:,.0f}"


def renderizar(ticker: str, periodo: str = "anual") -> str:
    dre = montar_dre(ticker, periodo)

    val_cols = [c for c in dre.columns if "(AV %)" not in str(c)]
    av_col_mais_recente = next(c for c in dre.columns if "(AV %)" in str(c))

    tabela = pd.DataFrame(index=dre.index)
    for c in val_cols:
        escala = dre[c].where(dre.index.isin(LINHAS_SEM_ESCALA), dre[c] / 1e6)
        tabela[str(c)] = escala
    tabela[f"AV % ({val_cols[0]})"] = dre[av_col_mais_recente]

    linhas_texto = []
    for idx in tabela.index:
        eh_eps = idx in LINHAS_SEM_ESCALA
        row = []
        for col in tabela.columns:
            eh_av = "AV %" in col
            row.append(_fmt(tabela.loc[idx, col], eh_av, eh_eps and not eh_av))
        linhas_texto.append(row)

    maior_rotulo = max(len(str(i)) for i in tabela.index)
    largura = maior_rotulo * 0.11 + len(tabela.columns) * 1.35
    fig, ax = plt.subplots(figsize=(largura, 0.55 * len(tabela.index) + 2))
    ax.axis("off")
    col_labels = [str(c).replace(" 00:00:00", "") for c in tabela.columns]
    tab = ax.table(
        cellText=linhas_texto,
        rowLabels=list(tabela.index),
        colLabels=col_labels,
        loc="center",
        cellLoc="right",
    )
    tab.auto_set_font_size(False)
    tab.set_fontsize(10)
    tab.auto_set_column_width(col=list(range(-1, len(col_labels))))
    tab.scale(1, 1.8)

    for (row, col), cell in tab.get_celld().items():
        if row == 0:
            cell.set_text_props(weight="bold")
            cell.set_facecolor("#e8e8e8")
        elif row > 0 and tabela.index[row - 1] in LINHAS_DESTAQUE:
            cell.set_facecolor("#eef3fb")
            if col == -1:
                cell.set_text_props(weight="bold")

    unidade = "" if periodo == "trimestral" else ""
    ax.set_title(
        f"DRE — {ticker} ({periodo}, R$ milhões)\nEstrutura Quadro 5.1 — Assaf Neto",
        fontsize=13,
        weight="bold",
        pad=20,
    )
    fig.text(
        0.5,
        0.01,
        "Fonte: yfinance. Receita Líquida já vem líquida da fonte "
        "(sem Receita Bruta/deduções em separado).",
        ha="center",
        fontsize=8,
        style="italic",
        color="#555",
    )
    fig.tight_layout()

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, f"dre_{ticker.replace('.SA', '').lower()}.png")
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return out_path


if __name__ == "__main__":
    args = sys.argv[1:]
    trimestral = "--trimestral" in args
    tickers_args = [a for a in args if not a.startswith("--")]
    ticker = tickers_args[0] if tickers_args else input("Ticker da B3 (ex: PETR4.SA): ").strip()
    if not ticker.upper().endswith(".SA"):
        ticker += ".SA"

    caminho = renderizar(ticker, "trimestral" if trimestral else "anual")
    print(f"Salvo em {caminho}")
