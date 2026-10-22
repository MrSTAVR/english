# -*- coding: utf-8 -*-
"""Обновления сайта из кабинета администратора: записки серверу, статус и журнал."""
import os

import updates
import version


def _ctrl(name=""):
    return os.path.join(updates.control_dir(), name)


def test_dashboard_without_server_reports(parent):
    html = parent.get("/parent/updates").get_data(as_text=True)
    assert 'id="updates"' in html and "Сервер ещё не присылал отчётов" in html
    assert "Обновить сейчас" in html and "Автообновление: включено" in html
    assert version.info()["full"] in html


def test_update_now_and_toggle(parent):
    r = parent.post("/parent/updates", data={"action": "now"}, follow_redirects=True)
    assert "Запрос отправлен" in r.get_data(as_text=True) and os.path.exists(_ctrl("update-now"))
    assert "Ждём сервер" in parent.get("/parent/updates").get_data(as_text=True)
    parent.post("/parent/updates", data={"action": "auto_off"})
    assert os.path.exists(_ctrl("autoupdate-off")) and not updates.auto_enabled()
    assert "Автообновление: выключено" in parent.get("/parent/updates").get_data(as_text=True)
    parent.post("/parent/updates", data={"action": "auto_on"})
    assert updates.auto_enabled()
    assert parent.post("/parent/updates", data={"action": "rm -rf"}).status_code == 400


def test_status_and_log_shown(parent):
    os.makedirs(_ctrl(), exist_ok=True)
    with open(_ctrl("status"), "w", encoding="utf-8") as f:
        f.write("checked=22.10.2026 18:00:00\nlocal=abc\nremote=fffffff1234\nremote_subject=Новый год\nresult=available\n")
    with open(_ctrl("update.log"), "w", encoding="utf-8") as f:
        f.write("22.10.2026 17:00:00 первая строка\n22.10.2026 18:00:00 <b>вторая</b>\n")
    html = parent.get("/parent/updates").get_data(as_text=True)
    assert "22.10.2026 18:00:00" in html and "есть новая версия" in html and "Есть новая версия fffffff" in html
    assert html.index("вторая") < html.index("первая строка")           # свежие сверху
    assert "&lt;b&gt;вторая" in html                                     # журнал экранируется


def test_no_badge_when_up_to_date(parent):
    os.makedirs(_ctrl(), exist_ok=True)
    with open(_ctrl("status"), "w", encoding="utf-8") as f:
        f.write(f"checked=x\nremote={version.info()['commit']}0000\nresult=up-to-date\n")
    assert "Есть новая версия" not in parent.get("/parent/updates").get_data(as_text=True)


def test_student_cannot_touch_updates(make_student):
    c = make_student()
    c.post("/parent/updates", data={"action": "now"})
    c.post("/parent/updates", data={"action": "auto_off"})
    assert not os.path.exists(_ctrl("update-now")) and not os.path.exists(_ctrl("autoupdate-off"))


def test_state_endpoint_for_waiting_page(parent, anon):
    assert anon.get("/parent/updates/state").status_code == 403
    assert parent.get("/parent/updates/state").get_json()["pending"] is False
    parent.post("/parent/updates", data={"action": "now"})
    html = parent.get("/parent/updates").get_data(as_text=True)
    assert 'data-pending="1"' in html and "/parent/updates/state" in html
    assert parent.get("/parent/updates/state").get_json()["pending"] is True
    os.remove(_ctrl("update-now"))                       # сервер забрал просьбу
    j = parent.get("/parent/updates/state").get_json()
    assert j["pending"] is False and j["version"] == version.info()["full"]
