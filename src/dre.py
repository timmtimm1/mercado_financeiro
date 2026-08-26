"""Monta a DRE de uma ação da B3 na estrutura do Quadro 5.1 (Lei das S.A.),
a partir de dados reais do yfinance — com Análise Vertical (% da Receita Líquida).

Referência: "Estruturas e Análise de Balanços" (Assaf Neto, 12ª ed.), Cap. 5.

Limitações de dado, por vir do yfinance e não da DFP/CVM diretamente:
  - Yahoo não separa Receita Bruta de Receita Líquida nem mostra a linha de
    deduções/impostos sobre vendas — "Receita Líquida" aqui já chega líquida
    da fonte, então a DRE começa nesse ponto, não em Receita Bruta.
  - Bancos (Cosif) usam uma estrutura de DRE totalmente diferente — sem CPV,
    sem Lucro Bruto — coberta no livro pelos Cap. 16-18, não pelo Quadro 5.1.
    Esta função detecta isso e recusa a montar a DRE nesse formato, em vez de
    forçar dados que não existem.

Uso:
    python dre.py                  # pede o ticker interativamente
    python dre.py PETR4.SA         # ticker direto
    python dre.py PETR4.SA --trimestral
"""

from __future__ import annotations

import sys

import pandas as pd
import yfinance as yf

LINHAS_DRE = [
    ("Receita Líquida", "Total Revenue"),
    ("(–) Custo dos Produtos/Serviços Vendidos", "Cost Of Revenue"),
    ("(=) Resultado Bruto", "Gross Profit"),
    ("(–) Despesas de Vendas", "Selling And Marketing Expense"),
    ("(–) Despesas Gerais e Administrativas", "General And Administrative Expense"),
    ("(–) Outras Despesas Operacionais", "Other Operating Expenses"),
    ("(+) Receitas Financeiras", "Interest Income"),
    ("(–) Despesas Financeiras", "Interest Expense"),
    ("(=) Resultado Antes do IR/CSLL", "Pretax Income"),
    ("(–) Provisão para IR e CSLL", "Tax Provision"),
    ("(=) Resultado Líquido do Exercício", "Net Income"),
]

LINHAS_INFORMATIVAS = [
    ("Lucro por Ação (diluído)", "Diluted EPS"),
]


def _eh_banco(income_stmt: pd.DataFrame) -> bool:
    """Bancos (Cosif) não têm CPV/Lucro Bruto — sinal de que o Quadro 5.1 não se aplica."""
    tem_cpv = "Cost Of Revenue" in income_stmt.index
    tem_receita_liquida_juros = "Net Interest Income" in income_stmt.index
    return tem_receita_liquida_juros and not tem_cpv


def montar_dre(ticker: str, periodo: str = "anual") -> pd.DataFrame:
    """Retorna a DRE de `ticker` no formato Quadro 5.1, com AV% em cada coluna de período.

    periodo: "anual" (padrão, últimos 4 exercícios) ou "trimestral" (últimos 4 trimestres).
    """
    t = yf.Ticker(ticker)
    income_stmt = t.quarterly_income_stmt if periodo == "trimestral" else t.income_stmt

    if income_stmt.empty:
        raise ValueError(f"Yahoo não retornou DRE para {ticker} — confira o ticker (sufixo .SA).")

    if _eh_banco(income_stmt):
        raise ValueError(
            f"{ticker} parece ser uma instituição financeira (estrutura Cosif) — "
            "o Quadro 5.1 (CPV/Lucro Bruto) não se aplica a bancos. "
            "Ver Cap. 16-18 do Assaf Neto pra estrutura correta de DRE bancária."
        )

    periodos = income_stmt.columns
    linhas = {}
    for nome_pt, nome_yahoo in LINHAS_DRE:
        linhas[nome_pt] = [
            income_stmt.loc[nome_yahoo, p] if nome_yahoo in income_stmt.index else None
            for p in periodos
        ]

    dre = pd.DataFrame(linhas, index=periodos).T
    dre.columns = [c.date() if hasattr(c, "date") else c for c in dre.columns]
    dre = dre.dropna(axis=1, how="all")  # remove períodos que o Yahoo não preencheu

    # Análise Vertical: cada linha como % da Receita Líquida (Cap. 7)
    receita_liquida = dre.loc["Receita Líquida"]
    av = dre.div(receita_liquida, axis=1) * 100
    av.columns = [f"{c} (AV %)" for c in av.columns]

    resultado = pd.concat([dre, av], axis=1)

    for nome_pt, nome_yahoo in LINHAS_INFORMATIVAS:
        if nome_yahoo in income_stmt.index:
            resultado.loc[nome_pt] = list(income_stmt.loc[nome_yahoo]) + [None] * len(av.columns)

    return resultado


def imprimir_dre(ticker: str, periodo: str = "anual") -> None:
    dre = montar_dre(ticker, periodo)
    pd.set_option("display.float_format", lambda x: f"{x:,.1f}")
    pd.set_option("display.width", 160)
    print(f"\nDRE — {ticker} ({periodo}) — estrutura Quadro 5.1 (Assaf Neto)\n")
    print(dre)
    print(
        "\nNota: 'Receita Líquida' vem líquida direto do yfinance — Receita Bruta e "
        "deduções/impostos sobre vendas não estão disponíveis nessa fonte."
    )


if __name__ == "__main__":
    args = sys.argv[1:]
    trimestral = "--trimestral" in args
    tickers_args = [a for a in args if not a.startswith("--")]

    ticker_escolhido = tickers_args[0] if tickers_args else input("Ticker da B3 (ex: PETR4.SA): ").strip()
    if not ticker_escolhido.upper().endswith(".SA"):
        ticker_escolhido += ".SA"

    try:
        imprimir_dre(ticker_escolhido, "trimestral" if trimestral else "anual")
    except ValueError as e:
        print(f"\nErro: {e}")
