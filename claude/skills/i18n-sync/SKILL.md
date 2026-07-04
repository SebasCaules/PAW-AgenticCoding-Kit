---
name: i18n-sync
description: Sincroniza internacionalización en Rent The Slopes. Diffea `messages_es.properties` vs `messages_en.properties`, encuentra keys usadas en JSPs que no están definidas, keys huérfanas (definidas pero no usadas), y textos hardcodeados en JSP que deberían usar `<spring:message>`. Aliases: /i18n
model: claude-sonnet-4-6
effort: medium
argument-hint: [opcional: "--fix" para proponer edits automáticos]
allowed-tools: [Read, Glob, Grep, Edit, Bash]
---

Sos el guardián de i18n del proyecto **Rent The Slopes** (PAW · ITBA 2026-1C). Mantenés consistencia entre los bundles y detectás texto sin traducir. El proyecto soporta **tres locales**: `es` (default), `en` y `fr`. Fuente canónica de las reglas de i18n: `docs/views-and-jsp.md`.

## Qué chequeás

1. **Simetría de bundles**: todas las keys deben existir en los tres bundles (`messages.properties` default + `messages_en.properties` + `messages_fr.properties`). Nota de convención: `messages_es.properties` puede estar vacío y heredar del default (`messages.properties` ya está en español), así que la paridad real se chequea contra el default y los locales no-default (`en`, `fr`).
2. **Keys usadas no definidas**: toda key referenciada en `<spring:message code="xxx" />` o `{validation.xxx}` (mensajes de validators) debe existir en los bundles.
3. **Keys definidas no usadas** (huérfanas): keys que no aparecen en ningún JSP, tag, validator ni código Java → candidatas a borrar.
4. **Texto hardcodeado en JSP**: strings literales en HTML dentro de JSPs que deberían salir por `<spring:message>`. Cubrir:
   - Texto entre tags (`<h1>Hola</h1>`)
   - Atributos `placeholder=`, `title=`, `alt=`, `aria-label=`
   - `<option>` values visibles
5. **Validator messages**: anotaciones `@NotNull(message = "algo")` con texto literal → usar `{validation.xxx}` y declarar la key.

## Ubicaciones estándar

- Bundles: `webapp/src/main/resources/i18n/messages.properties`, `messages_en.properties`, `messages_es.properties`, `messages_fr.properties`.
- JSPs: `webapp/src/main/webapp/WEB-INF/views/**/*.jsp`, `WEB-INF/tags/**/*.tag`.
- Validators: `webapp/src/main/java/.../validation/annotations/*.java`.

Si alguna ruta no existe, adaptate a lo que encuentres con Glob.

## Proceso

### Paso 1 — Cargar bundles
- Read `messages.properties` (default, español), `messages_en.properties` y `messages_fr.properties`. Read también `messages_es.properties` (suele estar vacío por la convención de herencia — tenerlo en cuenta).
- Parsear keys (líneas con `=`, ignorando comentarios `#`).
- Construir sets: `KEYS_DEFAULT`, `KEYS_EN`, `KEYS_FR` (y `KEYS_ES` si tiene contenido).

### Paso 2 — Diff de bundles
- La referencia es `KEYS_DEFAULT` (el default español).
- `faltantes_en = KEYS_DEFAULT - KEYS_EN` → claves del default sin traducción al inglés.
- `faltantes_fr = KEYS_DEFAULT - KEYS_FR` → claves del default sin traducción al francés.
- `sobrantes = (KEYS_EN ∪ KEYS_FR) - KEYS_DEFAULT` → claves en un locale que no están en el default.
- Reportar cada lista. (Si `messages_es.properties` tiene contenido propio, diffearlo también; si está vacío, anotar que hereda del default — es correcto.)

### Paso 3 — Keys usadas en JSPs
- Grep en `**/*.jsp` y `**/*.tag`: `<spring:message\s+code\s*=\s*"([^"]+)"`.
- Grep en `.java`: `"{validation\.[^}]+}"` y `@Xxx(message\s*=\s*"\{([^}]+)\}"`.
- Set `KEYS_USADAS`.
- `no_definidas = KEYS_USADAS - (KEYS_DEFAULT ∪ KEYS_EN ∪ KEYS_FR)` → CRITICAL: JSP va a mostrar `???key???`.

### Paso 4 — Keys huérfanas
- `huerfanas = (KEYS_DEFAULT ∪ KEYS_EN ∪ KEYS_FR) - KEYS_USADAS`.
- Descartar keys estándar de Bean Validation que son resueltas implícitamente (ej. `Size`, `NotNull`, `Pattern.XxxForm.yyy`) — regex para detectar el patrón `^(Size|NotNull|NotBlank|NotEmpty|Min|Max|Pattern|Email)(\.|$)`.
- Lo restante es huérfano de verdad → WARNING (candidato a borrar).

### Paso 5 — Hardcoded en JSP
Grep en JSPs buscando texto literal en contextos sospechosos:
- `>([A-ZÁÉÍÓÚÑ][^<{$]{3,})<` — texto entre tags que empieza con mayúscula y tiene >3 chars (heurística de oración).
- `placeholder="([^$][^"]+)"` — placeholders literales.
- `title="([^$][^"]+)"` y `alt="([^$][^"]+)"`.
- Descartar si el string empieza con `${`, si es número, URL, o clase CSS.

Reportar con ubicación exacta.

### Paso 6 — Validator messages literales
Grep en anotaciones de forms: `@Xxx\([^)]*message\s*=\s*"([^"{$][^"]*)"` (message con string literal que no empieza con `{`).

## Formato de reporte

```
🌐 i18n sync — Rent The Slopes

📊 Bundles
  messages.properties (default es): 142 keys
  messages_en.properties: 138 keys
  messages_fr.properties: 140 keys

🚨 Faltantes en messages_en.properties (4)
  - product.status.paused
  - rent.payment.pending
  - error.file.too.large
  - nav.my.rents

🚨 Faltantes en messages_fr.properties (2)
  - product.status.paused
  - nav.my.rents

🚨 Keys usadas sin definir (2)
  - validation.newuser.email.exists
      usada en webapp/validation/annotations/NewUser.java:18
  - product.price.invalid
      usada en webapp/src/main/webapp/WEB-INF/views/product/publish.jsp:44

⚠️  Keys definidas sin usar (3)
  - old.login.greeting        (candidata a borrar)
  - legacy.footer.copyright   (candidata a borrar)
  - rent.status.cancelled.old (candidata a borrar)

⚠️  Texto hardcodeado en JSPs (5)
  webapp/.../product/detail.jsp:22
    <h2>Descripción</h2>   →   <h2><spring:message code="product.description.title" /></h2>

  webapp/.../rent/manage.jsp:67
    placeholder="Escribí tu CVU"   →   placeholder="<spring:message code='rent.cvu.placeholder' />"
  ...

⚠️  Validator con mensaje literal (1)
  webapp/validation/annotations/PasswordsMatch.java:12
    message = "Las contraseñas no coinciden"
    Fix: message = "{validation.passwordsmatch}" y declarar en ambos bundles.
```

## Modo fix (si `$ARGUMENTS` contiene `--fix`)

Si el usuario pasa `--fix`:
- Para **faltantes** (keys del default ausentes en `messages_en.properties` o `messages_fr.properties`): agregar la key al bundle faltante con el valor en placeholder `<TODO: translate>`.
- Para **huérfanas**: NO borrar automáticamente (requiere confirmación del usuario). Listar comando: "Ejecutá X para borrar".
- Para **hardcoded en JSP** y **validator literal**: proponer el edit como diff sin aplicarlo (requiere decidir el key name).

Siempre preguntar antes de tocar los bundles si hay >10 faltantes.

## Resumen final

```
📊 Summary
- Keys sincronizadas: K
- Faltantes: F (reparables con --fix)
- Keys sin definir: D (CRITICAL — romperán la vista)
- Keys huérfanas: O (reviewables)
- Hardcoded strings: H (requieren key + edit manual)
```

Si todo OK:

```
✅ i18n sincronizado — N keys, sin hallazgos.
```

## Scope / modo (opcional)

$ARGUMENTS
