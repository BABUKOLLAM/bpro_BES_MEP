#!/usr/bin/env bash
# Nightly backup: database dump + Odoo filestore (attachments, SCORM content).
# Cron example (2:30 AM daily):
#   30 2 * * * /path/to/bpro-bes-mini-erp-odoo/scripts/backup.sh >> /var/log/bpro-backup.log 2>&1
set -euo pipefail

cd "$(dirname "$0")/../deploy"
STAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="${BACKUP_DIR:-$HOME/bpro-backups}"
KEEP_DAYS="${KEEP_DAYS:-14}"
mkdir -p "$BACKUP_DIR"

echo "[$STAMP] dumping database..."
docker compose -f docker-compose.prod.yml exec -T db \
    pg_dump -U odoo -Fc bpro > "$BACKUP_DIR/bpro-db-$STAMP.dump"

echo "[$STAMP] archiving filestore..."
docker compose -f docker-compose.prod.yml exec -T odoo \
    tar -czf - /var/lib/odoo > "$BACKUP_DIR/bpro-filestore-$STAMP.tgz"

find "$BACKUP_DIR" -name 'bpro-*' -mtime "+$KEEP_DAYS" -delete
echo "[$STAMP] done: $(du -sh "$BACKUP_DIR" | cut -f1) total in $BACKUP_DIR"
