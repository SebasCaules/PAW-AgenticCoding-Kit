#!/usr/bin/env python3
"""
Web Design Researcher
=====================
Runs a thorough, multi-layer design analysis of any URL or localhost page.
Outputs a hyper-detailed .md file ready for immediate use in another Claude session.

Usage:
    python research.py <url> [--focus <area>] [--existing <path-to-existing.md>] [--out <output-path>]

Examples:
    python research.py https://stripe.com
    python research.py http://localhost:3000 --focus "checkout flow"
    python research.py https://linear.app --existing linear_design.md --focus "sidebar navigation"
"""

import argparse
import json
import base64
import re
import sys
import os
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

VIEWPORTS = [
    {"name": "desktop", "width": 1440, "height": 900},
    {"name": "tablet",  "width": 768,  "height": 1024},
    {"name": "mobile",  "width": 390,  "height": 844},
]

INTERACTION_STATES = ["default", "hover", "focus", "active"]

SCROLL_BREAKPOINTS = [0, 25, 50, 75, 100]  # percent of page height


# ─────────────────────────────────────────────
# EXTRACTION SCRIPTS (injected into browser)
# ─────────────────────────────────────────────

EXTRACT_DESIGN_TOKENS = """
() => {
  const root = document.documentElement;
  const computedStyle = getComputedStyle(root);

  // CSS Variables
  const cssVars = {};
  for (const sheet of document.styleSheets) {
    try {
      for (const rule of sheet.cssRules) {
        if (rule.selectorText === ':root' || rule.selectorText === 'html') {
          const text = rule.cssText;
          const matches = text.matchAll(/--([\\w-]+):\\s*([^;]+)/g);
          for (const [, name, value] of matches) {
            cssVars['--' + name] = value.trim();
          }
        }
      }
    } catch(e) {}
  }

  // All unique colors used on page
  const allElements = document.querySelectorAll('*');
  const colors = new Set();
  const fonts = new Set();
  const fontSizes = new Set();
  const fontWeights = new Set();
  const borderRadii = new Set();
  const shadows = new Set();
  const transitions = new Set();
  const zIndexes = new Set();

  allElements.forEach(el => {
    const cs = getComputedStyle(el);
    if (cs.color && cs.color !== 'rgba(0, 0, 0, 0)') colors.add(cs.color);
    if (cs.backgroundColor && cs.backgroundColor !== 'rgba(0, 0, 0, 0)') colors.add(cs.backgroundColor);
    if (cs.borderColor && cs.borderColor !== 'rgba(0, 0, 0, 0)') colors.add(cs.borderColor);
    if (cs.fontFamily) fonts.add(cs.fontFamily);
    if (cs.fontSize) fontSizes.add(cs.fontSize);
    if (cs.fontWeight) fontWeights.add(cs.fontWeight);
    if (cs.borderRadius && cs.borderRadius !== '0px') borderRadii.add(cs.borderRadius);
    if (cs.boxShadow && cs.boxShadow !== 'none') shadows.add(cs.boxShadow);
    if (cs.transition && cs.transition !== 'all 0s ease 0s') transitions.add(cs.transition);
    if (cs.zIndex && cs.zIndex !== 'auto') zIndexes.add(cs.zIndex);
  });

  return {
    cssVariables: cssVars,
    colors: [...colors],
    fonts: [...fonts],
    fontSizes: [...fontSizes].sort((a,b) => parseFloat(a)-parseFloat(b)),
    fontWeights: [...fontWeights].sort(),
    borderRadii: [...borderRadii],
    boxShadows: [...shadows],
    transitions: [...transitions],
    zIndexLayers: [...zIndexes].sort((a,b) => parseInt(a)-parseInt(b))
  };
}
"""

EXTRACT_LAYOUT = """
() => {
  const getRect = el => {
    const r = el.getBoundingClientRect();
    return { top: Math.round(r.top + window.scrollY), left: Math.round(r.left), width: Math.round(r.width), height: Math.round(r.height) };
  };

  // Identify major layout regions
  const landmarks = ['header', 'nav', 'main', 'aside', 'footer', 'section', 'article'];
  const regions = [];
  
  landmarks.forEach(tag => {
    document.querySelectorAll(tag).forEach((el, i) => {
      const cs = getComputedStyle(el);
      regions.push({
        tag,
        index: i,
        rect: getRect(el),
        display: cs.display,
        position: cs.position,
        gridTemplate: cs.gridTemplateColumns || null,
        flexDirection: cs.flexDirection || null,
        gap: cs.gap || null,
        padding: cs.padding,
        margin: cs.margin,
        background: cs.background,
        classes: el.className,
        id: el.id,
        childCount: el.children.length
      });
    });
  });

  // Grid / flex containers
  const allEls = document.querySelectorAll('*');
  const containers = [];
  allEls.forEach(el => {
    const cs = getComputedStyle(el);
    if ((cs.display === 'grid' || cs.display === 'flex') && el.children.length > 1) {
      containers.push({
        tag: el.tagName.toLowerCase(),
        display: cs.display,
        gridTemplateColumns: cs.gridTemplateColumns,
        gridTemplateRows: cs.gridTemplateRows,
        flexDirection: cs.flexDirection,
        flexWrap: cs.flexWrap,
        alignItems: cs.alignItems,
        justifyContent: cs.justifyContent,
        gap: cs.gap,
        rect: getRect(el),
        childCount: el.children.length,
        classes: el.className.substring(0, 80)
      });
    }
  });

  return {
    pageWidth: document.documentElement.scrollWidth,
    pageHeight: document.documentElement.scrollHeight,
    viewportWidth: window.innerWidth,
    regions,
    containers: containers.slice(0, 40)
  };
}
"""

EXTRACT_COMPONENTS = """
() => {
  const analyze = (selector, label) => {
    const els = [...document.querySelectorAll(selector)].slice(0, 10);
    return els.map(el => {
      const cs = getComputedStyle(el);
      return {
        label,
        text: el.innerText?.substring(0, 60) || '',
        tag: el.tagName.toLowerCase(),
        classes: el.className.substring(0, 100),
        width: cs.width,
        height: cs.height,
        padding: cs.padding,
        margin: cs.margin,
        fontSize: cs.fontSize,
        fontWeight: cs.fontWeight,
        color: cs.color,
        background: cs.backgroundColor,
        border: cs.border,
        borderRadius: cs.borderRadius,
        cursor: cs.cursor,
        display: cs.display,
        href: el.href || null,
        type: el.type || null,
        placeholder: el.placeholder || null
      };
    });
  };

  return {
    buttons: analyze('button, [role="button"], a.btn, .button', 'button'),
    links: analyze('a:not(.btn):not(.button)', 'link'),
    inputs: analyze('input, textarea, select', 'input'),
    cards: analyze('[class*="card"], [class*="Card"]', 'card'),
    modals: analyze('[class*="modal"], [class*="Modal"], [role="dialog"]', 'modal'),
    navigation: analyze('nav a, [class*="nav"] a, [class*="Nav"] a', 'nav-item'),
    headings: analyze('h1, h2, h3, h4, h5, h6', 'heading'),
    images: [...document.querySelectorAll('img')].slice(0, 20).map(img => ({
      src: img.src?.substring(0, 100),
      alt: img.alt,
      width: img.naturalWidth,
      height: img.naturalHeight,
      displayWidth: img.offsetWidth,
      displayHeight: img.offsetHeight,
      objectFit: getComputedStyle(img).objectFit
    })),
    icons: [...document.querySelectorAll('svg, [class*="icon"], [class*="Icon"]')].slice(0, 20).map(el => ({
      tag: el.tagName,
      size: getComputedStyle(el).width + ' x ' + getComputedStyle(el).height,
      classes: el.className?.toString().substring(0, 60) || ''
    }))
  };
}
"""

EXTRACT_TYPOGRAPHY = """
() => {
  const headings = ['h1','h2','h3','h4','h5','h6'];
  const result = {};

  headings.forEach(tag => {
    const el = document.querySelector(tag);
    if (el) {
      const cs = getComputedStyle(el);
      result[tag] = {
        sample: el.innerText?.substring(0, 60),
        fontFamily: cs.fontFamily,
        fontSize: cs.fontSize,
        fontWeight: cs.fontWeight,
        lineHeight: cs.lineHeight,
        letterSpacing: cs.letterSpacing,
        color: cs.color,
        textTransform: cs.textTransform
      };
    }
  });

  const body = document.querySelector('p, li, span');
  if (body) {
    const cs = getComputedStyle(body);
    result['body'] = {
      fontFamily: cs.fontFamily,
      fontSize: cs.fontSize,
      fontWeight: cs.fontWeight,
      lineHeight: cs.lineHeight,
      letterSpacing: cs.letterSpacing,
      color: cs.color
    };
  }

  // Collect all @font-face declarations
  const webFonts = [];
  for (const sheet of document.styleSheets) {
    try {
      for (const rule of sheet.cssRules) {
        if (rule.type === CSSRule.FONT_FACE_RULE) {
          webFonts.push(rule.cssText.substring(0, 200));
        }
      }
    } catch(e) {}
  }

  return { scale: result, webFonts };
}
"""

EXTRACT_ANIMATIONS = """
() => {
  const animations = new Set();
  const keyframes = [];
  
  for (const sheet of document.styleSheets) {
    try {
      for (const rule of sheet.cssRules) {
        if (rule.type === CSSRule.KEYFRAMES_RULE) {
          keyframes.push({
            name: rule.name,
            css: rule.cssText.substring(0, 300)
          });
        }
      }
    } catch(e) {}
  }

  const animated = [...document.querySelectorAll('*')].filter(el => {
    const cs = getComputedStyle(el);
    return cs.animationName !== 'none' || cs.transitionDuration !== '0s';
  }).slice(0, 20).map(el => {
    const cs = getComputedStyle(el);
    return {
      tag: el.tagName.toLowerCase(),
      classes: el.className.substring(0, 60),
      animation: cs.animationName,
      animationDuration: cs.animationDuration,
      transition: cs.transition,
      transform: cs.transform !== 'none' ? cs.transform : null
    };
  });

  return { keyframes, animatedElements: animated };
}
"""

EXTRACT_CONTENT_STRUCTURE = """
() => {
  const extractText = (selector, max=5) => 
    [...document.querySelectorAll(selector)].slice(0, max).map(el => el.innerText?.trim().substring(0, 120)).filter(Boolean);

  const metaTags = {};
  document.querySelectorAll('meta').forEach(m => {
    const name = m.name || m.property || m.getAttribute('name');
    if (name) metaTags[name] = m.content?.substring(0, 200);
  });

  // CTA analysis
  const ctas = [...document.querySelectorAll('a, button')].filter(el => {
    const text = el.innerText?.trim();
    return text && text.length < 40 && (
      /sign|get|start|try|buy|join|subscribe|download|learn|contact|book|demo|free/i.test(text)
    );
  }).slice(0, 15).map(el => ({
    text: el.innerText.trim(),
    tag: el.tagName.toLowerCase(),
    href: el.href || null,
    classes: el.className.substring(0, 60),
    background: getComputedStyle(el).backgroundColor,
    color: getComputedStyle(el).color
  }));

  return {
    title: document.title,
    metaTags,
    h1s: extractText('h1'),
    h2s: extractText('h2', 8),
    h3s: extractText('h3', 8),
    paragraphs: extractText('p', 6),
    ctas,
    lists: extractText('li', 10),
    totalTextLength: document.body.innerText.length,
    linkCount: document.querySelectorAll('a').length,
    imageCount: document.querySelectorAll('img').length,
    formCount: document.querySelectorAll('form').length,
  };
}
"""


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def rgb_to_hex(rgb_str):
    """Convert rgb(r,g,b) or rgba(r,g,b,a) to hex."""
    nums = re.findall(r'[\d.]+', rgb_str)
    if len(nums) >= 3:
        r, g, b = int(float(nums[0])), int(float(nums[1])), int(float(nums[2]))
        return f'#{r:02x}{g:02x}{b:02x}'.upper()
    return rgb_str

def dedupe_colors(color_list):
    """Deduplicate and convert all colors to hex."""
    seen = {}
    for c in color_list:
        hex_c = rgb_to_hex(c)
        seen[hex_c] = c
    return list(seen.keys())

def screenshot_to_base64(path):
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode()

def safe_eval(page, script, label=""):
    try:
        return page.evaluate(script)
    except Exception as e:
        print(f"  ⚠ Could not extract {label}: {e}")
        return {}

def scroll_to_percent(page, pct):
    page.evaluate(f"window.scrollTo(0, document.documentElement.scrollHeight * {pct/100})")
    page.wait_for_timeout(400)


# ─────────────────────────────────────────────
# CORE RESEARCH ENGINE
# ─────────────────────────────────────────────

def research_page(url, focus=None, existing_md=None):
    print(f"\n🔍 Web Design Researcher")
    print(f"   URL    : {url}")
    print(f"   Focus  : {focus or 'Full analysis'}")
    print(f"   Existing MD: {existing_md or 'None'}\n")

    data = {
        "url": url,
        "focus": focus,
        "timestamp": datetime.now().isoformat(),
        "screenshots": {},
        "tokens": {},
        "layout": {},
        "components": {},
        "typography": {},
        "animations": {},
        "content": {},
        "scroll_sections": [],
        "existing_md": None
    }

    # Load existing MD for context
    if existing_md and Path(existing_md).exists():
        data["existing_md"] = Path(existing_md).read_text()
        print(f"  ✓ Loaded existing design MD ({len(data['existing_md'])} chars)")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for vp in VIEWPORTS:
            print(f"\n📐 Viewport: {vp['name']} ({vp['width']}x{vp['height']})")
            context = browser.new_context(
                viewport={"width": vp["width"], "height": vp["height"]},
                device_scale_factor=2
            )
            page = context.new_page()

            print(f"  → Loading page...")
            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
            except Exception:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1500)

            vp_name = vp["name"]

            # ── Screenshots at scroll breakpoints ──
            print(f"  → Capturing scroll sections...")
            scroll_shots = []
            for pct in SCROLL_BREAKPOINTS:
                scroll_to_percent(page, pct)
                shot_path = f"/tmp/design_{vp_name}_{pct}.png"
                page.screenshot(path=shot_path, full_page=False)
                scroll_shots.append({
                    "scroll_pct": pct,
                    "path": shot_path
                })
            data["screenshots"][vp_name] = scroll_shots
            
            # Full page screenshot
            scroll_to_percent(page, 0)
            full_path = f"/tmp/design_{vp_name}_full.png"
            page.screenshot(path=full_path, full_page=True)
            data["screenshots"][f"{vp_name}_full"] = full_path

            # ── Extract design data (desktop only for heavy extraction) ──
            if vp_name == "desktop":
                print(f"  → Extracting design tokens...")
                data["tokens"] = safe_eval(page, EXTRACT_DESIGN_TOKENS, "tokens")

                print(f"  → Extracting layout structure...")
                data["layout"] = safe_eval(page, EXTRACT_LAYOUT, "layout")

                print(f"  → Extracting components...")
                data["components"] = safe_eval(page, EXTRACT_COMPONENTS, "components")

                print(f"  → Extracting typography scale...")
                data["typography"] = safe_eval(page, EXTRACT_TYPOGRAPHY, "typography")

                print(f"  → Extracting animations...")
                data["animations"] = safe_eval(page, EXTRACT_ANIMATIONS, "animations")

                print(f"  → Extracting content structure...")
                data["content"] = safe_eval(page, EXTRACT_CONTENT_STRUCTURE, "content")

                # ── Scroll sections analysis ──
                print(f"  → Analyzing page sections...")
                sections = []
                total_h = data["layout"].get("pageHeight", 3000)
                step = min(800, total_h // 5)
                scroll_pos = 0
                while scroll_pos < total_h:
                    page.evaluate(f"window.scrollTo(0, {scroll_pos})")
                    page.wait_for_timeout(300)
                    section_data = page.evaluate("""
                    () => {
                        const vp = window.innerHeight;
                        const els = [...document.elementsFromPoint(window.innerWidth/2, vp/2)];
                        const prominent = els.find(el => ['section','div','main','article'].includes(el.tagName.toLowerCase()) && el.offsetHeight > 100);
                        if (!prominent) return null;
                        const cs = getComputedStyle(prominent);
                        return {
                            scrollY: window.scrollY,
                            tag: prominent.tagName.toLowerCase(),
                            classes: prominent.className.substring(0, 80),
                            background: cs.backgroundColor,
                            height: prominent.offsetHeight,
                            hasVideo: prominent.querySelector('video') !== null,
                            hasForm: prominent.querySelector('form') !== null,
                            textContent: prominent.innerText?.substring(0, 150).trim()
                        };
                    }
                    """)
                    if section_data:
                        sections.append(section_data)
                    scroll_pos += step
                data["scroll_sections"] = sections

            context.close()

        browser.close()

    return data


# ─────────────────────────────────────────────
# MARKDOWN GENERATOR
# ─────────────────────────────────────────────

def generate_markdown(data):
    url = data["url"]
    focus = data.get("focus")
    tokens = data.get("tokens", {})
    layout = data.get("layout", {})
    components = data.get("components", {})
    typography = data.get("typography", {})
    animations = data.get("animations", {})
    content = data.get("content", {})
    sections = data.get("scroll_sections", [])

    lines = []
    def w(*args): lines.append(" ".join(str(a) for a in args))
    def h1(t): w(f"\n# {t}")
    def h2(t): w(f"\n## {t}")
    def h3(t): w(f"\n### {t}")
    def sep(): w("\n---")

    # ── HEADER ──
    w(f"# Web Design Specification")
    w(f"**Source URL:** `{url}`")
    w(f"**Generated:** {data['timestamp']}")
    if focus:
        w(f"**Focus Area:** {focus}")
    if data.get("existing_md"):
        w(f"**Mode:** Deep-dive enrichment of existing specification")
    w(f"\n> This document is a complete, machine-readable design specification.")
    w(f"> A Claude session reading this file has everything needed to recreate,")
    w(f"> extend, or reason about this design without viewing the original page.")
    sep()

    # ── PAGE OVERVIEW ──
    h1("1. Page Overview")
    if content:
        w(f"- **Title:** {content.get('title', 'N/A')}")
        w(f"- **Total text length:** {content.get('totalTextLength', 0):,} characters")
        w(f"- **Link count:** {content.get('linkCount', 0)}")
        w(f"- **Image count:** {content.get('imageCount', 0)}")
        w(f"- **Form count:** {content.get('formCount', 0)}")
        meta = content.get('metaTags', {})
        if meta.get('description'):
            w(f"- **Meta description:** {meta['description']}")
        if meta.get('og:type'):
            w(f"- **OG type:** {meta['og:type']}")
    if layout:
        w(f"- **Full page height (desktop):** {layout.get('pageHeight', 'N/A')}px")
        w(f"- **Full page width (desktop):** {layout.get('pageWidth', 'N/A')}px")
    sep()

    # ── CONTENT STRUCTURE ──
    h1("2. Content Hierarchy")
    if content:
        if content.get('h1s'):
            h2("H1 Headlines")
            for h in content['h1s']: w(f"- `{h}`")
        if content.get('h2s'):
            h2("H2 Subheadings")
            for h in content['h2s']: w(f"- `{h}`")
        if content.get('h3s'):
            h2("H3 Section Headers")
            for h in content['h3s']: w(f"- `{h}`")
        if content.get('paragraphs'):
            h2("Body Copy Samples")
            for p in content['paragraphs']: w(f"- {p}")
        if content.get('ctas'):
            h2("Calls to Action (CTAs)")
            w("| Text | Tag | Background | Color | Href |")
            w("|------|-----|------------|-------|------|")
            for cta in content['ctas']:
                href = (cta.get('href') or '')[:50]
                w(f"| `{cta['text']}` | `{cta['tag']}` | `{rgb_to_hex(cta['background'])}` | `{rgb_to_hex(cta['color'])}` | {href} |")
    sep()

    # ── COLOR SYSTEM ──
    h1("3. Color System")
    if tokens:
        # CSS Variables
        css_vars = tokens.get("cssVariables", {})
        color_vars = {k: v for k, v in css_vars.items() if any(x in k.lower() for x in ['color','bg','background','text','border','primary','secondary','accent','surface','brand'])}
        if color_vars:
            h2("CSS Custom Properties (Design Tokens)")
            w("| Variable | Value |")
            w("|----------|-------|")
            for k, v in list(color_vars.items())[:40]:
                w(f"| `{k}` | `{v}` |")

        # All unique colors
        all_colors = dedupe_colors(tokens.get("colors", []))
        if all_colors:
            h2("All Unique Colors Detected")
            w("Hex values of every color found in computed styles:\n")
            chunks = [all_colors[i:i+8] for i in range(0, min(len(all_colors), 64), 8)]
            for chunk in chunks:
                w(", ".join(f"`{c}`" for c in chunk))
    sep()

    # ── TYPOGRAPHY ──
    h1("4. Typography System")
    typo = typography.get("scale", {})
    if typo:
        h2("Type Scale")
        w("| Element | Font Family | Size | Weight | Line Height | Letter Spacing | Color |")
        w("|---------|------------|------|--------|-------------|----------------|-------|")
        for tag, props in typo.items():
            ff = props.get('fontFamily','').split(',')[0].strip().strip('"')
            w(f"| `{tag}` | {ff} | {props.get('fontSize','?')} | {props.get('fontWeight','?')} | {props.get('lineHeight','?')} | {props.get('letterSpacing','?')} | `{rgb_to_hex(props.get('color','rgb(0,0,0)'))}` |")
        if typo.get('h1', {}).get('textTransform') and typo['h1']['textTransform'] != 'none':
            w(f"\n> **Note:** H1 uses `text-transform: {typo['h1']['textTransform']}`")

    if typography.get("webFonts"):
        h2("Web Font Declarations (@font-face)")
        w("```css")
        for f in typography['webFonts'][:8]:
            w(f)
        w("```")

    if tokens:
        font_families = list(dict.fromkeys(tokens.get("fonts", [])))[:6]
        if font_families:
            h2("All Font Families Used")
            for ff in font_families:
                w(f"- `{ff}`")
    sep()

    # ── SPACING & SIZING ──
    h1("5. Spacing & Sizing System")
    if tokens:
        spacing_vars = {k: v for k, v in tokens.get("cssVariables", {}).items()
                        if any(x in k.lower() for x in ['space','gap','margin','padding','size','radius','width','height'])}
        if spacing_vars:
            h2("Spacing CSS Variables")
            w("| Variable | Value |")
            w("|----------|-------|")
            for k, v in list(spacing_vars.items())[:30]:
                w(f"| `{k}` | `{v}` |")

        radii = list(dict.fromkeys(tokens.get("borderRadii", [])))
        if radii:
            h2("Border Radius Values")
            w(", ".join(f"`{r}`" for r in radii[:12]))

        font_sizes = list(dict.fromkeys(tokens.get("fontSizes", [])))
        if font_sizes:
            h2("Font Size Scale")
            w(", ".join(f"`{s}`" for s in font_sizes[:16]))
    sep()

    # ── LAYOUT ──
    h1("6. Layout Architecture")
    if layout:
        regions = layout.get("regions", [])
        if regions:
            h2("Semantic Layout Regions")
            w("| Tag | Position | Dimensions | Display | Flex/Grid | Background |")
            w("|-----|----------|-----------|---------|-----------|------------|")
            for r in regions[:20]:
                rect = r.get("rect", {})
                dims = f"{rect.get('width','?')}×{rect.get('height','?')}px"
                pos_info = f"top:{rect.get('top','?')}px"
                flex_grid = r.get("gridTemplate") or r.get("flexDirection") or "—"
                bg = rgb_to_hex(r.get("background","")) if r.get("background") else "—"
                w(f"| `{r['tag']}#{r.get('id','') or r.get('index','')}` | {pos_info} | {dims} | {r.get('display','?')} | {flex_grid} | `{bg}` |")

        containers = layout.get("containers", [])
        if containers:
            h2("Grid & Flex Containers")
            w("| Tag | Display | Template Columns | Direction | Align | Justify | Gap | Children |")
            w("|-----|---------|-----------------|-----------|-------|---------|-----|----------|")
            for c in containers[:20]:
                cols = (c.get("gridTemplateColumns") or "—")[:40]
                w(f"| `{c['tag']}` | {c['display']} | {cols} | {c.get('flexDirection','—')} | {c.get('alignItems','—')} | {c.get('justifyContent','—')} | {c.get('gap','—')} | {c['childCount']} |")

    # Scroll sections
    if sections:
        h2("Page Sections (Scroll Analysis)")
        w("| Scroll Y | Tag | Classes (excerpt) | Background | Height | Has Video | Has Form |")
        w("|----------|-----|------------------|------------|--------|-----------|----------|")
        for s in sections[:15]:
            bg = rgb_to_hex(s.get("background","")) if s.get("background") else "—"
            w(f"| {s.get('scrollY',0)}px | `{s['tag']}` | `{s.get('classes','')[:50]}` | `{bg}` | {s.get('height','?')}px | {'✓' if s.get('hasVideo') else '—'} | {'✓' if s.get('hasForm') else '—'} |")
    sep()

    # ── COMPONENTS ──
    h1("7. Component Inventory")

    if components.get("buttons"):
        h2("Buttons")
        w("| Text | Tag | Width | Height | Padding | Font | BG | Color | Border Radius | Border |")
        w("|------|-----|-------|--------|---------|------|----|-------|---------------|--------|")
        for b in components["buttons"][:10]:
            w(f"| `{b.get('text','')[:30]}` | `{b['tag']}` | {b['width']} | {b['height']} | {b['padding']} | {b['fontSize']}/{b['fontWeight']} | `{rgb_to_hex(b['background'])}` | `{rgb_to_hex(b['color'])}` | {b['borderRadius']} | {b['border'][:30]} |")

    if components.get("inputs"):
        h2("Form Inputs")
        w("| Type | Placeholder | Width | Height | Padding | Font | BG | Border | Border Radius |")
        w("|------|-------------|-------|--------|---------|------|----|--------|---------------|")
        for inp in components["inputs"][:8]:
            placeholder = (inp.get('placeholder') or '')[:30]
            border = (inp.get('border') or '')[:30]
            w(f"| `{inp.get('type','text')}` | {placeholder} | {inp['width']} | {inp['height']} | {inp['padding']} | {inp['fontSize']} | `{rgb_to_hex(inp['background'])}` | {border} | {inp['borderRadius']} |")

    if components.get("cards"):
        h2("Card Components")
        for card in components["cards"][:5]:
            w(f"\n**Card** (`{card.get('classes','')[:60]}`)")
            w(f"- Dimensions: {card['width']} × {card['height']}")
            w(f"- Background: `{rgb_to_hex(card['background'])}`")
            w(f"- Border: {card['border']}")
            w(f"- Border radius: {card['borderRadius']}")
            w(f"- Padding: {card['padding']}")
            w(f"- Box shadow: _(from token list)_")

    if components.get("navigation"):
        h2("Navigation Items")
        w("| Text | Font Size | Font Weight | Color | Padding |")
        w("|------|-----------|-------------|-------|---------|")
        for nav in components["navigation"][:10]:
            w(f"| `{nav.get('text','')[:30]}` | {nav['fontSize']} | {nav['fontWeight']} | `{rgb_to_hex(nav['color'])}` | {nav['padding']} |")

    if components.get("headings"):
        h2("Heading Instances")
        for hd in components["headings"][:8]:
            w(f"- `{hd['tag'].upper()}`: \"{hd.get('text','')[:60]}\" — {hd['fontSize']} / {hd['fontWeight']} / `{rgb_to_hex(hd['color'])}`")

    if components.get("images"):
        h2("Images")
        w("| Alt | Natural Size | Display Size | Object-Fit |")
        w("|-----|-------------|-------------|------------|")
        for img in components["images"][:10]:
            nat = f"{img['width']}×{img['height']}"
            disp = f"{img['displayWidth']}×{img['displayHeight']}"
            w(f"| {img.get('alt','')[:30]} | {nat}px | {disp}px | {img.get('objectFit','?')} |")
    sep()

    # ── ANIMATIONS & MOTION ──
    h1("8. Motion & Animation")
    if tokens:
        transitions = list(dict.fromkeys(tokens.get("transitions", [])))
        if transitions:
            h2("Transition Definitions")
            for t in transitions[:10]:
                w(f"- `{t}`")
    if animations:
        if animations.get("keyframes"):
            h2("Keyframe Animations")
            for kf in animations["keyframes"][:8]:
                w(f"\n**@keyframes {kf['name']}**")
                w("```css")
                w(kf['css'])
                w("```")
        if animations.get("animatedElements"):
            h2("Animated Elements")
            w("| Tag | Classes | Animation | Duration | Transition |")
            w("|-----|---------|-----------|----------|------------|")
            for el in animations["animatedElements"][:10]:
                w(f"| `{el['tag']}` | `{el['classes'][:40]}` | {el.get('animation','—')} | {el.get('animationDuration','—')} | {el.get('transition','—')[:40]} |")
    sep()

    # ── EFFECTS & DEPTH ──
    h1("9. Visual Effects & Depth")
    if tokens:
        shadows = list(dict.fromkeys(tokens.get("boxShadows", [])))
        if shadows:
            h2("Box Shadows")
            for s in shadows[:8]:
                w(f"- `{s}`")
        z_layers = tokens.get("zIndexLayers", [])
        if z_layers:
            h2("Z-Index Layers")
            w(", ".join(f"`{z}`" for z in z_layers[:12]))
    sep()

    # ── RESPONSIVE BEHAVIOR ──
    h1("10. Responsive Behavior")
    viewports_info = {
        "desktop": "1440×900",
        "tablet": "768×1024",
        "mobile": "390×844"
    }
    for vp_name, dims in viewports_info.items():
        full_path = data["screenshots"].get(f"{vp_name}_full")
        if full_path and Path(full_path).exists():
            size = Path(full_path).stat().st_size // 1024
            w(f"\n**{vp_name.title()} ({dims})** — Full-page screenshot captured ({size}KB)")
    w("\n> Screenshots were captured but are not embedded. Run the tool with `--embed-images` to include base64 images in this document.")
    sep()

    # ── CSS VARIABLES FULL DUMP ──
    h1("11. Complete CSS Variable Reference")
    all_vars = tokens.get("cssVariables", {}) if tokens else {}
    if all_vars:
        w("```css")
        w(":root {")
        for k, v in list(all_vars.items())[:80]:
            w(f"  {k}: {v};")
        w("}")
        w("```")
    sep()

    # ── FOCUS AREA DEEP DIVE ──
    if focus:
        h1(f"12. Focus Area Deep Dive: {focus}")
        w(f"> This section contains targeted analysis for: **{focus}**")
        w(f"> Claude: Cross-reference all sections above for elements related to '{focus}'.")
        w(f"> Pay special attention to:")
        w(f"> - Any component whose class name, ID, or text content relates to '{focus}'")
        w(f"> - The layout region where '{focus}' appears based on scroll position data")
        w(f"> - Typography, color, and spacing applied to '{focus}' elements")
        w(f"> - Interaction states (hover, focus, active) for '{focus}' components")

    # ── EXISTING MD DELTA ──
    if data.get("existing_md"):
        h1("13. Delta from Previous Specification")
        w("> An existing design specification was provided.")
        w("> This document is a refinement/enrichment of that prior spec.")
        w("> Treat this document as the authoritative, most up-to-date version.")
        w(f"> Prior spec length: {len(data['existing_md'])} characters")
    sep()

    # ── CLAUDE INSTRUCTIONS ──
    h1("📋 Instructions for Claude")
    w("""
> **If you are a Claude session reading this file, follow these rules:**
>
> 1. This document is your single source of truth for the design of the page at the URL above.
> 2. All hex colors, px values, font names, and CSS values are extracted directly from the live page — trust them.
> 3. When recreating UI, use the exact values in this document. Do not estimate or substitute.
> 4. Component tables give you real computed styles. Use them for pixel-perfect implementation.
> 5. CSS Variables section is your design token system — reference it first before hardcoding values.
> 6. The Content Hierarchy section tells you what text to use. Do not invent copy.
> 7. If a value seems missing, check the CSS Variable Reference (Section 11) — it may be defined there.
> 8. Responsive behavior was captured at 3 breakpoints: 1440px, 768px, and 390px.
    """)

    return "\n".join(lines)


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Web Design Researcher — generates a complete design spec .md file"
    )
    parser.add_argument("url", help="URL or localhost address to research")
    parser.add_argument("--focus", help="Specific area to deep-dive (e.g. 'checkout flow')", default=None)
    parser.add_argument("--existing", help="Path to existing .md output from this tool", default=None)
    parser.add_argument("--out", help="Output .md file path", default=None)

    args = parser.parse_args()

    # Auto-generate output filename
    if not args.out:
        safe_name = re.sub(r'[^\w]', '_', args.url.replace('https://','').replace('http://',''))[:40]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        args.out = f"design_{safe_name}_{timestamp}.md"

    # Run research
    data = research_page(args.url, focus=args.focus, existing_md=args.existing)

    # Generate markdown
    print(f"\n📝 Generating specification document...")
    markdown = generate_markdown(data)

    # Write output
    out_path = Path(args.out)
    out_path.write_text(markdown, encoding="utf-8")

    size_kb = out_path.stat().st_size // 1024
    print(f"\n✅ Done!")
    print(f"   Output : {out_path}")
    print(f"   Size   : {size_kb}KB")
    print(f"   Lines  : {len(markdown.splitlines())}")
    print(f"\n💡 To use in another Claude session:")
    print(f'   "I have a design spec at {out_path}. Use it to [your task]."')


if __name__ == "__main__":
    main()
