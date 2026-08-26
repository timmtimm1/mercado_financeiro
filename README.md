# Painel de Investimentos B3

Pipeline automatizada que coleta cotações e fundamentos de ~20 ações da B3 (bancos,
varejo, commodities, utilities, indústria) e alimenta um painel de screening no
Power BI — P/L, ROE, dividend yield e comparação setorial.

## Como funciona

```
GitHub Actions (agendado, dias úteis após o fechamento da B3)
        │
        ▼
  src/pipeline.py
   extract.py  → puxa cotação (1 ano) e fundamentos via yfinance
   transform.py → normaliza e calcula desvio em relação à média do setor
        │
        ▼
  data/quotes_history.csv
  data/fundamentals_latest.csv
        │
        ▼
  Power BI (conector Web, aponta pra URL raw do GitHub) → Atualizar
```

A automação roda de segunda a sexta, 18h15 (horário de Brasília) — depois do
fechamento do pregão. O histórico de execuções fica visível na aba **Actions** do
repositório.

## Rodando localmente

```bash
pip install -r requirements.txt
cd src && python pipeline.py
```

## Conectando no Power BI

Obter Dados → Web → cole a URL raw do arquivo no GitHub, por exemplo:

```
https://raw.githubusercontent.com/<seu-usuario>/mercado_financeiro/main/data/fundamentals_latest.csv
```

Clicar em **Atualizar** no Power BI Desktop sempre traz a versão mais recente
gerada pela automação — sem precisar rodar nada manualmente.

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
é só incluir a linha no YAML — a próxima execução da pipeline já pega.

## Próximos passos possíveis

- Migrar `fundamentals_latest.csv` pra um histórico versionado (uma foto por dia,
  não só a mais recente) pra permitir análise de tendência de fundamentos.
- Trocar CSV por PostgreSQL, com um schema de fato/dimensão de verdade.
- Publicar o painel no Power BI Service com atualização agendada nativa (hoje o
  refresh é manual, pela limitação do tier gratuito do Power BI Desktop).
