---
name: jdbc-to-jpa
description: Migra la persistencia de Spring JDBC a JPA/Hibernate UN agregado (DAO + entidades) por vez, siguiendo el playbook de la cátedra — entidades anotadas, JpaDao con EntityManager, patrón 1+1 en paginación, tests con em.flush(), swap de bean sin tocar contratos. Usar cuando llega la Entrega 2 de PAW ("migrar a Hibernate", "pasar X a JPA", "migrá el UserDao"). Aliases: /migrate
argument-hint: <agregado/DAO a migrar (ej. "User", "ProductDao"), o "fase-0" para la infraestructura inicial>
allowed-tools: [Read, Glob, Grep, Edit, Write, Bash]
---

Ejecutás la migración JDBC → JPA de un proyecto PAW, **un agregado por invocación**. Las fuentes
canónicas son `docs/hibernate-migration.md` (reglas finas con código canónico — LEELA ENTERA antes
de tocar nada) y `etapas/migracion-jdbc-a-jpa.md` del kit (orden de operaciones).

## Pedido

$ARGUMENTS

## Regla de oro

**Incremental, por agregado, siempre verde.** JDBC y JPA conviven sin problema; cada invocación
migra UN agregado y termina con `mvn test` verde y un commit de una línea. Nunca dos agregados a
la vez. Si el pedido nombra varios, migrá el primero y listá el orden sugerido para el resto.

## Paso 0 — Diagnóstico (siempre)

1. ¿Existe la infra JPA? (`LocalContainerEntityManagerFactoryBean` + `JpaTransactionManager` en
   `WebConfig`, ídem en la `TestConfiguration` de persistence, deps `hibernate-core`/`spring-orm`
   en el pom padre). Si NO existe → esta invocación hace **solo la fase 0** (infra + checkpoint
   `mvn clean test` verde con todo aún en JDBC) y termina.
2. Inventario: qué DAOs siguen en JDBC, cuáles ya son JPA, y de quién depende el agregado pedido.
   Si el agregado pedido referencia entidades de un agregado aún no migrado como FK-objeto,
   avisar: conviene migrar primero la hoja (orden típico: User/Image → Product → Price/Block →
   Rent → Review/Favorite).

## Pasos por agregado

1. **Entidades** (§1-§2 de hibernate-migration.md): `@Entity`/`@Table`, `@Id @GeneratedValue
   (SEQUENCE)` + `@SequenceGenerator` con la sequence real del schema, sacar `final`, constructor
   sin args `protected`, `@Column` donde difiere, enums `@Enumerated(EnumType.STRING)`,
   FKs `Long xId` → `@ManyToOne(fetch = FetchType.LAZY) @JoinColumn`. Propagar getters.
2. **`XxxJpaDao implements XxxDao`** con `@PersistenceContext EntityManager em`. **El contrato
   (interfaz) NO cambia** — services y tests de service no se enteran. Reads simples en JPQL;
   listados paginados con relaciones → **patrón 1+1 obligatorio** (§6: nativa de IDs + `JOIN FETCH
   ... WHERE id IN (:ids)` reordenada en memoria; query nativa devuelve `Number` → `.map(Number::longValue)`).
   Escape de `LIKE` (`%`/`_`) se conserva tal cual estaba. `em.getReference(...)` para FKs sin
   SELECT. **Sin `em.flush()` en el DAO.**
3. **Swap de bean**: `@Repository` queda SOLO en el JpaDao. El JdbcDao viejo se borra (preferido)
   — nunca dos beans del mismo contrato, nunca código muerto comentado.
4. **Tests del DAO**: mismos escenarios y fixtures (`populator.sql`, cero inserts en Arrange).
   En cada test de WRITE: `em.flush()` **antes** del `JdbcTestUtils.countRowsInTableWhere`
   (sin flush el assert pasa contra BD vacía — finding real de la cohorte). Inyectar el
   `EntityManager` en el test con `@PersistenceContext`.
5. **Verificar**: `mvn -q test -pl persistence,services`. Si el repo tiene el script del kit,
   correr también `python3 .claude/scripts/paw_checks.py all`.
6. **Cerrar**: proponer commit de UNA línea (`migrate: <Agregado> a JPA`). Si era el ÚLTIMO DAO
   en JDBC: actualizar la declaración de etapa del CLAUDE.md/AGENTS.md a
   `ETAPA ACTUAL: JPA (Entrega 2+)`, recordar borrar restos JDBC y recomendar boot real contra
   PostgreSQL (el usuario corre `mvn jetty:run` — vos no).

## Trampas a NO introducir durante la migración

- `FetchType.EAGER` "para que ande" ante un `LazyInitializationException` → la solución es
  `JOIN FETCH` puntual o materializar antes de un `@Async`, nunca EAGER global.
- `JOIN FETCH` + `setMaxResults` (pagina en memoria) en lugar del 1+1.
- `hbm2ddl.auto=update` — siempre `validate` (el schema lo maneja Flyway/schema.sql).
- Mutar entidades managed fuera del service (dirty checking persiste solo al commit).
- Contadores como columna escrita a mano → `@Formula`.

## Reporte final

Tabla: entidades anotadas · DAO migrado · tests actualizados (con em.flush) · resultado de
`mvn test` · qué agregados quedan en JDBC (orden sugerido).
