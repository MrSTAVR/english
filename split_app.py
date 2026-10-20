#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Шаг 2 рефакторинга: механически выносит логику из app.py в модули.

Запуск (из корня проекта, где лежит app.py):
    python split_app.py

Код переносится ДОСЛОВНО (через ast), меняются только импорты.
Маршруты и Flask-обвязка остаются в app.py (их разнесём на шаге 3).
Исходный файл сохраняется как app.py.bak.
"""
import ast
import builtins
import copy
import re
import shutil
import sys
from collections import OrderedDict, defaultdict
from pathlib import Path

SRC = Path("app.py")

# модуль -> (описание, [имена верхнего уровня, которые в него переезжают])
MODULES = OrderedDict([
    ("config", ("Конфигурация: пути и константы приложения.",
                ["BASE_DIR", "DB_PATH", "PASS_MARK", "PARENT_PASSWORD"])),
    ("database", ("SQLite: схема, подключение, миграции.",
                  ["SCHEMA", "get_db", "init_db"])),
    ("security", ("Хеширование и проверка паролей (PBKDF2).",
                  ["PBKDF2_ROUNDS", "hash_password", "verify_password"])),
    ("curriculum", ("Каталог уроков: списки, проверка целостности, разблокировка.",
                    ["ALL_LESSONS", "MAIN_COUNT", "LESSONS_BY_ID",
                     "validate_lessons", "unlocked_lesson_ids"])),
    ("grading", ("Проверка ответов: разбор формы и оценивание всех типов заданий.",
                 ["norm_answer", "parse_pairs", "parse_sort",
                  "match_columns", "grade_question"])),
    ("stats", ("Статистика успеваемости по попыткам.",
               ["compute_stats"])),
    ("achievements", ("Каталог ачивок и их выдача.",
                      ["ACHIEVEMENTS", "update_achievements"])),
    ("garden", ("Сад: серия дней, деревья, монетки, украшения.",
                ["MAX_SLOTS", "STREAK_CAP", "COIN_PASS", "COIN_PERFECT",
                 "TREES_START", "TREES_MAX", "TREES_EVERY", "tree_count_for",
                 "DECORATIONS", "DECOS_BY_KEY", "CATEGORY_NAMES", "TREE_GLYPHS",
                 "_STAGE_GLYPHS", "_stage_glyph", "_stage_size", "TREE_STAGES",
                 "_EMOJI_BY_GLYPH", "_GLYPH_VARIANTS", "variant_glyph",
                 "get_garden", "tree_stage", "cap_streak",
                 "compute_streak_from_history", "refresh_garden",
                 "award_coins", "touch_streak", "garden_view"])),
    ("template_filters", ("Фильтры Jinja и перемешивание заданий для шаблонов.",
                          ["human_time", "shuffle_words", "_stable_shuffle",
                           "shuffle_match", "shuffle_sort", "match_cols",
                           "match_answer_json", "match_expected_json",
                           "mistakes_count", "tree_glyph"])),
    ("mascot", ("Настройки анимированного помощника для base.html.",
                ["MASCOT_NAME", "MASCOT_ENABLED", "build_mascot_ctx"])),
])

NAME2MOD = {n: m for m, (_, names) in MODULES.items() for n in names}
BUILTINS = set(dir(builtins)) | {"__file__", "__name__", "__doc__"}
SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda,
          ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)


def fail(msg):
    print("ОШИБКА:", msg)
    sys.exit(1)


# ---------- анализ имён ----------
def defined_names(n):
    if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
        return [n.name]
    if isinstance(n, ast.Assign):
        return [t.id for t in n.targets if isinstance(t, ast.Name)]
    if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
        return [n.target.id]
    return []


def scope_binds(node):
    b = set()
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        a = node.args
        for x in a.posonlyargs + a.args + a.kwonlyargs:
            b.add(x.arg)
        if a.vararg:
            b.add(a.vararg.arg)
        if a.kwarg:
            b.add(a.kwarg.arg)
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name) and isinstance(sub.ctx, (ast.Store, ast.Del)):
            b.add(sub.id)
        elif isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
            b.add(sub.name)
        elif isinstance(sub, (ast.Import, ast.ImportFrom)):
            for al in sub.names:
                b.add((al.asname or al.name).split(".")[0])
        elif isinstance(sub, ast.ExceptHandler) and sub.name:
            b.add(sub.name)
        elif isinstance(sub, ast.arg):
            b.add(sub.arg)
    return b


def free(node, bound):
    """Имена, читаемые в node и не связанные локально (т.е. глобальные)."""
    if isinstance(node, SCOPES):
        bound = bound | scope_binds(node)
    out = set()
    for ch in ast.iter_child_nodes(node):
        if isinstance(ch, ast.Name):
            if isinstance(ch.ctx, ast.Load) and ch.id not in bound:
                out.add(ch.id)
        else:
            out |= free(ch, bound)
    return out


def app_decorators(n):
    return [d for d in getattr(n, "decorator_list", [])
            if any(isinstance(x, ast.Name) and x.id == "app" for x in ast.walk(d))]


def main():
    if not SRC.exists():
        fail("app.py не найден — запустите скрипт из корня проекта.")
    if Path("config.py").exists() or Path("database.py").exists():
        fail("config.py / database.py уже существуют — похоже, разбиение уже выполнено.")

    src = SRC.read_text(encoding="utf-8")
    lines = src.splitlines()
    tree = ast.parse(src)
    body = tree.body

    # --- импорты оригинала: связанное имя -> (module, name, asname) ---
    imports = {}
    last_import_end = 0
    for n in body:
        if isinstance(n, ast.Import):
            for al in n.names:
                imports[(al.asname or al.name).split(".")[0]] = ("import", al.name, al.asname)
            last_import_end = n.end_lineno
        elif isinstance(n, ast.ImportFrom):
            mod = "." * n.level + (n.module or "")
            for al in n.names:
                imports[al.asname or al.name] = ("from", mod, al.name, al.asname)
            last_import_end = n.end_lineno

    # --- диапазоны строк узлов (с декораторами и комментариями над ними) ---
    prev_end = 0
    spans = []
    for n in body:
        s = n.lineno
        decs = getattr(n, "decorator_list", [])
        if decs:
            s = min(s, min(d.lineno for d in decs))
        while s - 1 > prev_end and lines[s - 2].lstrip().startswith("#"):
            s -= 1
        spans.append((s, n.end_lineno))
        prev_end = n.end_lineno

    # --- кто куда переезжает ---
    assign, last_mod = {}, None
    for i, n in enumerate(body):
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            last_mod = None
            continue
        mod = None
        for nm in defined_names(n):
            if nm in NAME2MOD:
                mod = NAME2MOD[nm]
        if isinstance(n, ast.For) and last_mod:
            mod = last_mod                      # циклы-«сборщики» едут за соседом
        assign[i] = mod
        last_mod = mod

    # дубликаты определений (например, match_columns объявлена дважды): живёт последнее
    last_def = {}
    for i, n in enumerate(body):
        if assign.get(i) and isinstance(n, ast.FunctionDef):
            last_def[n.name] = i
    dropped = [i for i, n in enumerate(body)
               if assign.get(i) and isinstance(n, ast.FunctionDef) and last_def[n.name] != i]

    found = {nm for i, n in enumerate(body) if assign.get(i) for nm in defined_names(n)}
    for nm in NAME2MOD:
        if nm not in found:
            print(f"  ! предупреждение: имя {nm} не найдено в app.py")

    # --- сбор модулей ---
    mod_nodes = defaultdict(list)
    registrations = {}      # индекс узла -> строка регистрации фильтра в app.py
    for i, n in enumerate(body):
        m = assign.get(i)
        if m and i not in dropped:
            mod_nodes[m].append(i)

    exported = defaultdict(list)            # модуль -> публичные имена
    defined_in = {}                         # имя -> модуль
    for m, idxs in mod_nodes.items():
        for i in idxs:
            for nm in defined_names(body[i]):
                defined_in[nm] = m
                exported[m].append(nm)

    def node_text(i):
        n = body[i]
        s, e = spans[i]
        ad = app_decorators(n)
        if ad:
            first_dec = min(d.lineno for d in n.decorator_list)
            registrations[i] = f"{ast.get_source_segment(src, ad[0])}({n.name})"
            return "\n".join(lines[s - 1:first_dec - 1] + lines[n.lineno - 1:e])
        return "\n".join(lines[s - 1:e])

    def stripped(n):
        if app_decorators(n):
            n = copy.copy(n)
            n.decorator_list = []
        return n

    remaining = [i for i in range(len(body))
                 if not (assign.get(i) and i not in dropped) and i not in dropped
                 and not isinstance(body[i], (ast.Import, ast.ImportFrom))]
    remaining_defined = {nm for i in remaining for nm in defined_names(body[i])}

    warnings = []
    out_files = {}
    for m, (doc, _) in MODULES.items():
        idxs = mod_nodes.get(m)
        if not idxs:
            continue
        local, needed = set(), set()
        for i in idxs:
            n = body[i]
            local.update(defined_names(n))
            if not isinstance(n, ast.FunctionDef):
                local.update(s.id for s in ast.walk(n)
                             if isinstance(s, ast.Name) and isinstance(s.ctx, ast.Store))
            needed |= free(stripped(n), set())
        needed -= local
        needed -= BUILTINS

        std_imports, from_imports, local_imports = set(), defaultdict(set), defaultdict(set)
        for nm in sorted(needed):
            if nm in defined_in and defined_in[nm] != m:
                local_imports[defined_in[nm]].add(nm)
            elif nm in imports:
                info = imports[nm]
                if info[0] == "import":
                    std_imports.add(f"import {info[1]}" + (f" as {info[2]}" if info[2] else ""))
                else:
                    from_imports[info[1]].add(info[2] + (f" as {info[3]}" if info[3] else ""))
            else:
                warnings.append(f"{m}.py использует имя '{nm}', которое осталось в app.py или неизвестно")

        parts = ["# -*- coding: utf-8 -*-", f'"""{doc}"""', ""]
        block = sorted(std_imports)
        block += [f"from {mod} import {', '.join(sorted(names))}"
                  for mod, names in sorted(from_imports.items())]
        if block:
            parts += block + [""]
        block = [f"from {mod} import {', '.join(sorted(names))}"
                 for mod, names in sorted(local_imports.items())]
        if block:
            parts += block + [""]
        parts.append("")
        chunks = []
        for k, i in enumerate(idxs):
            if k:
                prev = idxs[k - 1]
                sep = ("\n" * (spans[i][0] - spans[prev][1])) if i == prev + 1 else "\n\n\n"
                chunks.append(sep)
            chunks.append(node_text(i))
        parts.append("".join(chunks))
        out_files[m] = "\n".join(parts).rstrip() + "\n"

    # --- новый app.py ---
    remove = set()
    inserts = {}
    for i in list(dropped) + [i for idxs in mod_nodes.values() for i in idxs]:
        s, e = spans[i]
        remove.update(range(s, e + 1))
        if i in registrations:
            inserts[s] = registrations[i]

    rem_free = set()
    for i in remaining:
        rem_free |= free(body[i], set())

    imp_block = ["", "# --- Модули, вынесенные из app.py (шаг 2 рефакторинга) ---"]
    for m in MODULES:
        names = [nm for nm in exported.get(m, []) if not nm.startswith("_") or nm in rem_free]
        if not names:
            continue
        imp_block.append(f"from {m} import (  # noqa: F401")
        imp_block += [f"    {nm}," for nm in names]
        imp_block.append(")")

    new_lines = []
    for ln, text in enumerate(lines, 1):
        if ln in inserts:
            new_lines.append(inserts[ln])
        if ln not in remove:
            new_lines.append(text)
        if ln == last_import_end:
            new_lines.extend(imp_block)
    new_src = re.sub(r"\n{4,}", "\n\n\n", "\n".join(new_lines)).rstrip() + "\n"

    # --- проверка синтаксиса ДО записи ---
    for name, text in list(out_files.items()) + [("app", new_src)]:
        try:
            ast.parse(text)
        except SyntaxError as e:
            fail(f"в сгенерированном {name}.py синтаксическая ошибка: {e}")

    shutil.copy(SRC, "app.py.bak")
    for m, text in out_files.items():
        Path(f"{m}.py").write_text(text, encoding="utf-8")
    SRC.write_text(new_src, encoding="utf-8")

    # --- отчёт ---
    print("Готово. Резервная копия: app.py.bak\n")
    for m, text in out_files.items():
        print(f"  {m}.py: {len(text.splitlines()):4d} строк  ({', '.join(exported[m][:4])}…)")
    print(f"  app.py: {len(lines)} -> {len(new_src.splitlines())} строк")
    if dropped:
        print("\nУдалены дубликаты определений:",
              ", ".join(f"{body[i].name} (стр. {spans[i][0]})" for i in dropped))
    if warnings:
        print("\nПРЕДУПРЕЖДЕНИЯ:")
        for w in warnings:
            print("  -", w)
    print("\nДальше: Ctrl+Alt+O в app.py (Optimize imports) и запустите pytest.")


if __name__ == "__main__":
    main()
