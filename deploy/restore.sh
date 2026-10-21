#!/usr/bin/env bash
# Восстановление базы из резервной копии. Запускать от root:
#   bash /opt/english/app/deploy/restore.sh /opt/english/backups/english_app-YYYYmmdd-HHMMSS.db.gz
# Текущая база не удаляется, а откладывается рядом с суффиксом .before-restore-<время>.
set -euo pipefail
ENV_FILE="${ENV_FILE:-/etc/english.env}"
SERVICE="${SERVICE:-english}"

[ "$(id -u)" = 0 ] || [ -n "${RESTORE_TEST:-}" ] || { echo "Запусти от root"; exit 1; }
BACKUP="${1:-}"
[ -f "$BACKUP" ] || { echo "Использование: $0 <файл-копии.db.gz>"; ls -1t /opt/english/backups 2>/dev/null | head -5; exit 1; }

set -a; . "$ENV_FILE"; set +a
DB="$ENGLISH_APP_DB"
TMP="$(mktemp "${DB}.restore.XXXXXX")"
trap 'rm -f "$TMP"' EXIT

echo "==> Проверяю копию"
gzip -dc "$BACKUP" > "$TMP"
[ "$(sqlite3 "$TMP" 'PRAGMA integrity_check;')" = "ok" ] || { echo "Копия повреждена, ничего не меняю."; exit 1; }
sqlite3 "$TMP" 'SELECT COUNT(*) FROM students;' >/dev/null || { echo "В копии нет таблицы students."; exit 1; }

echo "==> Останавливаю приложение"
systemctl stop "$SERVICE"
if [ -f "$DB" ]; then
  SAVED="$DB.before-restore-$(date +%Y%m%d-%H%M%S)"
  mv "$DB" "$SAVED"; echo "    старая база сохранена: $SAVED"
fi
rm -f "$DB-wal" "$DB-shm"
mv "$TMP" "$DB"; trap - EXIT
chown english:english "$DB" 2>/dev/null || true
chmod 640 "$DB"

echo "==> Запускаю приложение"
systemctl start "$SERVICE"
for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -fsS http://127.0.0.1:8000/healthz >/dev/null 2>&1; then echo "Готово: база восстановлена."; exit 0; fi
  sleep 1
done
echo "Приложение не поднялось: journalctl -u $SERVICE -n 50 --no-pager"; exit 1
