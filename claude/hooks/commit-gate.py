#!/usr/bin/env python3
"""
PreToolUse hook (matcher: Bash) — gate de `git commit`.

Antes de cualquier commit corre `paw_checks.py all` (paridad i18n + versiones Flyway
duplicadas + balance JSTL). Si falla, DENY con el detalle (clusters C3/C7 del audit:
keys cojas y V-duplicadas llegaban commiteadas y explotaban en runtime/boot).

Escape hatch: si el usuario pide commitear igual, anteponer `PAW_SKIP_SMOKE=1` al comando.
Falla en silencio (exit 0) ante cualquier error propio — el gate jamás debe colgar un commit.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

CHECK_TIMEOUT_SECONDS = 20


def main():
    data = json.load(sys.stdin)
    if data.get("tool_name") != "Bash":
        return
    command = (data.get("tool_input") or {}).get("command") or ""
    if not re.search(r"\bgit\s+commit\b", command):
        return
    if "PAW_SKIP_SMOKE=1" in command:
        return

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or str(Path(__file__).resolve().parents[2])
    script = os.path.join(project_dir, ".claude", "scripts", "paw_checks.py")
    try:
        result = subprocess.run(
            [sys.executable, script, "all"],
            capture_output=True, text=True, timeout=CHECK_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return  # el gate nunca cuelga un commit
    if result.returncode == 0:
        return

    detail = (result.stdout or "").strip()[-3000:]
    reason = (
        "Smoke checks del proyecto fallaron — no commiteo esto:\n"
        f"{detail}\n"
        "Arreglá los problemas y reintentá el commit. Si el usuario pide explícitamente "
        "commitear igual, reintentá anteponiendo PAW_SKIP_SMOKE=1 al comando de git."
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
