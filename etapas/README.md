# etapas/ — la cursada por etapas (JDBC → JPA → SPA+REST)

PAW se cursa en etapas: la **Entrega 1** se hace con **Spring JDBC** (`JdbcTemplate`,
`SimpleJdbcInsert`, `RowMapper`), en la **Entrega 2** la cátedra exige migrar la persistencia a
**JPA/Hibernate**, y la **Entrega Final** convierte el webapp JSP en una **API REST + SPA**.
Muchas reglas del kit son de una etapa específica — auditar un proyecto JDBC con reglas JPA
(o una SPA con reglas JSP) genera falsos positivos y ruido.

| Doc | Cuándo leerlo |
|---|---|
| [`entrega-1-jdbc.md`](entrega-1-jdbc.md) | Desde el día 1 hasta que la cátedra pida Hibernate. Reglas JDBC + qué reglas del kit NO aplican todavía |
| [`migracion-jdbc-a-jpa.md`](migracion-jdbc-a-jpa.md) | Cuando llega la consigna de migrar. Playbook fase por fase + la skill `/jdbc-to-jpa` |
| [`entrega-2-jpa.md`](entrega-2-jpa.md) | Desde que el primer DAO es JPA en adelante. Las trampas Hibernate que más nota costaron en la cohorte |
| [`entrega-final-spa-rest.md`](entrega-final-spa-rest.md) | Cuando llega la consigna final. El contrato REST primero, backend por olas (Jersey + JWT stateless + DTOs/mappers) y SPA pantalla-por-pantalla en espejo — con la tabla de qué regla JSP muere y cuál la reemplaza |

## Cómo le decís al agente en qué etapa estás

Las skills de auditoría del kit (`/gp`, `/corrector-eyes`, `/pre-delivery`) y los exports a otros
tools leen una declaración de etapa. Ponela en el `CLAUDE.md` de tu repo (o en el
`AGENTS.md`/`GEMINI.md` si usás otro agente):

```markdown
## Etapa de la cursada
ETAPA ACTUAL: JDBC (Entrega 1)
```

cuando migres la persistencia:

```markdown
## Etapa de la cursada
ETAPA ACTUAL: JPA (Entrega 2+)
```

y cuando arranque la entrega final:

```markdown
## Etapa de la cursada
ETAPA ACTUAL: SPA+REST (Entrega Final)
```

Si no hay declaración, las skills asumen **JPA** — declarala desde el día 1 para no comerte
findings de Hibernate en un TP que todavía usa `JdbcTemplate`, ni reglas de JSP sobre una SPA.

> El script de checks ya es etapa-aware: si tu repo no tiene `db/migration/` (Flyway llega
> con/tras la migración), el check de versiones duplicadas se saltea con un warning en vez de fallar.
