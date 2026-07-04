# PORTING.md — llevar el kit a otros agentic coding tools

El kit está escrito para **Claude Code**, pero casi todo su valor es texto (prompts + reglas +
un script python). Esta guía documenta el mapeo conceptual y el exportador automático.

## Export automático

```bash
python3 tools/export.py --target codex  --out /ruta/a/tu/repo   # OpenAI Codex CLI
python3 tools/export.py --target gemini --out /ruta/a/tu/repo   # Google Gemini CLI
python3 tools/export.py --target agents --out /ruta/a/tu/repo   # genérico (Cursor, Windsurf, aider...)
```

Cada target genera en el repo destino:

| Pieza del kit (Claude Code) | Codex CLI | Gemini CLI | Genérico |
|---|---|---|---|
| Skills (`claude/skills/*/SKILL.md`) | `.codex/prompts/*.md` (copiar a `~/.codex/prompts/`, se invocan `/nombre`) | `.gemini/commands/paw/*.toml` (se invocan `/paw:nombre`) | `prompts/*.md` (registrar como comandos custom o pegar a mano) |
| Reglas operativas (`CLAUDE.md` §Reglas) | `AGENTS.md` | `GEMINI.md` | `AGENTS.md` |
| `paw_checks.py` | `tools/paw_checks.py` | `tools/paw_checks.py` | `tools/paw_checks.py` |
| Hook `commit-gate` | `tools/git-hooks/pre-commit` (git nativo) | ídem | ídem |

## Mapeo conceptual (y qué se pierde)

| Concepto Claude Code | Traducción | Fidelidad |
|---|---|---|
| **Skill** (`SKILL.md` + frontmatter) | Prompt/comando custom del tool destino. El cuerpo es markdown puro y viaja intacto; `$ARGUMENTS` se convierte al placeholder del tool (`{{args}}` en Gemini). Se pierde el frontmatter `model:`/`effort:`/`allowed-tools:` (elegí el modelo en el tool destino). | Alta |
| **Hook `PreToolUse` commit-gate** | **Pre-commit hook de git** (`tools/git-hooks/pre-commit`): corre `paw_checks.py all` antes de cada commit, agente-agnóstico. Activar con `git config core.hooksPath tools/git-hooks`. Bypass: `git commit --no-verify`. | Alta (incluso mejor: aplica también a commits humanos) |
| **Hook `PostToolUse` i18n-parity** | No hay lifecycle equivalente → se traduce a (a) regla en AGENTS.md ("toda key en todos los bundles") + (b) el pre-commit que la fuerza al commitear. Se pierde el aviso *en el mismo turno*. | Media |
| **Hook `PreToolUse` db-server-guard** | Regla dura en AGENTS.md ("nunca corras psql/jetty; emití el comando"). Se pierde el bloqueo mecánico — queda a disciplina del modelo. En tools con allowlist/sandbox de comandos (Codex `approval_policy`, Gemini `excludeTools`), agregá `psql`/`jetty:run` a los bloqueados. | Media |
| **Hook `UserPromptSubmit` skill-autolaunch** | Sin equivalente (ningún tool inyecta contexto por prompt del usuario). El índice de comandos en AGENTS.md cumple el rol de descubrimiento. | Baja |
| **`settings.local.json` permissions** | Config nativa del tool: Codex `~/.codex/config.toml` (`approval_policy`, `sandbox_mode`), Gemini `.gemini/settings.json` (`coreTools`/`excludeTools`). No se auto-genera — ver notas abajo. | Manual |
| **Memoria / `0_Plans/` / `docs/`** | Son archivos del repo — funcionan igual en cualquier tool. | Total |

## Notas por tool

### Codex CLI
- Lee `AGENTS.md` automáticamente (repo y `~/.codex/AGENTS.md` global).
- Los prompts custom viven en `~/.codex/prompts/*.md` (global, no por-repo): el export los deja
  en `.codex/prompts/` del repo para versionarlos; copialos con
  `mkdir -p ~/.codex/prompts && cp .codex/prompts/*.md ~/.codex/prompts/`.
- Equivalente de permisos: `approval_policy` + `sandbox_mode` en `~/.codex/config.toml`.

### Gemini CLI
- Lee `GEMINI.md` automáticamente (se puede renombrar a AGENTS.md vía `contextFileName` en
  `.gemini/settings.json`).
- Los comandos TOML del export son por-repo (`.gemini/commands/paw/…`) y se invocan
  namespaceados: `/paw:smoke`, `/paw:good-practice`. El `prompt` usa `{{args}}`.
- Equivalente de permisos: `coreTools`/`excludeTools` en `.gemini/settings.json`.

### Otros (Cursor, Windsurf, aider, ...)
- `--target agents` genera el `AGENTS.md` (estándar emergente que varios tools ya leen) y la
  biblioteca `prompts/`. En Cursor podés además convertir las reglas a `.cursor/rules/*.mdc`;
  en aider, pasá `AGENTS.md` como read-only file de contexto.

## Qué NO portar

- Los archivos `claude/hooks/*.py` en sí — dependen del protocolo de hooks de Claude Code
  (JSON por stdin, `hookSpecificOutput`). Su *comportamiento* ya está traducido arriba.
- `settings-fragment.json` — es formato de Claude Code.

## Después de exportar — checklist

1. `git config core.hooksPath tools/git-hooks` en el repo destino (activa el gate de commits).
2. Declarar la **etapa de la cursada** en el AGENTS.md/GEMINI.md generado (`ETAPA ACTUAL: JDBC (Entrega 1)` o `JPA (Entrega 2+)`) — ver [`etapas/`](etapas/README.md).
3. Copiar `docs/` del kit al repo (`./install.sh <repo> --with-docs` o a mano) — los prompts las citan.
4. Probar: `python3 tools/paw_checks.py all` y un comando (p. ej. `/smoke` o `/paw:smoke`).
