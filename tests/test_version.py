# -*- coding: utf-8 -*-
"""Версия приложения: из git, видна в подвале и на /version."""
import version


def test_version_from_git():
    version.info.cache_clear()
    v = version.info()
    assert v["version"].startswith("v1.") and v["version"][3:].isdigit()
    assert len(v["commit"]) >= 7 and v["full"] == f'{v["version"]} · {v["commit"]} · {v["date"]}'


def test_version_without_git(monkeypatch):
    def broken(*args):
        raise OSError("no git")
    monkeypatch.setattr(version, "_git", broken)
    version.info.cache_clear()
    try:
        assert version.info()["full"] == "dev"
    finally:
        version.info.cache_clear()


def test_footer_and_endpoint(anon):
    version.info.cache_clear()
    assert version.info()["full"] in anon.get("/").get_data(as_text=True)
    assert anon.get("/version").get_json()["version"] == version.info()["version"]
