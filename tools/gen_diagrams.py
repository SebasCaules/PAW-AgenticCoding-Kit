#!/usr/bin/env python3
"""Genera los 4 diagramas del README como SVG estáticos, tema claro y oscuro,
con una estética compartida (misma paleta validada, tipografía de sistema,
tarjetas con acento de grupo, texto siempre en tinta).

Paletas validadas con dataviz/scripts/validate_palette.js:
- categórica claro  #2a78d6 #eda100 #4a3aa7 #1baf7a #eb6834  → PASS
- categórica oscuro #3987e5 #c98500 #9085e9 #199e70 #d95926  → PASS
- ordinal azul claro  #86b6ef #2a78d6 #104281 → PASS
- ordinal azul oscuro #6da7ec #3987e5 #184f95 → PASS
"""
import pathlib

SANS = "system-ui, -apple-system, &#39;Segoe UI&#39;, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, monospace"

MODES = {
    "light": dict(
        surface="#fcfcfb", node="#ffffff", node_border="#e1e0d9",
        ink="#0b0b0b", ink2="#52514e", muted="#898781",
        vos="#4a3aa7", fuente="#eda100", kit="#2a78d6", aqua="#1baf7a",
        naranja="#eb6834",
        good="#0ca30c", crit="#d03b3b",
        vos_tint="rgba(74,58,167,0.04)", fuente_tint="rgba(237,161,0,0.05)",
        kit_tint="rgba(42,120,214,0.04)", naranja_tint="rgba(235,104,52,0.05)",
        aqua_tint="rgba(27,175,122,0.05)",
        good_tint="rgba(12,163,12,0.06)", crit_tint="rgba(208,59,59,0.06)",
        ordinal=["#86b6ef", "#2a78d6", "#104281"],
        ordinal_tint=["rgba(42,120,214,0.04)", "rgba(42,120,214,0.07)", "rgba(42,120,214,0.10)"],
    ),
    "dark": dict(
        surface="#1a1a19", node="#242422", node_border="#383835",
        ink="#ffffff", ink2="#c3c2b7", muted="#898781",
        vos="#9085e9", fuente="#c98500", kit="#3987e5", aqua="#199e70",
        naranja="#d95926",
        good="#0ca30c", crit="#d03b3b",
        vos_tint="rgba(144,133,233,0.07)", fuente_tint="rgba(201,133,0,0.07)",
        kit_tint="rgba(57,135,229,0.07)", naranja_tint="rgba(217,89,38,0.08)",
        aqua_tint="rgba(25,158,112,0.08)",
        good_tint="rgba(12,163,12,0.10)", crit_tint="rgba(208,59,59,0.10)",
        ordinal=["#6da7ec", "#3987e5", "#184f95"],
        ordinal_tint=["rgba(57,135,229,0.05)", "rgba(57,135,229,0.08)", "rgba(57,135,229,0.12)"],
    ),
}


class Svg:
    def __init__(self, p, w, h):
        self.p, self.w, self.h = p, w, h
        self.s = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" font-family="{SANS}">',
            f'<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M 0 1 L 9 5 L 0 9 z" fill="{p["muted"]}"/></marker></defs>',
            f'<rect x="0" y="0" width="{w}" height="{h}" rx="12" fill="{p["surface"]}"/>',
        ]

    def group(self, x, y, w, h, hue, tint, title, subtitle=None):
        p = self.p
        self.s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{tint}" stroke="{hue}" stroke-width="1.5"/>')
        self.s.append(f'<rect x="{x+16}" y="{y+15}" width="9" height="9" rx="2" fill="{hue}"/>')
        t = (f'<text x="{x+32}" y="{y+24}" font-size="11" font-weight="700" letter-spacing="1.5" fill="{p["ink2"]}">{title}'
             + (f'<tspan font-weight="400" letter-spacing="0.2" fill="{p["muted"]}">&#160;&#160;{subtitle}</tspan>' if subtitle else '')
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
                self.s.append(f'<text x="{cx}" y="{ly}" font-size="13" font-weight="600" text-anchor="middle" fill="{p["ink"]}">{txt}</text>')
            elif kind == "b2":
                self.s.append(f'<text x="{cx}" y="{ly}" font-size="12" font-weight="600" text-anchor="middle" fill="{p["ink"]}">{txt}</text>')
            elif kind == "m":
                self.s.append(f'<text x="{cx}" y="{ly}" font-size="12" font-weight="600" text-anchor="middle" font-family="{MONO}" fill="{p["ink"]}">{txt}</text>')
            elif kind == "m2":
                self.s.append(f'<text x="{cx}" y="{ly}" font-size="11" text-anchor="middle" font-family="{MONO}" fill="{p["ink2"]}">{txt}</text>')
            elif kind == "i":
                self.s.append(f'<text x="{cx}" y="{ly}" font-size="11.5" font-style="italic" text-anchor="middle" fill="{p["ink2"]}">{txt}</text>')
            else:
                self.s.append(f'<text x="{cx}" y="{ly}" font-size="11.5" text-anchor="middle" fill="{p["ink2"]}">{txt}</text>')

    def pill(self, x, y, w, h, txt, hue):
        p = self.p
        self.s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h/2}" fill="{p["node"]}" stroke="{hue}" stroke-width="1.2"/>')
        self.s.append(f'<text x="{x+w/2}" y="{y+h/2+4.5}" font-size="12.5" font-weight="500" text-anchor="middle" fill="{p["ink"]}">{txt}</text>')

    def arrow(self, x1, y1, x2, y2, dashed=False):
        d = ' stroke-dasharray="5 5"' if dashed else ''
        self.s.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{self.p["muted"]}" stroke-width="1.5"{d} marker-end="url(#arr)"/>')

    def path(self, d, dashed=False, arrow=True):
        dd = ' stroke-dasharray="5 5"' if dashed else ''
        m = ' marker-end="url(#arr)"' if arrow else ''
        self.s.append(f'<path d="{d}" fill="none" stroke="{self.p["muted"]}" stroke-width="1.5"{dd}{m}/>')

    def label(self, x, y, txt, anchor="middle", mono=False, size=11):
        f = f' font-family="{MONO}"' if mono else ''
        halo = f' stroke="{self.p["surface"]}" stroke-width="5" paint-order="stroke" stroke-linejoin="round"'
        self.s.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{f}{halo} fill="{self.p["muted"]}">{txt}</text>')

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
                self.s.append(f'<text x="{tx}" y="{ly}" font-size="12.5" font-weight="600" fill="{p["ink"]}">{txt}</text>')
            else:
                self.s.append(f'<text x="{tx}" y="{ly}" font-size="11.5" fill="{p["ink2"]}">{txt}</text>')

    def render(self):
        return "\n".join(self.s + ["</svg>"])


def overview(p):
    v = Svg(p, 1160, 548)
    v.group(368, 24, 456, 118, p["fuente"], p["fuente_tint"], "FUENTE DE VERDAD")
    v.node(384, 56, 204, 68, [("docs/", "b"), ("convenciones de la cátedra", "n")])
    v.node(604, 56, 204, 68, [("ETAPA ACTUAL — CLAUDE.md", "b2"), ("JDBC → JPA → SPA+REST", "n")])
    v.group(328, 210, 520, 310, p["kit"], p["kit_tint"], "EL KIT", "vive en .claude/ de tu repo")
    v.node(352, 262, 204, 64, [("skill-autolaunch", "b"), ("sugiere la skill correcta", "i")])
    v.node(616, 250, 208, 88, [("18 skills", "b"), ("/plan · /impl · /gp · /deliver", "n"), ("/corrector · /jdbc-to-jpa …", "n")])
    v.node(352, 414, 204, 64, [("commit-gate", "b"), ("ningún commit sin checks", "i")])
    v.node(616, 414, 208, 64, [("paw_checks.py", "b"), ("i18n · Flyway · JSTL", "n")], border=p["aqua"], bw="1.5")
    v.arrow(556, 294, 610, 294)
    v.arrow(556, 446, 610, 446)
    v.group(24, 240, 244, 260, p["vos"], p["vos_tint"], "VOS")
    v.pill(44, 272, 204, 44, "escribís un prompt", p["vos"])
    v.pill(44, 424, 204, 44, "git commit", p["vos"])
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
    v.node(208, 62, 142, 60, [("/plan", "b"), ("plan por fases", "i")])
    v.arrow(350, 92, 380, 92)
    v.node(386, 62, 142, 60, [("/impl", "b"), ("código fase a fase", "i")])
    v.arrow(528, 92, 558, 92)
    v.node(564, 62, 142, 60, [("/gp", "b"), ("reglas del corrector", "i")])
    v.arrow(706, 92, 736, 92)
    v.pill(742, 70, 118, 44, "git commit", p["vos"])
    v.arrow(860, 92, 890, 92)
    v.node(896, 62, 152, 60, [("commit-gate", "b"), ("paw_checks.py", "n")], border=p["aqua"], bw="1.5")
    v.arrow(1048, 92, 1078, 92)
    v.label(1063, 80, "OK", size=10.5)
    v.outcome(1084, 66, 132, 52, p["good"], p["good_tint"], "check", [("commit pasa", "b")])
    # vuelta: falla → /gp
    v.path("M 972 122 C 972 176, 940 176, 850 176 L 680 176 C 650 176, 635 168, 635 132", dashed=False)
    v.label(800, 168, "falla")
    return v.render()


def etapas(p):
    v = Svg(p, 1160, 190)
    cards = [
        (24, 0, [("Entrega 1 — Spring JDBC", "b"), ("JdbcTemplate · RowMapper", "n"), ("modelos inmutables", "n")]),
        (428, 1, [("Entrega 2 — JPA / Hibernate", "b"), ("entidades · EntityManager", "n"), ("las 9 trampas TP2", "n")]),
        (832, 2, [("Entrega Final — API REST + SPA", "b"), ("Jersey · JWT · DTOs con links", "n"), ("frontend aparte", "n")]),
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
    v.node(24, 126, 236, 90, [("PAW-AgenticCoding-Kit", "b"), ("nativo Claude Code", "i")], border=p["kit"], bw="1.5", tint=p["kit_tint"])
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

REPO = pathlib.Path(__file__).resolve().parent.parent / "assets"
PREVIEW = None
REPO.mkdir(exist_ok=True)
for name, fn in DIAGRAMS.items():
    for mode, p in MODES.items():
        svg = fn(p)
        (REPO / f"{name}-{mode}.svg").write_text(svg)

        print(f"{name}-{mode}.svg ({len(svg)} bytes)")
