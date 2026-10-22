#!/usr/bin/env bash
# Включает автообновление сайта из GitHub (раз в 5 минут). Запускать от root.
#   bash /opt/english/app/deploy/setup-autoupdate.sh        — включить
#   bash /opt/english/app/deploy/setup-autoupdate.sh off    — выключить
set -euo pipefail
APP_DIR=/opt/english/app
[ "$(id -u)" = 0 ] || { echo "Запусти от root: sudo bash $0"; exit 1; }

if [ "${1:-}" = "off" ]; then
  systemctl disable --now english-autoupdate.timer 2>/dev/null || true
  echo "Автообновление выключено. Обновлять вручную: bash $APP_DIR/deploy/update.sh"
  exit 0
fi

install -m 644 "$APP_DIR/deploy/english-autoupdate.service" /etc/systemd/system/english-autoupdate.service
install -m 644 "$APP_DIR/deploy/english-autoupdate.timer" /etc/systemd/system/english-autoupdate.timer
systemctl daemon-reload
systemctl enable --now english-autoupdate.timer >/dev/null
echo "Автообновление включено: сервер проверяет GitHub раз в 5 минут."
echo "Журнал: journalctl -u english-autoupdate -n 30 --no-pager"
systemctl list-timers english-autoupdate.timer --no-pager | head -3
