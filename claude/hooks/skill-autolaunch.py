#!/usr/bin/env python3
"""
UserPromptSubmit hook — auto-launch de skills (personal, este proyecto).

Cuando el mensaje del usuario parece pedir una AUDITORÍA, un cambio de CSS/estilos, o un
CHEQUEO DE ERRORES, inyecta una instrucción para que Claude invoque la skill correspondiente
("sugerir y arrancar"). Siempre con una vía de escape: si el mensaje es en realidad sobre otra
cosa (p. ej. hablar de las skills o editarlas), Claude debe ignorar la sugerencia.

Falla en silencio (exit 0 sin output) ante cualquier error — nunca debe bloquear un prompt.
"""
import sys
import json
import re


def has(text, needles):
    return any(n in text for n in needles)


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return

    prompt = (data.get("prompt") or "")
    p = prompt.lower()
    if not p.strip():
        return

    # Guard negativo (audit 2026-07-03, C12): prompts sobre el harness mismo — sesiones de
    # Claude, skills, hooks, memoria, transcripts — no son trabajo sobre el proyecto. El
    # keyword pelado "audit" disparaba /general-audit ante "audit my claude session".
    if re.search(r"\b(sesi[oó]n(es)?|sessions?|claude|skills?|hooks?|transcripts?|mcp|memorias?|memory)\b", p):
        return

    suggestions = []  # (skill, descripción)

    # --- Seguridad (una clase de auditoría; va primero) ---
    if has(p, ["seguridad", "vulnerabilidad", "owasp", "inyección sql", "sql injection",
               "exploit", "secrets", "es seguro", "está seguro", "/security"]):
        suggestions.append(("/security-overseer", "una auditoría de seguridad / vulnerabilidades"))

    # --- Auditoría general / forense ---
    # "audit" solo dispara con un objeto de proyecto (evita falsos positivos con audits meta).
    audit_object = has(p, ["proyecto", "código", "codigo", "sprint", "entrega", "controller",
                           "service", "dao", "jsp", "feature", "dictamen", "forense"])
    if audit_object and has(p, ["audit", "dictamen", "revisar todo el proyecto", "revisión del proyecto"]):
        if has(p, ["forense", "profund", "exhaustiv", "todo el proyecto", "dictamen", "completa"]):
            suggestions.append(("/forensic-audit", "una auditoría forense profunda"))
        else:
            suggestions.append(("/general-audit", "una auditoría general del proyecto"))

    # --- Chequeo de errores / calidad ---
    corrector = has(p, ["corrector", "/corrector", "que me van a descontar", "ojos del corrector"])
    predelivery = has(p, ["pre-entrega", "preentrega", "antes de entregar", "para la entrega",
                          "checklist de entrega", "deploy final", "entregamos", "/deliver"])
    errors = has(p, ["errores", "bugs", "malas práctic", "malas practic", "buenas práctic",
                     "buenas practic", "code smell", "qué está mal", "que esta mal",
                     "revisá el código", "revisar el código", "revisá el codigo",
                     "chequeá el código", "chequear el código", "chequear errores",
                     "chequeando errores", "fijate si hay errores", "/gp", "good practice"])
    if errors:
        if corrector:
            suggestions.append(("/corrector-eyes", "un chequeo estilo corrector pre-entrega"))
        else:
            suggestions.append(("/good-practice", "un chequeo de errores / malas prácticas"))
    elif corrector:
        suggestions.append(("/corrector-eyes", "una revisión de pre-entrega"))
    if predelivery:
        suggestions.append(("/pre-delivery", "el checklist ejecutable de pre-entrega (smoke + build + tests)"))

    # --- CSS / estilos / UI ---
    new_ui = has(p, ["rediseñ", "rediseno", "nueva pantalla", "pantalla nueva", "nueva vista",
                     "nuevo componente", "nueva ui", "maqueta", "diseñar una pantalla",
                     "diseñar la ui", "diseñar la vista", "/design"])
    css = has(p, ["css", "estilo", "styling", "se ve feo", "se ve mal", "estética", "estetica",
                  "spacing", "responsive", "tipografía", "tipografia", "colores", "dark mode",
                  "modo oscuro", "diseño visual", "/enhance"])
    if new_ui:
        suggestions.append(("/design", "diseño de UI nueva o un rediseño"))
    elif css:
        suggestions.append(("/enhancer", "una mejora estética de CSS/JSP"))

    # --- Wiki sync (tras implementar/mergear una feature) ---
    if has(p, ["actualiza el wiki", "actualizar el wiki", "wiki desactualizad", "sincroniza el wiki",
               "sincronizar el wiki", "implementamos la feature", "mergeamos la feature",
               "termine la feature", "terminé la feature"]):
        suggestions.append(("/wiki-sync", "sincronizar el wiki de Obsidian con la codebase"))

    if not suggestions:
        return

    seen, uniq = set(), []
    for name, desc in suggestions:
        if name not in seen:
            seen.add(name)
            uniq.append((name, desc))

    lines = "\n".join(f"- `{name}` — para {desc}." for name, desc in uniq)
    ctx = (
        "AUTO-LAUNCH DE SKILLS (hook personal de este proyecto). El mensaje del usuario parece "
        "pedir una de estas tareas. Si esa es realmente su intención, invocá YA la skill "
        "correspondiente con la herramienta Skill — el usuario configuró 'sugerir y arrancar' "
        "(igual puede cancelar). Si en cambio el mensaje es sobre otra cosa (hablar de las skills, "
        "editarlas, o algo no relacionado), ignorá esto por completo.\n" + lines
    )
    out = {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": ctx}}
    print(json.dumps(out))


main()
