"""Carrega os CSVs gerados pela pipeline num Postgres local, pra o Metabase ler.

Roda só localmente (o GitHub Actions não tem acesso ao seu Postgres) — depois de
`pipeline.py` gerar os CSVs (seja local ou puxado do repo via git pull), rode:

    python load_postgres.py

Lê a conexão de variáveis de ambiente (.env, veja .env.example) — nunca tem senha
hardcoded aqui.
"""

from __future__ import annotations

import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(HERE, "data")


def get_engine():
    load_dotenv(os.path.join(HERE, ".env"))
    faltando = [
        v
        for v in ("POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD")
        if not os.environ.get(v)
    ]
    if faltando:
        raise RuntimeError(
            f"Variáveis de ambiente faltando: {', '.join(faltando)}. "
            "Copie .env.example pra .env e preencha."
        )
    url = (
        f"postgresql+psycopg2://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
        f"@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}"
    )
    return create_engine(url)


def run() -> None:
    engine = get_engine()

    quotes = pd.read_csv(os.path.join(DATA_DIR, "quotes_history.csv"))
    quotes.to_sql("quotes_history", engine, if_exists="replace", index=False)
    print(f"[load_postgres] {len(quotes)} linhas -> tabela quotes_history")

    fundamentals = pd.read_csv(os.path.join(DATA_DIR, "fundamentals_latest.csv"))
    fundamentals.to_sql("fundamentals_latest", engine, if_exists="replace", index=False)
    print(f"[load_postgres] {len(fundamentals)} linhas -> tabela fundamentals_latest")


if __name__ == "__main__":
    run()
