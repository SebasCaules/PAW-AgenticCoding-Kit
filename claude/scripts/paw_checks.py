#!/usr/bin/env python3
"""
paw_checks.py — chequeos determinísticos del proyecto (sin dependencias fuera de stdlib).

Uso: python3 .claude/scripts/paw_checks.py [i18n|flyway|jsp|all]

Exit 0 = todo OK. Exit 1 = hay errores (detalle por stdout). Los WARNING no afectan el exit code.

Origen: 0_Plans/claude-harness/plan_harness-friction-fixes.md (S-01). Cierra los clusters C3
(keys i18n incompletas → JasperException en runtime) y C7 (versiones Flyway duplicadas /
JSPs desbalanceados que los tests HSQLDB no atrapan).
"""
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
I18N_DIR = PROJECT_ROOT / "webapp/src/main/resources/i18n"
MIGRATIONS_DIR = PROJECT_ROOT / "persistence/src/main/resources/db/migration"
TEST_SCHEMA = PROJECT_ROOT / "persistence/src/test/resources/schema.sql"
VIEWS_DIR = PROJECT_ROOT / "webapp/src/main/webapp/WEB-INF/views"
TAGS_DIR = PROJECT_ROOT / "webapp/src/main/webapp/WEB-INF/tags"

MAX_LISTED_KEYS = 20


def parse_properties_keys(path):
    """Keys de un .properties, manejando comentarios y líneas de continuación (\\ final)."""
    keys = set()
    if not path.exists():
        return keys
    continuation = False
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if continuation:
            # esta línea es la cola de un valor multilínea, no una key
            continuation = _ends_with_odd_backslashes(raw)
            continue
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        m = re.match(r"([^=:\s]+)\s*[=:]", line)
        if m:
            keys.add(m.group(1))
        continuation = _ends_with_odd_backslashes(raw)
    return keys


def _ends_with_odd_backslashes(line):
    n = 0
    for ch in reversed(line.rstrip("\n")):
        if ch == "\\":
            n += 1
        else:
            break
    return n % 2 == 1


def check_i18n():
    """Paridad de bundles. Regla del equipo (docs/views-and-jsp.md): messages.properties es el
    default (es); _en y _fr deben tener TODAS sus keys; _es puede estar vacío (hereda).
    Una key presente solo en un bundle hijo tampoco sirve: los demás locales caen al default
    y no la encuentran → JasperException."""
    errors = []
    default = parse_properties_keys(I18N_DIR / "messages.properties")
    if not default:
        return ["i18n: no pude leer keys de messages.properties (¿path correcto? %s)" % I18N_DIR]
    for loc in ("en", "fr"):
        missing = default - parse_properties_keys(I18N_DIR / f"messages_{loc}.properties")
        if missing:
            listed = ", ".join(sorted(missing)[:MAX_LISTED_KEYS])
            extra = "" if len(missing) <= MAX_LISTED_KEYS else f" (+{len(missing) - MAX_LISTED_KEYS} más)"
            errors.append(f"i18n: messages_{loc}.properties — faltan {len(missing)} keys: {listed}{extra}")
    for loc in ("es", "en", "fr"):
        orphans = parse_properties_keys(I18N_DIR / f"messages_{loc}.properties") - default
        if orphans:
            listed = ", ".join(sorted(orphans)[:MAX_LISTED_KEYS])
            errors.append(
                f"i18n: messages_{loc}.properties — {len(orphans)} keys huérfanas (no están en el "
                f"default, los otros locales las resuelven a missing): {listed}"
            )
    return errors


def check_flyway():
    """Versiones V<nro> duplicadas en db/migration (el bug real: dos V54 tras un merge).
    Warning (no error) si la migración más nueva es posterior al schema.sql de test."""
    errors = []
    if not MIGRATIONS_DIR.exists():
        # Etapa JDBC (Entrega 1): todavía no hay Flyway — no es un error.
        print(f"WARNING flyway: no existe {MIGRATIONS_DIR} (¿proyecto en etapa JDBC sin Flyway aún?) — check salteado.")
        return []
    versions = {}
    newest_mtime = 0.0
    for f in MIGRATIONS_DIR.iterdir():
        m = re.match(r"V(\d+)__", f.name)
        if not m:
            continue
        versions.setdefault(int(m.group(1)), []).append(f.name)
        newest_mtime = max(newest_mtime, f.stat().st_mtime)
    for v, files in sorted(versions.items()):
        if len(files) > 1:
            errors.append(f"flyway: versión V{v} duplicada: {', '.join(sorted(files))} — la app no bootea")
    if TEST_SCHEMA.exists() and newest_mtime > TEST_SCHEMA.stat().st_mtime:
        print(
            "WARNING flyway: hay migraciones más nuevas que persistence/src/test/resources/schema.sql — "
            "verificá la paridad del schema HSQLDB (regla de docs/testing.md)."
        )
    return errors


# Tags de bloque cuyo balance de apertura/cierre chequeamos. Los self-closing (<c:if .../>)
# son válidos (p.ej. c:if con var) y se excluyen del conteo de aperturas.
BALANCED_TAGS = ("c:if", "c:forEach", "c:choose", "c:when", "c:otherwise", "form:form")


def check_jsp():
    """Balance de tags JSTL por archivo (el 500 real: </c:if> desbalanceado post-merge).
    Heurística por regex sobre el fuente sin comentarios JSP/HTML."""
    errors = []
    files = []
    for base in (VIEWS_DIR, TAGS_DIR):
        if base.exists():
            files.extend(base.rglob("*.jsp"))
            files.extend(base.rglob("*.tag"))
    for f in sorted(files):
        text = f.read_text(encoding="utf-8", errors="replace")
        text = re.sub(r"<%--.*?--%>", "", text, flags=re.DOTALL)
        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
        for tag in BALANCED_TAGS:
            all_open = re.findall(rf"<{re.escape(tag)}(?=[\s>/])[^>]*>", text)
            self_closing = sum(1 for t in all_open if t.rstrip().endswith("/>"))
            opens = len(all_open) - self_closing
            closes = len(re.findall(rf"</{re.escape(tag)}\s*>", text))
            if opens != closes:
                rel = f.relative_to(PROJECT_ROOT)
                errors.append(f"jsp: {rel} — <{tag}> desbalanceado (aperturas={opens}, cierres={closes})")
    return errors


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    checks = {"i18n": check_i18n, "flyway": check_flyway, "jsp": check_jsp}
    if what == "all":
        selected = list(checks.items())
    elif what in checks:
        selected = [(what, checks[what])]
    else:
        print(f"uso: paw_checks.py [{'|'.join(checks)}|all]")
        return 2
    errors = []
    for name, fn in selected:
        errs = fn()
        errors.extend(errs)
        if not errs:
            print(f"{name}: OK")
    if errors:
        print("\nPROBLEMAS ENCONTRADOS:")
        for e in errors:
            print(f"  - {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
