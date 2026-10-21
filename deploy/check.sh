#!/usr/bin/env bash
# Проверка здоровья сервера: bash /opt/english/app/deploy/check.sh
# Код выхода 0 — всё хорошо, 1 — есть проблемы (можно вызывать из cron/мониторинга).
ENV_FILE="${ENV_FILE:-/etc/english.env}"
DOMAIN="${DOMAIN:-stavr.mywire.org}"
HTTPS_PORT="${HTTPS_PORT:-8443}"
[ -r "$ENV_FILE" ] && { set -a; . "$ENV_FILE"; set +a; }
BACKUP_DIR="${ENGLISH_BACKUP_DIR:-/opt/english/backups}"
DB="${ENGLISH_APP_DB:-/opt/english/data/english_app.db}"
bad=0
ok()   { echo "  ✅ $*"; }
warn() { echo "  ❌ $*"; bad=1; }

echo "Службы"
for s in english caddy x-ui; do
  if systemctl is-active --quiet "$s"; then ok "$s работает"
  elif [ "$s" = "x-ui" ]; then echo "  ℹ️  x-ui не найден (не страшно)"
  else warn "$s НЕ работает: journalctl -u $s -n 30 --no-pager"; fi
done

echo "Сайт"
[ "$(curl -fsS -m 5 http://127.0.0.1:8000/healthz 2>/dev/null)" = "ok" ] && ok "приложение отвечает локально" || warn "приложение не отвечает на 127.0.0.1:8000"
[ "$(curl -fsS -m 10 "https://$DOMAIN:$HTTPS_PORT/healthz" 2>/dev/null)" = "ok" ] && ok "доступно снаружи: https://$DOMAIN:$HTTPS_PORT/" || warn "не открывается по https://$DOMAIN:$HTTPS_PORT/ (Caddy, порт, firewall хостера?)"

echo "Сертификат"
end=$(echo | timeout 10 openssl s_client -connect "$DOMAIN:$HTTPS_PORT" -servername "$DOMAIN" 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
if [ -n "$end" ]; then
  days=$(( ( $(date -d "$end" +%s) - $(date +%s) ) / 86400 ))
  [ "$days" -ge 10 ] && ok "действует ещё $days дн." || warn "сертификат истекает через $days дн. (Caddy должен продлить сам: journalctl -u caddy)"
else warn "не удалось прочитать сертификат"; fi

echo "Резервные копии"
last=$(ls -1t "$BACKUP_DIR"/english_app-*.db.gz 2>/dev/null | head -1)
if [ -z "$last" ]; then warn "копий нет в $BACKUP_DIR"
else
  age=$(( ( $(date +%s) - $(stat -c %Y "$last") ) / 3600 ))
  [ "$age" -le 36 ] && ok "последняя копия $age ч. назад ($(basename "$last"))" || warn "последней копии $age ч. (cron не работает?)"
  tmp=$(mktemp); gzip -dc "$last" > "$tmp" 2>/dev/null
  [ "$(sqlite3 "$tmp" 'PRAGMA integrity_check;' 2>/dev/null)" = "ok" ] && ok "копия читается и цела" || warn "копия повреждена"
  rm -f "$tmp"
fi
[ -f "$DB" ] && ok "база $(du -h "$DB" | cut -f1)" || warn "базы нет: $DB"

echo "Диск и память"
use=$(df --output=pcent / | tail -1 | tr -dc '0-9')
[ "$use" -lt 85 ] && ok "диск занят на $use%" || warn "диск занят на $use%"
free -m | awk '/Mem:/ {printf "  ℹ️  память: занято %d из %d МБ\n", $3, $2}'

echo
[ "$bad" = 0 ] && echo "Всё в порядке." || echo "Есть проблемы — см. ❌ выше."
exit $bad
