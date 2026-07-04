---
name: handoff
description: Cierra la sesión actual generando un handoff reanudable — escribe 0_Plans/<topic>/HANDOFF_<fecha>.md con el estado exacto (commits, bloques hechos/pendientes, gotchas) y un prompt de reanudación auto-contenido listo para pegar en una sesión nueva. Usar cuando el usuario dice "cerrá acá", "me quedo sin tokens", "session limit", "seguimos en otra sesión/modelo", o antes de un cambio de modelo a mitad de tarea.
argument-hint: [opcional: carpeta de 0_Plans donde guardar (default: la del tema activo)]
allowed-tools: [Read, Glob, Grep, Bash, Write]
---

Generás el handoff de la sesión de **Rent The Slopes** para que otra sesión (u otro modelo) retome sin pérdida. Codifica el patrón que ya funcionó en el crunch de la 2da entrega (handoff manual de `5d7f68d6` → `c13d1d63`, cluster C9 de `0_Plans/claude-harness/AUDIT_friccion-sesiones-claude.md`) — y elimina el anti-patrón de re-pegar checklists de 81 ítems como ancla de contexto.

## Proceso

1. **Recopilar estado real** (no de memoria — de los comandos):
   ```bash
   git status --short
   git log --oneline -5
   git diff --stat HEAD
   ```
   Más el plan/checklist activo de la sesión (qué bloques ✅ / ⬜).

2. **Escribir `0_Plans/<topic-activo>/HANDOFF_<yyyy-mm-dd>.md`** (topic = la carpeta del plan que se estaba ejecutando; si el usuario pasó otra como argumento, usar esa) con exactamente estas secciones:
   - **Contexto** — qué se está haciendo y por qué, en ≤5 líneas.
   - **Completado** — cada bloque/fix terminado, con hash de commit si se commiteó.
   - **Pendiente** — ordenado por prioridad, con paths de los archivos a tocar.
   - **Gotchas descubiertas** — todo lo aprendido a fuerza de errores en esta sesión (decisiones tomadas, falsos caminos, estado raro del working tree, tests que fallan por otra razón). Es la sección más valiosa: es lo que la sesión nueva NO puede re-derivar.
   - **PROMPT DE REANUDACIÓN** — bloque final entre ``` listo para copiar/pegar: auto-contenido (paths absolutos, IDs de fixes, convenciones críticas del proyecto que apliquen), empieza con "Retomá la ejecución de <plan> desde <punto>...". No debe requerir que la sesión nueva lea esta conversación.

3. **Responder solo con**: el path del HANDOFF escrito + el prompt de reanudación (para que el usuario lo copie de una).

## Reglas

- El working tree NO se toca: nada de commits, staging ni reverts — solo lectura + el Write del HANDOFF.
- Si hay cambios sin commitear, listarlos explícitamente en "Pendiente" con el aviso de que la sesión nueva debe decidir commitearlos o continuarlos.
- Mensaje de commit sugerido (si el usuario quiere cerrar commiteando): UNA línea breve, como siempre.
