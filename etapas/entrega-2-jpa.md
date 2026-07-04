# Entrega 2+ — etapa JPA/Hibernate

Persistencia con **JPA/Hibernate** (`EntityManager`, `@PersistenceContext`, namespace
`javax.persistence`). Acá viven las **trampas nuevas del TP2** — la cohorte 2026-1C las pagó caro
(fuente: `docs/correcciones-cohorte.md` §4, `docs/anti-patterns.md` §TP2, `docs/hibernate-migration.md`).

## Declaración de etapa (pegala en tu CLAUDE.md / AGENTS.md)

```markdown
## Etapa de la cursada
ETAPA ACTUAL: JPA (Entrega 2+)
- Persistencia: EntityManager/JPA. Los DAOs nuevos son *JpaDao; no escribir JdbcTemplate nuevo.
- Modelos: entidades JPA (no-final, constructor protected sin args, setters solo donde el service muta).
- FKs mapeadas como ENTIDAD (@ManyToOne ... LAZY), no Long xId pelado.
- Schema: migraciones Flyway en persistence/src/main/resources/db/migration/ + paridad con
  el schema.sql de test (HSQLDB).
- Aplican TODAS las trampas TP2 de abajo.
```

## Las trampas TP2 (error conceptual grave — tolerancia cero del corrector)

1. **`FetchType.EAGER` en cascada.** Default **LAZY** en todo `@ManyToOne`/`@OneToMany`; cada
   EAGER justificado con comentario. Caso real de la cohorte: ~200 queries para paginar una lista.
2. **Paginación con relaciones sin modelo 1+1.** Query 1: IDs paginados (`LIMIT/OFFSET`).
   Query 2: `JOIN FETCH ... WHERE id IN (:ids)` + reordenar en memoria según los IDs. `JOIN FETCH`
   directo con `setMaxResults` pagina EN MEMORIA (Hibernate trae la tabla entera). Patrón canónico
   completo en `docs/hibernate-migration.md` §6.
3. **`@Async` + relaciones lazy.** El thread async no tiene la sesión Hibernate: materializar
   antes de cruzar (`entity.getRelacion().getId()`) o `JOIN FETCH` en la query que alimenta.
4. **Tests de write sin `em.flush()`.** Sin flush, el write queda en el first-level cache y
   `JdbcTestUtils.countRowsInTableWhere` lee la BD vacía → el assert pasa sin testear nada.
   El `flush()` va **en el test** (antes del assert), no en el DAO.
5. **Contadores como columna escrita por varios DAOs.** Usar `@Formula("(SELECT COUNT(*) ...)")`.
   Ídem `.size()` sobre colección lazy solo para contar → `COUNT(*)` o `@Formula`.
6. **FK como `Long xId`.** Mapear la entidad (`@ManyToOne Product product`). Sin la relación,
   JPQL no navega y la BD pierde integridad referencial. (Las firmas públicas de DAO/service
   siguen recibiendo IDs; el DAO resuelve con `em.getReference(...)` — ver `docs/guidelines.md`.)
7. **Precedencia `OR`/`AND` sin paréntesis** en JPQL/SQL — filtros que fugan datos.
8. **Dirty checking**: toda mutación de una entidad managed dentro de transacción SE PERSISTE
   sola al commit. No mutar entidades en controllers/vistas; la mutación vive en el service.
9. **`hsqldb` con scope `compile` en webapp** → siempre `test`.

## Qué cambia respecto de la Entrega 1

| Tema | Entrega 1 (JDBC) | Entrega 2 (JPA) |
|---|---|---|
| DAO | `JdbcTemplate` + `RowMapper` estático | `EntityManager` + JPQL/nativas |
| Modelos | Inmutables, constructor-only | Entidades: no-final, ctor vacío `protected`, setters mínimos |
| FKs en el modelo | `Long xId` | `@ManyToOne(fetch = LAZY) Entidad x` |
| Paginación con relaciones | `JOIN` + `LIMIT/OFFSET` en SQL | **Modelo 1+1 obligatorio** |
| Tests de write | assert directo con `JdbcTestUtils` | **`em.flush()` antes** del assert |
| Schema | `schema.sql` (DataSourceInitializer) | Flyway (prod) + paridad `schema.sql` de test |
| Contadores derivados | columna o COUNT en SQL | `@Formula` |

Los tests de lectura, el `populator.sql`, la prohibición de `Mockito.verify` y todo lo
transversal (XSS, i18n, ownership, layering) siguen idénticos.

## Qué skills usar en esta etapa

Todas, con `ETAPA ACTUAL: JPA` declarada — `/gp` y `/corrector-eyes` activan el set completo de
trampas Hibernate, `/deliver` exige paridad Flyway↔schema de test, y `/jdbc-to-jpa` te queda para
los DAOs que falten migrar.

## Señal de que esta etapa termina

La cátedra publica la consigna de la **entrega final** (API REST + SPA). Antes de escribir el
primer endpoint, leé [`entrega-final-spa-rest.md`](entrega-final-spa-rest.md): en esa migración
el contrato se cierra en papel ANTES que el código, y la capa de services que construiste en
estas dos etapas queda intacta — es exactamente lo que la API va a exponer.
