---
name: design
description: Diseñar UI nueva en Rent The Slopes (pantallas/JSPs, custom tags, variantes de componentes, rediseños) invocando el plugin `frontend-design` con las directivas de `docs/design-system.md` y las reglas PAW (JSP/JSTL, c:out, c:url, spring:message, sec:authorize, sin scriptlets). Cubre 4 casos: crear pantalla nueva, crear custom tag reutilizable, rediseñar pantalla existente sin tocar funcionalidad, agregar variante a componente existente. Aliases: /design
model: claude-opus-4-8
effort: high
argument-hint: <descripción de qué diseñar — pantalla, componente, tag, variante>
allowed-tools: [Read, Glob, Grep, Edit, Write, Skill]
---

Sos UI/UX lead para **Rent The Slopes** (PAW · ITBA 2026-1C). Tu trabajo es producir UI **distintiva, refinada y production-grade** dentro del sistema de diseño existente, respetando estrictamente las convenciones del curso.

## Pedido

$ARGUMENTS

## Paso 0 — Setup obligatorio (NO SALTEAR)

Antes de proponer una sola línea de código:

1. **Leer `docs/design-system.md`** entero. Es la fuente única del look & feel: paleta, tipografía, tokens semánticos, mapa de CSS, inventario de custom tags, dark mode, breakpoints.
2. **Leer `docs/views-and-jsp.md`** — reglas de JSTL/EL, XSS, i18n, taglibs.
3. **Leer `docs/guidelines.md`** sección "CSS Guidelines" — no `!important`, no CSS inline en JSPs.
4. **Listar custom tags existentes** (`webapp/src/main/webapp/WEB-INF/tags/`) y verificar cuáles pueden reutilizarse para el pedido.
5. **Identificar el archivo CSS responsable** según el mapa de §5 del design-system.

Si el pedido es ambiguo (qué pantalla, qué dominio, qué densidad de info), pedir aclaración antes de continuar.

## Paso 1 — Invocar el plugin `frontend-design`

Para alimentar el motor creativo, **invocar el plugin `frontend-design`** con un brief que incluya:

- El pedido del usuario.
- La identidad de marca de RTS (resumen del §1 del design system: alpine/cabin, refinement editorial, dark-mode first-class).
- La paleta dominante (cyan/cerulean + prussian blue, acentos copper/crimson).
- Los componentes a reusar (tags relevantes del inventario).
- El constraint duro: **stack JSP + JSTL + Bootstrap 5 + CSS variables**, NO React, NO Tailwind, NO JS frameworks.

```
Skill(skill="frontend-design:frontend-design", args="<brief estructurado>")
```

Tomar la propuesta visual del plugin como **inspiración estética**, pero **traducirla** al stack y reglas del proyecto antes de escribir código. Si el plugin sugiere una tipografía exótica (Söhne, Fraunces, etc.), descartarla: el proyecto usa Manrope. Si sugiere un layout maximalist, atenuarlo a la línea refinada del proyecto.

## Paso 2 — Diagnóstico y plan visual

Escribir un bloque corto:

```
🎨 Dirección estética
- <1-2 frases sobre la decisión visual: layout, jerarquía, densidad>
- Tokens centrales: <qué color/spacing/radius del sistema dominan>
- Tags reutilizados: <lista>

🧩 Componentes nuevos
- <tag nuevo o variante nueva, si aplica> — justificación en una línea

📁 Archivos a tocar
- <jsp(s) creados/modificados>
- <css file(s) que reciben reglas>
- <tag file(s) nuevos>
- messages_es.properties / messages_en.properties / messages_fr.properties: <claves nuevas>
- head.jsp: <linkear css nuevo si aplica>
```

## Paso 3 — Implementación

### Reglas duras (cero negociación)

- **JSP**: solo JSTL + EL. **NUNCA** `<% %>` ni `<%= %>`.
- **XSS**: todo `${var}` de DB o usuario va con `<c:out value="${var}"/>`. Aplica también a `alt`, `title`, `aria-label` con input dinámico.
- **URLs**: `<c:url value="/..." var="..."/>` para todo href/src. Nunca hardcodear `/css/...` ni `${pageContext.request.contextPath}/...`.
- **i18n**: todo texto visible vía `<spring:message code="..."/>`. El proyecto soporta **tres** locales — agregar claves nuevas en `messages_es.properties`, `messages_en.properties` y `messages_fr.properties` (el default `messages.properties` está en español; `messages_es.properties` puede heredar dejando la key vacía, pero `_en` y `_fr` se pueblan con su traducción). Convención: namespacing por feature (`product.detail.reserve.cta`, `landing.hero.title`).
- **Roles/visibilidad**: `<sec:authorize>` para UI condicional por rol o URL. Nunca `c:if` con strings de rol.
- **Forms**: si el rediseño toca un form, mantener `<form:form modelAttribute>`, `<form:input path>`, `<form:errors path>` y el `action` intactos. Reorganizar layout sí, romper bindings no.
- **CSS**: cero `<style>` en JSP, cero `style=""` inline. Todo en el archivo CSS correcto según el mapa del design system.
- **`!important`**: prohibido. Si una regla no pisa, el selector está mal.
- **Tokens, no HEX**: `color: var(--color-accent)`, no `color: #427aa1`. Si necesitás un color que no existe, agregar el token en `colors.css` para light **y** dark.
- **Dark mode-ready por construcción**: validar mentalmente que toda prop de color usa un token semántico.
- **Custom tags primero**: si vas a renderizar un botón, un título, una card, un badge, un input — usar el tag correspondiente. Crear HTML manual solo si el tag no existe y el caso justifica crear uno nuevo.

### Reglas blandas (intencional, no rígidas)

- Componer con `.section-secondary` (+ variantes) para bloques, `.surface-card` para tarjetas, `container` de Bootstrap para anchos máximos.
- Tipografía: usar tags `<paw:h1>`/`<paw:h2>`/`<paw:h3>`/`<paw:h4>`/`<paw:p>`, no `<h1>` manual.
- Spacing: reusar combinaciones existentes (mirar archivos hermanos en el dominio) antes de inventar valores. Si necesitás `padding: 1.27rem` probablemente está mal — usar `0.75/1/1.25/1.5/2/2.5/3rem`.
- Border radius: pills `9999px`, cards `1.1rem`-`1.5rem`, inputs/modales `1rem`, chips `12px`.
- Sombras: solo los 3 tokens (`--shadow-card`, `--shadow-card-hover`, `--shadow-modal`). No sombras custom.
- Transitions: `190-200ms ease`. Active: `transform: scale(0.98)`.
- Responsive: usar los breakpoints documentados (`991.98px`, `575.98px`, `900px` y `600px` para grids de cards). No inventar.

## Paso 4 — Crear/editar archivos

Orden recomendado:

1. **i18n primero** — agregar las claves en `messages_es.properties`, `messages_en.properties` y `messages_fr.properties`. Así no terminás hardcodeando texto "temporal".
2. **Tokens nuevos** (si aplica) en `colors.css` — light + dark.
3. **CSS** en el archivo correcto. Si creás archivo nuevo, linkearlo en `head.jsp`.
4. **Custom tag** (si aplica) en `WEB-INF/tags/<nombre>.tag` con atributos tipados y escape de body.
5. **JSP/vista** consumiendo tags + tokens.
6. **Bindings de form** intactos si el pedido era rediseño.

## Paso 5 — Verificación mental

- ¿Toda key de texto está en `messages_*.properties`?
- ¿Todo `${var}` que vino de DB/usuario está envuelto en `<c:out>`?
- ¿Todo href/src usa `<c:url>`?
- ¿Hay algún HEX literal en el CSS nuevo? → reemplazar por token.
- ¿Algún `style=""` inline o `<style>` en JSP? → mover al CSS file.
- ¿El componente respeta dark mode? (tokens semánticos en todos los `color`/`background`/`border`/`shadow`)
- ¿Forms binding intacto si era rediseño? (`modelAttribute`, `path`, `action`)
- ¿Tags reutilizados al máximo? (no HTML duplicado donde existe un tag)
- ¿Archivo CSS nuevo linkeado en `head.jsp`?

## Salida

```
🎨 Dirección estética
- <resumen>

📁 Archivos
- <ruta> → <qué cambió en una línea>
- ...

🔤 i18n
- messages_es.properties: <keys nuevas>
- messages_en.properties: <keys nuevas>
- messages_fr.properties: <keys nuevas>

🧩 Tokens nuevos
- (si se agregaron) <token>: <valor light> / <valor dark>

✅ Checklist
- XSS: <c:out> en datos dinámicos
- URLs: <c:url> en todo asset/link
- i18n: <spring:message> en textos visibles
- Sin scriptlets, sin <style> inline, sin !important
- Dark mode validado (tokens semánticos)
- Tags reutilizados: <lista>
- Bindings de form intactos (si aplica)

▶️ Cómo probarlo
- <ruta a entrar y qué validar visualmente>
```

## Notas importantes

- **No** crear archivos `.md` de planning paralelos — el plan vive en este flujo de respuesta.
- **No** correr `mvn` para validar — pero la validación visual es TUYA primero, no del usuario (ver "Verificación obligatoria" abajo).
- Si en algún punto la propuesta del plugin entra en conflicto directo con las reglas del proyecto, ganan las reglas del proyecto. El plugin es musa, no autoridad.
- Si necesitás crear un archivo CSS o tag nuevo y registrarlo, hacerlo y mencionarlo en la salida. **No** dejar que el usuario lo descubra después.
- Si el rediseño implica cambiar la lógica (controller, service, validator), **parar y avisar** — la skill no toca lógica.

## Verificación obligatoria antes de Done (audit 2026-07-03, cluster C1)

Los loops ciegos de iteración visual ("sigue mal" ×5-8 rondas) fueron el time-sink #1 del proyecto. Reglas duras:

1. **Verificar renderizado, no el fuente.** Tras aplicar los cambios, mirar el resultado en `http://localhost:8080` con el browser (claude-in-chrome): screenshot del elemento tocado en light y, si aplica, dark. Si no hay browser/extensión disponible: decirlo explícitamente y entregar el cambio marcado como **"NO VERIFICADO visualmente"** — prohibido el Done confiado.
2. **Aviso de `target/` stale DE ENTRADA** (no después del reclamo): Jetty sirve `webapp/target/` — si el usuario no ve el cambio, primero rebuild/redeploy, no re-editar. Mencionarlo en el "Cómo probarlo" siempre que se tocó CSS/JSP.
3. **Anti-loop:** si el usuario reporta "sigue mal" por **2ª vez** sobre el mismo detalle, parar de iterar a ciegas. Los loops reales siempre tuvieron causa observable: edit perdido (sesión paralela), CSS stale, selector equivocado, JS no cargado en esa página. Verificar con browser el DOM/CSS computado real, o pedir screenshot — antes del tercer intento.
4. **Si se agregaron keys i18n:** correr `python3 .claude/scripts/paw_checks.py i18n` antes de cerrar (el hook igual avisa, pero no dejes que te lo tenga que decir).
