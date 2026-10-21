#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Шаг 4: исправление багов (после шага 3).

Запуск из корня проекта:   python apply_step4.py

Правки точечные (замена конкретных строк). Если хоть одна строка не найдена,
скрипт НИЧЕГО не меняет и объясняет, что именно не совпало.

  #1  доп. уроки больше не попадают в прогресс основного курса (stats.py)
  #2  при удалении ученика удаляются сад и украшения (routes/parent.py)
  #3  стабильное перемешивание слов «собери предложение» (template_filters.py)
  #4  пароль родителя из переменной окружения + сравнение за постоянное время
  #5  CSRF-защита всех POST-форм (новый csrf.py + скрытое поле в шаблонах)
  #6  понятные имена в подсчёте серии «идеальных тестов» (stats.py)
"""
import re
import sys
from pathlib import Path

CSRF_PY = '''# -*- coding: utf-8 -*-
"""CSRF-защита: токен в сессии + скрытое поле во всех POST-формах."""
import hmac
import secrets

from flask import abort, request, session

UNSAFE = ("POST", "PUT", "PATCH", "DELETE")


def csrf_token():
    """Токен текущей сессии (создаётся при первом обращении)."""
    if not session.get("csrf_token"):
        session["csrf_token"] = secrets.token_hex(16)
    return session["csrf_token"]


def init_csrf(app):
    """Подключает проверку токена ко всем небезопасным запросам."""
    app.config.setdefault("CSRF_ENABLED", True)
    app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def _check_csrf():
        if not app.config.get("CSRF_ENABLED", True):
            return
        if request.method not in UNSAFE:
            return
        expected = session.get("csrf_token")
        sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token", "")
        if not expected or not hmac.compare_digest(str(sent), str(expected)):
            abort(400, description="Форма устарела или подделана. Обнови страницу и попробуй ещё раз.")
'''

FORM_RE = re.compile(r"""(<form\b[^>]*\bmethod\s*=\s*["']post["'][^>]*>)""", re.I)
HIDDEN = '<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">'


class Plan:
    def __init__(self):
        self.files = {}      # Path -> новый текст
        self.errors = []
        self.notes = []

    def read(self, path):
        p = Path(path)
        if p in self.files:
            return self.files[p]
        if not p.exists():
            self.errors.append(f"{path}: файл не найден")
            return None
        return p.read_text(encoding="utf-8")

    def replace(self, path, old, new, what):
        t = self.read(path)
        if t is None:
            return
        n = t.count(old)
        if n != 1:
            self.errors.append(f"{path}: [{what}] ожидалась 1 вставка, найдено {n}: {old.strip()[:70]!r}")
            return
        self.files[Path(path)] = t.replace(old, new)
        self.notes.append(f"{path}: {what}")

    def regex(self, path, pattern, new, what, flags=re.M):
        t = self.read(path)
        if t is None:
            return
        t2, n = re.subn(pattern, lambda m: new, t, count=1, flags=flags)
        if n != 1:
            self.errors.append(f"{path}: [{what}] шаблон не найден: {pattern!r}")
            return
        self.files[Path(path)] = t2
        self.notes.append(f"{path}: {what}")

    def add_import(self, path, line):
        t = self.read(path)
        if t is None or line in t:
            return
        ls = t.split("\n")
        idx = [i for i, l in enumerate(ls) if re.match(r"(import|from)\s", l)]
        if not idx:
            self.errors.append(f"{path}: не найден блок импортов для {line!r}")
            return
        ls.insert(idx[0], line)
        self.files[Path(path)] = "\n".join(ls)


def main():
    if Path("csrf.py").exists():
        print("ОШИБКА: csrf.py уже существует — шаг 4 уже применён.")
        sys.exit(1)
    for need in ("stats.py", "routes/parent.py", "routes/auth.py", "app.py"):
        if not Path(need).exists():
            print(f"ОШИБКА: не найден {need} — сначала выполните шаги 2 и 3.")
            sys.exit(1)

    p = Plan()

    # --- #1 + #6: stats.py ---
    p.replace("stats.py",
              "    completed_ids = sorted(best_by_lesson.keys())\n",
              "    completed_ids = sorted(best_by_lesson.keys())\n"
              "    main_ids = [i for i in completed_ids if not LESSONS_BY_ID[i].get(\"is_extra\")]\n",
              "#1 отделяем основные уроки от дополнительных")
    p.replace("stats.py",
              '        "lessons_completed": len(completed_ids),',
              '        "lessons_completed": len(main_ids),          # только основной курс\n'
              '        "extras_completed": len(completed_ids) - len(main_ids),',
              "#1 lessons_completed считает только основной курс")
    p.replace("stats.py",
              "    best_clean_run = 0\n    current_clean_run = 0\n",
              "    clean_run = 0        # текущая серия идеальных тестов подряд\n"
              "    best_clean_run = 0   # лучшая серия\n",
              "#6 понятные имена серии")
    p.replace("stats.py",
              "                best_clean_run += 1\n"
              "                current_clean_run = max(current_clean_run, best_clean_run)\n"
              "            else:\n"
              "                best_clean_run = 0\n"
              "        else:\n"
              "            best_clean_run = 0\n",
              "                clean_run += 1\n"
              "                best_clean_run = max(best_clean_run, clean_run)\n"
              "            else:\n"
              "                clean_run = 0\n"
              "        else:\n"
              "            clean_run = 0\n",
              "#6 подсчёт серии")
    p.replace("stats.py",
              '        "best_clean_run": current_clean_run,',
              '        "best_clean_run": best_clean_run,',
              "#6 возвращаем лучшую серию")

    # --- #1: помощник «ты прошла все уроки» ---
    p.replace("routes/student.py",
              'mascot["allDone"] = len(stats["completed_ids"]) == len(LESSONS)',
              'mascot["allDone"] = stats["lessons_completed"] >= len(LESSONS)',
              "#1 allDone не зависит от доп. уроков")

    # --- #2: удаление ученика ---
    p.replace("routes/parent.py",
              '    db.execute("DELETE FROM achievements WHERE student_id=?", (sid,))\n',
              '    db.execute("DELETE FROM achievements WHERE student_id=?", (sid,))\n'
              '    db.execute("DELETE FROM decorations WHERE student_id=?", (sid,))\n'
              '    db.execute("DELETE FROM garden WHERE student_id=?", (sid,))\n',
              "#2 удаляем сад и украшения вместе с учеником")

    # --- #3: перемешивание ---
    p.replace("template_filters.py",
              "random.Random(hash(tuple(w)))",
              'random.Random("|".join(w))',
              "#3 стабильный seed вместо hash()")

    # --- #4: пароль родителя ---
    p.regex("config.py", r"^PARENT_PASSWORD = .*$",
            'PARENT_PASSWORD = os.environ.get("ENGLISH_PARENT_PASSWORD", "1234")  '
            "# пароль родителя; смените через переменную окружения",
            "#4 пароль родителя из окружения")
    p.add_import("security.py", "from config import PARENT_PASSWORD")
    sec = p.read("security.py")
    if sec is not None and "check_parent_password" not in sec:
        p.files[Path("security.py")] = (p.files.get(Path("security.py"), sec).rstrip() + '''


def check_parent_password(password):
    """Сравнение пароля родителя за постоянное время."""
    return hmac.compare_digest(str(password).encode("utf-8"),
                               PARENT_PASSWORD.encode("utf-8"))
''')
        p.notes.append("security.py: #4 check_parent_password()")
    p.replace("routes/auth.py",
              "if pwd != PARENT_PASSWORD:",
              "if not check_parent_password(pwd):",
              "#4 сравнение пароля за постоянное время")
    p.add_import("routes/auth.py", "from security import check_parent_password")
    auth = p.files.get(Path("routes/auth.py"))
    if auth is not None:
        p.files[Path("routes/auth.py")] = re.sub(r"^from config import PARENT_PASSWORD\n", "", auth, flags=re.M)

    # --- #5: CSRF ---
    p.add_import("app.py", "from csrf import init_csrf")
    p.replace("app.py", "register_blueprints(app)\n",
              "init_csrf(app)\nregister_blueprints(app)\n", "#5 подключаем CSRF-защиту")
    forms = 0
    tdir = Path("templates")
    if tdir.exists():
        for t in sorted(tdir.glob("*.html")):
            text = t.read_text(encoding="utf-8")
            if "csrf_token" in text:
                continue
            new, n = FORM_RE.subn(lambda m: m.group(1) + "\n  " + HIDDEN, text)
            if n:
                p.files[t] = new
                forms += n
                p.notes.append(f"{t}: #5 CSRF-поле в {n} форм(ах)")
    else:
        p.errors.append("папка templates не найдена")

    if p.errors:
        print("НИЧЕГО НЕ ИЗМЕНЕНО. Не совпали правки:\n")
        for e in p.errors:
            print("  -", e)
        print("\nПришлите этот вывод — я подгоню скрипт под ваш код.")
        sys.exit(1)

    for path, text in p.files.items():
        ast_ok = True
        if path.suffix == ".py":
            import ast
            try:
                ast.parse(text)
            except SyntaxError as e:
                ast_ok = False
                print(f"ОШИБКА: синтаксис {path}: {e}")
        if not ast_ok:
            sys.exit(1)
    Path("csrf.py").write_text(CSRF_PY, encoding="utf-8")
    for path, text in p.files.items():
        path.write_text(text, encoding="utf-8")
    print("Готово:\n")
    for n in p.notes:
        print("  +", n)
    print(f"  + csrf.py создан; CSRF-полей в формах: {forms}")
    print("\nДальше: замените tests/ из step4.zip, снимите xfail (уже снят в новых тестах) и запустите pytest.")


if __name__ == "__main__":
    main()
