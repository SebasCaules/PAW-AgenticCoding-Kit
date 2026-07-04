#!/usr/bin/env python3
"""Genera los 4 diagramas del README como SVG estáticos (claro y oscuro) con la
estética de la página del kit (index.html, sistema "Technical Split" / StudyVaults):
superficies marrón/crema, celeste #92cff2 como primario, coral #f47c59 como acento,
serif Newsreader/Georgia para prosa y JetBrains Mono para comandos y paths.

Los SVG se referencian desde el README con <picture> (prefers-color-scheme).
Correr: python3 tools/gen_diagrams.py  →  escribe en assets/.

Color: contraste ≥3:1 sobre ambas superficies verificado con el validador de la
skill dataviz; la identidad de grupo nunca depende solo del color (cada grupo
lleva etiqueta de texto y forma propia). En claro los hues van mezclados con el
marrón, igual que hace la propia página (--primary-line, --accent-text).
"""
import pathlib

SERIF = "Newsreader, Georgia, &#39;Times New Roman&#39;, serif"
MONO = "&#39;JetBrains Mono&#39;, ui-monospace, SFMono-Regular, Menlo, monospace"

MODES = {
    "light": dict(
        surface="#f6f5f3", node="#ffffff", node_border="#e5e2e1",
        ink="#241208", ink2="#7c716b", muted="#8a7f78",
        kit="#617a89", vos="#a5543a", fuente="#a28257", aqua="#2d8a7b",
        good="#3f8a5a", crit="#8f5d53",
        kit_tint="rgba(97,122,137,0.08)", vos_tint="rgba(165,84,58,0.06)",
        fuente_tint="rgba(162,130,87,0.08)", aqua_tint="rgba(45,138,123,0.07)",
        naranja="#a5543a", naranja_tint="rgba(165,84,58,0.06)",
        good_tint="rgba(63,138,90,0.08)", crit_tint="rgba(143,93,83,0.07)",
        ordinal=["#77a0b8", "#617a89", "#4b545a"],
        ordinal_tint=["rgba(97,122,137,0.05)", "rgba(97,122,137,0.09)", "rgba(97,122,137,0.14)"],
    ),
    "dark": dict(
        surface="#382519", node="#301d12", node_border="rgba(255,255,255,0.14)",
        ink="#ffffff", ink2="#a1a1aa", muted="#a1a1aa",
        kit="#92cff2", vos="#f47c59", fuente="#d8b279", aqua="#2f9f8f",
        good="#46a86e", crit="#d68f85",
        kit_tint="rgba(146,207,242,0.10)", vos_tint="rgba(244,124,89,0.10)",
        fuente_tint="rgba(216,178,121,0.08)", aqua_tint="rgba(47,159,143,0.10)",
        naranja="#f47c59", naranja_tint="rgba(244,124,89,0.10)",
        good_tint="rgba(70,168,110,0.12)", crit_tint="rgba(214,143,133,0.12)",
        ordinal=["#c9e7f9", "#92cff2", "#7393a6"],
        ordinal_tint=["rgba(146,207,242,0.07)", "rgba(146,207,242,0.12)", "rgba(146,207,242,0.18)"],
    ),
}


class Svg:
    def __init__(self, p, w, h):
        self.p, self.w, self.h = p, w, h
        self.s = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" font-family="{SERIF}">',
            f'<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M 0 1 L 9 5 L 0 9 z" fill="{p["muted"]}"/></marker></defs>',
            f'<rect x="0" y="0" width="{w}" height="{h}" rx="12" fill="{p["surface"]}"/>',
        ]

    def group(self, x, y, w, h, hue, tint, title, subtitle=None):
        p = self.p
        self.s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{tint}" stroke="{hue}" stroke-width="1.5"/>')
        self.s.append(f'<rect x="{x+16}" y="{y+15}" width="9" height="9" rx="2" fill="{hue}"/>')
        t = (f'<text x="{x+32}" y="{y+24}" font-size="10.5" font-weight="700" letter-spacing="2" font-family="{MONO}" fill="{p["ink2"]}">{title}'
             + (f'<tspan font-weight="400" letter-spacing="0.3" font-family="{SERIF}" font-style="italic" font-size="12" fill="{p["muted"]}">&#160;&#160;{subtitle}</tspan>' if subtitle else '')
             + '</text>')
        self.s.append(t)

    def node(self, x, y, w, h, lines, border=None, bw="1", tint=None, spacing=17):
        p = self.p
        self.s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="{tint or p["node"]}" stroke="{border or p["node_border"]}" stroke-width="{bw}"/>')
        cx = x + w / 2
        n = len(lines)
        for i, (txt, kind) in enumerate(lines):
            ly = y + h / 2 + (i - (n - 1) / 2) * spacing + 4
            if kind == "b":
                self.s.append(f'<text x="{cx}" y="{ly}" font-size="14" font-weight="600" text-anchor="middle" fill="{p["ink"]}">{txt}</text>')
            elif kind == "b2":
                self.s.append(f'<text x="{cx}" y="{ly}" font-size="12.5" font-weight="600" text-anchor="middle" fill="{p["ink"]}">{txt}</text>')
            elif kind == "m":
                self.s.append(f'<text x="{cx}" y="{ly}" font-size="12" font-weight="600" text-anchor="middle" font-family="{MONO}" fill="{p["ink"]}">{txt}</text>')
            elif kind == "m2":
                self.s.append(f'<text x="{cx}" y="{ly}" font-size="10.5" text-anchor="middle" font-family="{MONO}" fill="{p["ink2"]}">{txt}</text>')
            elif kind == "i":
                self.s.append(f'<text x="{cx}" y="{ly}" font-size="12" font-style="italic" text-anchor="middle" fill="{p["ink2"]}">{txt}</text>')
            else:
                self.s.append(f'<text x="{cx}" y="{ly}" font-size="12" text-anchor="middle" fill="{p["ink2"]}">{txt}</text>')

    def pill(self, x, y, w, h, txt, hue, mono=False):
        p = self.p
        f = f' font-family="{MONO}" font-size="12"' if mono else ' font-size="13"'
        self.s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h/2}" fill="{p["node"]}" stroke="{hue}" stroke-width="1.2"/>')
        self.s.append(f'<text x="{x+w/2}" y="{y+h/2+4.5}"{f} font-weight="500" text-anchor="middle" fill="{p["ink"]}">{txt}</text>')

    def arrow(self, x1, y1, x2, y2, dashed=False):
        d = ' stroke-dasharray="5 5"' if dashed else ''
        self.s.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{self.p["muted"]}" stroke-width="1.5"{d} marker-end="url(#arr)"/>')

    def path(self, d, dashed=False, arrow=True):
        dd = ' stroke-dasharray="5 5"' if dashed else ''
        m = ' marker-end="url(#arr)"' if arrow else ''
        self.s.append(f'<path d="{d}" fill="none" stroke="{self.p["muted"]}" stroke-width="1.5"{dd}{m}/>')

    def label(self, x, y, txt, anchor="middle", mono=False, size=11):
        f = f' font-family="{MONO}" font-size="{size-1}"' if mono else f' font-style="italic" font-size="{size}"'
        halo = f' stroke="{self.p["surface"]}" stroke-width="5" paint-order="stroke" stroke-linejoin="round"'
        self.s.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}"{f}{halo} fill="{self.p["muted"]}">{txt}</text>')

    def outcome(self, x, y, w, h, hue, tint, icon, lines):
        p = self.p
        self.s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{min(h/2, 24)}" fill="{tint}" stroke="{hue}" stroke-width="1.2"/>')
        cy = y + h / 2
        self.s.append(f'<circle cx="{x+26}" cy="{cy}" r="9" fill="none" stroke="{hue}" stroke-width="1.5"/>')
        if icon == "check":
            self.s.append(f'<path d="M {x+21.5} {cy} l 3 3.2 l 6 -6.4" fill="none" stroke="{hue}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>')
        else:
            self.s.append(f'<path d="M {x+22.5} {cy-3.5} l 7 7 M {x+29.5} {cy-3.5} l -7 7" fill="none" stroke="{hue}" stroke-width="2" stroke-linecap="round"/>')
        tx = x + 44
        n = len(lines)
        for i, (txt, kind) in enumerate(lines):
            ly = cy + (i - (n - 1) / 2) * 17 + 4
            if kind == "b":
                self.s.append(f'<text x="{tx}" y="{ly}" font-size="13" font-weight="600" fill="{p["ink"]}">{txt}</text>')
            else:
                self.s.append(f'<text x="{tx}" y="{ly}" font-size="11.5" fill="{p["ink2"]}">{txt}</text>')

    def render(self):
        return "\n".join(self.s + ["</svg>"])


def overview(p):
    v = Svg(p, 1160, 548)
    v.group(368, 24, 456, 118, p["fuente"], p["fuente_tint"], "FUENTE DE VERDAD")
    v.node(384, 56, 204, 68, [("docs/", "m"), ("convenciones de la cátedra", "n")])
    v.node(604, 56, 204, 68, [("ETAPA ACTUAL — CLAUDE.md", "m2"), ("JDBC → JPA → SPA+REST", "n")])
    v.group(328, 210, 520, 310, p["kit"], p["kit_tint"], "EL KIT", "vive en .claude/ de tu repo")
    v.node(352, 262, 204, 64, [("skill-autolaunch", "m"), ("sugiere la skill correcta", "i")])
    v.node(616, 250, 208, 88, [("18 skills", "b"), ("/plan · /impl · /gp · /deliver", "m2"), ("/corrector · /jdbc-to-jpa …", "m2")])
    v.node(352, 414, 204, 64, [("commit-gate", "m"), ("ningún commit sin checks", "i")])
    v.node(616, 414, 208, 64, [("paw_checks.py", "m"), ("i18n · Flyway · JSTL", "n")], border=p["aqua"], bw="1.5")
    v.arrow(556, 294, 610, 294)
    v.arrow(556, 446, 610, 446)
    v.group(24, 240, 244, 260, p["vos"], p["vos_tint"], "VOS")
    v.pill(44, 272, 204, 44, "escribís un prompt", p["vos"])
    v.pill(44, 424, 204, 44, "git commit", p["vos"], mono=True)
    v.arrow(248, 294, 346, 294)
    v.arrow(248, 446, 346, 446)
    v.path("M 486 124 C 486 187, 668 181, 668 244", dashed=True)
    v.path("M 706 124 C 706 187, 756 181, 756 244", dashed=True)
    v.label(536, 196, "las skills leen", anchor="end")
    v.label(776, 196, "calibra qué exigir", anchor="start")
    v.outcome(872, 268, 264, 52, p["good"], p["good_tint"], "check", [("código según las convenciones", "b")])
    v.outcome(872, 394, 264, 44, p["good"], p["good_tint"], "check", [("commit pasa", "b")])
    v.outcome(872, 458, 264, 56, p["crit"], p["crit_tint"], "cross", [("commit bloqueado", "b"), ("arreglás y reintentás", "n")])
    v.arrow(824, 294, 866, 294)
    v.arrow(824, 440, 866, 418)
    v.arrow(824, 452, 866, 482)
    return v.render()


def dia_a_dia(p):
    v = Svg(p, 1240, 224)
    v.pill(24, 70, 148, 44, "feature nueva", p["vos"])
    v.arrow(172, 92, 202, 92)
    v.node(208, 62, 142, 60, [("/plan", "m"), ("plan por fases", "i")])
    v.arrow(350, 92, 380, 92)
    v.node(386, 62, 142, 60, [("/impl", "m"), ("código fase a fase", "i")])
    v.arrow(528, 92, 558, 92)
    v.node(564, 62, 142, 60, [("/gp", "m"), ("reglas del corrector", "i")])
    v.arrow(706, 92, 736, 92)
    v.pill(742, 70, 118, 44, "git commit", p["vos"], mono=True)
    v.arrow(860, 92, 890, 92)
    v.node(896, 62, 152, 60, [("commit-gate", "m"), ("paw_checks.py", "m2")], border=p["aqua"], bw="1.5")
    v.arrow(1048, 92, 1078, 92)
    v.label(1063, 80, "OK", size=10.5)
    v.outcome(1084, 66, 132, 52, p["good"], p["good_tint"], "check", [("commit pasa", "b")])
    v.path("M 972 122 C 972 176, 940 176, 850 176 L 680 176 C 650 176, 635 168, 635 132")
    v.label(800, 168, "falla")
    return v.render()


def etapas(p):
    v = Svg(p, 1160, 190)
    cards = [
        (24, 0, [("Entrega 1 — Spring JDBC", "b2"), ("JdbcTemplate · RowMapper", "m2"), ("modelos inmutables", "n")]),
        (428, 1, [("Entrega 2 — JPA / Hibernate", "b2"), ("entidades · EntityManager", "m2"), ("las 9 trampas TP2", "n")]),
        (832, 2, [("Entrega Final — API REST + SPA", "b2"), ("Jersey · JWT · DTOs con links", "m2"), ("frontend aparte", "n")]),
    ]
    for x, i, lines in cards:
        v.node(x, 36, 276, 118, lines, border=p["ordinal"][i], bw="1.5", tint=p["ordinal_tint"][i], spacing=19)
    v.arrow(304, 95, 422, 95)
    v.label(364, 64, "/jdbc-to-jpa", mono=True, size=10.5)
    v.label(364, 80, "un agregado por vez", size=10.5)
    v.arrow(708, 95, 826, 95)
    v.label(768, 64, "contrato REST primero", size=10.5)
    v.label(768, 80, "backend por olas ⇄ SPA", size=10.5)
    return v.render()


def export(p):
    v = Svg(p, 1160, 342)
    v.node(24, 126, 236, 90, [("PAW-AgenticCoding-Kit", "b2"), ("nativo Claude Code", "i")], border=p["kit"], bw="1.5", tint=p["kit_tint"])
    ky = 171
    targets = [
        (54, "--target codex", [("AGENTS.md", "m"), (".codex/prompts/*.md", "m2")], p["naranja"], p["naranja_tint"], False),
        (132, "--target gemini", [("GEMINI.md", "m"), (".gemini/commands/paw/*.toml", "m2")], p["naranja"], p["naranja_tint"], False),
        (210, "--target agents", [("AGENTS.md genérico + prompts/*.md", "m"), ("Cursor · Windsurf · aider", "n")], p["naranja"], p["naranja_tint"], False),
        (288, "siempre", [("tools/paw_checks.py", "m"), ("+ pre-commit hook de git", "n")], p["aqua"], p["aqua_tint"], True),
    ]
    for cy, lbl, lines, hue, tint, dashed in targets:
        v.node(620, cy - 30, 516, 60, lines, border=hue, bw="1.5", tint=tint)
        v.path(f"M 260 {ky} C 400 {ky}, 470 {cy}, 614 {cy}", dashed=dashed)
        v.label(437, (ky + cy) / 2 - 8, lbl, mono=not dashed)
    return v.render()


DIAGRAMS = {
    "kit-overview": overview,
    "dia-a-dia": dia_a_dia,
    "etapas": etapas,
    "export": export,
}

if __name__ == "__main__":
    out = pathlib.Path(__file__).resolve().parent.parent / "assets"
    out.mkdir(exist_ok=True)
    for name, fn in DIAGRAMS.items():
        for mode, p in MODES.items():
            svg = fn(p)
            (out / f"{name}-{mode}.svg").write_text(svg)
            print(f"{name}-{mode}.svg ({len(svg)} bytes)")
