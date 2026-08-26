# Painel de Investimentos B3

Pipeline automatizada que coleta cotações e fundamentos de **~150 ações líquidas da
B3** (filtradas de um universo de referência de quase 1.000 tickers) e alimenta um
painel de screening no Metabase — P/L, ROE, dividend yield e comparação setorial —
além de ferramentas de análise fundamentalista por ativo (DRE, Análise Horizontal,
ROI/RSPL) baseadas em *Estruturas e Análise de Balanços* (Assaf Neto).

## Como funciona

```
src/fetch_universe.py  (roda esporádico — listagem muda pouco)
   scrape fundamentus.com.br → ~994 tickers da B3 inteira
        │
        ├──► Postgres: tabela universo_b3 (referência completa)
        │
        └──► config/tickers_ativos.txt (filtrado por liquidez > R$5mi/dia,
              ~150 tickers — versionado no git, é isso que a pipeline usa)

GitHub Actions (agendado, dias úteis após o fechamento da B3)
        │
        ▼
  src/pipeline.py  (lê config/tickers_ativos.txt — não depende de Postgres)
   extract.py   → yfinance: cotação (1 ano) + fundamentos, setor descoberto
                  em tempo real (info['sector']), não uma classificação manual
   transform.py → normaliza e calcula desvio em relação à média do setor
        │
        ▼
  data/quotes_history.csv
  data/fundamentals_latest.csv  (committados no repo — histórico versionado)
        │
        ▼
  scripts/atualizar_local.sh  (cron local — git pull + recarrega só se mudou)
        │
        ▼
  src/load_postgres.py
        │
        ▼
  Postgres (Docker, local)  →  Metabase (Docker, local) → painel
```

A automação roda de segunda a sexta, 18h15 (horário de Brasília) — depois do
fechamento do pregão, com ~150 tickers, leva em torno de 5 minutos. O histórico de
execuções fica visível na aba **Actions** do repositório.

`load_postgres.py` e `fetch_universe.py` são locais porque o GitHub Actions não tem
acesso ao seu Postgres — é por isso que a lista ativa vira um arquivo versionado
(`config/tickers_ativos.txt`) em vez de uma consulta ao vivo no banco.

**Status confirmado com um teste real de ponta a ponta em 2026-08-26**: GitHub Actions
rodou os 151 tickers com sucesso e commitou os dados; o cron local detectou a
mudança, puxou via `git pull` e recarregou o Postgres sozinho — as duas camadas de
automação, testadas juntas, não só cada uma isoladamente.

**Pegadinha real que vale registrar**: um workflow cujos únicos gatilhos são
`schedule` e `workflow_dispatch` pode nunca ser indexado pelo GitHub (não aparece em
`gh workflow list`, nem no botão "Run workflow" da aba Actions) — `schedule` só é
avaliado por um processo interno periódico, e `workflow_dispatch` exige que o
workflow já esteja indexado pra poder ser disparado, um catch-22. A correção foi
adicionar um `push` restrito ao próprio arquivo do workflow (`paths:
.github/workflows/update_data.yml`), que força esse primeiro reconhecimento sempre
que o arquivo for editado — já está assim no `update_data.yml`, permanente, não é
resíduo de teste.

## Universo B3 (Postgres como referência de verdade)

```bash
cd src && python fetch_universe.py
```

Baixa a listagem completa da B3 (fundamentus.com.br, ~994 tickers, todas as classes
de ação) e grava em duas formas:

- **`universo_b3`** (Postgres) — tabela de referência completa, com P/L, ROE,
  liquidez, patrimônio líquido etc. de **todos** os tickers, líquidos ou não. É essa
  tabela que dá substância real ao banco (não só os ~150 ativamente monitorados) —
  útil pra consultas SQL exploratórias, tipo "quais small caps têm ROIC > 20% mas
  liquidez baixa".
- **`config/tickers_ativos.txt`** — só os tickers com liquidez em 2 meses > R$5
  milhões/dia (~150), a lista que `pipeline.py` de fato usa pra puxar cotação e
  fundamentos completos via yfinance.

**Por que filtrar por liquidez**: a mediana de liquidez em 2 meses no universo
inteiro é **zero** — mais da metade dos ~994 tickers praticamente não negocia. Rodar
yfinance pra shell company sem liquidez não teria sentido nem seria seguro pra
qualquer análise de investimento.

Rode `fetch_universe.py` de novo se quiser mudar o corte de liquidez (edite
`LIQUIDEZ_MINIMA_PADRAO` no topo do arquivo) ou só pra atualizar a listagem depois de
IPOs/deslistagens.

## Rodando a pipeline localmente

```bash
pip install -r requirements.txt

# lista ativa (config/tickers_ativos.txt, ~150 tickers) — comportamento padrão
cd src && python pipeline.py

# ou só os papéis que você quiser
python pipeline.py PETR4.SA VALE3.SA
```

Uma seleção avulsa de papéis grava em `data/consulta_*.csv` — nunca sobrescreve o
dataset principal usado pelo painel. Se `config/tickers_ativos.txt` ainda não existir
(nunca rodou `fetch_universe.py`), cai pro fallback `config/tickers.yaml` (lista
curada manual de 20 tickers, mantida só como rede de segurança).

## Painel (Postgres + Metabase, via Docker)

Requer Docker. Power BI Desktop e Tableau Desktop não rodam no Linux — por isso o
painel usa Metabase (open source, self-hosted).

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
senha os mesmos do seu `.env`. Depois disso as tabelas `quotes_history`,
`fundamentals_latest` e `universo_b3` aparecem prontas pra montar os gráficos ou
consultar via SQL nativo (New → SQL query — bom lugar pra CTEs e window functions).

**5. Automatizar a atualização local** (opcional, recomendado):

```bash
crontab -e
# adiciona uma linha tipo:
0 19 * * 1-5 /home/SEU_USUARIO/Projects/mercado_financeiro/scripts/atualizar_local.sh
```

Isso roda todo dia útil às 19h (depois do GitHub Actions, que roda 18h15) — puxa o
repo e recarrega o Postgres só se algo realmente mudou. Log em
`logs/atualizar_local.log`. **Não instalei isso automaticamente** — o script está
pronto, mas alterar o crontab é uma configuração persistente do seu sistema, então
fica por sua conta rodar o comando acima quando quiser ativar.

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

- **Fontes**: [yfinance](https://github.com/ranaroussi/yfinance) (cotação/fundamentos
  por ticker, atraso de mercado — não tempo real, padrão mesmo em ferramentas pagas
  de varejo) e [fundamentus.com.br](https://www.fundamentus.com.br) (listagem
  completa da B3, pra descobrir o universo).
- **`quotes_history.csv`**: fechamento diário e volume, 1 ano, ~150 tickers ativos.
- **`fundamentals_latest.csv`**: snapshot atual de P/L, P/VP, ROE, dividend yield,
  margem líquida, dívida/patrimônio e market cap, com o desvio de cada ativo em
  relação à média do seu setor (setor descoberto via yfinance, não classificação
  manual).
- **`universo_b3`** (só Postgres, não vira CSV): referência completa dos ~994
  tickers da B3, incluindo os ilíquidos — não faz parte do pipeline diário.

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

- Agendar `fetch_universe.py` também (ex: mensal, via outro workflow do GitHub
  Actions) — hoje é manual, de propósito, já que listagem da B3 muda pouco.
- Migrar `fundamentals_latest.csv` pra um histórico versionado no próprio Postgres
  (uma foto por dia, não só a mais recente) pra permitir análise de tendência de
  fundamentos ano a ano.
- Publicar o Metabase num servidor próprio (VPS) se quiser acesso remoto — nesse caso,
  revisitar a exposição de portas e trocar a senha do `.env` de produção.
