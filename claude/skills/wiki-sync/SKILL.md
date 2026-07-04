---
name: wiki-sync
description: Detecta desincronización entre la codebase y el wiki de Obsidian (PAW_Obsidian). Tras implementar/modificar features, identifica qué páginas de wiki/entities, wiki/concepts y wiki/index.md quedaron desactualizadas y propone los updates. También agrega una entrada a log.md. Aliases: /wiki
model: claude-sonnet-4-6
effort: medium
argument-hint: [opcional: rango de commits a analizar, e.g. "main..HEAD" o "HEAD~5..HEAD"]
allowed-tools: [Read, Glob, Grep, Edit, Write, Bash]
---

Sos el encargado de mantener el wiki de **PAW_Obsidian** sincronizado con el código de **Rent The Slopes**. Tras cambios en la codebase, identificás qué páginas del wiki necesitan update y los aplicás.

## Reglas del wiki

Leé **siempre primero** `~/Desktop/ITBA/26-1C/PAW/PAW_Obsidian/CLAUDE.md` — define la estructura, el template de las páginas (frontmatter YAML), los tipos (`source` / `entity` / `concept` / `analysis`) y la convención de `[[wikilinks]]`.

Ubicaciones:
- Wiki root: `~/Desktop/ITBA/26-1C/PAW/PAW_Obsidian/wiki/`
- Index: `wiki/index.md` — catálogo por categoría; cada entrada es `- [[Page]] — summary`.
- Log: `wiki/log.md` — append-only, entradas `## [YYYY-MM-DD] operation | Subject`.
- `wiki/entities/` — inventario del código (Domain Models, Controllers, Services, DAOs, etc.).
- `wiki/concepts/` — patrones y reglas (testing, validation, security, etc.).
- `wiki/sources/` — resúmenes de material de cátedra (inmutable, solo append cuando hay nueva fuente).
- `wiki/analyses/` — deep dives transversales (arquitectura, errores comunes, roadmap).

## Proceso

### Paso 1 — Determinar el rango de cambios

- Si `$ARGUMENTS` incluye rango (ej. `main..HEAD`, `HEAD~10..HEAD`), usarlo.
- Si no, por default: `git diff --stat HEAD~5..HEAD` + `git log HEAD~5..HEAD --oneline`.
- Si el usuario dice "el último feature" o "desde ayer", mapear a un rango razonable.

### Paso 2 — Inventariar los cambios

```bash
git diff --name-status <rango>         # A (added), M (modified), D (deleted)
git log --pretty=format:"%h %s" <rango>  # para contexto
```

Categorizar cada archivo tocado:

| Ruta | Impacta wiki en |
|------|-----------------|
| `models/.../*.java` (clase) | `entities/domain-models.md` |
| `models/.../enums/*.java` | `entities/enums.md` |
| `webapp/.../controller/*.java` | `entities/controllers.md` |
| `services/.../*Service*.java` | `entities/services.md` |
| `persistence/.../*JpaDao*.java` | `entities/daos.md` |
| `webapp/.../form/*.java` | `entities/controllers.md` (sección Forms) |
| `webapp/.../validation/**/*.java` | `concepts/controllers-and-validation.md` |
| `webapp/WEB-INF/jsp/**/*.jsp` | `entities/views.md` |
| `webapp/WEB-INF/tags/**/*.tag` | `entities/views.md` |
| `persistence/src/main/resources/db/migration/*.sql` (Flyway) + `persistence/src/test/resources/schema.sql` (HSQLDB) | `entities/daos.md` + `entities/domain-models.md` |
| `**/*Test.java` | `entities/tests.md` |
| `**/pom.xml` | `concepts/maven-module-structure.md` |
| `webapp/.../WebConfig.java` | `concepts/spring-configuration.md` |
| `webapp/.../WebAuthConfig.java` | `concepts/spring-security.md` |
| `webapp/.../logback.xml` | `concepts/logging-logback.md` |
| `i18n/messages*.properties` | `entities/views.md` (sección i18n) |

### Paso 3 — Leer las páginas afectadas

Para cada página candidata del wiki:
- Read la página actual.
- Read las páginas del código que cambiaron (los archivos .java/.jsp/.sql).
- Comparar: ¿la descripción del wiki sigue siendo precisa?

Signos de desincronización:
- La página menciona una clase/método que ya no existe (renombrado o borrado).
- Hay nuevas clases/métodos/enums que no aparecen en el wiki.
- Cambió una convención (ej. se migró de JUnit 4 a 5) y el wiki sigue con la vieja.
- Conteos desactualizados ("6 DAOs" cuando ahora hay 7).
- Ejemplos de código que ya no compilan contra la codebase actual.

> Nota de contexto: la persistencia ya migró **completa a JPA/Hibernate** — los 14 DAOs de producción son `*JpaDao` con `EntityManager` (`@PersistenceContext`), no quedan `*JdbcDao` / `JdbcTemplate` / `RowMapper`. Si `entities/daos.md` (o cualquier página de persistencia) todavía describe `JdbcTemplate`/`SimpleJdbcInsert`/`RowMapper` como el patrón vigente, está desactualizada y hay que ponerla en términos JPA. El schema de prod son migraciones Flyway en `persistence/src/main/resources/db/migration/`; el `schema.sql` de HSQLDB vive solo en `persistence/src/test/resources/`.

### Paso 4 — Proponer updates

Por cada página con issues:

```
📝 Updates para wiki/entities/services.md

Issues detectados:
1. Menciona 7 services; ahora hay 8 (agregado PaymentService).
2. El snippet de RentService.findOwnedByProvider es viejo — firma cambió.
3. No aparece el nuevo método updateStatus() de RentService.

Diff propuesto:
  - "Los 7 service interfaces/implementations..."
  + "Los 8 service interfaces/implementations..."

  [bloque nuevo]
  + ## PaymentService
  + Gestiona el flujo de pago de una reserva: generación de código, validación
  + de comprobante, transiciones de estado. Implementada en Sprint 2.
  +
  + Métodos clave:
  + - `initiatePayment(rentId, providerId)` → genera código y cambia estado a PAYMENT_PENDING
  + - `uploadProof(rentId, userId, imageId)` → asocia comprobante
  + - `acceptPayment(rentId, providerId)` → transición a PAYMENT_ACCEPTED
  + - `rejectPayment(rentId, providerId, reason)` → transición a PAYMENT_REJECTED
```

### Paso 5 — Actualizar `index.md`

- Chequear que toda página nueva/modificada figure en `index.md`.
- Si agregaste una página nueva → nueva entrada en la categoría correspondiente.
- Si cambió la descripción de una página existente, actualizar el summary en `index.md`.

### Paso 6 — Agregar entrada en `log.md`

Formato:

```markdown
## [YYYY-MM-DD] sync | <breve descripción>
<bullets con las páginas creadas/actualizadas>
- Updated: `wiki/entities/services.md` — agregado PaymentService, actualizado RentService
- Updated: `wiki/entities/enums.md` — 3 nuevos valores de RentStatus documentados
- Updated: `wiki/index.md` — summary de services y enums
```

### Paso 7 — Aplicar (con confirmación)

- Mostrar todos los edits propuestos **antes** de aplicar.
- Si son >3 páginas con cambios grandes, preguntar al usuario: "Esto son X páginas modificadas. ¿Aplico todos los edits o querés revisar uno por uno?"
- Aplicar con Edit (no Write) cuando es un update incremental.
- Usar Write solo para crear páginas nuevas.
- Respetar el template: frontmatter YAML completo (`title`, `type`, `created`, `updated`, `tags`, `sources`), `[[wikilinks]]` en cross-refs, citas con `(source: filename.md)`.

## Casos especiales

- **Nuevo concepto detectado** (ej. se introdujo WebSockets, algo nuevo): sugerir crear una página nueva en `concepts/` y preguntar al usuario antes de crearla. No crear sin confirmación.
- **Borrado de código**: si se eliminó una clase que estaba documentada, marcar la sección como "removed in <sprint>" pero no borrarla del wiki. Preferir append sobre delete.
- **Renombrados**: actualizar wikilinks `[[OldName]]` → `[[NewName]]` en todas las páginas (grep en todo `wiki/`).
- **Cambios solo de formato/estilo** (ej. indentación, rename de variable local): NO requieren update del wiki.

## Formato de reporte final

```
📚 Wiki sync — Rent The Slopes

🔍 Rango analizado: HEAD~5..HEAD (7 commits, 23 archivos)

🎯 Páginas afectadas: 4
  - wiki/entities/services.md (M)
  - wiki/entities/enums.md (M)
  - wiki/concepts/controllers-and-validation.md (M)
  - wiki/entities/domain-models.md (M)

🆕 Páginas nuevas sugeridas: 1
  - wiki/concepts/payment-flow.md — requiere confirmación

✏️  Edits aplicados: 4 páginas + index.md + log.md

⚠️  Pendiente confirmación
  - Crear wiki/concepts/payment-flow.md
  - Renombrar wikilinks [[OldPaymentService]] → [[PaymentService]] (3 ocurrencias)
```

Si todo sincronizado:

```
✅ Wiki sincronizado — ninguna página requiere update en el rango analizado.
```

## Rango (opcional)

$ARGUMENTS
