#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Шаг 6: новый сад. Запуск из корня проекта ПОСЛЕ копирования файлов из архива:
    garden.py, garden_scene.py, templates/garden.html, garden.css, tests/

Скрипт вносит точечные правки в остальные файлы. Если хоть одна не находится,
ничего не меняется, и он объясняет, что именно не совпало.
"""
import ast
import re
import sys
from pathlib import Path

MARK = "/* ============ 🌳 Новый сад"


class Plan:
    def __init__(self):
        self.files, self.errors, self.notes, self.warn = {}, [], [], []

    def read(self, path):
        p = Path(path)
        if p in self.files:
            return self.files[p]
        if not p.exists():
            self.errors.append(f"{path}: файл не найден")
            return None
        return p.read_text(encoding="utf-8")

    def put(self, path, text, note):
        self.files[Path(path)] = text
        self.notes.append(f"{path}: {note}")

    def replace(self, path, old, new, note, count=1):
        t = self.read(path)
        if t is None:
            return
        n = t.count(old)
        if n != count:
            self.errors.append(f"{path}: [{note}] ожидалось вхождений: {count}, найдено: {n} -> {old.strip()[:60]!r}")
            return
        self.put(path, t.replace(old, new), note)

    def sub(self, path, pattern, new, note, flags=re.M):
        t = self.read(path)
        if t is None:
            return
        t2, n = re.subn(pattern, lambda m: new, t, count=1, flags=flags)
        if n != 1:
            self.errors.append(f"{path}: [{note}] шаблон не найден: {pattern!r}")
            return
        self.put(path, t2, note)

    def add_import(self, path, line):
        t = self.read(path)
        if t is None or line in t:
            return
        ls = t.split("\n")
        idx = [i for i, l in enumerate(ls) if re.match(r"(import|from)\s", l)]
        if not idx:
            self.errors.append(f"{path}: нет блока импортов для {line!r}")
            return
        ls.insert(idx[0], line)
        self.put(path, "\n".join(ls), f"импорт {line}")


def main():
    for need, hint in (("garden_scene.py", "скопируйте garden_scene.py из архива"),
                       ("garden.css", "скопируйте garden.css из архива")):
        if not Path(need).exists():
            print(f"ОШИБКА: нет {need} — {hint}.")
            sys.exit(1)
    g = Path("garden.py").read_text(encoding="utf-8") if Path("garden.py").exists() else ""
    if "garden_scene" not in g:
        print("ОШИБКА: garden.py — старая версия. Скопируйте новый garden.py из архива поверх.")
        sys.exit(1)
    gt = Path("templates/garden.html").read_text(encoding="utf-8") if Path("templates/garden.html").exists() else ""
    if "garden-stage" not in gt:
        print("ОШИБКА: templates/garden.html — старая версия. Скопируйте новый из архива поверх.")
        sys.exit(1)
    css = Path("static/style.css").read_text(encoding="utf-8") if Path("static/style.css").exists() else None
    if css is not None and MARK in css:
        print("ОШИБКА: стили нового сада уже добавлены — шаг уже применён.")
        sys.exit(1)

    p = Plan()

    # --- фильтры шаблонов: старый tree_glyph -> tree_mini ---
    tf = p.read("template_filters.py")
    if tf is not None:
        i = tf.find("def tree_glyph(")
        if i < 0:
            p.errors.append("template_filters.py: не найдена функция tree_glyph")
        else:
            tail = tf[i:]
            if re.search(r"^\S", tail.split("\n", 1)[1], re.M):
                p.errors.append("template_filters.py: после tree_glyph есть другой код — править вручную")
            else:
                new = tf[:i] + ('def tree_mini(streak_days):\n'
                                '    """Иконка-деревце для главной ученика (по дню серии)."""\n'
                                '    return tree_mini_svg(streak_days)\n')
                new = re.sub(r"^from garden import TREE_GLYPHS\n", "", new, flags=re.M)
                p.put("template_filters.py", new, "tree_glyph заменён на tree_mini")
                p.add_import("template_filters.py", "from garden_scene import tree_mini_svg")

    # --- app.py: регистрация фильтра (импорт может быть в одну строку или в скобках в несколько:
    #     после Ctrl+Alt+O PyCharm переформатирует длинные импорты) ---
    a = p.read("app.py")
    if a is not None:
        try:
            body = ast.parse(a).body
        except SyntaxError as e:
            body = []
            p.errors.append(f"app.py: синтаксическая ошибка: {e}")
        node = next((n for n in body if isinstance(n, ast.ImportFrom) and n.module == "template_filters"
                     and any(al.name == "tree_glyph" for al in n.names)), None)
        a2, n_reg = re.subn(r"""app\.template_filter\(\s*(['"])tree_glyph\1\s*\)\(\s*tree_glyph\s*\)""",
                            'app.template_filter("tree_mini")(tree_mini)', a)
        if node is None:
            p.errors.append("app.py: не найден импорт tree_glyph из template_filters")
        elif n_reg != 1:
            p.errors.append('app.py: не найдена строка app.template_filter("tree_glyph")(tree_glyph)')
        else:
            ls = a2.split("\n")
            seg = re.sub(r"\btree_glyph\b", "tree_mini", "\n".join(ls[node.lineno - 1:node.end_lineno]))
            p.put("app.py", "\n".join(ls[:node.lineno - 1] + [seg] + ls[node.end_lineno:]),
                  "фильтр tree_mini вместо tree_glyph")

    # --- главная ученика: иконка-деревце ---
    p.replace("templates/student_home.html", "{{ tree_stage.glyph | tree_glyph }}",
              "{{ garden.streak_days | tree_mini }}", "иконка сада на главной")

    # --- стили ---
    if css is None:
        p.errors.append("static/style.css: файл не найден")
    else:
        p.put("static/style.css", css.rstrip("\n") + "\n" + Path("garden.css").read_text(encoding="utf-8"),
              "добавлены стили нового сада")
    b = p.read("templates/base.html")
    if b is not None:
        b2, n = re.subn(r"(style\.css'\) \}\}\?v=)(\d+)", lambda m: m.group(1) + str(int(m.group(2)) + 1), b)
        if n == 1:
            p.put("templates/base.html", b2, "версия стилей +1 (сброс кэша браузера)")
        else:
            p.warn.append("base.html: не нашёл ?v=N у style.css — сбросьте кэш браузера вручную (Ctrl+F5)")

    # --- миграция: радуга выведена из магазина (теперь это находка 21-го дня) ---
    p.replace("database.py", "def init_db():\n",
              'RETIRED_DECORATIONS = {"rainbow": 30}   # ключ -> цена: выведены из магазина, монеты возвращаются\n\n\n'
              "def init_db():\n", "список выведенных украшений")
    p.replace("database.py", "    conn.commit()\n    conn.close()\n",
              "    for key, cost in RETIRED_DECORATIONS.items():\n"
              "        conn.execute(\n"
              '            "UPDATE garden SET coins = coins + ? * (SELECT COUNT(*) FROM decorations d "\n'
              '            "WHERE d.student_id = garden.student_id AND d.deco_key = ?)", (cost, key))\n'
              '        conn.execute("DELETE FROM decorations WHERE deco_key = ?", (key,))\n'
              "    conn.commit()\n    conn.close()\n", "возврат монет за выведенные украшения")

    # --- README (необязательно) ---
    r = Path("README.md")
    if r.exists():
        t = r.read_text(encoding="utf-8")
        t2, n = re.subn(r"- \*\*🌳 Сад\*\*:.*?монеты остаются\.",
                        "- **🌳 Сад**: каждый день серии (до 30 дней) приносит находку — травку, бабочку, зайчика, пруд, радугу, домик…\n"
                        "  Дерево растёт каждый день, а на 5/10/15/22/28-й день вырастают новые. Находки собираются в альбом.\n"
                        "  За сданный тест — +5 монет, за 100 % — ещё +5. На монеты покупаются украшения (15 штук: гирлянды, снег,\n"
                        "  самолётик, ночной фон…; до 5 одновременно; при снятии возвращается половина цены).\n"
                        "  Пропущенный день сбрасывает серию: сад «сдувается» до жёлудя, украшения пропадают, монеты остаются.",
                        t, count=1, flags=re.S)
        t2 = t2.replace("garden.py           сад: серия, деревья, монеты, украшения\n",
                        "garden.py           сад: серия, монеты, магазин, данные для страницы\n"
                        "garden_scene.py     SVG-сцена сада: дерево, 30 находок, украшения\n")
        if t2 != t:
            p.put("README.md", t2, "описание сада обновлено")
        else:
            p.warn.append("README.md: описание сада не найдено — обновите вручную")

    if p.errors:
        print("НИЧЕГО НЕ ИЗМЕНЕНО. Не совпали правки:\n")
        for e in p.errors:
            print("  -", e)
        print("\nПришлите этот вывод — я подгоню скрипт под ваш код.")
        sys.exit(1)
    for path, text in p.files.items():
        if path.suffix == ".py":
            try:
                ast.parse(text)
            except SyntaxError as e:
                print(f"ОШИБКА: синтаксис {path}: {e}")
                sys.exit(1)
    for path, text in p.files.items():
        path.write_text(text, encoding="utf-8")
    print("Готово:\n")
    for n in p.notes:
        print("  +", n)
    for w in p.warn:
        print("  !", w)
    print("\nДальше: pytest. Потом можно удалить apply_garden.py и garden.css.")


if __name__ == "__main__":
    main()
