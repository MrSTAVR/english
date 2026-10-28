#!/usr/bin/env bash
# Включает автообновление сайта из GitHub (раз в 5 минут + кнопка в кабинете). Запускать от root.
#   bash /opt/english/app/deploy/setup-autoupdate.sh        — включить
#   bash /opt/english/app/deploy/setup-autoupdate.sh off    — выключить полностью (и кнопку тоже)
#   bash /opt/english/app/deploy/setup-autoupdate.sh sync   — обновить unit-файлы (вызывает autoupdate.sh)
set -euo pipefail
APP_DIR=/opt/english/app
UNITS="english-autoupdate.service english-autoupdate.timer english-autoupdate.path english-remind.service english-remind.timer"
[ "$(id -u)" = 0 ] || { echo "Запусти от root: sudo bash $0"; exit 1; }

if [ "${1:-}" = "off" ]; then
  systemctl disable --now english-autoupdate.timer english-autoupdate.path 2>/dev/null || true
  echo "Автообновление выключено. Обновлять вручную: bash $APP_DIR/deploy/update.sh"
  exit 0
fi

changed=0
for u in $UNITS; do
  if ! cmp -s "$APP_DIR/deploy/$u" "/etc/systemd/system/$u"; then
    install -m 644 "$APP_DIR/deploy/$u" "/etc/systemd/system/$u"; changed=1
  fi
done
[ "$changed" = 1 ] && systemctl daemon-reload

if [ "${1:-}" = "sync" ]; then
  # включаем кнопку «Обновить сейчас», только если автообновление уже настроено
  systemctl is-enabled -q english-autoupdate.timer && systemctl enable --now english-autoupdate.path >/dev/null 2>&1
  systemctl is-enabled -q english-remind.timer || systemctl enable --now english-remind.timer >/dev/null 2>&1
  exit 0
fi

mkdir -p /opt/english/data/control && chown english:english /opt/english/data/control
systemctl enable --now english-autoupdate.timer english-autoupdate.path english-remind.timer >/dev/null
echo "Автообновление включено: сервер проверяет GitHub раз в 5 минут, кнопка в кабинете обновляет сразу."
echo "Журнал: journalctl -u english-autoupdate -n 30 --no-pager"
systemctl list-timers english-autoupdate.timer --no-pager | head -3
