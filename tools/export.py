#!/usr/bin/env python3
"""
export.py — traduce el kit a otros agentic coding tools (Codex CLI, Gemini CLI, genérico AGENTS.md).

Uso:
    python3 tools/export.py --target codex  --out /ruta/a/tu/repo
    python3 tools/export.py --target gemini --out /ruta/a/tu/repo
    python3 tools/export.py --target agents --out /ruta/a/tu/repo   # genérico (Cursor, Windsurf, etc.)

Qué genera (ver PORTING.md para el mapeo conceptual completo):
- Las 18 skills → biblioteca de prompts en el formato del tool destino
  (Codex: .codex/prompts/*.md · Gemini: .gemini/commands/paw/*.toml · genérico: prompts/*.md).
- AGENTS.md (o GEMINI.md) con las reglas operativas + el índice de comandos.
- tools/paw_checks.py (los checks son python puro, corren igual en cualquier tool).
- tools/git-hooks/pre-commit — la traducción universal del hook commit-gate de Claude:
  un pre-commit hook de git que corre los checks sin depender del agente.

Los hooks de Claude Code NO tienen equivalente 1:1 en otros tools; sus comportamientos se
traducen a (a) reglas en AGENTS.md/GEMINI.md (que el agente lee siempre) y (b) el pre-commit
hook de git (determinístico, agente-agnóstico).
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
SKILLS_DIR = KIT / "claude" / "skills"
TEMPLATE = KIT / "tools" / "AGENTS.template.md"
CHECKS = KIT / "claude" / "scripts" / "paw_checks.py"
PRE_COMMIT = KIT / "tools" / "git-pre-commit"

TOOL_NOTES = {
    "codex": (
        "## Cómo invocar los comandos (Codex CLI)\n\n"
        "Los prompts viven en `.codex/prompts/` de este repo. Codex CLI los levanta desde\n"
        "`~/.codex/prompts/` (global): copialos o symlinkealos una vez:\n\n"
        "```bash\nmkdir -p ~/.codex/prompts && cp .codex/prompts/*.md ~/.codex/prompts/\n```\n\n"
        "Después se invocan como `/nombre` (ej. `/good-practice`, `/smoke`). El texto que\n"
        "escribas después del comando reemplaza `$ARGUMENTS` dentro del prompt."
    ),
    "gemini": (
        "## Cómo invocar los comandos (Gemini CLI)\n\n"
        "Los comandos viven en `.gemini/commands/paw/*.toml` de este repo — Gemini CLI los\n"
        "descubre solo y se invocan namespaceados: `/paw:good-practice`, `/paw:smoke`, etc.\n"
        "El texto después del comando reemplaza `{{args}}` dentro del prompt."
    ),
    "agents": (
        "## Cómo usar la biblioteca de prompts (tool genérico)\n\n"
        "Los prompts viven en `prompts/*.md`. Si tu tool soporta comandos custom, registralos\n"
        "apuntando a esos archivos; si no, pegá el contenido del prompt + tu pedido donde va\n"
        "`$ARGUMENTS`. Este AGENTS.md lo leen de fábrica Codex, Cursor, Windsurf y otros;\n"
        "para Gemini CLI usá `--target gemini` (genera GEMINI.md y comandos TOML nativos)."
    ),
}


def parse_skill(skill_dir):
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return None
    text = skill_md.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not m:
        return {"name": skill_dir.name, "description": "", "body": text.strip()}
    frontmatter, body = m.groups()

    def field(key):
        fm = re.search(rf"^{key}:\s*(.+)$", frontmatter, re.MULTILINE)
        return fm.group(1).strip() if fm else ""

    return {"name": skill_dir.name, "description": field("description"), "body": body.strip()}


def load_skills():
    skills = []
    for d in sorted(SKILLS_DIR.iterdir()):
        if d.is_dir():
            s = parse_skill(d)
            if s:
                skills.append(s)
    return skills


def short(desc, n=160):
    desc = desc.split(" Aliases:")[0].split(" Usar cuando")[0].split(" Use ")[0]
    return (desc[: n - 1] + "…") if len(desc) > n else desc


def build_agents_md(skills, target, cmd_prefix):
    template = TEMPLATE.read_text(encoding="utf-8")
    rows = "\n".join(
        f"| `{cmd_prefix}{s['name']}` | {short(s['description'])} |" for s in skills
    )
    return (
        template.replace("{{COMMANDS_TABLE}}", rows)
        .replace("{{TOOL_NOTES}}", TOOL_NOTES[target])
    )


def write_common(out, skills, target, cmd_prefix, main_doc_name):
    out.mkdir(parents=True, exist_ok=True)
    (out / main_doc_name).write_text(
        build_agents_md(skills, target, cmd_prefix), encoding="utf-8"
    )
    tools_dir = out / "tools"
    tools_dir.mkdir(exist_ok=True)
    shutil.copy2(CHECKS, tools_dir / "paw_checks.py")
    hooks_dir = tools_dir / "git-hooks"
    hooks_dir.mkdir(exist_ok=True)
    shutil.copy2(PRE_COMMIT, hooks_dir / "pre-commit")
    (hooks_dir / "pre-commit").chmod(0o755)


def export_codex(out, skills):
    write_common(out, skills, "codex", "/", "AGENTS.md")
    prompts = out / ".codex" / "prompts"
    prompts.mkdir(parents=True, exist_ok=True)
    for s in skills:
        content = f"# /{s['name']}\n\n> {s['description']}\n\n{s['body']}\n"
        (prompts / f"{s['name']}.md").write_text(content, encoding="utf-8")
    return [
        f"AGENTS.md + {len(skills)} prompts en .codex/prompts/",
        "Copiá los prompts a ~/.codex/prompts/ (Codex los levanta global): "
        "mkdir -p ~/.codex/prompts && cp .codex/prompts/*.md ~/.codex/prompts/",
    ]


def export_gemini(out, skills):
    write_common(out, skills, "gemini", "/paw:", "GEMINI.md")
    commands = out / ".gemini" / "commands" / "paw"
    commands.mkdir(parents=True, exist_ok=True)
    for s in skills:
        body = s["body"].replace("$ARGUMENTS", "{{args}}")
        # json.dumps con ensure_ascii=False produce strings escapadas válidas como TOML basic
        # string (los \uXXXX con surrogates de emoji NO son TOML válido — UTF-8 crudo sí).
        toml = (
            f"description = {json.dumps(short(s['description'], 200), ensure_ascii=False)}\n"
            f"prompt = {json.dumps(body, ensure_ascii=False)}\n"
        )
        (commands / f"{s['name']}.toml").write_text(toml, encoding="utf-8")
    return [f"GEMINI.md + {len(skills)} comandos en .gemini/commands/paw/ (se invocan /paw:<nombre>)"]


def export_agents(out, skills):
    write_common(out, skills, "agents", "prompts/", "AGENTS.md")
    prompts = out / "prompts"
    prompts.mkdir(exist_ok=True)
    for s in skills:
        content = f"# {s['name']}\n\n> {s['description']}\n\n{s['body']}\n"
        (prompts / f"{s['name']}.md").write_text(content, encoding="utf-8")
    return [f"AGENTS.md + {len(skills)} prompts genéricos en prompts/"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, choices=["codex", "gemini", "agents"])
    parser.add_argument("--out", required=True, help="repo destino (o carpeta de export)")
    args = parser.parse_args()

    skills = load_skills()
    if not skills:
        print(f"ERROR: no encontré skills en {SKILLS_DIR}", file=sys.stderr)
        return 1
    out = Path(args.out).expanduser().resolve()
    notes = {"codex": export_codex, "gemini": export_gemini, "agents": export_agents}[
        args.target
    ](out, skills)

    print(f"✔ Export '{args.target}' generado en {out}")
    for n in notes:
        print(f"  - {n}")
    print("  - tools/paw_checks.py + tools/git-hooks/pre-commit (checks agente-agnósticos)")
    print("  - Activá el pre-commit: git config core.hooksPath tools/git-hooks")
    print("  - Leé PORTING.md del kit para el mapeo completo y las limitaciones.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
