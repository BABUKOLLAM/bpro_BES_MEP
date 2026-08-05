#!/usr/bin/env bash
# Checks the live site and the three containers; logs every check, and logs
# loudly (with a distinct marker line) on any state change so a human
# reviewing the log - or a future alerting hook - can find transitions
# without reading every line.
set -uo pipefail

URL="https://mepcrm.in/odoo/login"
LOG_FILE="/var/log/bpro-healthcheck.log"
STATE_FILE="/var/run/bpro-healthcheck.state"
STAMP=$(date "+%Y-%m-%d %H:%M:%S")

HTTP_CODE=$(curl -sL -o /dev/null -w "%{http_code}" --max-time 15 "$URL" 2>/dev/null || echo "000")

DB_STATUS="down"
ODOO_STATUS="down"
CADDY_STATUS="down"
docker inspect -f '{{.State.Health.Status}}' deploy-db-1 2>/dev/null | grep -q healthy && DB_STATUS="up"
docker inspect -f '{{.State.Status}}' deploy-odoo-1 2>/dev/null | grep -q running && ODOO_STATUS="up"
docker inspect -f '{{.State.Status}}' deploy-caddy-1 2>/dev/null | grep -q running && CADDY_STATUS="up"

if [ "$HTTP_CODE" = "200" ] && [ "$DB_STATUS" = "up" ] && [ "$ODOO_STATUS" = "up" ] && [ "$CADDY_STATUS" = "up" ]; then
    CURRENT_STATE="up"
else
    CURRENT_STATE="down"
fi

PREV_STATE="unknown"
[ -f "$STATE_FILE" ] && PREV_STATE=$(cat "$STATE_FILE")

echo "[$STAMP] http=$HTTP_CODE db=$DB_STATUS odoo=$ODOO_STATUS caddy=$CADDY_STATUS state=$CURRENT_STATE" >> "$LOG_FILE"

if [ "$CURRENT_STATE" != "$PREV_STATE" ]; then
    echo "[$STAMP] *** STATE CHANGE: $PREV_STATE -> $CURRENT_STATE ***" >> "$LOG_FILE"
fi

echo "$CURRENT_STATE" > "$STATE_FILE"

# keep the log from growing unbounded
if [ -f "$LOG_FILE" ] && [ "$(stat -c%s "$LOG_FILE" 2>/dev/null || echo 0)" -gt 20971520 ]; then
    tail -c 10485760 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
fi
