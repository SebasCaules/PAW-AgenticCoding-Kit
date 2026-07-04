# AGENTS.md — Proyecto PAW (ITBA)

Instrucciones para el agente de coding que trabaje en este repo. Vienen del `paw-claude-kit`
(tooling batalla-probado en una cursada real de PAW); el detalle fino de convenciones vive en
`docs/` de este repo — **leelas antes de auditar o escribir código**: `docs/testing.md`,
`docs/anti-patterns.md`, `docs/correcciones-cohorte.md`, `docs/security.md`,
`docs/views-and-jsp.md`, `docs/pagination-and-search.md`, entre otras.

## Etapa de la cursada

Buscá en este archivo (o en el doc de instrucciones del repo) la línea `ETAPA ACTUAL:`.
- `ETAPA ACTUAL: JDBC (Entrega 1)` → la persistencia usa Spring JDBC (`JdbcTemplate`,
  `SimpleJdbcInsert`, `RowMapper` estático compartido). NO apliques ni exijas reglas JPA
  (EAGER/LAZY, modelo 1+1, `em.flush()` en tests, `@Formula`) — todavía no existen en el código.
- `ETAPA ACTUAL: JPA (Entrega 2+)` → aplican TODAS las reglas, incluidas las trampas Hibernate
  (fetch LAZY por defecto, paginación 1+1, `@Async` sin lazy sin materializar, `em.flush()` antes
  de asserts, `@Formula` para contadores).
- La migración de una a otra sigue `docs/hibernate-migration.md` (checklist por archivo).

<!-- ETAPA ACTUAL: (declarala acá — JDBC (Entrega 1) | JPA (Entrega 2+)) -->

## Reglas operativas (innegociables)

### BD, server y mails — el usuario ejecuta
- NUNCA corras `psql`, `mvn jetty:run` ni envíes mails. Emití el comando listo para copiar/pegar.
  Antes de cualquier comando destructivo u outbound, primero el comando de PREVIEW (qué filas /
  qué destinatarios).
- NUNCA manipules credenciales/roles en la BD dev para reproducir un bug (sobrescribir passwords,
  insertar admins). Pedí al usuario que se loguee él, o sembrá datos NO sensibles con rollback.

### Verificación antes de declarar "listo"
- Cambio visual (CSS/JSP): verificá contra la página renderizada en localhost, o entregá el cambio
  marcado explícitamente como NO VERIFICADO. Jetty sirve `webapp/target/` — un cambio puede no
  verse hasta rebuild; avisalo de entrada.
- "Los tests pasan" ≠ "la app anda": HSQLDB no ejercita Flyway ni PostgreSQL. Tras un merge o un
  cambio en `db/migration/`: chequeá versiones duplicadas y que el contexto Spring bootee.
  Queries nativas: alias en toda expresión (`EXTRACT`...) — HSQLDB perdona, PostgreSQL no.
- Toda key i18n nueva va en TODOS los bundles de `webapp/src/main/resources/i18n/` en el mismo
  cambio (una key faltante = JasperException en runtime).
- Checks determinísticos del proyecto: `python3 tools/paw_checks.py all` (o
  `.claude/scripts/paw_checks.py` si existe). Corrélos antes de cerrar cualquier tarea y antes
  de commitear. El pre-commit hook (`git config core.hooksPath tools/git-hooks`) los fuerza.

### Formato de entregables
- Commits: UNA línea breve. Sin body.
- Reportes largos: índice breve + archivos por tema; tabla con una fila por finding; link a todo
  archivo mencionado. Sin emojis en documentos para la cátedra.
- "Armá un plan / lista de fixes" = persistí el .md en `0_Plans/<topic>/` — no solo lo muestres.
- Ante duda de formato: preguntá, no asumas.

### Auditorías
- Antes de reportar findings, leé `0_Plans/audits/ADJUDICACIONES.md` si existe (falsos positivos
  ya cerrados — p. ej. CSRF disabled es decisión deliberada de la cátedra). No re-litigues lo
  adjudicado.
- Todo conteo ("hay N endpoints/keys/tests") se verifica con grep contra el código.
- Todo finding con archivo:línea. Sin cita, no existe.

### Bugs
- Si el usuario reporta un síntoma, buscá primero en `0_Plans/BUGS.md` (si existe): puede ser un
  re-reporte con intentos fallidos ya documentados. Registrá los bugs ahí — un bug se describe
  una sola vez.

## Biblioteca de comandos

| Comando | Para qué sirve |
|---|---|
{{COMMANDS_TABLE}}

{{TOOL_NOTES}}
