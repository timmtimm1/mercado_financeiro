"""Puxa a listagem completa da B3 (Fundamentus) e grava no Postgres como tabela de
referência — universo_b3. Roda com pouca frequência (listagem muda pouco, não é
tempo real) — pense em rodar manualmente uma vez por mês, não no cron diário.

Uso:
    python fetch_universe.py

Depois disso, `pipeline.py --universo` usa essa tabela (filtrada por liquidez) como
lista de tickers ativos, em vez do config/tickers.yaml manual.
"""

from __future__ import annotations

import os

import pandas as pd
import requests

from load_postgres import get_engine

FUNDAMENTUS_URL = "https://www.fundamentus.com.br/resultado.php"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

RENOMEIA_COLUNAS = {
    "Papel": "ticker",
    "Cotação": "cotacao",
    "P/L": "p_l",
    "P/VP": "p_vp",
    "PSR": "psr",
    "Div.Yield": "dividend_yield_fundamentus",
    "P/Ativo": "p_ativo",
    "P/Cap.Giro": "p_cap_giro",
    "P/EBIT": "p_ebit",
    "P/Ativ Circ.Liq": "p_ativ_circ_liq",
    "EV/EBIT": "ev_ebit",
    "EV/EBITDA": "ev_ebitda",
    "Mrg Bruta": "margem_bruta",
    "Mrg Ebit": "margem_ebit",
    "Mrg. Líq.": "margem_liquida",
    "Liq. Corr.": "liquidez_corrente",
    "ROIC": "roic",
    "ROE": "roe",
    "Liq.2meses": "liquidez_2meses",
    "Patrim. Líq": "patrimonio_liquido",
    "Dív.Líq/ Patrim.": "divida_liquida_patrimonio",
    "Cresc. Rec.5a": "crescimento_receita_5a",
}


def baixar_html() -> str:
    resp = requests.get(FUNDAMENTUS_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    resp.encoding = "ISO-8859-1"
    return resp.text


def parsear(html: str) -> pd.DataFrame:
    tabelas = pd.read_html(pd.io.common.StringIO(html), decimal=",", thousands=".")
    df = tabelas[0].rename(columns=RENOMEIA_COLUNAS)
    df["ticker"] = df["ticker"].str.upper() + ".SA"
    # colunas de percentual vêm como texto "31,91%" em algumas versões — normaliza
    for col in ("margem_bruta", "margem_ebit", "margem_liquida", "roic", "roe", "crescimento_receita_5a"):
        if df[col].dtype == object:
            df[col] = (
                df[col].astype(str).str.replace("%", "", regex=False).str.replace(",", ".", regex=False)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


LIQUIDEZ_MINIMA_PADRAO = 5_000_000  # ativos, ~150 tickers — ver ADR na decisão do usuário


def run(liquidez_minima: float = LIQUIDEZ_MINIMA_PADRAO) -> None:
    print("[fetch_universe] baixando fundamentus.com.br/resultado.php ...")
    html = baixar_html()
    df = parsear(html)
    print(f"[fetch_universe] {len(df)} tickers na listagem completa da B3")

    engine = get_engine()
    df.to_sql("universo_b3", engine, if_exists="replace", index=False)
    print("[fetch_universe] gravado em Postgres -> tabela universo_b3 (referência completa, 994 tickers)")

    for corte in (100_000, 1_000_000, 5_000_000):
        n = (df["liquidez_2meses"] > corte).sum()
        print(f"[fetch_universe] liquidez_2meses > {corte:>10,}: {n} tickers")

    # a lista ATIVA (usada pela pipeline/GitHub Actions) vai pra um arquivo versionado
    # no git — pipeline.py não tem acesso ao Postgres local quando roda no GitHub Actions
    ativos = sorted(df.loc[df["liquidez_2meses"] > liquidez_minima, "ticker"])
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_path = os.path.join(here, "config", "tickers_ativos.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# Gerado por fetch_universe.py — liquidez_2meses > {liquidez_minima:,.0f}\n")
        f.write(f"# {len(ativos)} tickers. Não editar manualmente — rode fetch_universe.py de novo.\n")
        for ticker in ativos:
            f.write(f"{ticker}\n")
    print(f"[fetch_universe] {len(ativos)} tickers ativos -> {out_path}")


if __name__ == "__main__":
    run()
