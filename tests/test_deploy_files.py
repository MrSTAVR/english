# -*- coding: utf-8 -*-
"""Файлы развёртывания: скрипты синтаксически верны и не испорчены Windows-переводами строк."""
import shutil
import subprocess
from pathlib import Path

import pytest

DEPLOY = Path(__file__).resolve().parent.parent / "deploy"
SCRIPTS = ["setup.sh", "update.sh", "restore.sh", "check.sh"]


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
