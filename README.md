# paw-claude-kit

**Tooling de agentic coding para cursar PAW (Proyecto de Aplicaciones Web · ITBA)** — 18 skills, 4 hooks, 1 script de checks determinísticos, las convenciones de la cátedra en `docs/`, guías por **etapa de la cursada** (JDBC → migración → JPA) y un **exportador a otros agentes** (Codex, Gemini CLI, AGENTS.md genérico). Nativo de Claude Code, instalable con un comando.

Nació del proyecto del **Grupo 10 (2026-1C, "Rent The Slopes")**: después de una meta-auditoría de ~113 sesiones de Claude Code se detectaron los 12 puntos de fricción más caros de la cursada (keys i18n que rompen en runtime, migraciones Flyway duplicadas post-merge, iteración visual a ciegas, auditorías que re-flagean falsos positivos, "tests verdes ≠ la app anda"...) y se construyó este kit para eliminarlos. Todo lo que hay acá está batalla-probado sobre un TP real de la materia.

## Requisitos

- [Claude Code](https://claude.com/claude-code) (CLI o app).
- `python3` (los hooks y el script de checks son stdlib puro, sin dependencias).
- Un proyecto PAW con la estructura estándar de la cátedra: Maven multi-módulo (`models` / `persistence-contracts` / `persistence` / `service-contracts` / `services` / `webapp`), Spring MVC + JSP, PostgreSQL + Flyway, HSQLDB para tests, i18n en `webapp/src/main/resources/i18n/`.

## Instalación

```bash
git clone <este-repo> paw-claude-kit
cd paw-claude-kit
./install.sh /ruta/a/tu/repo-paw              # tooling
./install.sh /ruta/a/tu/repo-paw --with-docs  # tooling + convenciones en docs/
```

El instalador copia `claude/{skills,hooks,scripts}` a `<tu-repo>/.claude/` y mergea [`settings-fragment.json`](settings-fragment.json) en tu `settings.local.json` sin pisar lo que ya tengas. Después **cerrá y volvé a abrir Claude Code** en el repo — los hooks se cargan al arrancar la sesión.

<details>
<summary>Alternativa: que lo instale tu Claude (sin correr el script vos)</summary>

Pegale esto a Claude Code parado en tu clon del proyecto:

```
Instalá el tooling de Claude Code desde <ruta>/paw-claude-kit:
1) Copiá el contenido de claude/ (skills/, hooks/, scripts/) adentro de .claude/ de este repo.
2) Mergeá settings-fragment.json dentro de mi .claude/settings.local.json: el bloque "hooks"
   completo, y sumá a "permissions.allow" lo que no tenga — más mis permisos de Edit/Write
   para la ruta de ESTE clon.
3) Verificá: python3 .claude/scripts/paw_checks.py all debe dar i18n/flyway/jsp OK y los
   4 hooks deben parsear.
4) Leé el README del kit y explicame en una línea por elemento qué es cada cosa y cuándo
   la uso. Aclarame que los hooks recién se activan en la PRÓXIMA sesión.
```
</details>

## Etapas de la cursada: JDBC (Entrega 1) → JPA (Entrega 2)

PAW arranca con **Spring JDBC** y recién en la segunda entrega migra a **JPA/Hibernate** — y las
reglas de cada etapa son distintas (auditar un TP1 con reglas de Hibernate genera puro falso
positivo). El kit es etapa-aware: declarás en tu `CLAUDE.md` la línea
**`ETAPA ACTUAL: JDBC (Entrega 1)`** (o `JPA (Entrega 2+)`) y las skills de planificación y
auditoría calibran solas qué exigir.

| Doc | Qué cubre |
|---|---|
| [`entrega-1-jdbc.md`](etapas/entrega-1-jdbc.md) | Reglas de la etapa JDBC (RowMapper estático, SimpleJdbcInsert, modelos inmutables, escape de LIKE) + qué reglas JPA NO aplican todavía + snippet de declaración |
| [`migracion-jdbc-a-jpa.md`](etapas/migracion-jdbc-a-jpa.md) | Playbook de la migración: fase 0 de infra, orden por agregado (hojas primero), checklist por DAO, errores clásicos. Se ejecuta con la skill [`jdbc-to-jpa`](claude/skills/jdbc-to-jpa/SKILL.md) |
| [`entrega-2-jpa.md`](etapas/entrega-2-jpa.md) | Las 9 trampas TP2 de Hibernate (EAGER cascada, modelo 1+1, `@Async`+lazy, `em.flush()`...) y la tabla de qué cambia respecto de la Entrega 1 |

Empezá por [`etapas/README.md`](etapas/README.md).

## Usarlo con otros agentes (Codex, Gemini CLI, Cursor...)

El kit es nativo de Claude Code, pero casi todo su valor es texto — un exportador lo traduce:

```bash
python3 tools/export.py --target codex  --out /ruta/a/tu/repo   # AGENTS.md + .codex/prompts/
python3 tools/export.py --target gemini --out /ruta/a/tu/repo   # GEMINI.md + .gemini/commands/paw/*.toml
python3 tools/export.py --target agents --out /ruta/a/tu/repo   # AGENTS.md genérico + prompts/
```

Las 18 skills se convierten en comandos/prompts del tool destino, las reglas operativas van a un
`AGENTS.md`/`GEMINI.md`, y el hook de commit se traduce a un **pre-commit hook de git**
(agente-agnóstico, corre los mismos checks). El mapeo completo — y qué se pierde en cada
traducción — está en [`PORTING.md`](PORTING.md).

## Qué incluye

### Hooks — automatizaciones que corren solas

| Archivo | Tipo de elemento | Para qué sirve |
|---|---|---|
| [`paw_checks.py`](claude/scripts/paw_checks.py) | Script (lo usan hooks y skills) | Checks determinísticos en segundos: paridad de keys i18n entre los 4 bundles (una key coja = `JasperException` en runtime), versiones Flyway duplicadas (la app no bootea), balance de tags JSTL en JSPs (500 que `mvn test` no atrapa) |
| [`skill-autolaunch.py`](claude/hooks/skill-autolaunch.py) | Hook `UserPromptSubmit` | Sugiere la skill correcta según tu prompt ("antes de entregar" → `/pre-delivery`, "se ve feo" → `/enhancer`, "auditá el proyecto" → `/general-audit`), con guards para no disparar en falso |
| [`i18n-parity-posttool.py`](claude/hooks/i18n-parity-posttool.py) | Hook `PostToolUse` | Si Claude edita un `messages*.properties` y deja keys cojas, se lo marca en el mismo turno |
| [`commit-gate.py`](claude/hooks/commit-gate.py) | Hook `PreToolUse` | Todo `git commit` corre los checks primero; si fallan, bloquea el commit con el detalle. Bypass: `PAW_SKIP_SMOKE=1 git commit ...` |
| [`db-server-guard.py`](claude/hooks/db-server-guard.py) | Hook `PreToolUse` | Impide que Claude corra `psql`/`pg_*`/`jetty:run` por su cuenta — lo obliga a darte el comando listo para copiar, con preview antes de lo destructivo. Bypass: `PAW_ALLOW_DB=1` |
| [`settings-fragment.json`](settings-fragment.json) | Config | Registra los 4 hooks + allowlist de permisos frecuentes (mvn, grep, git...) |

### Skills — comandos `/algo` para cada momento de la cursada

| Archivo | Tipo de elemento | Para qué sirve |
|---|---|---|
| [`planning`](claude/skills/planning/SKILL.md) | Skill (`/plan`) | Plan fase-a-fase de una feature (models → persistence JPA → services → validators → controllers → views → tests) |
| [`implementation`](claude/skills/implementation/SKILL.md) | Skill (`/impl`) | Ejecuta un plan fase por fase respetando las convenciones del curso |
| [`feature-engineering`](claude/skills/feature-engineering/SKILL.md) | Skill | Entrevista de descubrimiento: idea vaga → spec implementable |
| [`good-practice`](claude/skills/good-practice/SKILL.md) | Skill (`/gp`) | Chequeo de lo modificado contra las reglas del corrector (XSS, ownership, `Mockito.verify`, N+1, trampas Hibernate). Después de codear, antes de commitear |
| [`smoke`](claude/skills/smoke/SKILL.md) | Skill (`/smoke`) | Sanidad en <2 min: checks + test-compile. Solo reporta, no arregla |
| [`pre-delivery`](claude/skills/pre-delivery/SKILL.md) | Skill (`/deliver`) | Checklist completo de pre-entrega + build + tests; integra los chequeos de XSS y ownership |
| [`corrector-eyes`](claude/skills/corrector-eyes/SKILL.md) | Skill (`/corrector`) | Simula al corrector con tolerancia cero y estima puntos en riesgo. Stress-test final |
| [`forensic-audit`](claude/skills/forensic-audit/SKILL.md) | Skill (`/audit`) | Auditoría forense profunda con agentes paralelos por feature |
| [`general-audit`](claude/skills/general-audit/SKILL.md) | Skill (`/general`) | Auditoría en dos pasadas (vertical + horizontal) con dictamen |
| [`i18n-sync`](claude/skills/i18n-sync/SKILL.md) | Skill (`/i18n`) | Diff fino de bundles: keys sin definir, huérfanas, textos hardcodeados |
| [`design`](claude/skills/design/SKILL.md) | Skill (`/design`) | UI nueva o rediseño dentro del design system; verifica el renderizado antes de dar Done |
| [`enhancer`](claude/skills/enhancer/SKILL.md) | Skill (`/enhance`) | Retoque estético liviano de JSP/CSS sin tocar funcionalidad |
| [`frontend-analyzer`](claude/skills/frontend-analyzer/SKILL.md) | Skill | Análisis forense del diseño de una página local → spec de tokens/componentes |
| [`bug`](claude/skills/bug/SKILL.md) | Skill (`/bug`) | Ledger de bugs en `0_Plans/BUGS.md`: síntoma verbatim + intentos fallidos; un bug se explica una sola vez |
| [`handoff`](claude/skills/handoff/SKILL.md) | Skill (`/handoff`) | Cierre de sesión reanudable: estado + prompt de reanudación auto-contenido (session limits, cambio de modelo) |
| [`jdbc-to-jpa`](claude/skills/jdbc-to-jpa/SKILL.md) | Skill (`/migrate`) | Migra la persistencia JDBC → JPA un agregado por vez (entidades, JpaDao, 1+1, tests con `em.flush()`, swap de bean) siguiendo `etapas/migracion-jdbc-a-jpa.md` |
| [`wiki-sync`](claude/skills/wiki-sync/SKILL.md) | Skill (`/wiki`) | Sincroniza un wiki de Obsidian con la codebase (opcional — ajustá la ruta del wiki en su SKILL.md) |
| [`skillset-port`](claude/skills/skillset-port/SKILL.md) | Skill (`/port`) | Adapta todo este set a OTRO proyecto/stack (detecta, entrevista, reescribe) |
| [`README.md`](claude/skills/README.md) | Doc | Índice del set: categorías, workflows, guía de portabilidad |

### Docs — convenciones de la cátedra ([`docs/`](docs/))

15 documentos que las skills de auditoría usan como fuente de verdad y que valen oro desde el sprint 1: [`testing.md`](docs/testing.md) (las reglas de tests que la cátedra corrige de verdad), [`anti-patterns.md`](docs/anti-patterns.md) (checklist negativo consolidado de 27+ grupos), [`correcciones-cohorte.md`](docs/correcciones-cohorte.md) (todo lo que descontó el corrector en TP1+TP2), [`security.md`](docs/security.md), [`views-and-jsp.md`](docs/views-and-jsp.md), [`pagination-and-search.md`](docs/pagination-and-search.md), y más. Copialos a tu repo con `--with-docs` y **adaptá lo específico del Grupo 10** (nombres de clases, notas, findings propios) a tu proyecto — importalos desde tu `CLAUDE.md` con `@docs/<archivo>.md`.

## Flujo de trabajo recomendado

```
Arranque de cursada:  declarar "ETAPA ACTUAL: JDBC (Entrega 1)" en CLAUDE.md (ver etapas/)
Feature nueva:        /plan → /impl → /gp → commit (el gate corre solo)
Llega la Entrega 2:   /jdbc-to-jpa fase-0 → /jdbc-to-jpa <agregado> (uno por vez) → ETAPA: JPA
Ajuste visual:        /enhance → (verificación renderizada automática) → /i18n
Chequeo rápido:       /smoke
Antes de entregar:    /smoke → /deliver → /corrector
Reportar un bug:      /bug <síntoma>          (y Claude consulta el ledger antes de re-diagnosticar)
Te quedaste sin tokens: /handoff              (prompt de reanudación para la próxima sesión)
```

## Cómo funciona por dentro

- **Los hooks se registran en `settings.local.json`** y corren fuera del modelo: son python stdlib, determinísticos, y fallan en silencio (jamás bloquean un prompt por un bug propio). Se cargan **al arrancar la sesión**.
- **Escapes explícitos** cuando de verdad hace falta saltear un guard: `PAW_SKIP_SMOKE=1` (commitear con checks rotos) y `PAW_ALLOW_DB=1` (autorizar a Claude a tocar la BD dev).
- **Las skills leen `docs/` de tu repo** como fuente canónica — cuanto mejor mantengas esas convenciones, mejor auditan.
- Piezas complementarias que conviene crear en tu repo (las skills las referencian): `0_Plans/` para planes, `0_Plans/BUGS.md` (lo crea `/bug` al primer uso) y `0_Plans/audits/ADJUDICACIONES.md` (registro de falsos positivos ya cerrados, para que las auditorías no re-litiguen).

## Adaptarlo a otro proyecto / otra cátedra

El set está pensado para portarse: corré `/port <ruta-del-proyecto-destino>` y la skill detecta el stack, entrevista lo que falte y reescribe rutas y reglas. La guía manual (qué es project-specific y qué no) está en [`claude/skills/README.md`](claude/skills/README.md) §Portabilidad.

## Advertencias honestas

- `docs/correcciones-cohorte.md` incluye feedback y notas **del Grupo 10 (2026-1C)** — es el ejemplo más completo de "qué castiga el corrector", pero revisalo antes de difundirlo fuera de tu grupo.
- `wiki-sync` y algunas auditorías citan un wiki de Obsidian externo; sin ese wiki degradan con gracia usando solo `docs/`.
- `frontend-analyzer` se usa **solo contra localhost** — nunca contra el deploy del pawserver de la cátedra.
- El `paw_checks.py` asume la estructura Maven estándar; si tu proyecto recién arranca y no tiene `webapp/`/`persistence/`, los checks avisan en vez de romper.

---

*Grupo 10 · PAW 2026-1C · ITBA. Construido y validado durante la cursada real; el análisis de origen (meta-auditoría de sesiones, plan y ejecución) vive en el repo del proyecto bajo `0_Plans/claude-harness/`.*
