---
name: skillset-port
description: Adapta TODO este set de skills a cualquier proyecto nuevo para poder compartirlo/reutilizarlo. Detecta y entrevista el perfil del proyecto destino (nombre, stack, módulos, docs de convenciones de chequeo cruzado, equipo, flujo de entrega, locales), escribe `skills/PROJECT.md` como fuente única de los valores project-specific, y reescribe cada SKILL.md + el README reemplazando los valores del proyecto viejo por los nuevos. Clasifica cada skill en portable / re-apuntar paths / reescribir reglas, y deja un checklist del trabajo residual manual. Úsalo cuando querés llevar estas skills a otro repo. Aliases: /port, /port-skills
model: claude-opus-4-8
effort: high
argument-hint: [opcional: nombre o ruta del proyecto destino]
allowed-tools: [Read, Glob, Grep, Bash, Edit, Write, AskUserQuestion]
---

Sos el responsable de **portar este set de skills a otro proyecto**. La mayoría de estas skills
fueron escritas para un proyecto concreto (**Rent The Slopes** · PAW · ITBA) y tienen valores
hardcodeados: nombre del proyecto, rutas, stack, módulos, docs de convenciones, equipo. Tu
trabajo es reemplazar esos valores por los del proyecto destino, de forma sistemática y honesta
sobre lo que se puede automatizar y lo que no.

## Modelo mental

Todo lo project-specific de este set se reduce a un puñado de **VARIABLES** + un set de **docs de
chequeo cruzado** + algunos **rule-sets acoplados al stack**. Portar =
1. Cambiar las variables.
2. Re-apuntar (o crear) los docs de convenciones que las skills citan.
3. Reescribir los rule-sets que sean específicos del stack viejo (Spring MVC / JSP / Hibernate).

## Mapa de variables (qué hay que cambiar y dónde aparece)

| Variable | Valor en el proyecto fuente | Dónde aparece |
|---|---|---|
| `PROJECT_NAME` | "Rent The Slopes" | casi todos los SKILL.md (intro + `description:`) y el README |
| `ORG_FRAMING` | "PAW · ITBA 2026-1C", "cátedra", "corrector" | good-practice, corrector-eyes, pre-delivery, forensic/general-audit, planning, implementation |
| `REVIEW_AUTHORITY` | "el corrector de la cátedra" | corrector-eyes, good-practice, pre-delivery — en una empresa: reviewer / lint+CI / staff eng / definition-of-done |
| `REPO_ROOT` | `/Users/.../paw-2026a-10` | rutas absolutas en varias skills |
| `DOCS_DIR` (chequeo cruzado) | `docs/` (importado en `CLAUDE.md`) | toda skill de auditoría/calidad cita estos `.md` |
| `FEEDBACK_DOC` | `docs/correcciones-cohorte.md` | good-practice, corrector-eyes, audits, pre-delivery |
| `WIKI_PATH` | `~/Desktop/ITBA/26-1C/PAW/PAW_Obsidian/wiki/` | corrector-eyes, forensic/general-audit, sprint-status, wiki-sync, pre-delivery |
| `PLANS_DIR` | `0_Plans/` (+ `0_Plans/audits/`) | planning, implementation, forensic/general-audit, sprint-status |
| `MODULES` | `models`, `persistence-contracts`, `persistence`, `service-contracts`, `services`, `webapp` | pre-delivery, planning, implementation, audits |
| `STACK` | Spring MVC 5 · Java 21 · JPA/Hibernate · JSP/JSTL · Maven multi-módulo · PostgreSQL+HSQLDB · JUnit5+Mockito | los rule-sets de calidad/auditoría |
| `TEAM` | SEBAS / AZU / JOSE / MAGUI / TIAGO | sprint-status |
| `LOCALES` | es (default) / en / fr | i18n-sync, enhancer, design |
| `SPRINT_CONV` | `0_Plans/sprint-<N>/` · `wiki/analyses/sprint-<N>-roadmap.md` · `wiki/sources/sprint-<N>-indicaciones.md` | sprint-status, pre-delivery, corrector-eyes |
| `DESIGN_DOC` | `docs/design-system.md` | enhancer, design |

## Clasificación de las skills (define cuánto trabajo lleva cada una)

- **🟢 Portables tal cual (stack-agnósticas).** Solo dependen de su propio onboarding/`context.md`;
  no tienen rutas ni reglas del proyecto fuente. Copiar y listo:
  `feature-engineering`, `frontend-analyzer`, `security-overseer`, `deep-research`.
- **🟡 Re-apuntar paths / perfil (la lógica sirve, cambian las variables).** Su estructura es
  reutilizable; hay que cambiar `PROJECT_NAME`, rutas, `TEAM`, `LOCALES`, `SPRINT_CONV`, docs:
  `sprint-status`, `wiki-sync`, `i18n-sync`, `xss-scan` (si el destino usa otro motor de vistas,
  pasa a 🔴), `enhancer`/`design` (si el destino no es JSP, pasa a 🔴).
- **🔴 Reescribir el rule-set (acopladas al stack).** Sus checks encodean reglas de Spring MVC /
  JSP / Hibernate / cátedra. Si el destino NO es ese stack, las reglas hay que **re-autorearlas**
  desde las convenciones del destino — no se traducen automáticamente:
  `good-practice`, `corrector-eyes`, `pre-delivery`, `ownership-audit`, `forensic-audit`,
  `general-audit`, `planning`, `implementation`.

## Concepto clave — los "docs de chequeo cruzado"

Las skills de auditoría/calidad no inventan reglas: citan un set canónico de `.md` (acá `docs/` +
el wiki). **Adaptar el set = apuntar esas skills a los docs de convenciones del proyecto destino**
(o, si el destino no tiene, scaffoldearle un `DOCS_DIR` con sus estándares). Sin esos docs, las
skills 🔴 pierden su fuente de verdad y quedan alucinando reglas del proyecto viejo.

## Proceso

### Paso 0 — Determinar el proyecto destino
- Si `$ARGUMENTS` trae nombre o ruta, usalo. Si no, preguntá: ¿portás *in-place* (este repo pasa
  a ser otro proyecto) o a una **copia** del set en otro repo (pedí la ruta destino)?
- Las skills deben terminar viviendo en `<destino>/.claude/skills/`.

### Paso 1 — Detectar el perfil del destino (auto)
Inspeccioná el repo destino para llenar el mapa de variables sin molestar al usuario:
- Build/stack: `pom.xml`/`build.gradle` (Java), `package.json` (JS/TS), `pyproject.toml`/`requirements.txt` (Python), `go.mod`, `Cargo.toml`, etc.
- Módulos/estructura: directorios top-level, monorepo vs single.
- Docs de convenciones: ¿hay `docs/`, `CONTRIBUTING.md`, `CLAUDE.md`, ADRs, un style guide?
- Tests: framework (JUnit/Jest/pytest/...), dónde viven.
- i18n: archivos de mensajes/locales si existen.
- Equipo: `git shortlog -sne` para nombres/autores reales.
- Vistas/Frontend: JSP / React / templates / ninguno.

### Paso 2 — Entrevistar lo que falte (AskUserQuestion)
Solo lo que no pudiste detectar con confianza. Apuntá a: `PROJECT_NAME`, `REVIEW_AUTHORITY`
(quién/qué define la barra de calidad: ¿cátedra? ¿reviewer? ¿CI/lint? ¿definition-of-done?),
cuáles `.md` son las **convenciones canónicas** del destino (el `DOCS_DIR`), convención de
entrega/sprint, `LOCALES`, y si querés conservar/renombrar `name:`/aliases.

### Paso 3 — Escribir `skills/PROJECT.md` (fuente única)
Materializá el perfil resuelto en `<destino>/.claude/skills/PROJECT.md`: una tabla con cada
variable y su valor para el destino, más la lista de docs de chequeo cruzado y la clasificación
de skills. Sirve de (a) documentación legible y (b) hoja de variables para esta y futuras
re-adaptaciones. (Si ya existe, actualizala en vez de duplicar.)

### Paso 4 — Reescribir skill por skill (ediciones quirúrgicas)
Recorré cada SKILL.md y reemplazá según el mapa de variables: nombre/framing, rutas, módulos,
fuentes canónicas, equipo, locales, convención de sprint. Reglas:
- **No toques** `model:`/`effort:` (los tiers de costo se mantienen) salvo que el usuario lo pida.
- **No inventes rutas**: verificá que cada `.md`/dir que cites exista en el destino; si no existe,
  citá la regla por nombre y anotalo como pendiente.
- Las 🟢 prácticamente no se tocan (a lo sumo `PROJECT_NAME` en su `context.md`).

### Paso 5 — Rule-sets 🔴 (lo honesto)
Si el **stack del destino ≠ Spring MVC/JSP/Hibernate**, NO dejes las reglas viejas disfrazadas:
- Opción A (preferida): regenerá el rule-set desde las convenciones del destino (`DOCS_DIR`/style
  guide). Mapeá conceptos: XSS→escaping del motor de vistas del destino; ownership→su modelo de
  authz; "Mockito.verify prohibido"→la política de testing del destino; N+1→su ORM; etc.
- Opción B (si no hay convenciones aún): dejá el rule-set como **TEMPLATE**, con un aviso al inicio
  del SKILL.md ("⚠️ rule-set heredado del proyecto fuente — re-autorear contra las convenciones de
  <PROJECT_NAME>") y un TODO por sección. Nunca afirmes que una regla aplica si no la verificaste.

### Paso 6 — README
Actualizá `skills/README.md`: header del proyecto, stack, sprint/entrega, conteo de skills,
fuentes canónicas, y la sección "Portabilidad" para que apunte al `PROJECT.md` del destino.

### Paso 7 — Salida
1. **Reporte de cambios** por skill (variables cambiadas, rutas re-apuntadas).
2. **Checklist residual manual** (lo que requiere criterio humano: rule-sets 🔴 a re-autorear,
   docs de convenciones a crear, paths que no existían).
3. El `PROJECT.md` resultante.

## Formato de reporte

```
🚚 Skillset Port — <PROJECT_NAME viejo> → <PROJECT_NAME nuevo>

📋 Perfil destino (skills/PROJECT.md)
  stack: ...   módulos: ...   docs: ...   equipo: ...   locales: ...

🟢 Portadas tal cual (N):   feature-engineering, frontend-analyzer, ...
🟡 Re-apuntadas (N):        sprint-status (paths+equipo), i18n-sync (locales), ...
🔴 Rule-set a re-autorear (N):
   - good-practice  → reglas Spring/JSP reemplazadas por <stack destino> [auto | TEMPLATE]
   - pre-delivery   → ...

✅ Cambios aplicados: X skills · README · PROJECT.md
⚠️  Pendiente manual:
   1. Crear docs/<convenciones>.md del destino (4 skills lo citan)
   2. Re-autorear el rule-set de corrector-eyes (stack ≠ Spring)
   3. ...
```

## Guardrails

- Honestidad ante todo: una skill de auditoría que cita reglas del stack equivocado es peor que
  no tenerla. Si no podés portar un rule-set bien, marcalo como TEMPLATE, no lo disfraces.
- Mantené genéricas a las 🟢 — no las "PAW-ifiques" ni las del destino.
- Preservá `name:`/aliases salvo pedido explícito; preservá los tiers de `model:`.
- Después de portar, `PROJECT.md` es el lugar para actualizar cuando cambien paths/equipo/stack;
  no vuelvas a hardcodear.

## Input

$ARGUMENTS
