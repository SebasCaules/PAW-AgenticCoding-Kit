#!/usr/bin/env python3
"""
PreToolUse hook (matcher: Bash) — guard de BD/server: el usuario ejecuta, Claude emite comandos.

Regla del proyecto (cluster C5 del audit): Claude NUNCA corre psql/pg_*/Jetty por su cuenta.
En jun-2026 hubo 3 denials del clasificador por manipulación de credenciales en la BD dev y
6+ re-pedidos de "dame el comando listo". Este hook convierte eso en una corrección instantánea.

Escape hatch: si el usuario autorizó explícitamente en la sesión (p. ej. seeding sancionado
con rollback), anteponer `PAW_ALLOW_DB=1` al comando.
Falla en silencio (exit 0) ante cualquier error propio.
"""
import json
import re
import sys

BLOCKED = re.compile(
    r"\b(psql|pg_isready|pg_dump|pg_dumpall|pg_restore|createdb|dropdb)\b|jetty:run"
)


def main():
    data = json.load(sys.stdin)
    if data.get("tool_name") != "Bash":
        return
    command = (data.get("tool_input") or {}).get("command") or ""
    if "PAW_ALLOW_DB=1" in command:
        return
    if not BLOCKED.search(command):
        return

    reason = (
        "Regla del proyecto: el usuario ejecuta psql/Jetty/mails — vos no. "
        "Emití el comando LISTO para copiar/pegar (una línea, con todos los flags), y antes de "
        "cualquier comando destructivo u outbound (UPDATE/DELETE/mails) dale primero el comando "
        "de PREVIEW (qué filas afecta / qué destinatarios). Nunca manipules credenciales o roles "
        "en la BD dev para reproducir bugs. Si el usuario te autorizó explícitamente a correr "
        "esto vos, reintentá anteponiendo PAW_ALLOW_DB=1 al comando."
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
