# Entrega 1 — etapa JDBC

Persistencia con **Spring JDBC**: `JdbcTemplate`, `SimpleJdbcInsert`, `RowMapper`. Todo lo de
esta página es lo que el corrector mira en el TP1 (fuentes: `docs/correcciones-cohorte.md` §2-§3,
`docs/anti-patterns.md`, `docs/testing.md`).

## Declaración de etapa (pegala en tu CLAUDE.md / AGENTS.md)

```markdown
## Etapa de la cursada
ETAPA ACTUAL: JDBC (Entrega 1)
- Persistencia: JdbcTemplate + SimpleJdbcInsert + RowMapper. NADA de JPA/Hibernate todavía.
- Modelos de dominio INMUTABLES: constructor-only, sin setters, campos final.
- FKs en el modelo como `Long xId` (la entidad-objeto llega con la migración JPA).
- Schema: schema.sql aplicado por DataSourceInitializer (sin Flyway todavía).
- NO aplicar reglas JPA: fetch LAZY/EAGER, modelo 1+1, em.flush() en tests, @Formula.
```

## Reglas de la etapa (lo que SÍ aplica)

### DAOs
- Un DAO por tabla; nadie más toca esa tabla.
- `RowMapper` como **`private static final`**, compartido entre métodos — **nunca** lambda inline
  duplicada por método (finding nominal del TP1: el mismo mapper copiado en `findByProductId` y
  `save`).
- Si un mapper necesita reconstruir una entidad de OTRO dominio (ej. `Review` con su `User`),
  reusar el mapper del DAO dueño (`UserJdbcDao.USER_ROW_MAPPER` expuesto `public static final`)
  — no re-mapear inline: se desincroniza en silencio cuando la entidad cambia.
- Inserts con `SimpleJdbcInsert` + `usingGeneratedKeyColumns("id")`.
- **Escapar `%` y `_`** en todo `LIKE` (búsquedas): `replace("\\","\\\\").replace("%","\\%").replace("_","\\_")` + `ESCAPE '\\'`. Finding real de demo.
- Sin N+1: nada de `findById` en loop — `JOIN` o `WHERE id IN (...)` en SQL.
- `java.sql.*` SOLO dentro de `persistence` — el resto del proyecto usa `java.time.*`.

### Modelos
- **Inmutables**: campos `final`, constructor-only, sin setters. (Esta regla se relaja recién con
  JPA — Hibernate exige no-final + constructor vacío. No lo hagas antes de tiempo.)
- Campo opcional = `null` interno + getter `Optional.ofNullable(...)`. `Optional` solo como retorno.
- Enums para vocabularios controlados; `.name()` para persistir.

### Tests (idénticos a la etapa JPA salvo lo marcado)
- `persistence/src/test/` contra HSQLDB (`sql.syntax_pgs=true`); fixtures SOLO en `populator.sql`
  (nunca INSERT/UPDATE en Arrange); asserts de write con `JdbcTestUtils.countRowsInTableWhere`.
- `services/src/test/` con Mockito sobre interfaces de DAO. **Jamás `Mockito.verify`/`spy`**.
- ⚠️ La regla "`em.flush()` antes del assert" **NO aplica** — es de la etapa JPA. Con
  `JdbcTemplate` los writes pegan directo en la BD.

### Lo transversal que el corrector castiga desde el día 1
XSS (`<c:out>`), `<c:url>`, `<spring:message>` + bundles completos, ownership declarativo,
lógica de negocio fuera de controllers, `@Transactional` en services (readOnly en reads),
versiones solo en el pom padre, sin credenciales/URLs hardcodeadas, logging SLF4J a archivos
propios, paginación clampeada (nunca 500 con `page=-1`). Ver el checklist completo en
`docs/anti-patterns.md` y `docs/correcciones-cohorte.md` §5.

## Qué skills usar en esta etapa

Todas — pero con la etapa declarada: `/plan` y `/impl` generan DAOs JDBC (no JPA), y `/gp`,
`/corrector-eyes` y `/deliver` no te van a flagear reglas Hibernate que aún no existen.
El flujo es el mismo: `/plan → /impl → /gp → commit` y `/smoke → /deliver → /corrector` antes
de entregar.

## Señal de que esta etapa termina

La cátedra publica la consigna de la Entrega 2 (Hibernate). En ese momento: leé
[`migracion-jdbc-a-jpa.md`](migracion-jdbc-a-jpa.md) **antes** de tocar el primer DAO.
