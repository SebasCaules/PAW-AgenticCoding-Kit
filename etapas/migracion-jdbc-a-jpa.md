# Migración JDBC → JPA/Hibernate — playbook

Cómo pasar de la Entrega 1 a la 2 **sin romper nada y sin regalar nota**. La referencia técnica
completa (con código canónico de cada patrón) es [`docs/hibernate-migration.md`](../docs/hibernate-migration.md)
— este playbook es el orden de operaciones; aquella, la regla fina de cada paso. La skill
[`/jdbc-to-jpa`](../claude/skills/jdbc-to-jpa/SKILL.md) ejecuta este playbook un DAO por vez.

> Regla de oro: **la migración es incremental y por agregado**. JDBC y JPA conviven sin problema
> (un `UserJdbcDao` y un `ProductJpaDao` pueden vivir juntos semanas). Nunca migres dos agregados
> en el mismo commit; cada DAO migrado deja el build verde y los tests pasando.

## Fase 0 — Infraestructura (una sola vez)

1. **Deps** en el pom padre (`<dependencyManagement>`, versiones por property): `hibernate-core`,
   `spring-orm`. `persistence` las referencia solo por groupId+artifactId.
2. **`WebConfig`**: reemplazar el `DataSourceTransactionManager` por
   `LocalContainerEntityManagerFactoryBean` (packages a escanear: `ar.edu.itba.paw.models`) +
   `JpaTransactionManager`. Propiedades Hibernate: dialect PostgreSQL, `hbm2ddl.auto=validate`
   (nunca `update` en prod).
3. **`TestConfiguration`** (persistence/src/test): mismo cambio contra HSQLDB.
4. **Flyway** (si la cátedra lo pide en esta entrega): mover el schema a
   `persistence/src/main/resources/db/migration/V1__baseline.sql` y de acá en más todo cambio de
   schema = migración nueva + actualización del `schema.sql` de test (paridad HSQLDB).
5. Checkpoint: `mvn clean test` verde con TODOS los DAOs todavía en JDBC.

## Fase 1 — Entidades (por agregado, junto con su DAO)

Por cada modelo del agregado a migrar (`docs/hibernate-migration.md` §1-§2):
- `@Entity` + `@Table`; `@Id @GeneratedValue(SEQUENCE)` con su `@SequenceGenerator`.
- Sacar `final` de los campos; constructor sin args `protected`; IDs `Long`.
- `@Column` donde el nombre/constraint difiere; enums con `@Enumerated(EnumType.STRING)`.
- FKs `Long xId` → **entidad** `@ManyToOne(fetch = FetchType.LAZY) @JoinColumn(...)`. Propagar el
  cambio de getters (`getAuthorId()` → `getAuthor().getId()` o exponer un delegante).

## Fase 2 — DAO por DAO (orden recomendado: hojas primero)

Migrar primero los agregados sin dependencias hacia otros (típico: `User`, `Image`), después los
que referencian a esos (`Product`), y al final los más relacionales (`Rent`, `Review`, `Favorite`).
Por cada DAO — checklist destilado de `docs/hibernate-migration.md` §9:

1. Crear `XxxJpaDao implements XxxDao` con `@PersistenceContext EntityManager em`.
   **La interfaz del contrato NO cambia** (los services no se enteran).
2. Reads simples → JPQL; búsquedas complejas/paginadas → patrón **1+1** (§6): query nativa de IDs
   + JPQL `JOIN FETCH ... WHERE id IN (:ids)` reordenada. Escape de `LIKE` se conserva.
3. Writes: `em.persist` / dirty-checking sobre entidad managed. **Sin `em.flush()` en el DAO.**
   Para poblar FKs sin SELECT: `em.getReference(...)`.
4. Sacar el `@Repository` del `XxxJdbcDao` (o borrarlo directo) y dejarlo solo en el JpaDao —
   nunca dos beans del mismo contrato activos.
5. Tests del DAO: mismos escenarios; en cada test de write agregar `em.flush()` **antes** del
   `JdbcTestUtils`. Ni un INSERT nuevo en Arrange — sigue todo en `populator.sql`.
6. `mvn test -pl persistence,services` verde → commit (una línea: `migrate: XxxDao a JPA`).

## Fase 3 — Cierre

- Borrar los `XxxJdbcDao` muertos (código comentado/stale = finding).
- Actualizar la **declaración de etapa** en CLAUDE.md/AGENTS.md a `ETAPA ACTUAL: JPA (Entrega 2+)`.
- Pasada completa: `/smoke` → `/gp` (ahora con trampas TP2 activas) → boot real contra PostgreSQL
  (el usuario corre `mvn jetty:run`) — dirty checking y lazy-loading solo se ven en runtime.
- Leer [`entrega-2-jpa.md`](entrega-2-jpa.md): desde acá rigen las trampas TP2.

## Errores clásicos DE la migración (todos pasaron de verdad)

- Migrar el test "a medias": el DAO ya es JPA pero el test no hace `em.flush()` → asserts que
  pasan con la BD vacía (finding real de la cohorte).
- `JOIN FETCH` + `setMaxResults` (paginación en memoria) en vez del 1+1.
- Dejar `hbm2ddl.auto=update` — pisa/crea schema por atrás de Flyway.
- EAGER "para que ande" al primer `LazyInitializationException` — la solución es `JOIN FETCH`
  puntual o materializar antes del `@Async`, no EAGER global.
- Dos beans del mismo contrato (`@Repository` en el Jdbc y el Jpa) → `NoUniqueBeanDefinitionException`.
- Query nativa que devuelve `Number`: convertir con `.map(Number::longValue)` antes del `IN`.
