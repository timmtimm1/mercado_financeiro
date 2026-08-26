#!/usr/bin/env bash
# Puxa os dados mais recentes do repo (gerados pelo GitHub Actions) e recarrega o
# Postgres local, pro Metabase refletir sempre o dado mais novo.
#
# Pensado pra rodar via cron — ver crontab.exemplo.txt nesta pasta.

set -euo pipefail

PROJETO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$PROJETO_DIR/logs"
LOG_FILE="$LOG_DIR/atualizar_local.log"

mkdir -p "$LOG_DIR"
exec >> "$LOG_FILE" 2>&1

echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

cd "$PROJETO_DIR"

# só atualiza o Postgres se o git pull realmente trouxe dado novo — não recarrega
# o banco à toa se o Action ainda não rodou (ex: dia sem novidade)
ANTES=$(git rev-parse HEAD)
git pull --ff-only
DEPOIS=$(git rev-parse HEAD)

if [ "$ANTES" = "$DEPOIS" ]; then
    echo "Sem mudanças no repo — Postgres não foi recarregado."
    exit 0
fi

echo "Repo atualizado ($ANTES -> $DEPOIS). Recarregando Postgres..."
source "$PROJETO_DIR/.venv/bin/activate"
cd "$PROJETO_DIR/src"
python load_postgres.py

echo "OK."
