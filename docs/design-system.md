## Design System — Rent The Slopes

Documento canónico del diseño visual del proyecto. Toda decisión estética nueva (pantalla, componente, custom tag, variante) tiene que respetar lo que está acá, y agregarse acá cuando se introduce algo nuevo.

Para crear o rediseñar UI, usar la skill `/design` (alias `/design`). La skill envuelve el plugin `frontend-design` con las reglas de este documento + las convenciones de `docs/views-and-jsp.md`.

---

## 1. Identidad de marca

Rent The Slopes es un marketplace de alquiler de equipamiento de nieve. La estética combina:

- **Frío alpino** — paleta dominante azul/cyan (cerulean + prussian blue) que evoca hielo, cielo de montaña, agua glaciar.
- **Calidez de cabaña** — acentos de cobre opaco (`--faded-copper`) y crimson profundo (`--deep-crimson`) usados con moderación.
- **Refinamiento editorial** — tipografía Manrope (sans serif con personalidad geométrica), tracking ligeramente cerrado en titulares (`letter-spacing: -0.03em`), pesos altos (700-800) en H1/H2.
- **Superficies suaves y elevadas** — bordes redondeados generosos (1.1rem a 1.5rem en cards), sombras de baja opacidad que mezclan el azul prussian con transparencia (no negro puro).
- **Soporte first-class de dark mode** — paleta "Nordic Navy": fondos casi negros (`#10161f`), cyan más suave (`#6aa9d6`), shadows con negro real (no mezclas).

La sensación general: limpio, premium, confiable. Nada brutalist, nada maximalista. Espacios generosos, jerarquía clara, micro-interacciones suaves (transitions de 190-200ms ease).

---

## 2. Design tokens — fuente única

Todos los tokens viven en **[`webapp/src/main/webapp/css/colors.css`](../webapp/src/main/webapp/css/colors.css)** como CSS variables en `:root` y `:root[data-theme="dark"]`. **Nunca** hardcodear valores HEX en otros archivos — usar la variable.

### 2.1 Paleta de marca

| Token | Light | Dark | Uso |
|---|---|---|---|
| `--alice-blue` | `#ebf2fa` | (heredado) | Backgrounds de chips, soft surfaces legacy |
| `--rich-cerulean` | `#427aa1` | `#6aa9d6` (vía `--color-accent`) | Acento primario, links, borders activos |
| `--deep-crimson` | `#931f1d` | (vía `--color-danger`) | Errores destructivos legacy, decoración |
| `--faded-copper` | `#937b63` | (heredado) | Detalles cálidos puntuales |
| `--prussian-blue` | `#0b132b` | (vía `--color-text`) | Texto principal, footer bg light, sombras |

### 2.2 Escala neutral (slate)

`--slate-50` a `--slate-900`. **Importante**: en dark mode estos tokens están redefinidos para invertirse semánticamente (`--slate-50` pasa a ser oscuro, `--slate-900` pasa a ser claro) — así las utilities `.text-color-slate-900` y `.bg-slate-50` "funcionan" en ambos temas sin reescribir.

### 2.3 Tokens semánticos (preferidos)

Estos son los que se usan en componentes nuevos — abstraen el tema:

```
Surface:    --color-bg, --color-surface, --color-surface-elev, --color-surface-muted
Text:       --color-text, --color-text-muted, --color-text-subtle, --color-text-on-accent
Borders:    --color-border, --color-accent-border, --color-danger-border
Accent:     --color-accent, --color-accent-hover, --color-accent-soft
Status:     --color-danger, --color-success, --color-warning (+ -soft, -text, -border)
Overlays:   --color-overlay, --color-overlay-strong, --color-glass, --color-glass-opaque
Shadows:    --shadow-card, --shadow-card-hover, --shadow-modal
Footer:     --color-footer-bg, --color-footer-text, --color-footer-title
```

**Regla:** un componente nuevo debe usar tokens semánticos. Los tokens de marca (`--rich-cerulean`, etc.) son legacy y solo se mantienen para no romper componentes viejos.

### 2.4 Sistema de botones (paleta cyan/blue)

`--btn-cyan-50` a `--btn-cyan-900`, `--btn-blue-600`, `--btn-blue-700`. El primary usa el gradiente `linear-gradient(90deg, --btn-cyan-500, --btn-blue-600)`. Hover oscurece a `--btn-cyan-600 → --btn-blue-700`. Active aplica `transform: scale(0.98)`.

### 2.5 Soft buttons (tonos suaves con variantes light/dark)

`--{danger,success,cyan}-soft-{bg,text,border}` + variantes `-dark` para hover. Sirven para CTAs no destructivos visualmente "calmados" en cualquier tema.

### 2.6 Bootstrap override

`colors.css` reescribe las variables `--bs-body-*`, `--bs-border-color`, `--bs-dark-rgb`, etc. para que las utilities de Bootstrap (`.text-muted`, `.bg-white`, `.border`) se reciclen automáticamente con el tema activo. **No** hardcodear colores Bootstrap — usar las utilities y dejar que el override haga el trabajo.

---

## 3. Tipografía

Fuente principal: **Manrope** (display + body, vía Bootstrap default + override en `.text`). Fallbacks: `"Avenir Next", "Segoe UI", sans-serif`.

Archivo: **[`webapp/src/main/webapp/css/typography.css`](../webapp/src/main/webapp/css/typography.css)**

### Escala (clase + props)

| Clase | Tamaño | Peso | Line height | Uso |
|---|---|---|---|---|
| `.text-h1` | `2.5rem` | 800 | 1.15 | Page title fuerte |
| `.text-h1--hero` | `clamp(1.95rem, 3.2vw, 2.65rem)` | 700 | — | Hero (responsive fluid) |
| `.text-h2` | `2rem` | 750 | 1.2 | Section heading |
| `.text-h3` | `1.5rem` | 700 | 1.25 | Sub-section |
| `.text-h4` | `1.2rem` | 650 | 1.3 | Card title / form section |
| `.text-body` | `1rem` | 450 | 1.7 | Párrafos |
| `.text-subtitle` | `1.125rem` | 400 | 1.5 | Lead text bajo H1 |
| `.text-meta` | `0.875rem` | 400 | 1.45 | Captions, metadatos |
| `.text-inline` | `0.9rem` | 600 | 1.3 | Pills inline con border + radius 999px |

**Letter spacing default:** `.text { letter-spacing: 0.01em }`. Hero usa `-0.03em` (tracking más cerrado para titulares grandes).

Cualquier texto se renderiza vía un custom tag (`<paw:h1>`, `<paw:h2>`, `<paw:h3>`, `<paw:h4>`, `<paw:p>`) que aplica la clase + escapa el texto + acepta `color` y `cssClass`. **No** escribir `<h1>...</h1>` directo en JSP nuevos — usar el tag.

---

## 4. Layout & spacing

### Sticky navbar reserva

`body { padding-top: 65px }` (light) / 58px tablet / 54px mobile. La navbar es sticky y todos los layouts respetan ese offset.

### Secciones

**`.section-secondary`** es el wrapper canónico de cualquier "bloque de contenido" debajo del hero:
- `padding: 4rem 0` (desktop), 2.5rem (tablet), 1.75rem (mobile).
- Variantes: `--white` (fondo `--color-surface`), `--transparent`, `--compact` (1.5rem padding — para páginas con CTA above the fold como detalle de producto).

### Containers

Usar Bootstrap `.container` para el ancho máximo. Para layouts edge-to-edge usar `.page-shell` (1.5rem padding, full width).

### Cards / superficies

**`.surface-card`** es el patrón canónico:
- `background-color: var(--color-surface)`
- `border: 1px solid color-mix(in srgb, var(--color-accent) 22%, transparent)`
- `border-radius: 1.1rem`
- `box-shadow: var(--shadow-card)`

Cards específicos heredan de esta base y agregan: aspect-ratio en imágenes (4/3 para `location-card`), `transform: translateY(-2px)` en hover, transición de 190ms.

### Border radius

Patrón general:
- **9999px / 999px** — pills, botones, badges, CTAs redondos.
- **1.5rem** — cards grandes (product card, location card).
- **1.1rem** — surface card base.
- **12px** — atributos compactos (product attribute).
- **1rem** — inputs, modales.

### Sombras

```
--shadow-card:       0 8px 20px rgba(11, 19, 43, 0.08)
--shadow-card-hover: 0 14px 28px rgba(11, 19, 43, 0.12)
--shadow-modal:      0 20px 40px rgba(0, 0, 0, 0.15)
```

En dark mode son negras puras con mayor opacidad (0.5 → 0.7). **No** usar sombras de un color cualquiera — tomar siempre los tokens.

---

## 5. Mapa de archivos CSS

Cada archivo tiene un dominio bien definido. Antes de agregar reglas nuevas, identificar el archivo correcto. Si ninguno encaja, crear uno (lowercase, kebab-case) y registrarlo en `head.jsp`.

Ubicación: **`webapp/src/main/webapp/css/`**

| Archivo | Dominio | Cuándo tocar |
|---|---|---|
| **`colors.css`** | Design tokens: paleta, semánticos, dark mode, Bootstrap override | Solo para agregar tokens nuevos o ajustar el tema |
| **`base.css`** | `html`/`body`, body padding, `.page-shell`, `.section-secondary`, `.surface-card`, responsive del shell | Layout global y wrappers de página |
| **`typography.css`** | `.text-*`, escala tipográfica, color helpers de texto | Tipografía nueva o variantes |
| **`buttons.css`** | `.btn-custom` y todas las variantes (primary, secondary, outline, danger, success + soft + sizes) | Nueva variante de botón |
| **`cards.css`** | `.location-card`, `.product-card`, `.rent-card`, status cards | Card nueva |
| **`badges.css`** | `.product-badge`, status badges, condition chips, `.price`, `.product-attribute` | Badges, chips, precio |
| **`modals.css`** | Modal shell, header, body, footer, backdrop, toasts (`.rts-toast`) | Modal nuevo o variante |
| **`forms.css`** | Inputs base, labels, errores | Form genérico — para forms específicos preferir `publish.css` patterns |
| **`publish.css`** | `.publish-field`, password rules, sliders, publish form completo | Form de publicación / edición de producto |
| **`profile.css`** | Vista de perfil | Vista de perfil |
| **`onboarding.css`** | Muro de onboarding del primer pickup spot (`.onboarding-card` split-panel: aside alpino + form panel). Linkeado ad-hoc en `pickup-spot-setup.jsp` (page-specific, como `publish.css`) | Pantalla de onboarding forzado |
| **`dashboard.css`** | Dashboard de rents (renter + provider), tabs, sub-tabs | Vistas de gestión de reservas |
| **`admin.css`** | Vista de admin | Pantallas admin |
| **`reviews.css`** | Reviews list + submission | Reviews |
| **`navbar.css`** | Navbar sticky, dropdowns, lang toggle, theme toggle | Navbar y menus |
| **`footer.css`** | Footer | Footer |
| **`landing.css`** | Hero, location grid landing | Landing |
| **`catalog.css`** | Grid de catálogo, vacío, paginación catalog-specific | Catálogo |
| **`filters.css`** | Filter panel, filter sections, checkboxes | Filtros laterales |
| **`pagination.css`** | Paginador genérico | Cualquier paginación |
| **`carousel.css`** | Image carousel del detalle de producto | Carrusel |
| **`calendar.css`** | Calendario de availability (publish + detail) | Calendario |
| **`tabs.css`** | Tabs reutilizables | Tabs |
| **`search-bar.css`** | Search bar hero + navbar | Search |
| **`inline-replacements.css`** | Utilities chicas para reemplazar estilos inline históricos | Caso por caso |
| **`components.css`** | (≈188 KB) Catch-all legacy de componentes. **Evitar tocar** — preferir mover reglas nuevas a un archivo específico | Solo si ninguna otra categoría encaja y la regla es realmente "generic" |
| **`styles.css`** | (~60 bytes) Stub histórico. **Ignorar** | Nunca |

**Reglas duras:**
- Cada archivo nuevo se linkea en **[`webapp/src/main/webapp/WEB-INF/views/layout/head.jsp`](../webapp/src/main/webapp/WEB-INF/views/layout/head.jsp)** con `<c:url>`. No agregar `<link>` ad-hoc en otras JSPs.
- **No** escribir CSS dentro de JSPs (sin `<style>`, sin inline `style=`). Ver `docs/guidelines.md` "CSS Guidelines".
- **No** usar `!important` jamás. Si una regla no pisa, el problema es de cascada — arreglar el selector.
- Toda color reference va por `var(--token)`, nunca HEX literal.
- Toda spacing reference que represente un design token (gaps de secciones, padding de cards) reusar valores existentes — no inventar `padding: 1.3727rem`.

---

## 6. Custom tags reutilizables

Ubicación: **`webapp/src/main/webapp/WEB-INF/tags/`**

Inventario completo (39 tags). Antes de armar markup nuevo, revisar si ya existe el pattern.

### Tipografía / contenido
- `h1.tag`, `h2.tag`, `h3.tag`, `h4.tag` — headings con escape + color + cssClass
- `p.tag` — párrafo con variantes (`subtitle`, `meta`)

### Acción / inputs
- `button.tag` — botón unificado: variantes `primary` (default), `secondary`, `outline`, `danger`, `danger-soft`, `success`, `success-soft`. Sizes `sm`, `md` (default), `lg`. Acepta `href` (renderiza `<a>`), `onclick`, `type=submit/button/reset`, `disabled`.
- `text-input.tag` — **componente canónico** de todo text input / textarea / password de form (`.publish-field`: label + control + `<form:errors>`). Soporta `maxlength`, `placeholder`, `textarea` (con `maxlength` agrega el char counter automático), `password` (con toggle + reglas). Todo text input nuevo va por acá — no escribir `<form:input>`/`<form:textarea>` crudos en una vista (excepciones deliberadas: editores con skin bespoke como `.review-card-form__*`, y templates clonados por JS con `__INDEX__`).
- `filter-checkbox.tag`, `filter-section.tag`, `filter-panel.tag` — filtros laterales
- `dropdown.tag` — **componente canónico** de todo `<select>` de form (`.publish-field` + `.publish-select` + chevron + `<form:errors>`). Modos: `optionMsgPrefix` (label = `${optionMsgPrefix}.${opt}` por el `name()` del enum — usar para `report.reason.<NAME>`, `report.resolution.action.<NAME>`), `msgKeyPrefix` (label por `${opt.slug}`), `<form:options>`, u `optionsMap` (HTML plano sin binding).
- `search-bar.tag` — barra de búsqueda
- `pagination.tag` — paginador con metadata `currentPage` / `totalPages`

### Cards / displays
- `location-card.tag` — card de ubicación con imagen 4:3
- `product-card.tag` — card de producto en catálogo
- `rent-card.tag` — card de reserva en dashboard
- `product-badge.tag`, `rent-status-badge.tag` — badges
- `product-attribute.tag`, `product-attributes-grid.tag`, `product-attribute-total.tag` — attribute chips
- `price.tag` — precio con variante `--detail` (más grande)

### Imágenes
- `image-carousel.tag`, `image-gallery.tag`, `image-upload.tag`

### Calendario
- `calendar.tag` — availability calendar

### Layout chrome
- `navbar.tag`, `auth-navbar.tag`, `footer.tag`
- `lang-toggle.tag`, `theme-toggle.tag`

### Modales / overlays
- `modal.tag`, `confirm-modal.tag`, `feedback-modal.tag`

### Forms / sections
- `form-section.tag`, `product-details-fields.tag`, `product-images-section.tag`
- `rent-action-panel.tag`, `rent-tabs.tag`, `rent-total-price.tag`

**Regla de oro:** si vas a crear una UI nueva que combina elementos que ya existen como tag, **usar los tags** — no escribir HTML duplicado. Si necesitás una variante que ya existe (ej. agregar `variant="ghost"` a `button.tag`), extender el tag, no reinventarlo.

---

## 7. Dark mode

El theming se hace 100% por CSS variables. El switch lo controla `<paw:theme-toggle>` que setea `data-theme="dark"` en `<html>` y persiste en `localStorage` (key `rts-theme`). El bootstrap script en `head.jsp` lee la preferencia antes del primer paint para evitar flash.

**Regla:** un componente nuevo es dark-mode-ready si:
1. Todos los `color`, `background-color`, `border-color`, `box-shadow` usan tokens semánticos (no HEX literal, no marca-tokens si se puede evitar).
2. Si necesita un color que no existe en `colors.css`, agregar el token en **ambos** bloques (`:root` y `:root[data-theme="dark"]`).
3. Probar visualmente en ambos temas antes de dar por hecho.

Algunos componentes legacy (los que usan `--prussian-blue`, `--rich-cerulean` directo) "funcionan" en dark porque los semantic tokens del dark mode están seteados para reciclar — pero los componentes nuevos deben preferir directamente los semantic tokens.

---

## 8. Responsive — breakpoints

Mobile-first con overrides en max-width. Breakpoints usados consistentemente:

| Breakpoint | Trigger | Qué cambia |
|---|---|---|
| `991.98px` (≤ tablet) | `@media (max-width: 991.98px)` | `body padding-top: 58px`, secciones reducen padding, `.page-shell: 1rem` |
| `575.98px` (≤ mobile) | `@media (max-width: 575.98px)` | `body padding-top: 54px`, `font-size: 0.95rem` (escala el root rem), `.page-shell: 0.75rem` |
| `900px` (cards) | `@media (max-width: 900px)` | Location grid pasa de 4 a 2 columnas |
| `600px` (cards) | `@media (max-width: 600px)` | Location grid pasa a 1 columna |

Reutilizar estos breakpoints en componentes nuevos. **No** inventar `@media (max-width: 768px)` o `(min-width: 1234px)` si los existentes ya cubren el caso.

---

## 9. Animaciones & micro-interacciones

Filosofía: suaves, rápidas, predecibles. Nada que distraiga.

- **Transitions estándar:** `190-200ms ease` para hover, `transform 0.2s` para active.
- **Hover de card:** `transform: translateY(-2px)` + sombra crece a `--shadow-card-hover` + border se intensifica.
- **Active de botón:** `transform: scale(0.98)`.
- **Focus visible:** `outline: 3px solid color-mix(in srgb, var(--rich-cerulean) 40%, white)` con `outline-offset: 2px`.
- **Toasts:** entran desde el costado, dismiss tras 4500ms (`.rts-toast--out` triggerea fade).
- **Spinner en submit:** auto-aplicado a cualquier `button[type=submit]` (script en `head.jsp`). Se puede opt-out con `data-no-spinner`.
- **Copy-to-clipboard:** toda acción de "copiar" (link de compartir, email/CBU) usa el helper compartido `window.pawCopyToClipboard(text, onCopied)` (`assets/js/clipboard-copy.js`, cargado global en `head.jsp`). HTTP-safe: el deploy es HTTP y `navigator.clipboard` no existe sin secure context — el helper cae al fallback `document.execCommand`. **Nunca** llamar `navigator.clipboard` directo. Ver `docs/views-and-jsp.md`.
- **Action bar del detalle (excepción de delight):** los botones de compartir / favoritos / reportar en `detail.jsp` tienen micro-interacciones temáticas (share = light sweep + "send", favoritos = heartbeat + corazones que flotan, reportar = bandera que flamea). Son **CSS-only** (hover / focus-visible / active / `aria-pressed`), nunca demoran la acción real, y están **scopeadas a `.product-detail__actions`** (en `buttons.css`) para no filtrarse al `.btn-outline-custom` global del resto de la app. Respetan `prefers-reduced-motion`. Es la única zona con animación decorativa permitida — replicar este patrón scopeado si se quiere delight en otra superficie, no animar la clase de botón global.
- **Form-loading text:** botón muestra `data-loading-text` si está seteado, sino reusa el texto actual.

**No** usar animaciones decorativas (bouncing, rotating, parallax). Si una transición no aporta a la usabilidad, no va.

---

## 10. Accesibilidad mínima

- **Contraste:** los tokens de texto sobre los tokens de surface respetan WCAG AA. Verificar al crear combinaciones nuevas.
- **Focus:** todo elemento interactivo necesita estado `:focus-visible` con outline custom (ver §9).
- **Touch targets:** mínimo 44×44px en mobile (botones de la navbar móvil ya están dimensionados).
- **`aria-*`:** usar `aria-label`, `aria-pressed`, `aria-checked`, `aria-disabled` donde el HTML semántico no alcanza. Los textos de aria también van por `<spring:message javaScriptEscape="true"/>` cuando es necesario.
- **Imágenes:** `alt` obligatorio, resuelto por `<spring:message>` (no hardcodear textos).

---

## 11. Cómo diseñar algo nuevo — workflow

### Pantalla / vista nueva

1. **Leer este documento + `docs/views-and-jsp.md`.** No saltearse las reglas de `<c:out>`, `<c:url>`, `<spring:message>`, `<sec:authorize>`, no scriptlets.
2. **Definir la intención estética.** Refinamiento minimal por default (es la línea del proyecto). No introducir aesthetics nuevas sin razón fuerte.
3. **Buscar tags existentes** (§6) que cubran partes del layout. Reusar siempre que sea posible.
4. **Identificar archivos CSS afectados** (§5). Las reglas nuevas van en el archivo correcto.
5. **Componer con tokens** (§2). Surface, text, accent, status — siempre vía `var(--color-*)`.
6. **Layout:** usar `.section-secondary` (+ variantes) para bloques, `.surface-card` para tarjetas, container de Bootstrap para anchos máximos.
7. **i18n:** todo texto visible en `messages_es.properties` y `messages_en.properties` (este último existe y hereda del default si está vacío — ver `docs/views-and-jsp.md`).
8. **Dark mode:** validar mentalmente que cada propiedad de color usa un token semántico.
9. **Responsive:** validar en los breakpoints conocidos (§8).
10. **Linkear archivos nuevos** en `head.jsp` con `<c:url>`.

### Custom tag nuevo

1. Identificar **3+ usos** potenciales (si no se va a reutilizar, mejor JSP inline).
2. Crear `WEB-INF/tags/<nombre>.tag` con `<%@ tag ... %>` y `<%@ attribute ... %>` para cada prop.
3. Escapar todo `body`/atributo de usuario con `<c:out>`/`fn:escapeXml`.
4. Estilos asociados van al CSS file correcto (§5), con prefijo BEM-ish (`.<tag-name>__<element>--<modifier>`).
5. Usarlo en una vista real para validar.

### Variante nueva de componente existente

1. Identificar el archivo CSS responsable (ej. `buttons.css` para una variante nueva de botón).
2. Replicar el patrón de las variantes existentes (cada variante define base + hover + focus + active + disabled, todas seteando explícitamente `box-shadow: none` y `border` para evitar regressions de Bootstrap).
3. Si la variante introduce un color nuevo, agregar el token en `colors.css` para light y dark.
4. Si es un botón: extender el `<c:choose>` en `button.tag` para mapear el nuevo `variant` string a la clase.

### Rediseñar una pantalla existente manteniendo funcionalidad

1. **No tocar** controllers, services, validators, formularios (`modelAttribute`, `path`, `action`).
2. Sí se puede reescribir markup, agregar clases, reordenar bloques, cambiar de `<div>` a `<section>`, etc. — siempre que `<form:form>`, `<form:input>`, `<form:errors>` mantengan bindings.
3. Validar regressions: el flujo (submit, validación, redirect, render de errores) sigue intacto.
4. Reusar tags y tokens al máximo. Si el rediseño introduce algo radicalmente nuevo, justificar.

---

## 12. Anti-patterns específicos del diseño

Además de los listados en `docs/anti-patterns.md` y `docs/views-and-jsp.md`:

- ❌ Hardcodear HEX en CSS (`color: #427aa1`) en lugar de usar `var(--color-accent)`.
- ❌ Inventar paddings/margins/radius nuevos sin reusar el sistema (`padding: 0.85rem 1.32rem` en vez de combinaciones existentes).
- ❌ Crear un archivo CSS nuevo y olvidar linkearlo en `head.jsp`.
- ❌ Usar `<style>` o `style=""` inline en JSPs.
- ❌ Usar `!important` para pisar Bootstrap — preferible un selector más específico o tocar el override en `colors.css`.
- ❌ Reescribir un patrón que ya está en un custom tag (`<button>` manual en vez de `<paw:button>`, `<h1>` manual en vez de `<paw:h1>`).
- ❌ Mezclar tokens semánticos con HEX literal en el mismo componente.
- ❌ Olvidar el override para `:root[data-theme="dark"]` cuando se introduce un token nuevo → componente roto en dark mode.
- ❌ Romper la jerarquía tipográfica (H3 más grande que H2, etc.) o usar tamaños fuera de escala.
- ❌ Animaciones >300ms o keyframes decorativos.
- ❌ Componentes que dependen de un breakpoint inexistente (768px, 1024px) — usar los del §8.
