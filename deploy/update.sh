#!/usr/bin/env bash
# Обновление: бэкап базы, git pull, зависимости, перезапуск, проверка. Запускать от root.
set -euo pipefail
APP_DIR=/opt/english/app
VENV=/opt/english/venv
[ "$(id -u)" = 0 ] || { echo "Запусти от root"; exit 1; }

set -a; . /etc/english.env; set +a
sudo -u english env ENGLISH_APP_DB="$ENGLISH_APP_DB" ENGLISH_BACKUP_DIR="$ENGLISH_BACKUP_DIR" \
  "$VENV/bin/python" "$APP_DIR/backup_db.py"

cd "$APP_DIR"
git pull --ff-only
"$VENV/bin/pip" install -q -r requirements.txt
systemctl restart english
for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -fsS http://127.0.0.1:8000/healthz >/dev/null 2>&1; then echo "Обновлено, работает."; exit 0; fi
  sleep 1
done
echo "Не запустилось! journalctl -u english -n 50 --no-pager"; exit 1
