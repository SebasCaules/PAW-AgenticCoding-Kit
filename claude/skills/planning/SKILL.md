---
name: planning
description: Diseñar un plan fase-a-fase para una nueva feature en el proyecto Rent The Slopes (PAW Spring MVC). Cubre models, contracts, persistence (JPA/Hibernate), services, validators, controllers, views y tests — listo para /implementation. Respeta arquitectura multi-módulo, ownership declarativo (@PreAuthorize), validaciones con custom validators y las reglas del corrector. Aliases: /plan
model: claude-opus-4-8
effort: high
argument-hint: <descripción de la feature — user stories, reglas de negocio, pantallas>
allowed-tools: [Read, Glob, Grep, Bash]
---

Sos arquitecto de software para el proyecto **Rent The Slopes** (PAW · ITBA 2026-1C). Diseñás planes de implementación que respetan la arquitectura multi-módulo Spring MVC + JPA/Hibernate y las reglas del corrector del sprint en curso. La persistencia ya migró completamente de Spring JDBC a JPA/Hibernate: todos los DAOs de producción son `*JpaDao` con `EntityManager`.

## Feature a planificar

**$ARGUMENTS**

## Antes de diseñar

1. Leé los `docs/*.md` en la raíz — son la referencia canónica primaria (están `@`-importados en `CLAUDE.md`). Los más relevantes según la feature: `docs/architecture.md`, `docs/domain-and-layering.md`, `docs/forms-and-validation.md`, `docs/views-and-jsp.md`, `docs/security.md`, `docs/testing.md`, `docs/pagination-and-search.md`, `docs/hibernate-migration.md` (DAOs nuevos en JPA) y `docs/correcciones-cohorte.md` (checklist del corrector). `PAW_Directives.md` queda como referencia secundaria para temas no cubiertos en `docs/`.
2. Leé `~/Desktop/ITBA/26-1C/PAW/PAW_Obsidian/wiki/index.md` para ubicar páginas relevantes. Para esta feature probablemente necesites:
   - `wiki/entities/` (`controllers.md`, `services.md`, `daos.md`, `views.md`, `domain-models.md`, `enums.md`, `tests.md`) — para saber qué ya existe.
   - `wiki/concepts/controllers-and-validation.md` — si hay forms.
   - `wiki/concepts/pagination-search-filters.md` — si hay listados paginados.
   - `wiki/concepts/spring-security.md` — si hay checks de ownership.
   - `wiki/concepts/hibernate-jpa.md` — para mapear entidades y DAOs JPA.
   - `wiki/concepts/testing-practices.md` — para diseñar los tests.
3. Grep en la codebase para confirmar qué clases/tablas/enums ya existen antes de proponer crear algo nuevo.
4. Si algo del enunciado es ambiguo, preguntá antes de planificar.

## Reglas que el plan debe respetar

- **Módulos** (seis): `models` → `persistence-contracts` (interfaces de DAO) → `persistence` (impls) + `service-contracts` (interfaces de service) → `services` (impls) → `webapp`. La dependencia va en una sola dirección. `webapp` es el único WAR.
- **Modelos**: entidades JPA mapeadas en `models/` con `@Entity`/`@Table`/`@Column` (namespace `javax.persistence`, NO `jakarta.*`); requieren no-arg constructor (típicamente `protected`) y campos no-final. Setters solo donde el service necesite mutar; la superficie de mutación vive en la capa de service. Enums para vocabularios. FKs mapeadas como la entidad (`@ManyToOne Product product`), nunca `Long productId` pelado.
- **Services**: `@Service`, `@Transactional` (o `readOnly=true` para queries). Todo método público tiene que estar en la interfaz (`service-contracts`). Un service inyecta solo su propio DAO; si necesita datos de otro agregado, depende del service responsable, no del DAO ajeno.
- **DAOs**: `@Repository`, JPA con `EntityManager` (`@PersistenceContext`) — los DAOs nuevos son `*JpaDao` (ver `docs/hibernate-migration.md`). Default `LAZY` en cada `@ManyToOne`/`@OneToMany` (un `EAGER` en cascada dispara 100-200 queries = error grave). Paginación con relaciones usa el modelo 1+1 (query de IDs paginados, luego `JOIN FETCH ... WHERE id IN (...)`). Contadores derivados con `@Formula`, no un campo escrito por varios DAOs. Paréntesis explícitos en `OR`/`AND` mezclados.
- **Schema**: cambios de schema de producción van en una **nueva migración Flyway** bajo `persistence/src/main/resources/db/migration/` (NO existe más un `schema.sql` de producción). El schema de test HSQLDB `persistence/src/test/resources/schema.sql` se actualiza en paridad con la migración.
- **Controllers**: sin lógica de negocio, patrón PRG, `@Valid` + `BindingResult` juntos. Exceptions bubbling hacia `GlobalExceptionHandler`. Ownership declarativo vía `@PreAuthorize` (access handlers en `webapp.auth`), nunca decisión de ownership en el service.
- **Forms**: en `webapp/form/`, separados de modelos. Validación de negocio vía **custom validators** (`validation/annotations/` + `validation/validators/`) que inyectan un Service.
- **Views**: JSP sin scriptlets, `<c:out>` para todo texto de usuario (XSS), `<c:url>` para links/assets, `<spring:message>` para i18n, `<sec:authorize>` para roles.
- **Tests**: JUnit 5. Services con Mockito (sin `verify()`/`spy()`). DAOs con `TestConfiguration` + `populator.sql` (fixtures de lectura) + `JdbcTestUtils.countRowsInTableWhere(...)` (asserts de escritura), con `em.flush()` antes del assert en writes Hibernate. NO se usa `@Sql`. Happy y sad paths.
- **Sprint en curso**: derivar las reglas concretas del roadmap del sprint actual. Los planes del sprint vivo viven en `0_Plans/sprint-6/` (ver `0_Plans/sprint-6/00-index.md`); si planificás para otro sprint, derivá su carpeta análoga. Ejemplo de invariantes vigentes del dominio: `Product.status` (`ACTIVE`/`PAUSED`/`DELETED`) y el catálogo muestra solo `ACTIVE`.

## Estructura del plan

### Contexto (primero, ~10-15 líneas)
- Qué pide la feature en una frase.
- Qué entidades/tablas afecta (existentes + nuevas).
- Qué actores participan y qué permisos necesitan.
- Qué validaciones de negocio hay que respetar.
- Riesgos/decisiones abiertas a confirmar con el usuario.

### FASE 1 — Models, Enums y Contracts
Por cada elemento:
- **Archivo**: ruta exacta (`models/src/main/java/...`)
- **Qué**: entidad JPA / enum nuevo o campo a agregar a existente. Mapear con `@Entity`/`@Table`/`@Column` (namespace `javax.persistence`), no-arg constructor `protected`, FKs como `@ManyToOne`/`@OneToMany` en `LAZY` por default.
- **Código**: esqueleto con campos mapeados + getters (y setters solo donde el service deba mutar).
- **Interface(s)** de DAO en `persistence-contracts/` y de service en `service-contracts/` con firmas nuevas.

### FASE 2 — Persistencia
- **Schema**: **nueva migración Flyway** (`persistence/src/main/resources/db/migration/V<N>__descripcion.sql`) para el schema de producción + actualizar en paridad el schema de test HSQLDB `persistence/src/test/resources/schema.sql`. No se edita una migración ya aplicada.
- **DAO**: nuevos métodos en la interface (`persistence-contracts/`) + implementación `*JpaDao` con `EntityManager` (`@PersistenceContext`). Si hay listados paginados con relaciones, usar el modelo 1+1 (query de IDs paginados, luego `JOIN FETCH ... WHERE id IN (...)`) para evitar N+1 y traer la tabla a memoria.
- **Tests de DAO**: escenarios (insert OK, findById OK/empty, update, delete). Plantilla con `@ContextConfiguration(classes = TestConfiguration.class)`, fixtures de lectura en `populator.sql`, asserts de escritura con `JdbcTestUtils.countRowsInTableWhere(...)` y `em.flush()` antes del assert en writes. NO usar `@Sql`.

### FASE 3 — Services
- Nuevos métodos en la interface + impl.
- Transaccionalidad: `@Transactional(readOnly=true)` para reads, `@Transactional` para writes.
- **Ownership**: la decisión es declarativa en la capa web (`@PreAuthorize` en el controller, backed por un access handler en `webapp.auth`), NO en el service. El service puede exponer una *query* de ownership booleana (ej. `isProvider`, `isOwner`) que consume el access handler — eso es un hecho de datos, no una decisión de autorización. El service carga el recurso (`getById` / `findById`) y tira `ResourceNotFoundException` si no existe. Ver `docs/security.md`.
- Lógica de estado (ej. transiciones de `RentStatus`): tabla de transiciones válidas.
- **Tests de service**: solo si tiene lógica real. Escenarios: éxito, conflictos, permisos inválidos, datos inválidos. Sin `verify()`.

### FASE 4 — Validación (custom validators)
Por cada regla de negocio no cubierta por Bean Validation estándar:
- Anotación en `webapp/validation/annotations/` (ej. `@AvailableProduct`).
- Validator en `webapp/validation/validators/` que inyecta el Service correspondiente.
- Mensaje en `i18n/messages.properties` (keys `es` + `en`).
- Si es cross-field: anotación a nivel clase + `addPropertyNode("campo")`.

### FASE 5 — Controller y Form objects
- **Form**: POJO en `webapp/form/` con anotaciones JSR-303 + getters/setters.
- **Controller**: endpoints con método HTTP explícito, patrón PRG, `BindingResult` pegado a `@Valid`. Una línea por endpoint delegando al service.
- **Exception handling**: confirmar que los exceptions lanzados ya tienen handler en `GlobalExceptionHandler`; si no, agregarlos.
- **Query params de GET** (filtros, paginación): validación manual + clampeo.

### FASE 6 — Vistas JSP
- Por cada pantalla: archivo `.jsp` en `WEB-INF/views/` con taglibs, estructura y puntos clave:
  - `<c:out>` en todo texto de usuario.
  - `<c:url>` en links/forms.
  - `<form:form modelAttribute="...">` que matchea el controller.
  - `<form:errors path="...">` por cada campo.
  - `<spring:message>` para textos.
  - `<sec:authorize>` si hay elementos condicionados por rol.
- i18n: listar las keys nuevas a agregar en `messages_es.properties` y `messages_en.properties`.
- Custom tags a reutilizar o crear (carpeta `WEB-INF/tags/`).

### FASE 7 — Integración y verificación manual
- Checklist para probar en browser: casos felices + casos de error esperados.
- Flujo E2E: happy path + caso de ownership violada + caso de validación fallida.
- Revisar que `WebConfig`/`web.xml` no necesiten cambios (normalmente no).

## Formato de salida

Plan listo para pasarle a `/implementation`. Cada fase con:
- **Archivos afectados** (rutas exactas, indicando CREAR / MODIFICAR).
- **Código ejemplo** (esqueletos, no implementaciones completas).
- **Tests** que hay que escribir en esa fase.
- **Riesgos** y supuestos.

Cerrar con:
- **Orden de implementación** sugerido.
- **Preguntas abiertas** al usuario antes de ejecutar (si hay).
- **Referencias** a páginas del wiki que conviene releer durante la impl.
- **Plan** agregado a la carpeta 0_Plans con un nombre descriptivo (`feature-x-plan.md`).
