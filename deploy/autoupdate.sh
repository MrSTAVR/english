#!/usr/bin/env bash
# Автообновление: если в main на GitHub появился новый коммит — запускает update.sh.
# Если после обновления сайт не поднялся — откатывается на прежний коммит.
# Запускается от root таймером english-autoupdate.timer (раз в 5 минут) и сразу —
# по кнопке «Обновить сейчас» в кабинете администратора (english-autoupdate.path).
#
# Связь с сайтом — папка $CTRL (сайт может писать только в /opt/english/data):
#   update-now      — просьба обновить сейчас (её создаёт сайт, удаляет этот скрипт)
#   autoupdate-off  — автообновление выключено (по таймеру только проверяем)
#   status, update.log — что видно в кабинете администратора
set -uo pipefail
APP_DIR="${APP_DIR:-/opt/english/app}"     # переменные окружения — только для тестов
VENV="${VENV:-/opt/english/venv}"
STATE="${STATE:-/opt/english/autoupdate}"
CTRL="${CTRL:-/opt/english/data/control}"
BAD="$STATE/bad-commit"            # коммит, на котором обновление сломалось: сам его не повторяем
LOG="$CTRL/update.log"
mkdir -p "$STATE" "$CTRL"
id english >/dev/null 2>&1 && chown english:english "$CTRL"

exec 9>"$STATE/lock"
flock -n 9 || exit 0               # предыдущий запуск ещё идёт

log() { echo "$(date '+%d.%m.%Y %H:%M:%S') $*" | tee -a "$LOG"; }
status() {                         # status <результат>: снимок для кабинета
  { echo "checked=$(date '+%d.%m.%Y %H:%M:%S')"
    echo "local=$(git rev-parse HEAD 2>/dev/null)"
    echo "remote=${NEW:-}"
    echo "remote_subject=$(git log -1 --no-merges --format=%s "${NEW:-HEAD}" 2>/dev/null)"
    echo "result=$1"; } > "$CTRL/status.tmp" && mv "$CTRL/status.tmp" "$CTRL/status"
}
finish() {                         # журнал не растёт бесконечно
  [ -f "$LOG" ] && tail -n 1000 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
  exit "$1"
}

# новые версии unit-файлов автообновления ставятся сами
if [ "${AUTOUPDATE_SYNC:-1}" = 1 ] && [ -f "$APP_DIR/deploy/setup-autoupdate.sh" ]; then
  bash "$APP_DIR/deploy/setup-autoupdate.sh" sync >/dev/null 2>&1 || true
fi

FORCE=0
if [ -f "$CTRL/update-now" ]; then FORCE=1; rm -f "$CTRL/update-now"; fi

cd "$APP_DIR" || finish 1
BRANCH=$(git symbolic-ref --short -q HEAD || true)
if [ "$BRANCH" != "main" ]; then
  [ "$FORCE" = 1 ] && log "Код не на ветке main (${BRANCH:-отдельный коммит}) — обновление пропущено."
  status "not-main"; finish 0
fi
if ! git fetch -q origin main; then
  [ "$FORCE" = 1 ] && log "Не удалось связаться с GitHub."
  status "no-network"; finish 0
fi
OLD=$(git rev-parse HEAD)
NEW=$(git rev-parse origin/main)
if [ "$OLD" = "$NEW" ]; then
  [ "$FORCE" = 1 ] && log "Проверка по кнопке: обновлений нет, установлена последняя версия."
  status "up-to-date"; finish 0
fi
if [ "$FORCE" = 0 ]; then
  if [ -f "$CTRL/autoupdate-off" ]; then status "available"; finish 0; fi
  if [ -f "$BAD" ] && [ "$(cat "$BAD")" = "$NEW" ]; then status "bad"; finish 0; fi   # ждём исправление
fi

log "Обновление ${OLD:0:7} → ${NEW:0:7}: $(git log -1 --no-merges --format=%s "$NEW")$([ "$FORCE" = 1 ] && echo ' (по кнопке)')"
bash "$APP_DIR/deploy/update.sh" 2>&1 | tee -a "$LOG"
if [ "${PIPESTATUS[0]}" = 0 ]; then
  rm -f "$BAD"
  log "Готово: работает ${NEW:0:7}."
  status "updated"; finish 0
fi

log "Обновление не удалось — откат на ${OLD:0:7}."
echo "$NEW" > "$BAD"
git reset -q --hard "$OLD"
"$VENV/bin/pip" install -q -r requirements.txt
systemctl restart english
for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -fsS http://127.0.0.1:8000/healthz >/dev/null 2>&1; then
    log "Откат выполнен, сайт работает."; status "rolled-back"; finish 1
  fi
  sleep 1
done
log "После отката сайт не отвечает! journalctl -u english -n 50 --no-pager"
status "down"; finish 1
