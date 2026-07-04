# PAW Project Skills — Rent The Slopes

Skills locales de Claude Code para el proyecto **Rent The Slopes** (PAW · ITBA 2026-1C). Asumen
la arquitectura Spring MVC multi-módulo del curso (hoy con persistencia **JPA/Hibernate**) y las
reglas del corrector consolidadas en `docs/correcciones-cohorte.md`.

> La mayoría son específicas de este proyecto, pero el set está pensado para **compartirse**:
> ver [Portabilidad](#portabilidad--adaptar-este-set-a-otro-proyecto) y la skill `/port`.

Cada skill declara su modelo según el peso de la tarea (tier de costo):
**🪶 haiku-4.5** (scans livianos) · **⚖️ sonnet-4.6** (tareas medias) · **🧠 opus-4.8** (auditorías y diseño pesados).
Las marcadas **✦** son genéricas/portables (no acopladas a PAW).

## Skills disponibles

### Especificación & planificación

| Skill | Alias | Modelo | Cuándo |
|---|---|---|---|
| `feature-engineering` ✦ | — | 🧠 | Una idea vaga de feature → spec implementable. Entrevista de descubrimiento antes de planear. |
| `planning` | `/plan` | 🧠 | Plan fase-a-fase (models → contracts → persistence JPA → services → validators → controllers → views → tests), listo para `/impl`. |
| `implementation` | `/impl` | ⚖️ | Ejecuta un plan fase por fase: DAOs JPA, ownership declarativo (`@PreAuthorize`), validators, `<c:out>`, JUnit 5 sin `verify`, migraciones Flyway + `schema.sql` de test. |

### Calidad & revisión continua

| Skill | Alias | Modelo | Cuándo |
|---|---|---|---|
| `good-practice` | `/gp` | 🧠 | Audita archivos modificados contra las reglas PAW. Detecta XSS, ownership mal ubicado, scriptlets, `Mockito.verify`, N+1, trampas Hibernate (EAGER cascada, 1+1, `@Async`+lazy), lógica en controllers. Correr **después de codear, antes de commitear**. |

### Auditorías

| Skill | Alias | Modelo | Cuándo |
|---|---|---|---|
| `forensic-audit` | `/audit`, `/dictamen` | 🧠 | Auditoría forense profunda: carga el contexto canónico, pre-vuelo con el usuario, agentes en paralelo por slice vertical (model → DAO → service → controller → JSP). Crea carpeta bajo `0_Plans/audits/`. |
| `general-audit` | `/general` | 🧠 | Auditoría en dos pasadas (vertical por feature + horizontal por capa), deduplica y produce un DICTAMEN con el formato de `AUDIT_GUIDE.md`. |
| `i18n-sync` | `/i18n` | ⚖️ | Diff de `messages*.properties` (es/en/fr), keys usadas-sin-definir, huérfanas, y textos hardcodeados en JSP. |

> Todas las skills de auditoría leen **`0_Plans/audits/ADJUDICACIONES.md`** (falsos positivos ya
> cerrados — CSRF disabled, `_es` vacío, etc.) y lo inyectan en el prompt de cada sub-agente.
> `xss-scan`, `ownership-audit` y `security-overseer` fueron **absorbidas por `/pre-delivery` /
> `/corrector-eyes`** y archivadas en `.claude/skills-archived/` (0 usos en 2.114 prompts).

### Sesión & sanidad (audit de fricción 2026-07-03)

| Skill | Alias | Modelo | Cuándo |
|---|---|---|---|
| `smoke` | — | (hereda) | Sanidad determinística en <2 min: paridad i18n, Flyway duplicados, balance JSTL, test-compile. Antes de commit/push/entrega o tras un merge. Solo reporta, no arregla. |
| `bug` ✦ | — | (hereda) | Ledger de bugs en `0_Plans/BUGS.md`: registra síntoma verbatim + intentos fallidos; detecta re-reportes. Un bug se describe una sola vez. |
| `handoff` ✦ | — | (hereda) | Cierra sesión con handoff reanudable: `HANDOFF_<fecha>.md` con estado + prompt de reanudación auto-contenido. Para session limits / cambio de modelo. |

### Frontend / UI

| Skill | Alias | Modelo | Cuándo |
|---|---|---|---|
| `design` | `/design` | 🧠 | UI nueva o rediseño profundo. Envuelve el plugin `frontend-design` con `docs/design-system.md` y las reglas PAW. Crea pantalla/JSP, custom tag, rediseño, o variante de componente. |
| `enhancer` | `/enhance` | 🪶 | Retoca estética de JSP/CSS existente sin tocar funcionalidad (spacing, tipografía, color, responsive, accesibilidad). Más liviano que `/design`. |
| `frontend-analyzer` ✦ | — | 🧠 | Análisis forense del diseño de una URL/localhost (colores, fuentes, tokens, componentes) → spec `.md`. |

### Entrega

| Skill | Alias | Modelo | Cuándo |
|---|---|---|---|
| `pre-delivery` | `/deliver` | 🧠 | Checklist completo de pre-entrega (Maven, Spring, DI, controllers, vistas, persistencia, testing, seguridad, logging, sprint actual) + `mvn compile` + `mvn test`. `--skip-tests` opcional. |
| `corrector-eyes` | `/corrector` | 🧠 | Modo paranoico: simula al corrector con tolerancia cero (todos los findings TP1+TP2 + trampas Hibernate + reglas del sprint). Estima puntos en riesgo. Stress-test final. |

### Gestión & sincronización

| Skill | Alias | Modelo | Cuándo |
|---|---|---|---|
| `wiki-sync` | `/wiki` | ⚖️ | Detecta páginas del wiki de Obsidian desincronizadas tras cambios de código y propone updates. (El hook de auto-launch la sugiere al terminar/mergear una feature.) |

> `sprint-status` (sprints terminados) está archivada en `.claude/skills-archived/`.

### Meta / toolkit

| Skill | Alias | Modelo | Cuándo |
|---|---|---|---|
| `skillset-port` | `/port`, `/port-skills` | 🧠 | **Adapta todo este set a otro proyecto** para compartirlo. Detecta/entrevista el perfil destino, escribe `PROJECT.md` y reescribe cada skill + README. Ver [Portabilidad](#portabilidad--adaptar-este-set-a-otro-proyecto). |

## Workflows típicos

### Desarrollo de feature
```
/plan <descripción de la feature>     → revisar plan, ajustar supuestos
/impl <plan aprobado>                 → código generado por fase
/gp                                   → validar calidad antes de commitear
/wiki                                 → sincronizar wiki si la feature es significativa
```

### Triaging de bug
```
/gp <área afectada>                   → posibles violaciones que causan el bug
[aplicar fix]
/gp                                   → confirmar que no se introdujeron regresiones
```

### Ajuste visual
```
/enhance <componente>                 → estética mejorada sin romper funcionalidad
/i18n                                  → confirmar que no se metieron textos hardcodeados
```

### Auditoría de entrega (profunda)
```
/audit <entrega>                      → DICTAMEN FORENSE completo + planes para CRÍTICOS/ALTOS
```

### Pre-entrega (rápida)
```
/smoke → /deliver → /corrector
```
(`/deliver` ya integra los ex `/xss` y `/ownership`, y arranca con el Bloque 0 de smoke.)

### Cierre de sesión con budget agotado
```
/handoff                              → HANDOFF_<fecha>.md + prompt de reanudación para la sesión nueva
```

## Referencias canónicas

Las skills de calidad/auditoría leen primero estas fuentes (las **"docs de chequeo cruzado"**):

1. **`docs/`** en la raíz del repo — referencia interna, `@`-importada en `CLAUDE.md`. La más
   importante es **`docs/correcciones-cohorte.md`** (consolida TP1+TP2 + checklist pre-entrega).
   Otras: `architecture.md`, `domain-and-layering.md`, `anti-patterns.md`, `forms-and-validation.md`,
   `views-and-jsp.md`, `security.md`, `testing.md`, `logging.md`, `pagination-and-search.md`,
   `guidelines.md`, `setup.md`, `hibernate-migration.md`, `design-system.md`.
2. **Wiki** en `~/Desktop/ITBA/26-1C/PAW/PAW_Obsidian/wiki/` — navegar vía `index.md`
   (`entities/`, `concepts/`, `sources/`, `analyses/`; archivos kebab-case).
3. **`PAW_Directives.md`** en la raíz — referencia más vieja, válida para lo no cubierto por `docs/`.

## Portabilidad — adaptar este set a otro proyecto

Este set fue escrito para un proyecto concreto, pero está pensado para **reutilizarse**. Hay dos
caminos: la skill `/port` (automatiza) o el proceso manual (lo entendés y lo controlás).

### Lo que es project-specific (qué hay que cambiar)

Casi todo lo específico se reduce a un puñado de **variables** + el set de **docs de chequeo
cruzado** + los **rule-sets acoplados al stack**:

| Qué | En este proyecto | Quién lo usa |
|---|---|---|
| Nombre del proyecto | "Rent The Slopes" | casi todas (intro + `description:`) |
| Autoridad de calidad | "el corrector de la cátedra" | corrector-eyes, good-practice, pre-delivery |
| Docs de convenciones | `docs/*.md` (chequeo cruzado) | toda skill de auditoría/calidad |
| Doc de feedback | `docs/correcciones-cohorte.md` | good-practice, corrector-eyes, audits |
| Wiki | `~/.../PAW_Obsidian/wiki/` | corrector-eyes, audits, sprint-status, wiki-sync |
| Planes | `0_Plans/` | planning, implementation, audits |
| Módulos | los 6 módulos Maven | pre-delivery, planning, implementation, audits |
| Stack | Spring MVC · JPA · JSP · Maven · PostgreSQL/HSQLDB · JUnit5 | los rule-sets de calidad |
| Equipo | SEBAS/AZU/JOSE/MAGUI/TIAGO | sprint-status |
| Locales | es/en/fr | i18n-sync, enhancer, design |
| Convención de sprint | `0_Plans/sprint-<N>/`, `wiki/.../sprint-<N>-*.md` | sprint-status, pre-delivery, corrector-eyes |

### Las skills se agrupan en tres niveles de esfuerzo de adaptación

- **🟢 Portables tal cual** (stack-agnósticas): `feature-engineering`, `frontend-analyzer`,
  `bug`, `handoff`. Copialas y listo (a lo sumo cambiás el nombre del proyecto y la ruta de planes).
- **🟡 Re-apuntar paths/perfil**: `wiki-sync`, `i18n-sync`, `enhancer`, `design`, `smoke` (+ su
  `paw_checks.py`). La lógica sirve; cambiás variables y rutas (si el destino no usa JSP, las
  dos de UI suben a 🔴 y `smoke` necesita otros checks).
- **🔴 Reescribir el rule-set** (acopladas al stack): `good-practice`, `corrector-eyes`,
  `pre-delivery`, `forensic-audit`, `general-audit`, `planning`,
  `implementation`. Sus checks encodean reglas de Spring/JSP/Hibernate; si el destino es otro
  stack, hay que **re-autorearlas** desde las convenciones del destino.
- Las archivadas (`.claude/skills-archived/`: `xss-scan`, `ownership-audit`, `security-overseer`,
  `sprint-status`) siguen disponibles como material de porteo.

### Camino automático — `/port`

```
/port <ruta-del-proyecto-destino>
```

`skillset-port` detecta el stack/módulos/docs/equipo del destino, entrevista lo que falte, escribe
`skills/PROJECT.md` (la fuente única de los valores del nuevo proyecto), reescribe cada `SKILL.md`
+ este README, y te deja un **checklist del trabajo residual** (rule-sets 🔴 a re-autorear, docs de
convenciones a crear). Es honesto: si un rule-set no se puede portar bien, lo marca como TEMPLATE
en vez de disfrazarlo.

### Camino manual (resumen)

1. **Modificá los directorios de referencia.** Apuntá las skills a las "docs de chequeo cruzado"
   del destino (su `docs/`, `CONTRIBUTING.md`, style guide, ADRs). Si el destino no tiene
   convenciones escritas, **creáselas primero** — las skills 🔴 sin esas docs alucinan reglas.
2. **Cambiá las variables** de la tabla de arriba en cada `SKILL.md` (nombre, autoridad de calidad,
   rutas, módulos, equipo, locales, convención de sprint).
3. **Re-autoreá los rule-sets 🔴** si el stack cambia: mapeá conceptos (XSS → escaping del motor de
   vistas del destino; ownership → su modelo de authz; "no `Mockito.verify`" → su política de
   testing; N+1 → su ORM).
4. **No toques** los frontmatter `model:`/`effort:` (los tiers de costo se mantienen) ni las 🟢.
5. **Actualizá este README** (header, stack, conteo, fuentes).

> Después de portar, `PROJECT.md` es el lugar para actualizar cuando cambien paths/equipo/stack —
> no vuelvas a hardcodear.

## Cómo funcionan

Cada skill es un `SKILL.md` con frontmatter (`name`, `description`, `model`, `effort`,
`argument-hint`, `allowed-tools`) + el prompt. Claude Code la carga cuando usás `/<nombre>` o uno
de sus aliases. Para modificar una skill, editá su `SKILL.md`.

## Mantenimiento

Cuando el corrector publique nuevas indicaciones o cambien las convenciones del equipo:
1. Actualizar `docs/` (sobre todo `docs/correcciones-cohorte.md`) y/o `PAW_Directives.md`.
2. Ingerir las nuevas indicaciones al wiki (`wiki/sources/`).
3. Revisar si alguna skill necesita ajuste — muchas referencian `docs/` y el wiki dinámicamente,
   así que muchos cambios propagan solos.

## Tips

1. **Sé específico** al invocar: `/plan sistema de reviews con moderación` > `/plan reviews`.
2. **Encadená skills**: `/plan → /impl → /gp → /wiki`. No saltes al código sin plan en features no triviales.
3. **Antes de entregar**: `/xss → /ownership → /i18n → /deliver → /corrector`.
4. **El `docs/` y el wiki mandan**: si una skill contradice las fuentes canónicas, ganan las fuentes.

---

**Stack:** Spring MVC 5.3.33 · Java 21 · Maven multi-módulo · JPA/Hibernate · PostgreSQL (prod, Flyway) · HSQLDB (test) · JUnit 5 · Mockito
**Etapa actual:** entrega final — migración REST + SPA (ver `0_Plans/rest-migration/final/README.md`)
**Skills totales:** 17 activas (+4 archivadas en `.claude/skills-archived/`)
**Hooks del proyecto** (`.claude/hooks/`, registrados en `settings.local.json`): `skill-autolaunch` (sugerencias con guards anti-falso-positivo) · `i18n-parity-posttool` (paridad de bundles al editarlos) · `commit-gate` (corre `paw_checks.py` antes de todo `git commit`; bypass `PAW_SKIP_SMOKE=1`) · `db-server-guard` (bloquea `psql`/`jetty:run` — el usuario ejecuta; bypass `PAW_ALLOW_DB=1`). Script compartido: `.claude/scripts/paw_checks.py`.
