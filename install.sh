#!/usr/bin/env bash
# paw-claude-kit — instalador
#
# Copia el tooling de Claude Code (skills + hooks + scripts) al .claude/ de tu proyecto PAW
# y mergea los hooks/permisos en tu settings.local.json sin pisar lo que ya tengas.
#
# Uso:
#   ./install.sh /ruta/a/tu/repo-paw              # instala el tooling
#   ./install.sh /ruta/a/tu/repo-paw --with-docs  # además copia docs/ (convenciones) al repo
set -euo pipefail

DEST="${1:?Uso: ./install.sh /ruta/a/tu/repo-paw [--with-docs]}"
WITH_DOCS="${2:-}"
KIT="$(cd "$(dirname "$0")" && pwd)"

[ -d "$DEST" ] || { echo "ERROR: no existe el directorio $DEST"; exit 1; }
command -v python3 >/dev/null || { echo "ERROR: se necesita python3"; exit 1; }

echo "→ Copiando skills, hooks y scripts a $DEST/.claude/ ..."
mkdir -p "$DEST/.claude"
cp -R "$KIT/claude/skills"  "$DEST/.claude/"
cp -R "$KIT/claude/hooks"   "$DEST/.claude/"
cp -R "$KIT/claude/scripts" "$DEST/.claude/"

echo "→ Mergeando settings-fragment.json en $DEST/.claude/settings.local.json ..."
python3 - "$KIT/settings-fragment.json" "$DEST/.claude/settings.local.json" <<'PYEOF'
import json, os, sys

frag_path, dest_path = sys.argv[1], sys.argv[2]
with open(frag_path) as f:
    frag = json.load(f)
frag.pop("_leeme", None)

dest = {}
if os.path.exists(dest_path):
    with open(dest_path) as f:
        dest = json.load(f)

allow = dest.setdefault("permissions", {}).setdefault("allow", [])
for perm in frag["permissions"]["allow"]:
    if perm not in allow:
        allow.append(perm)

# Los hooks del kit reemplazan el evento homónimo (si ya tenías hooks propios en el
# mismo evento, revisá el resultado a mano).
hooks = dest.setdefault("hooks", {})
hooks.update(frag["hooks"])

with open(dest_path, "w") as f:
    json.dump(dest, f, indent=2, ensure_ascii=False)
    f.write("\n")
print("  settings.local.json actualizado")
PYEOF

if [ "$WITH_DOCS" = "--with-docs" ]; then
    echo "→ Copiando docs/ (convenciones) a $DEST/docs/ ..."
    mkdir -p "$DEST/docs"
    cp -n "$KIT/docs/"*.md "$DEST/docs/" 2>/dev/null || true
    echo "  (solo se copiaron los que no existían — no se pisó nada)"
fi

echo ""
echo "✔ Instalado. Verificación:"
python3 "$DEST/.claude/scripts/paw_checks.py" all || {
    echo "  (si tu proyecto todavía no tiene la estructura Maven completa, es normal que falle — el script asume webapp/ y persistence/)"
}
echo ""
echo "⚠ Los hooks se activan al ARRANCAR la sesión: cerrá y abrí Claude Code en el repo."
echo "→ Después pedile a Claude: 'leé .claude/skills/README.md y explicame qué skill uso para qué'."
