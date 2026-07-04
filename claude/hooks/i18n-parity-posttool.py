#!/usr/bin/env python3
"""
PostToolUse hook (matcher: Edit|Write|MultiEdit) — paridad i18n al editar los bundles.

Si el Edit/Write tocó webapp/src/main/resources/i18n/messages*.properties, corre
`paw_checks.py i18n` y, si hay keys cojas, inyecta el detalle al contexto para que Claude
las complete AHORA (cluster C3 del audit: keys faltantes = JasperException en runtime).

Debounce de 10 s vía stamp en /tmp para no correr 4 veces en una tanda de edits.
Falla en silencio (exit 0 sin output) ante cualquier error — nunca debe romper un turno.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

STAMP = "/tmp/paw-i18n-check.stamp"
DEBOUNCE_SECONDS = 10


def main():
    data = json.load(sys.stdin)
    tool_input = data.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    if "/i18n/messages" not in file_path:
        return

    now = time.time()
    try:
        if os.path.exists(STAMP) and now - os.path.getmtime(STAMP) < DEBOUNCE_SECONDS:
            return
        Path(STAMP).touch()
    except OSError:
        pass

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or str(Path(__file__).resolve().parents[2])
    script = os.path.join(project_dir, ".claude", "scripts", "paw_checks.py")
    result = subprocess.run(
        [sys.executable, script, "i18n"], capture_output=True, text=True, timeout=20
    )
    if result.returncode == 0:
        return

    detail = (result.stdout or "").strip()[-3000:]
    ctx = (
        "PARIDAD i18n ROTA (hook automático del proyecto):\n"
        f"{detail}\n"
        "→ Completá las keys faltantes en los bundles indicados AHORA, antes de cualquier otra cosa. "
        "Regla del proyecto: toda key nueva va en messages.properties + messages_en + messages_fr "
        "(messages_es hereda del default y puede quedar vacío). Una key coja rompe la página con "
        "JasperException en runtime — ya pasó dos veces en la entrega."
    )
    print(json.dumps({
        "hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": ctx}
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
