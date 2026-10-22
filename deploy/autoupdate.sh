#!/usr/bin/env bash
# Автообновление: если в main на GitHub появился новый коммит — запускает update.sh.
# Если после обновления сайт не поднялся — откатывается на прежний коммит.
# Запускается таймером english-autoupdate.timer (раз в 5 минут) от root.
set -uo pipefail
APP_DIR="${APP_DIR:-/opt/english/app}"     # переменные окружения — только для тестов
VENV="${VENV:-/opt/english/venv}"
STATE="${STATE:-/opt/english/autoupdate}"
BAD="$STATE/bad-commit"            # коммит, на котором обновление сломалось: его не повторяем
mkdir -p "$STATE"

exec 9>"$STATE/lock"
flock -n 9 || exit 0               # предыдущий запуск ещё идёт

cd "$APP_DIR" || exit 1
BRANCH=$(git symbolic-ref --short -q HEAD || true)
if [ "$BRANCH" != "main" ]; then
  echo "Код не на ветке main (${BRANCH:-отдельный коммит}) — автообновление пропущено."
  exit 0
fi
git fetch -q origin main || { echo "Не удалось связаться с GitHub."; exit 0; }
OLD=$(git rev-parse HEAD)
NEW=$(git rev-parse origin/main)
[ "$OLD" = "$NEW" ] && exit 0
if [ -f "$BAD" ] && [ "$(cat "$BAD")" = "$NEW" ]; then
  exit 0                           # этот коммит уже ломал сайт — ждём следующий
fi

echo "Обновление ${OLD:0:7} → ${NEW:0:7}: $(git log -1 --format=%s "$NEW")"
if bash "$APP_DIR/deploy/update.sh"; then
  rm -f "$BAD"
  exit 0
fi

echo "Обновление не удалось — откат на ${OLD:0:7}."
echo "$NEW" > "$BAD"
git reset -q --hard "$OLD"
"$VENV/bin/pip" install -q -r requirements.txt
systemctl restart english
for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -fsS http://127.0.0.1:8000/healthz >/dev/null 2>&1; then echo "Откат выполнен, сайт работает."; exit 1; fi
  sleep 1
done
echo "После отката сайт не отвечает! journalctl -u english -n 50 --no-pager"
exit 1
