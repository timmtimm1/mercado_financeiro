# Painel de Investimentos B3

Pipeline automatizada que coleta cotações e fundamentos de ~20 ações da B3 (bancos,
varejo, commodities, utilities, indústria) e alimenta um painel de screening no
Metabase — P/L, ROE, dividend yield e comparação setorial — além de ferramentas de
análise fundamentalista por ativo (DRE, Análise Horizontal, ROI/RSPL) baseadas em
*Estruturas e Análise de Balanços* (Assaf Neto).

## Como funciona

```
GitHub Actions (agendado, dias úteis após o fechamento da B3)
        │
        ▼
  src/pipeline.py
   extract.py   → puxa cotação (1 ano) e fundamentos via yfinance
   transform.py → normaliza e calcula desvio em relação à média do setor
        │
        ▼
  data/quotes_history.csv
  data/fundamentals_latest.csv  (committados no repo, viram o histórico versionado)
        │
        ▼
  src/load_postgres.py  (rodado localmente)
        │
        ▼
  Postgres (Docker, local)  →  Metabase (Docker, local) → painel
```

A automação roda de segunda a sexta, 18h15 (horário de Brasília) — depois do
fechamento do pregão. O histórico de execuções fica visível na aba **Actions** do
repositório. `load_postgres.py` é local porque o GitHub Actions não tem acesso ao seu
Postgres — puxe os dados mais recentes (`git pull`) e rode o load quando quiser
atualizar o painel.

## Rodando localmente

```bash
pip install -r requirements.txt

# lista completa do config/tickers.yaml (comportamento padrão)
cd src && python pipeline.py

# ou só os papéis que você quiser
python pipeline.py PETR4.SA VALE3.SA
```

Uma seleção avulsa de papéis grava em `data/consulta_*.csv` — nunca sobrescreve o
dataset principal usado pelo painel.

## Painel (Postgres + Metabase, via Docker)

Requer Docker. Metabase não roda no Power BI Desktop nem no Tableau Desktop no
Linux — por isso o painel usa Metabase (open source, self-hosted).

**1. Configurar credenciais locais** (nunca commitadas):

```bash
cp .env.example .env
# edite .env e troque POSTGRES_PASSWORD por uma senha forte sua
```

**2. Subir os containers** (só expostos em `localhost`, não na rede):

```bash
docker compose up -d
docker compose ps   # confira os dois "healthy"/"Up"
```

**3. Carregar os dados no Postgres:**

```bash
cd src && python load_postgres.py
```

**4. Abrir o Metabase**: [http://localhost:3000](http://localhost:3000) — a primeira
vez pede pra você criar uma conta local (interativo, não dá pra automatizar) e
conectar um banco: escolha **PostgreSQL**, host `postgres`, porta `5432`, banco/usuário/
senha os mesmos do seu `.env`. Depois disso as tabelas `quotes_history` e
`fundamentals_latest` aparecem prontas pra montar os gráficos.

Pra atualizar o painel depois de uma nova execução da pipeline: `git pull` (traz os
CSVs novos) → `python load_postgres.py` (recarrega o Postgres) → o Metabase já reflete
os dados novos, sem precisar reconfigurar nada.

## Análise fundamentalista por ativo

```bash
cd src
python dre.py TICKER.SA               # DRE no terminal (estrutura Quadro 5.1)
python dre_report.py TICKER.SA        # DRE como imagem PNG
python indicadores.py TICKER.SA       # AH, margens, ROI/RSPL, endividamento, liquidez → PNG
```

Bancos (estrutura Cosif, sem CPV/Lucro Bruto) não são suportados por `dre.py` — a
função detecta e recusa em vez de forçar dados que não existem.

## Dados

- **Fonte**: [yfinance](https://github.com/ranaroussi/yfinance) (Yahoo Finance, não
  oficial). Cotação com atraso de mercado, não tempo real — padrão mesmo em
  ferramentas pagas de varejo.
- **`quotes_history.csv`**: fechamento diário e volume, 1 ano, por ticker.
- **`fundamentals_latest.csv`**: snapshot atual de P/L, P/VP, ROE, dividend yield,
  margem líquida, dívida/patrimônio e market cap, com o desvio de cada ativo em
  relação à média do seu setor.

## Tickers acompanhados

Configurados em `config/tickers.yaml`, agrupados por setor. Adicionar um ticker novo
é só incluir a linha no YAML — a próxima execução completa da pipeline já pega.

## Segurança

- Nenhuma credencial fica no código nem no histórico do git — tudo via `.env`
  (gitignored; `.env.example` documenta as chaves esperadas, sem valores reais).
- Postgres e Metabase só escutam em `127.0.0.1` — não ficam acessíveis pra
  rede/internet a partir do `docker-compose.yml` como está.
- Dependências com versão fixada em `requirements.txt` (não `>=` solto).
- O GitHub Actions roda com `permissions: contents: write` apenas — sem escopo mais
  amplo que o necessário pra commitar os dados.
- O input de papéis do disparo manual (`workflow_dispatch`) passa por variável de
  ambiente no workflow, nunca interpolado direto num `run:` — evita injeção de
  comando a partir do input.

## Próximos passos possíveis

- Rodar `load_postgres.py` automaticamente depois de um `git pull`, via hook ou cron
  local (hoje é manual, de propósito).
- Migrar `fundamentals_latest.csv` pra um histórico versionado no próprio Postgres
  (uma foto por dia, não só a mais recente) pra permitir análise de tendência de
  fundamentos ano a ano.
- Publicar o Metabase num servidor próprio (VPS) se quiser acesso remoto — nesse caso,
  revisitar a exposição de portas e trocar a senha do `.env` de produção.
