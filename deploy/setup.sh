#!/usr/bin/env bash
# Первичная установка English Fun на Debian 12 (запускать от root).
# Не трогает Xray/x-ui и порт 443. Можно запускать повторно.
set -euo pipefail

DOMAIN="${DOMAIN:-stavr.mywire.org}"
HTTPS_PORT="${HTTPS_PORT:-8443}"
BASE=/opt/english
APP_DIR=$BASE/app
VENV=$BASE/venv
DATA_DIR=$BASE/data
BACKUP_DIR=$BASE/backups
ENV_FILE=/etc/english.env

[ "$(id -u)" = 0 ] || { echo "Запусти от root: sudo bash $0"; exit 1; }
[ -f "$APP_DIR/wsgi.py" ] || { echo "Нет $APP_DIR/wsgi.py — сначала: git clone <репозиторий> $APP_DIR"; exit 1; }

# 80 нужен для получения сертификата, HTTPS_PORT — для сайта
for port in 80 "$HTTPS_PORT"; do
  if ss -tlnp | grep -E ":${port}\b" | grep -vq caddy; then
    echo "Порт $port занят другой программой:"; ss -tlnp | grep -E ":${port}\b"; exit 1
  fi
done

echo "==> Пакеты"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3-venv python3-pip caddy sqlite3 git curl

echo "==> Пользователь и папки"
id english >/dev/null 2>&1 || useradd --system --home-dir $BASE --shell /usr/sbin/nologin english
mkdir -p "$DATA_DIR" "$BACKUP_DIR"
chown english:english "$DATA_DIR" "$BACKUP_DIR"
chmod 750 "$DATA_DIR" "$BACKUP_DIR"

echo "==> Python-окружение"
[ -d "$VENV" ] || python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q -r "$APP_DIR/requirements.txt"

if [ ! -f "$ENV_FILE" ]; then
  echo "==> Настройки ($ENV_FILE)"
  while true; do
    read -rsp "Придумай пароль кабинета родителя (от 8 символов): " PW; echo
    read -rsp "Повтори пароль: " PW2; echo
    if [ "$PW" != "$PW2" ]; then echo "Не совпали."; continue; fi
    if [ "${#PW}" -lt 8 ]; then echo "Слишком короткий."; continue; fi
    case "$PW" in *\"*|*\'*|*\\*) echo "Не используй символы \" ' \\"; continue;; esac
    break
  done
  KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
  umask 027
  cat > "$ENV_FILE" <<EOT
ENGLISH_ENV=production
ENGLISH_BEHIND_PROXY=1
ENGLISH_PARENT_PASSWORD="$PW"
ENGLISH_SECRET_KEY="$KEY"
ENGLISH_APP_DB=$DATA_DIR/english_app.db
ENGLISH_BACKUP_DIR=$BACKUP_DIR
EOT
  chown root:english "$ENV_FILE"; chmod 640 "$ENV_FILE"
else
  echo "==> $ENV_FILE уже есть, оставляю как есть"
fi

echo "==> Сервис приложения"
install -m 644 "$APP_DIR/deploy/english.service" /etc/systemd/system/english.service
systemctl daemon-reload
systemctl enable english >/dev/null
systemctl restart english

echo "==> Caddy (HTTPS на порту $HTTPS_PORT)"
sed -e "s/__DOMAIN__/$DOMAIN/" -e "s/__HTTPS_PORT__/$HTTPS_PORT/" \
    "$APP_DIR/deploy/Caddyfile.template" > /etc/caddy/Caddyfile
systemctl enable caddy >/dev/null
systemctl restart caddy

echo "==> Ежедневная резервная копия (03:17)"
cat > /etc/cron.d/english-backup <<EOT
ENGLISH_APP_DB=$DATA_DIR/english_app.db
ENGLISH_BACKUP_DIR=$BACKUP_DIR
17 3 * * * english $VENV/bin/python $APP_DIR/backup_db.py >/dev/null 2>&1
EOT
chmod 644 /etc/cron.d/english-backup

echo "==> Проверка"
for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -fsS http://127.0.0.1:8000/healthz >/dev/null 2>&1; then OK=1; break; fi
  sleep 1
done
if [ "${OK:-0}" = 1 ]; then
  echo "Приложение работает."
else
  echo "Приложение не отвечает. Смотри: journalctl -u english -n 50 --no-pager"; exit 1
fi
echo
echo "Готово. Открой https://$DOMAIN:$HTTPS_PORT/ (сертификат появится за ~30 секунд)."
echo "Если не открывается: journalctl -u caddy -n 50 --no-pager"
