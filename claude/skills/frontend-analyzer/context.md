# Frontend Analyzer — Project Context

> This file holds project-specific context for the frontend-analyzer skill.
> When fields contain `<NULL>`, the skill will run an onboarding interview to fill them.
> After onboarding, this file becomes Lyra's living memory of the project.

---

## Project Identity

- **Project name:** PAW 2026A-10
- **What it does:** Marketplace de alquiler de equipamiento de snow (esquí, snowboard, ropa, accesorios) con catálogo, reservas, reviews y panel de admin. Two-sided: renters publican y reservan.
- **Target audience:** Consumidores generales — turistas / esquiadores ocasionales que viajan a destinos de snow (Bariloche, Las Leñas) y necesitan alquilar equipamiento por días.

## Aesthetic Direction

- **Brand vibe (3 adjectives):** Limpio, técnico, confiable. Referencia: Stripe / Linear — tipografía neutral, paleta sobria, mucho whitespace, sin gradients chillones.

## Environments

- **Local dev URL:** http://localhost:8080
- **Production URL:** http://pawserver.it.itba.edu.ar/paw-2026a-10/

## Design System

- **Existing design system / Figma / tokens:** `docs/design-system.md` en el repo es el source of truth canónico. Tokens / componentes / typography scale / dark mode definidos ahí. Cualquier análisis debe alinear con ese doc — si el CSS actual difiere del doc, eso es un finding a reportar.

## Stack

- **Frontend framework:** JSP + JSTL + Bootstrap 5 + JS vanilla. Custom JSP tag files en `webapp/src/main/webapp/WEB-INF/tags/` (navbar, footer, product-card, calendar, modals, stat-card, etc.). CSS propio en `webapp/src/main/webapp/css/` (colors.css, components.css, etc.). No hay framework JS — Spring MVC server-rendered.

## Default focus

- **Pages of interest:**
  - `/` (landing pública)
  - `/catalog` (catálogo con filtros + paginación — core de la experiencia del renter)
  - `/products/{id}` (detalle de producto: calendario de disponibilidad, reserva, reviews)
  - Dashboards: `/my-rents`, `/my-listings`, `/admin` (backoffice usuario y admin)

---

## Analysis history

> Lyra appends a one-line entry here every time she completes an analysis.
> Format: `YYYY-MM-DD | <url or page> | <focus or "full audit"> | <output filename>`

2026-05-28 | http://localhost:8080/ | full audit | design_localhost_landing_20260528.md
2026-05-28 | http://localhost:8080/catalog | full audit | design_localhost_catalog_20260528.md
2026-05-28 | http://localhost:8080/products/9 | full audit | design_localhost_product_9_20260528.md
2026-05-31 | code-level (all JSPs) | back-link consistency audit | design_back-link-consistency_20260531.md
2026-06-02 | code-level (all CSS + JSPs + tags + WebConfig) | end-to-end CSS audit (cache, modals, render drift) | design_css-end-to-end-audit_20260602.md