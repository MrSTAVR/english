# -*- coding: utf-8 -*-
"""Файлы развёртывания: скрипты синтаксически верны и не испорчены Windows-переводами строк."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

DEPLOY = Path(__file__).resolve().parent.parent / "deploy"
SCRIPTS = ["setup.sh", "update.sh", "restore.sh", "check.sh", "autoupdate.sh", "setup-autoupdate.sh"]


@pytest.mark.parametrize("name", SCRIPTS)
def test_script_is_lf_and_valid_bash(name):
    data = (DEPLOY / name).read_bytes()
    assert data.startswith(b"#!/usr/bin/env bash\n") and b"\r" not in data
    if shutil.which("bash"):
        assert subprocess.run(["bash", "-n", str(DEPLOY / name)]).returncode == 0


def test_service_and_caddy_templates():
    svc = (DEPLOY / "english.service").read_text(encoding="utf-8")
    assert "EnvironmentFile=/etc/english.env" in svc and "User=english" in svc
    assert "ReadWritePaths=/opt/english/data" in svc
    caddy = (DEPLOY / "Caddyfile.template").read_text(encoding="utf-8")
    assert "__DOMAIN__" in caddy and "__HTTPS_PORT__" in caddy and "reverse_proxy 127.0.0.1:8000" in caddy


def test_setup_does_not_touch_xray_port():
    setup = (DEPLOY / "setup.sh").read_text(encoding="utf-8")
    assert 'HTTPS_PORT="${HTTPS_PORT:-8443}"' in setup and ":443" not in setup


def test_autoupdate_units():
    svc = (DEPLOY / "english-autoupdate.service").read_text(encoding="utf-8")
    timer = (DEPLOY / "english-autoupdate.timer").read_text(encoding="utf-8")
    assert "Type=oneshot" in svc and "/opt/english/app/deploy/autoupdate.sh" in svc
    assert "OnUnitActiveSec=5min" in timer and "WantedBy=timers.target" in timer
    path = (DEPLOY / "english-autoupdate.path").read_text(encoding="utf-8")
    assert "PathExists=/opt/english/data/control/update-now" in path and "Unit=english-autoupdate.service" in path
    for name in ("english-autoupdate.service", "english-autoupdate.timer", "english-autoupdate.path"):
        assert b"\r" not in (DEPLOY / name).read_bytes()


def _git(cwd, *args):
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=cwd, check=True,
                   capture_output=True)


@pytest.mark.skipif(not (shutil.which("git") and shutil.which("flock") and shutil.which("bash")),
                    reason="нужны git, flock и bash")
def test_autoupdate_updates_and_rolls_back(tmp_path):
    """Песочница: «GitHub» — локальный bare-репозиторий; systemctl/curl/pip — заглушки.
    update.sh в песочнице делает git pull и «падает», если в коде есть файл BROKEN."""
    origin, work, app = tmp_path / "origin.git", tmp_path / "work", tmp_path / "app"
    fake = tmp_path / "bin"
    fake.mkdir()
    for tool in ("systemctl", "curl"):
        (fake / tool).write_text("#!/bin/sh\nexit 0\n")
        (fake / tool).chmod(0o755)
    (tmp_path / "venv" / "bin").mkdir(parents=True)
    (tmp_path / "venv" / "bin" / "pip").write_text("#!/bin/sh\nexit 0\n")
    (tmp_path / "venv" / "bin" / "pip").chmod(0o755)

    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    subprocess.run(["git", "clone", "-q", str(origin), str(work)], check=True, capture_output=True)
    (work / "deploy").mkdir()
    (work / "deploy" / "update.sh").write_text(
        "#!/usr/bin/env bash\nset -e\ncd \"$APP_DIR\"\ngit pull -q --ff-only\n[ ! -f BROKEN ]\n")
    (work / "requirements.txt").write_text("")
    (work / "v.txt").write_text("1")
    _git(work, "checkout", "-q", "-b", "main")
    _git(work, "add", ".")
    _git(work, "commit", "-qm", "v1")
    _git(work, "push", "-q", "origin", "main")
    subprocess.run(["git", "clone", "-q", "-b", "main", str(origin), str(app)], check=True, capture_output=True)

    ctrl = tmp_path / "control"
    env = {**os.environ, "APP_DIR": str(app), "VENV": str(tmp_path / "venv"), "STATE": str(tmp_path / "state"),
           "CTRL": str(ctrl), "AUTOUPDATE_SYNC": "0", "PATH": f"{fake}:{os.environ['PATH']}"}

    def result():
        return dict(l.split("=", 1) for l in (ctrl / "status").read_text().splitlines())["result"]

    def run():
        return subprocess.run(["bash", str(DEPLOY / "autoupdate.sh")], env=env, capture_output=True, text=True)

    def head():
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=app, capture_output=True, text=True).stdout.strip()

    r = run()                                                  # нечего обновлять
    assert r.returncode == 0 and r.stdout == "" and result() == "up-to-date"

    (work / "v.txt").write_text("2")
    _git(work, "commit", "-qam", "v2")
    _git(work, "push", "-q", "origin", "main")
    r = run()
    assert r.returncode == 0 and "Обновление" in r.stdout and (app / "v.txt").read_text() == "2"
    assert result() == "updated" and "Готово" in (ctrl / "update.log").read_text()
    good = head()

    (work / "BROKEN").write_text("x")                           # сломанное обновление
    _git(work, "add", ".")
    _git(work, "commit", "-qm", "broken")
    _git(work, "push", "-q", "origin", "main")
    r = run()
    assert r.returncode == 1 and "откат" in r.stdout and head() == good and not (app / "BROKEN").exists()
    assert result() == "rolled-back"
    r = run()                                                  # тот же сломанный коммит не повторяем
    assert r.returncode == 0 and r.stdout == "" and head() == good and result() == "bad"
    (ctrl / "update-now").write_text("1")                      # кнопка «Обновить сейчас» пробует снова
    r = run()
    assert r.returncode == 1 and "(по кнопке)" in r.stdout and head() == good
    assert not (ctrl / "update-now").exists()

    (work / "BROKEN").unlink()                                  # исправление приходит следующим коммитом
    _git(work, "commit", "-qam", "fix")
    _git(work, "push", "-q", "origin", "main")
    (ctrl / "autoupdate-off").write_text("1")                  # автообновление выключено в кабинете
    r = run()
    assert r.returncode == 0 and head() == good and result() == "available"
    (ctrl / "update-now").write_text("1")                      # …но кнопка работает
    r = run()
    assert r.returncode == 0 and head() != good and not (tmp_path / "state" / "bad-commit").exists()
    (ctrl / "update-now").write_text("1")
    r = run()
    assert "обновлений нет" in r.stdout and result() == "up-to-date"
    (ctrl / "autoupdate-off").unlink()

    _git(app, "checkout", "-q", "--detach", good)              # ручной откат родителем — не трогаем
    (work / "v.txt").write_text("3")
    _git(work, "commit", "-qam", "v3")
    _git(work, "push", "-q", "origin", "main")
    r = run()
    assert r.returncode == 0 and head() == good and result() == "not-main"
