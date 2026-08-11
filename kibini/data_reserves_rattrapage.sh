#!/bin/bash
# Comble dans statdb.stat_reserves les jours sans aucune ligne (jamais
# traités, ou traitement précédent en échec). Suppose koha_prod déjà à jour.
#
# Usage : ./data_reserves_rattrapage.sh [--dry-run] [date_depart AAAA-MM-JJ]
#   --dry-run   : liste les jours manquants sans lancer data_reserves.py
#   date_depart : début de la fenêtre de recherche des jours vides
#                 (par défaut : 30 jours avant aujourd'hui)
#
# Contrairement à data_issues_rattrapage.sh, rejouer un jour déjà traité par
# data_reserves.py ne crée pas de doublons (reserves_new exclut déjà les
# reserve_id présents via NOT IN) : on ne cible ici que les jours vides
# uniquement pour éviter du travail inutile, pas par nécessité de sécurité.

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

dry_run=false
since=""
for arg in "$@"; do
    case "$arg" in
        --dry-run)
            dry_run=true
            ;;
        *)
            since="$arg"
            ;;
    esac
done
since="${since:-$(date -d '30 days ago' +%Y-%m-%d)}"

echo "=== Recherche des jours sans donnée dans statdb.stat_reserves depuis $since ==="
missing_days=$(python - "$since" <<'EOF'
import sys
from datetime import date, timedelta

from sqlalchemy import text

from kiblib.utils.db import DbConn

since = date.fromisoformat(sys.argv[1])
yesterday = date.today() - timedelta(days=1)

engine = DbConn().create_engine()
with engine.connect() as conn:
    result = conn.execute(
        text("SELECT DISTINCT reservedate FROM statdb.stat_reserves WHERE reservedate >= :since"),
        {"since": since},
    )
    present = {row[0] for row in result}

day = since
while day <= yesterday:
    if day not in present:
        print(day.isoformat())
    day += timedelta(days=1)
EOF
)

if [ -z "$missing_days" ]; then
    echo "Aucun jour manquant depuis $since."
    exit 0
fi

echo "Jours manquants détectés :"
echo "$missing_days"
echo

if [ "$dry_run" = true ]; then
    echo "--dry-run : aucun traitement lancé."
    exit 0
fi

failed_days=()
while IFS= read -r day; do
    echo "=== Traitement de $day ==="
    if ! python data_reserves.py --date "$day"; then
        echo "ECHEC pour $day"
        failed_days+=("$day")
    fi
done <<< "$missing_days"

echo
if [ "${#failed_days[@]}" -gt 0 ]; then
    echo "Jours en échec : ${failed_days[*]}"
    exit 1
fi
echo "Rattrapage terminé sans erreur."
