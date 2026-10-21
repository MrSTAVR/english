#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Шаг 3 рефакторинга: разносит маршруты app.py по Blueprints (пакет routes/).

Запуск (из корня проекта, ПОСЛЕ шага 2):
    python split_routes.py

Что делает:
  * маршруты -> routes/auth.py, student.py, garden.py, parent.py;
    общие помощники (require_role, get_student_or_none) -> routes/common.py;
  * @app.route -> @bp.route, endpoint-ы получают префикс blueprint-а
    (student_home -> student.student_home);
  * переписывает url_for(...) в шаблонах и в коде, а также проверки
    request.endpoint в mascot.py;
  * пересобирает app.py: только создание приложения + регистрация blueprint-ов,
    «мостик» импортов из шага 2 убирается.
Код функций переносится дословно (через ast).
"""
import ast
import builtins
import copy
import re
import sys
from collections import OrderedDict, defaultdict
from pathlib import Path

SRC = Path("app.py")
TEMPLATES = Path("templates")

# модуль -> (описание, имя blueprint или None, [имена верхнего уровня])
ROUTE_MODULES = OrderedDict([
    ("routes/common", ("Общие помощники для маршрутов: проверка роли и текущий ученик.", None,
                       ["require_role", "get_student_or_none"])),
    ("routes/auth", ("Вход, выход и главная страница.", "auth",
                     ["index", "login_student", "login_parent", "logout"])),
    ("routes/student", ("Режим ученика: список уроков, урок, сдача теста.", "student",
                        ["student_home", "lesson_page", "submit_test"])),
    ("routes/garden", ("Сад ученика: просмотр, покупка и снятие украшений.", "garden",
                       ["garden_page", "garden_buy", "garden_remove"])),
    ("routes/parent", ("Кабинет родителя: аккаунты учеников, статистика, API ошибок.", "parent",
                       ["STUDENT_EMOJIS", "valid_username", "add_student", "delete_student",
                        "reset_student_password", "parent_update_garden",
                        "parent_dashboard", "api_mistakes"])),
])
NAME2MOD = {n: m for m, (_, _, names) in ROUTE_MODULES.items() for n in names}
BUILTINS = set(dir(builtins)) | {"__file__", "__name__", "__doc__"}
SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda,
          ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)


def fail(msg):
    print("ОШИБКА:", msg)
    sys.exit(1)


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


def stripped(n):
    if app_decorators(n):
        n = copy.copy(n)
        n.decorator_list = []
    return n


def route_endpoint_ok(n):
    """True, если у функции @app.route(...) без явного endpoint=."""
    for d in app_decorators(n):
        if isinstance(d, ast.Call) and any(k.arg == "endpoint" for k in d.keywords):
            return False
    return True


def gen_imports(needed, imports, defined_in, own_module, extra_from=None):
    """Строки импортов для набора имён."""
    std, frm, loc = set(), defaultdict(set), defaultdict(set)
    unknown = []
    for nm in sorted(needed):
        if nm in defined_in and defined_in[nm] != own_module:
            loc[defined_in[nm].replace("/", ".")].add(nm)
        elif nm in imports:
            info = imports[nm]
            if info[0] == "import":
                std.add(f"import {info[1]}" + (f" as {info[2]}" if info[2] else ""))
            else:
                frm[info[1]].add(info[2] + (f" as {info[3]}" if info[3] else ""))
        else:
            unknown.append(nm)
    for mod, names in (extra_from or {}).items():
        frm[mod] |= set(names)
    block = sorted(std)
    block += [f"from {m} import {', '.join(sorted(n))}" for m, n in sorted(frm.items())]
    blk2 = [f"from {m} import {', '.join(sorted(n))}" for m, n in sorted(loc.items())]
    return block, blk2, unknown


def main():
    if not SRC.exists():
        fail("app.py не найден — запустите скрипт из корня проекта.")
    if Path("routes").exists():
        fail("папка routes/ уже существует — похоже, разбиение уже выполнено.")
    if not Path("config.py").exists() or not Path("database.py").exists():
        fail("не найдены config.py / database.py — сначала выполните шаг 2 (split_app.py).")

    src = SRC.read_text(encoding="utf-8")
    lines = src.splitlines()
    body = ast.parse(src).body

    imports, import_idx = {}, set()
    first_import = None
    for i, n in enumerate(body):
        if isinstance(n, ast.Import):
            import_idx.add(i)
            for al in n.names:
                imports[(al.asname or al.name).split(".")[0]] = ("import", al.name, al.asname)
        elif isinstance(n, ast.ImportFrom):
            import_idx.add(i)
            mod = "." * n.level + (n.module or "")
            for al in n.names:
                imports[al.asname or al.name] = ("from", mod, al.name, al.asname)
        else:
            continue
        if first_import is None:
            first_import = n.lineno

    prev_end, spans = 0, []
    for n in body:
        s = n.lineno
        decs = getattr(n, "decorator_list", [])
        if decs:
            s = min(s, min(d.lineno for d in decs))
        while s - 1 > prev_end and lines[s - 2].lstrip().startswith("#"):
            s -= 1
        spans.append((s, n.end_lineno))
        prev_end = n.end_lineno

    # --- кто куда ---
    assign = {}
    for i, n in enumerate(body):
        if i in import_idx:
            continue
        for nm in defined_names(n):
            if nm in NAME2MOD:
                assign[i] = NAME2MOD[nm]
    found = {nm for i in assign for nm in defined_names(body[i])}
    for nm in NAME2MOD:
        if nm not in found:
            print(f"  ! предупреждение: {nm} не найдено в app.py")

    # --- карта эндпоинтов: старое имя -> blueprint.имя ---
    endpoint_map = {}
    for i, m in assign.items():
        n = body[i]
        bp = ROUTE_MODULES[m][1]
        if bp and isinstance(n, ast.FunctionDef) and app_decorators(n):
            if not route_endpoint_ok(n):
                fail(f"у {n.name} задан endpoint= вручную — скрипт такое не поддерживает.")
            endpoint_map[n.name] = f"{bp}.{n.name}"

    url_re = re.compile(r"""url_for\(\s*(['"])(\w+)\1""")

    def fix_url_for(text):
        return url_re.sub(
            lambda mo: f"url_for({mo.group(1)}{endpoint_map.get(mo.group(2), mo.group(2))}{mo.group(1)}",
            text)

    defined_in = {nm: m for i, m in assign.items() for nm in defined_names(body[i])}

    # --- генерация модулей маршрутов ---
    mod_nodes = defaultdict(list)
    for i, m in sorted(assign.items()):
        mod_nodes[m].append(i)

    out_files, warnings = {}, []
    for m, (doc, bpname, _) in ROUTE_MODULES.items():
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
        extra = {"flask": {"Blueprint"}} if bpname else None
        std_and_from, local_imps, unknown = gen_imports(needed, imports, defined_in, m, extra)
        for nm in unknown:
            warnings.append(f"{m}.py использует имя '{nm}', которое осталось в app.py или неизвестно")

        parts = ["# -*- coding: utf-8 -*-", f'"""{doc}"""', ""]
        if std_and_from:
            parts += std_and_from + [""]
        if local_imps:
            parts += local_imps + [""]
        if bpname:
            parts += [f'bp = Blueprint("{bpname}", __name__)', ""]
        parts.append("")
        chunks = []
        for k, i in enumerate(idxs):
            if k:
                prev = idxs[k - 1]
                chunks.append(("\n" * (spans[i][0] - spans[prev][1])) if i == prev + 1 else "\n\n\n")
            s, e = spans[i]
            text = "\n".join(lines[s - 1:e])
            text = re.sub(r"^@app\.", "@bp.", text, flags=re.M)
            chunks.append(fix_url_for(text))
        parts.append("".join(chunks))
        out_files[m + ".py"] = "\n".join(parts).rstrip() + "\n"

    bps = [(bp, m) for m, (_, bp, _) in ROUTE_MODULES.items() if bp and m in mod_nodes]
    out_files["routes/__init__.py"] = (
        '# -*- coding: utf-8 -*-\n"""Blueprint-ы приложения."""\n\n'
        + "".join(f"from {m.replace('/', '.')} import bp as {bp}_bp\n" for bp, m in bps)
        + "\n\ndef register_blueprints(app):\n"
        + "    for bp in (" + ", ".join(f"{bp}_bp" for bp, _ in bps) + ",):\n"
        + "        app.register_blueprint(bp)\n")

    # --- новый app.py: оставшиеся узлы + регистрация blueprint-ов ---
    # узлы выше первого импорта (докстринг модуля) уже входят в header
    remaining = [i for i in range(len(body))
                 if i not in import_idx and i not in assign and spans[i][1] >= first_import]
    local, needed = set(), set()
    for i in remaining:
        n = body[i]
        local.update(defined_names(n))
        if not isinstance(n, ast.FunctionDef):
            local.update(s.id for s in ast.walk(n)
                         if isinstance(s, ast.Name) and isinstance(s.ctx, ast.Store))
        needed |= free(stripped(n), set())
    needed -= local
    needed -= BUILTINS
    needed.discard("app")
    imp_lines, _, unknown = gen_imports(needed, imports, {}, "app")
    for nm in unknown:
        warnings.append(f"app.py использует имя '{nm}', источник которого не найден")
    imp_lines.append("from routes import register_blueprints")

    header = "\n".join(lines[:first_import - 1]).rstrip()
    out = [header, ""] + imp_lines + ["", ""]
    reg_done = False
    for k, i in enumerate(remaining):
        n = body[i]
        is_main = isinstance(n, ast.If) and "__name__" in ast.dump(n.test)
        if is_main and not reg_done:
            out += ["", "", "register_blueprints(app)", "", ""]
            reg_done = True
        if k:
            prev = remaining[k - 1]
            gap = spans[i][0] - spans[prev][1] - 1
            out.append("\n" * max(gap, 0) if i == prev + 1 else "\n")
        s, e = spans[i]
        out.append("\n".join(lines[s - 1:e]))
    if not reg_done:
        out += ["", "", "register_blueprints(app)"]
    new_app = re.sub(r"\n{4,}", "\n\n\n", "\n".join(out)).rstrip() + "\n"

    # --- шаблоны и mascot.py ---
    changed = []
    new_templates = {}
    if TEMPLATES.exists():
        for p in sorted(TEMPLATES.glob("*.html")):
            t = p.read_text(encoding="utf-8")
            t2 = fix_url_for(t)
            if t2 != t:
                new_templates[p] = t2
                changed.append(p.name)
    new_mascot = None
    mp = Path("mascot.py")
    if mp.exists():
        t = mp.read_text(encoding="utf-8")
        t2 = t
        for old, new in endpoint_map.items():
            t2 = re.sub(rf"""(endpoint\s*==\s*)(['"]){old}\2""", rf"\1\2{new}\2", t2)
        for old in ("index",):
            pass
        if t2 != t:
            new_mascot = t2
    else:
        warnings.append("mascot.py не найден — проверки request.endpoint не обновлены")

    # --- проверка синтаксиса ДО записи ---
    for name, text in list(out_files.items()) + [("app.py", new_app)]:
        try:
            ast.parse(text)
        except SyntaxError as e:
            fail(f"синтаксическая ошибка в сгенерированном {name}: {e}")

    Path("app.py.step3.bak").write_text(src, encoding="utf-8")
    for name, text in out_files.items():
        p = Path(name)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    SRC.write_text(new_app, encoding="utf-8")
    for p, t in new_templates.items():
        p.write_text(t, encoding="utf-8")
    if new_mascot:
        mp.write_text(new_mascot, encoding="utf-8")

    print("Готово. Резервная копия: app.py.step3.bak\n")
    for name, text in out_files.items():
        print(f"  {name:22s} {len(text.splitlines()):4d} строк")
    print(f"  app.py: {len(lines)} -> {len(new_app.splitlines())} строк")
    print("\nЭндпоинты:")
    for old, new in endpoint_map.items():
        print(f"  {old:24s} -> {new}")
    print(f"\nШаблоны с обновлёнными url_for: {', '.join(changed) or '—'}")
    print("mascot.py: " + ("обновлён" if new_mascot else "изменений нет"))
    print("\nОстались в app.py:", ", ".join(
        n for i in remaining for n in (defined_names(body[i]) or [type(body[i]).__name__])))
    if warnings:
        print("\nПРЕДУПРЕЖДЕНИЯ:")
        for w in warnings:
            print("  -", w)
    print("\nДальше: обновите тесты (tests/ из step3.zip) и запустите pytest.")


if __name__ == "__main__":
    main()
