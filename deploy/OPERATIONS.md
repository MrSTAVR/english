# Эксплуатация English Fun на сервере

Сайт: https://stavr.mywire.org:8443/ · код: `/opt/english/app` · база: `/opt/english/data` · копии: `/opt/english/backups`
Все команды — на сервере под root.

## Каждый день ничего делать не нужно
Копия базы создаётся сама в 03:17 (хранятся последние 14). Сертификат продлевает Caddy.

## Проверка здоровья (раз в неделю или когда что-то не так)
```bash
bash /opt/english/app/deploy/check.sh
```
Покажет ✅/❌: службы, доступность снаружи, срок сертификата, свежесть и целостность копии, диск.

## Уведомление, если сайт упал
Бесплатный внешний монитор (например, UptimeRobot): тип «HTTP(s)», адрес
`https://stavr.mywire.org:8443/healthz`, проверка раз в 5 минут, ключевое слово `ok`. Письмо или Telegram придут, когда сайт не отвечает.

## Копия базы на свой компьютер (рекомендуется раз в неделю)
Копии на самом сервере не спасут, если сломается сам сервер. PowerShell на Windows:
```powershell
mkdir C:\english-backups -Force
scp "root@stavr.mywire.org:/opt/english/backups/*" C:\english-backups\
```

## Восстановление базы из копии
```bash
ls -1t /opt/english/backups | head          # выбрать файл
bash /opt/english/app/deploy/restore.sh /opt/english/backups/english_app-ГГГГММДД-ЧЧММСС.db.gz
```
Копия проверяется до начала, текущая база не удаляется, а откладывается как `*.before-restore-…`.
Если копия лежит на компьютере: сначала `scp C:\english-backups\файл.db.gz root@stavr.mywire.org:/root/`.

## Обновление приложения
В PyCharm: коммит и Push, затем на сервере:
```bash
bash /opt/english/app/deploy/update.sh
```
Скрипт делает копию базы, `git pull`, ставит зависимости, перезапускает и проверяет.
Откат кода: `cd /opt/english/app && git log --oneline -5`, затем `git checkout <коммит> && systemctl restart english`
(вернуться на актуальный код: `git checkout main && git pull`).

## Частые действия
| Что | Команда |
|---|---|
| Логи приложения | `journalctl -u english -n 100 --no-pager` |
| Логи Caddy / сертификата | `journalctl -u caddy -n 100 --no-pager` |
| Перезапуск | `systemctl restart english` |
| Сменить пароль родителя | `nano /etc/english.env` (строка `ENGLISH_PARENT_PASSWORD`), затем `systemctl restart english` |
| Копия прямо сейчас | `sudo -u english env ENGLISH_APP_DB=/opt/english/data/english_app.db ENGLISH_BACKUP_DIR=/opt/english/backups /opt/english/venv/bin/python /opt/english/app/backup_db.py` |

## Автоматические обновления безопасности Debian (один раз)
```bash
apt-get install -y unattended-upgrades
dpkg-reconfigure -plow unattended-upgrades      # ответить «Да»
```
Ядро и сервисы после обновлений иногда требуют перезагрузки: `reboot` в тихий час. Приложение и Caddy поднимутся сами.

## Что не трогаем
Xray/x-ui (VPN) занимает порт 443: приложение живёт на 8443, чтобы им не мешать. Firewall (ufw) не включали,
чтобы не отрезать VPN и SSH; при желании ограничить порты — настраивать вместе с правилами x-ui.
