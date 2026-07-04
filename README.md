<div align="center">

# PAW-AgenticCoding-Kit

**Tooling de agentic coding para cursar PAW (Proyecto de Aplicaciones Web · ITBA).**

⚡ 18 skills · 🪝 4 hooks · 🐍 checks determinísticos · 📚 las convenciones de la cátedra<br/>
🧭 guías por etapa (JDBC → JPA → SPA+REST) · 🔁 exportador a otros agentes

*Nativo de Claude Code, instalable con un comando.*

</div>

> Nació del TP real del **Grupo 10 (2026-1C, "Rent The Slopes")**: una meta-auditoría de ~113
> sesiones de Claude Code detectó los 12 puntos de fricción más caros de la cursada — keys i18n
> que rompen en runtime, migraciones Flyway duplicadas post-merge, iteración visual a ciegas,
> auditorías que re-flagean falsos positivos, "tests verdes ≠ la app anda" — y el kit existe
> para eliminarlos. Todo lo que hay acá está batalla-probado sobre un TP real de la materia.

## Índice

- [El kit de un vistazo](#el-kit-de-un-vistazo)
- [Instalación](#instalación)
- [El día a día con el kit](#el-día-a-día-con-el-kit)
- [Etapas de la cursada](#etapas-de-la-cursada-jdbc--jpa--sparest)
- [Qué incluye](#qué-incluye) — [hooks](#hooks--corren-solos) · [skills](#skills--comandos-algo) · [docs](#docs--las-convenciones-de-la-cátedra)
- [Usarlo con otros agentes](#usarlo-con-otros-agentes-codex-gemini-cursor)
- [Cómo funciona por dentro](#cómo-funciona-por-dentro)
- [Adaptarlo a otro proyecto](#adaptarlo-a-otro-proyecto--otra-cátedra)
- [Advertencias honestas](#advertencias-honestas)

## El kit de un vistazo

```mermaid
flowchart LR
    subgraph VOS["👤&nbsp;&nbsp;Vos"]
        direction TB
        P(["✍️ escribís un prompt"])
        G(["📦 git commit"])
    end

    subgraph FUENTE["📚&nbsp;&nbsp;Fuente de verdad"]
        direction TB
        D["docs/<br/>convenciones de la cátedra"]
        E["ETAPA ACTUAL — CLAUDE.md<br/>JDBC → JPA → SPA+REST"]
    end

    subgraph KIT["🧰&nbsp;&nbsp;El kit — vive en .claude/ de tu repo"]
        direction LR
        SA["🪝 skill-autolaunch<br/><i>sugiere la skill correcta</i>"]
        SK["⚡ 18 skills<br/>/plan · /impl · /gp · /deliver<br/>/corrector · /jdbc-to-jpa …"]
        CG["🪝 commit-gate<br/><i>ningún commit sin checks</i>"]
        PC[["🐍 paw_checks.py<br/>i18n · Flyway · JSTL"]]
        SA --> SK
        CG --> PC
    end

    RES(["✅ código según<br/>las convenciones"])
    OK(["✔ commit pasa"])
    NO(["⛔ bloqueado con el detalle<br/>— arreglás y reintentás"])

    P --> SA
    G --> CG
    D -. "las skills leen" .-> SK
    E -. "calibra qué exigir" .-> SK
    SK --> RES
    PC -- "checks OK" --> OK
    PC -- "algo roto" --> NO

    classDef vos fill:#EDE9FE,stroke:#7C3AED,color:#312E81
    classDef kit fill:#DBEAFE,stroke:#2563EB,color:#1E3A8A
    classDef checks fill:#E0F2FE,stroke:#0284C7,color:#0C4A6E
    classDef fuente fill:#FEF3C7,stroke:#D97706,color:#78350F
    classDef ok fill:#DCFCE7,stroke:#16A34A,color:#14532D
    classDef bad fill:#FEE2E2,stroke:#DC2626,color:#7F1D1D
    class P,G vos
    class SA,SK,CG kit
    class PC checks
    class D,E fuente
    class RES,OK ok
    class NO bad
    style VOS fill:transparent,stroke:#7C3AED,stroke-dasharray:4 4
    style KIT fill:transparent,stroke:#2563EB
    style FUENTE fill:transparent,stroke:#D97706,stroke-dasharray:4 4
```

Dos caminos, un mismo kit: **tu prompt** entra por el hook que sugiere la skill correcta, y las
skills producen código calibrado por la fuente de verdad; **tu commit** entra por el gate, y solo
pasa si los checks determinísticos dan verde. Cuatro tipos de pieza, cada una con su rol:

| Pieza | Qué es | Cuándo actúa |
|---|---|---|
| **Hooks** | Automatizaciones python que corren *fuera* del modelo | Solas: al escribir un prompt, editar un bundle, commitear |
| **Skills** | Comandos `/algo` con las reglas de la cátedra encodeadas | Cuando las invocás (o el hook te las sugiere) |
| **Checks** | Script determinístico (`paw_checks.py`) | Lo usan hooks y skills; también corre a mano |
| **Docs + etapas** | Convenciones de la cátedra + reglas por entrega | Las skills las leen como fuente de verdad |

## Instalación

**Requisitos:** [Claude Code](https://claude.com/claude-code) · `python3` (hooks y checks son stdlib puro, sin dependencias) · un proyecto PAW con la estructura estándar de la cátedra (Maven multi-módulo `models`/`persistence-contracts`/`persistence`/`service-contracts`/`services`/`webapp`, Spring MVC + JSP, PostgreSQL + Flyway, HSQLDB para tests, i18n en `webapp/src/main/resources/i18n/`).

```bash
git clone <este-repo> paw-claude-kit
cd paw-claude-kit
./install.sh /ruta/a/tu/repo-paw              # tooling
./install.sh /ruta/a/tu/repo-paw --with-docs  # tooling + convenciones en docs/
```

El instalador copia `claude/{skills,hooks,scripts}` a `<tu-repo>/.claude/` y mergea
[`settings-fragment.json`](settings-fragment.json) en tu `settings.local.json`: **suma permisos
sin pisar los tuyos**; los hooks del kit reemplazan el evento homónimo (si ya tenías hooks
propios en ese evento, revisá el merge). Después **cerrá y volvé a abrir Claude Code** en el
repo — los hooks se cargan al arrancar la sesión.

<details>
<summary><strong>Alternativa: que lo instale tu Claude</strong> (sin correr el script vos)</summary>

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

## El día a día con el kit

```mermaid
flowchart LR
    ID(["💡 feature nueva"]) --> PL["/plan<br/><i>plan por fases</i>"]
    PL --> IM["/impl<br/><i>código fase a fase</i>"]
    IM --> GP["/gp<br/><i>reglas del corrector</i>"]
    GP --> CM(["📦 git commit"])
    CM --> GT{{"🪝 commit-gate<br/>paw_checks.py"}}
    GT -- "✅ checks OK" --> OK(["commit ✔"])
    GT -- "❌ falla" --> GP

    classDef vos fill:#EDE9FE,stroke:#7C3AED,color:#312E81
    classDef kit fill:#DBEAFE,stroke:#2563EB,color:#1E3A8A
    classDef gate fill:#E0F2FE,stroke:#0284C7,color:#0C4A6E
    classDef ok fill:#DCFCE7,stroke:#16A34A,color:#14532D
    class ID,CM vos
    class PL,IM,GP kit
    class GT gate
    class OK ok
```

| Momento | Qué hacés |
|---|---|
| Arranque de cursada | Declarar `ETAPA ACTUAL: JDBC (Entrega 1)` en tu `CLAUDE.md` (ver [`etapas/`](etapas/README.md)) |
| Feature nueva | `/plan` → `/impl` → `/gp` → commit (el gate corre solo) |
| Llega la Entrega 2 | `/jdbc-to-jpa fase-0` → `/jdbc-to-jpa <agregado>` (uno por vez) → `ETAPA: JPA` |
| Llega la Final | Contrato REST en `0_Plans/` → olas backend ⇄ SPA ([guía](etapas/entrega-final-spa-rest.md)) → `ETAPA: SPA+REST` |
| Ajuste visual | `/enhance` (la skill verifica el render antes de dar Done) → `/i18n` |
| Chequeo rápido | `/smoke` (sanidad en <2 min, solo reporta) |
| Antes de entregar | `/smoke` → `/deliver` → `/corrector` |
| Encontraste un bug | `/bug <síntoma>` — Claude consulta el ledger antes de re-diagnosticar |
| Te quedaste sin tokens | `/handoff` — prompt de reanudación para la próxima sesión |

## Etapas de la cursada: JDBC → JPA → SPA+REST

PAW cambia de reglas en cada entrega — auditar un TP1 con reglas de Hibernate, o una SPA con
reglas de JSP, genera puro falso positivo. El kit es **etapa-aware**: declarás la etapa en tu
`CLAUDE.md` y las skills de planificación y auditoría calibran solas qué exigir.

```mermaid
flowchart LR
    E1["📗 <b>Entrega 1 — Spring JDBC</b><br/>JdbcTemplate · RowMapper<br/>modelos inmutables"]
    E2["📘 <b>Entrega 2 — JPA / Hibernate</b><br/>entidades · EntityManager<br/>las 9 trampas TP2"]
    EF["📕 <b>Entrega Final — API REST + SPA</b><br/>Jersey · JWT · DTOs con links<br/>frontend aparte"]

    E1 == "/jdbc-to-jpa<br/>un agregado por vez" ==> E2
    E2 == "contrato REST primero,<br/>backend por olas ⇄ SPA" ==> EF

    classDef e1 fill:#DCFCE7,stroke:#16A34A,color:#14532D
    classDef e2 fill:#DBEAFE,stroke:#2563EB,color:#1E3A8A
    classDef ef fill:#FEE2E2,stroke:#DC2626,color:#7F1D1D
    class E1 e1
    class E2 e2
    class EF ef
```

```markdown
## Etapa de la cursada          ← esto va en el CLAUDE.md de tu repo
ETAPA ACTUAL: JDBC (Entrega 1)  ← o «JPA (Entrega 2+)» / «SPA+REST (Entrega Final)»
```

| Doc | Qué cubre |
|---|---|
| [`entrega-1-jdbc.md`](etapas/entrega-1-jdbc.md) | Reglas de la etapa JDBC (RowMapper estático, SimpleJdbcInsert, modelos inmutables, escape de LIKE) + qué reglas JPA **no** aplican todavía |
| [`migracion-jdbc-a-jpa.md`](etapas/migracion-jdbc-a-jpa.md) | Playbook de la migración: fase 0 de infra, orden por agregado (hojas primero), checklist por DAO. Se ejecuta con la skill [`jdbc-to-jpa`](claude/skills/jdbc-to-jpa/SKILL.md) |
| [`entrega-2-jpa.md`](etapas/entrega-2-jpa.md) | Las 9 trampas TP2 de Hibernate (EAGER cascada, modelo 1+1, `@Async`+lazy, `em.flush()`...) y qué cambia respecto de la Entrega 1 |
| [`entrega-final-spa-rest.md`](etapas/entrega-final-spa-rest.md) | JSP → API REST + SPA: el contrato primero, backend por olas (Jersey `/api/*`, JWT stateless, DTOs con links, paginación por headers, ExceptionMappers), SPA pantalla-por-pantalla, y la tabla "qué regla JSP muere y cuál la reemplaza" |

Empezá por [`etapas/README.md`](etapas/README.md).

## Qué incluye

### Hooks — corren solos

| Archivo | Evento | Para qué sirve |
|---|---|---|
| [`skill-autolaunch.py`](claude/hooks/skill-autolaunch.py) | `UserPromptSubmit` | Sugiere la skill correcta según tu prompt ("antes de entregar" → `/pre-delivery`, "se ve feo" → `/enhancer`, "auditá el proyecto" → `/general-audit`), con guards para no disparar en falso |
| [`i18n-parity-posttool.py`](claude/hooks/i18n-parity-posttool.py) | `PostToolUse` | Si Claude edita un `messages*.properties` y deja keys cojas, se lo marca **en el mismo turno** |
| [`commit-gate.py`](claude/hooks/commit-gate.py) | `PreToolUse` | Todo `git commit` corre los checks primero; si fallan, bloquea el commit con el detalle. Bypass: `PAW_SKIP_SMOKE=1 git commit ...` |
| [`db-server-guard.py`](claude/hooks/db-server-guard.py) | `PreToolUse` | Impide que Claude corra `psql`/`pg_*`/`jetty:run` por su cuenta — lo obliga a darte el comando listo para copiar, con preview antes de lo destructivo. Bypass: `PAW_ALLOW_DB=1` |

`commit-gate` e `i18n-parity` se apoyan en [`paw_checks.py`](claude/scripts/paw_checks.py), el
script de checks determinísticos que corre en segundos: **paridad de keys i18n** entre los 4
bundles (una key coja = `JasperException` en runtime), **versiones Flyway duplicadas** (la app
no bootea) y **balance de tags JSTL** en JSPs (500 que `mvn test` no atrapa).
[`settings-fragment.json`](settings-fragment.json) registra los 4 hooks + una allowlist de
permisos frecuentes (mvn, grep, git...).

### Skills — comandos `/algo`

<details open>
<summary><strong>Planificar y codear</strong></summary>

| Skill | Comando | Para qué sirve |
|---|---|---|
| [`feature-engineering`](claude/skills/feature-engineering/SKILL.md) | `/feature-engineering` | Entrevista de descubrimiento: idea vaga → spec implementable |
| [`planning`](claude/skills/planning/SKILL.md) | `/plan` | Plan fase-a-fase de una feature (models → persistence → services → validators → controllers → views → tests) |
| [`implementation`](claude/skills/implementation/SKILL.md) | `/impl` | Ejecuta un plan fase por fase respetando las convenciones del curso |
| [`jdbc-to-jpa`](claude/skills/jdbc-to-jpa/SKILL.md) | `/jdbc-to-jpa` (alias `/migrate`) | Migra la persistencia JDBC → JPA un agregado por vez (entidades, JpaDao, 1+1, tests con `em.flush()`, swap de bean) |
</details>

<details open>
<summary><strong>Calidad y auditorías</strong></summary>

| Skill | Comando | Para qué sirve |
|---|---|---|
| [`good-practice`](claude/skills/good-practice/SKILL.md) | `/gp` | Chequeo de lo modificado contra las reglas del corrector (XSS, ownership, `Mockito.verify`, N+1, trampas Hibernate). Después de codear, antes de commitear |
| [`smoke`](claude/skills/smoke/SKILL.md) | `/smoke` | Sanidad en <2 min: checks + test-compile. Solo reporta, no arregla |
| [`pre-delivery`](claude/skills/pre-delivery/SKILL.md) | `/deliver` | Checklist completo de pre-entrega + build + tests; integra los chequeos de XSS y ownership |
| [`corrector-eyes`](claude/skills/corrector-eyes/SKILL.md) | `/corrector` | Simula al corrector con tolerancia cero y estima puntos en riesgo. Stress-test final |
| [`forensic-audit`](claude/skills/forensic-audit/SKILL.md) | `/audit` | Auditoría forense profunda con agentes paralelos por feature |
| [`general-audit`](claude/skills/general-audit/SKILL.md) | `/general` | Auditoría en dos pasadas (vertical + horizontal) con dictamen |
| [`i18n-sync`](claude/skills/i18n-sync/SKILL.md) | `/i18n` | Diff fino de bundles: keys sin definir, huérfanas, textos hardcodeados |
</details>

<details open>
<summary><strong>Frontend / UI</strong></summary>

| Skill | Comando | Para qué sirve |
|---|---|---|
| [`design`](claude/skills/design/SKILL.md) | `/design` | UI nueva o rediseño dentro del design system; verifica el renderizado antes de dar Done |
| [`enhancer`](claude/skills/enhancer/SKILL.md) | `/enhance` | Retoque estético liviano de JSP/CSS sin tocar funcionalidad |
| [`frontend-analyzer`](claude/skills/frontend-analyzer/SKILL.md) | `/frontend-analyzer` | Análisis forense del diseño de una página local → spec de tokens/componentes |
</details>

<details open>
<summary><strong>Sesión, bugs y meta</strong></summary>

| Skill | Comando | Para qué sirve |
|---|---|---|
| [`bug`](claude/skills/bug/SKILL.md) | `/bug` | Ledger de bugs en `0_Plans/BUGS.md`: síntoma verbatim + intentos fallidos; un bug se explica una sola vez |
| [`handoff`](claude/skills/handoff/SKILL.md) | `/handoff` | Cierre de sesión reanudable: estado + prompt de reanudación auto-contenido (session limits, cambio de modelo) |
| [`wiki-sync`](claude/skills/wiki-sync/SKILL.md) | `/wiki` | Sincroniza un wiki de Obsidian con la codebase (opcional — ajustá la ruta del wiki en su SKILL.md) |
| [`skillset-port`](claude/skills/skillset-port/SKILL.md) | `/port` | Adapta todo este set a OTRO proyecto/stack (detecta, entrevista, reescribe) |
</details>

El índice completo del set — categorías, workflows, guía de portabilidad — está en
[`claude/skills/README.md`](claude/skills/README.md).

### Docs — las convenciones de la cátedra

15 documentos en [`docs/`](docs/) que las skills de auditoría usan como fuente de verdad y que
valen oro desde el sprint 1: [`testing.md`](docs/testing.md) (las reglas de tests que la cátedra
corrige de verdad), [`anti-patterns.md`](docs/anti-patterns.md) (checklist negativo consolidado
de 27+ grupos), [`correcciones-cohorte.md`](docs/correcciones-cohorte.md) (todo lo que descontó
el corrector en TP1+TP2), [`security.md`](docs/security.md), [`views-and-jsp.md`](docs/views-and-jsp.md),
[`pagination-and-search.md`](docs/pagination-and-search.md), y más.

Copialos a tu repo con `--with-docs` y **adaptá lo específico del Grupo 10** (nombres de clases,
notas, findings propios) a tu proyecto — importalos desde tu `CLAUDE.md` con `@docs/<archivo>.md`.

## Usarlo con otros agentes (Codex, Gemini, Cursor...)

El kit es nativo de Claude Code, pero casi todo su valor es texto — un exportador lo traduce:

```bash
python3 tools/export.py --target codex  --out /ruta/a/tu/repo   # AGENTS.md + .codex/prompts/
python3 tools/export.py --target gemini --out /ruta/a/tu/repo   # GEMINI.md + .gemini/commands/paw/*.toml
python3 tools/export.py --target agents --out /ruta/a/tu/repo   # AGENTS.md genérico + prompts/
```

```mermaid
flowchart LR
    K["🧰 <b>PAW-AgenticCoding-Kit</b><br/><i>nativo Claude Code</i>"]
    K == "--target codex" ==> CX["AGENTS.md<br/>.codex/prompts/*.md"]
    K == "--target gemini" ==> GM["GEMINI.md<br/>.gemini/commands/paw/*.toml"]
    K == "--target agents" ==> AG["AGENTS.md genérico + prompts/*.md<br/>Cursor · Windsurf · aider"]
    K -. "siempre" .-> PCM["tools/paw_checks.py<br/>+ pre-commit hook de git"]

    classDef kit fill:#DBEAFE,stroke:#2563EB,color:#1E3A8A
    classDef tgt fill:#FEF3C7,stroke:#D97706,color:#78350F
    classDef chk fill:#E0F2FE,stroke:#0284C7,color:#0C4A6E
    class K kit
    class CX,GM,AG tgt
    class PCM chk
```

Las 18 skills se convierten en comandos/prompts del tool destino, las reglas operativas van a un
`AGENTS.md`/`GEMINI.md`, y el hook de commit se traduce a un **pre-commit hook de git**
(agente-agnóstico, corre los mismos checks). El mapeo completo — y qué se pierde en cada
traducción — está en [`PORTING.md`](PORTING.md).

## Cómo funciona por dentro

- **Los hooks se registran en `settings.local.json`** y corren fuera del modelo: son python
  stdlib, determinísticos, y fallan en silencio (jamás bloquean un prompt por un bug propio).
  Se cargan **al arrancar la sesión**.
- **Escapes explícitos** cuando de verdad hace falta saltear un guard: `PAW_SKIP_SMOKE=1`
  (commitear con checks rotos) y `PAW_ALLOW_DB=1` (autorizar a Claude a tocar la BD dev).
- **Las skills leen `docs/` de tu repo** como fuente canónica — cuanto mejor mantengas esas
  convenciones, mejor auditan.
- Piezas complementarias que conviene crear en tu repo (las skills las referencian): `0_Plans/`
  para planes, `0_Plans/BUGS.md` (lo crea `/bug` al primer uso) y
  `0_Plans/audits/ADJUDICACIONES.md` (registro de falsos positivos ya cerrados, para que las
  auditorías no re-litiguen).

## Adaptarlo a otro proyecto / otra cátedra

El set está pensado para portarse: corré `/port <ruta-del-proyecto-destino>` y la skill detecta
el stack, entrevista lo que falte y reescribe rutas y reglas. La guía manual (qué es
project-specific y qué no) está en [`claude/skills/README.md`](claude/skills/README.md)
§Portabilidad.

## Advertencias honestas

- `docs/correcciones-cohorte.md` incluye feedback y notas **del Grupo 10 (2026-1C)** — es el
  ejemplo más completo de "qué castiga el corrector", pero revisalo antes de difundirlo fuera
  de tu grupo.
- `wiki-sync` y algunas auditorías citan un wiki de Obsidian externo; sin ese wiki degradan con
  gracia usando solo `docs/`.
- `frontend-analyzer` se usa **solo contra localhost** — nunca contra el deploy del pawserver
  de la cátedra.
- El `paw_checks.py` asume la estructura Maven estándar. En un proyecto que recién arranca,
  el check de Flyway se saltea con warning si no hay `db/migration/`, pero el de i18n falla
  si todavía no existe `webapp/` — el instalador te lo avisa al verificar.

---

*Grupo 10 · PAW 2026-1C · ITBA. Construido y validado durante la cursada real; el análisis de
origen (meta-auditoría de sesiones, plan y ejecución) vive en el repo del proyecto bajo
`0_Plans/claude-harness/`.*