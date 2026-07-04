---
name: pre-delivery
description: Corre el checklist completo de pre-entrega de Rent The Slopes (PAW). Verifica estructura Maven, configuración Spring, DI, controllers, vistas, persistencia, testing, i18n, seguridad y reglas del sprint actual. Además corre `mvn compile` + `mvn test` para asegurar que compila y los tests pasan. Usar antes de cada entrega. Aliases: /deliver
model: claude-opus-4-8
effort: high
argument-hint: [opcional: "--skip-tests" para saltear mvn test si ya está probado]
allowed-tools: [Read, Glob, Grep, Bash]
---

Sos el responsable de que la entrega salga sin regalar puntos al corrector. Ejecutás el checklist completo de pre-delivery del proyecto **Rent The Slopes** (PAW · ITBA 2026-1C).

## Fuentes de verdad

- `docs/correcciones-cohorte.md` §5 — checklist negativo canónico de pre-entrega (consolida TP1+TP2). Fuente primaria.
- `PAW_Directives.md` — checklist oficial de la cátedra (citar por nombre; no tiene secciones numeradas).
- `~/Desktop/ITBA/26-1C/PAW/PAW_Obsidian/wiki/concepts/pre-delivery-checklist.md` — versión del wiki.
- Indicaciones del sprint actual (ver `PAW_Obsidian/wiki/sources/sprint-<N>-indicaciones.md`, p. ej. `sprint-2-indicaciones.md`).

## Proceso

Ejecutá los bloques en orden. Por cada item: ✅ si cumple, ❌ si no (con archivo+línea), ⚠️ si hay ambigüedad. Podés ir mostrando el progreso en vivo.

### Bloque 0 — Smoke determinístico (fast-path, < 2 min — SIEMPRE primero)

```bash
python3 .claude/scripts/paw_checks.py all   # paridad i18n + Flyway duplicados + balance JSTL
mvn -q -pl webapp -am test-compile          # compila main+tests de todos los módulos
```

- Estos son los fallos que "tests verdes" no atrapa y explotaron en entregas pasadas: keys i18n cojas (JasperException en runtime), versiones Flyway duplicadas post-merge (la app no bootea), tags JSTL desbalanceados (500).
- Si el Bloque 0 da ❌: reportarlo YA con el detalle y preguntar si seguís con el resto del checklist — estos fixes son siempre prioridad 1.
- Recordar (sin ejecutarlo vos — regla del proyecto): la verificación final de boot real es del usuario: `cd webapp && mvn jetty:run` contra PostgreSQL.

### Bloque 1 — Estructura Maven

- [ ] Existen los 6 módulos: `models`, `persistence-contracts`, `persistence`, `service-contracts`, `services`, `webapp`. (`webapp` es el único WAR; `*-contracts` = interfaces, `persistence`/`services` = implementaciones.)
- [ ] Versiones **solo** en pom padre (`<properties>` + `<dependencyManagement>`). Los scopes también viven una sola vez en el padre.
- [ ] Poms hijos **sin** `<version>` (ni `<scope>` ni `<type>`) en `<dependencies>` (grep `<version>` en cada hijo).
- [ ] `services` tiene scope `runtime` (en el `<dependencyManagement>` del padre).
- [ ] `javax.servlet-api` tiene scope `provided`.
- [ ] `spring-test`, `hsqldb`, `mockito-core` tienen scope `test`.

### Bloque 2 — Configuración Spring

- [ ] `WebConfig.java` tiene `@EnableWebMvc`, `@Configuration`, `@ComponentScan` con los 3 paquetes (controller, service, persistence).
- [ ] Define beans: `ViewResolver`, `DataSource`, `MessageSource`, `DataSourceInitializer`.
- [ ] `web.xml` es versión 2.4 con XML Schema (no DTD 2.3).
- [ ] `contextClass` = `AnnotationConfigWebApplicationContext` aparece dos veces (context-param y init-param del servlet).
- [ ] `ContextLoaderListener` declarado.
- [ ] `DispatcherServlet` mapeado a `/`.

### Bloque 3 — Inyección de dependencias

- [ ] Cero `new UserServiceImpl()` / `new XxxDaoImpl()` fuera de tests: `grep -r "new [A-Z][a-zA-Z]*\(Service\|Dao\)Impl"`.
- [ ] Estereotipos correctos por módulo: `@Controller` en webapp, `@Service` en services, `@Repository` en persistence.
- [ ] DAOs con constructor `@Autowired` recibiendo `DataSource`.
- [ ] Todo método público del service está declarado en la interface.

### Bloque 4 — Controllers y validación

- [ ] `BindingResult` siempre inmediatamente después de `@Valid` (grep controllers).
- [ ] Cero `try-catch` en controllers (grep `try\s*\{` en `controller/`).
- [ ] Cero lógica de negocio en controllers: si un método tiene >20 líneas o tiene `if` con reglas de dominio, revisar a mano.
- [ ] Form objects en `ar.edu.itba.paw.webapp.form/`, separados de modelos.
- [ ] `GlobalExceptionHandler` maneja `ResourceNotFoundException`, `ForbiddenException`, `MaxUploadSizeExceededException`.
- [ ] Custom validators estructurados en `validation/annotations/` + `validation/validators/`.

### Bloque 5 — Vistas JSP

- [ ] Cero scriptlets: `grep -rE "<%[^@\-]" webapp/src/main/webapp/WEB-INF/ | grep -v "<%--"`.
- [ ] Todo JSP tiene taglibs `c`, `spring`, `form` al inicio.
- [ ] Texto de usuario → `<c:out>` (correr `/xss-scan` internamente o mencionar al usuario).
- [ ] URLs con `<c:url>` (grep `href="/` y `src="/` fuera de `<c:url>`).
- [ ] Textos visibles con `<spring:message>` (correr `/i18n-sync` internamente o mencionar al usuario).

### Bloque 6 — Persistencia (JPA / Hibernate)

> El proyecto YA es JPA: los 14 DAOs de producción son `*JpaDao` con `EntityManager` (`@PersistenceContext`). Namespace `javax.persistence` (no `jakarta.*`). No quedan `JdbcTemplate` / `SimpleJdbcInsert` / `RowMapper` en DAOs de producción.

- [ ] Schema: producción con migraciones **Flyway** en `persistence/src/main/resources/db/migration/`; único `schema.sql` es el de **test** (HSQLDB) en `persistence/src/test/resources/schema.sql`. Toda migración Flyway que cambie estructura actualiza el `schema.sql` de test (paridad).
- [ ] Default `LAZY` en todo `@ManyToOne` / `@OneToMany`; cada `EAGER` justificado y comentado (EAGER en cascada dispara 100-200 queries = grave).
- [ ] Paginación con relaciones usa modelo 1+1 (query de IDs paginados, luego `JOIN FETCH ... WHERE id IN (...)`).
- [ ] FKs mapeadas como la entidad (`@ManyToOne Product product`), no `Long productId` pelado.
- [ ] `@Async` materializa relaciones lazy ANTES de cruzar de thread (si no, `LazyInitializationException`).
- [ ] Sin `.size()` sobre colección lazy — usar `COUNT(*)` o `@Formula`. Contadores derivados con `@Formula`, no columna escrita por varios DAOs.
- [ ] HQL/SQL con `OR`/`AND` mezclados tiene paréntesis explícitos.
- [ ] **No N+1**: nada de `findById` en loop; JOIN en SQL o `WHERE id IN (...)`.
- [ ] `@Transactional` solo en services (grep `@Transactional` fuera de services/). `readOnly=true` en lecturas; sin flags en writes.
- [ ] `java.sql.*` solo dentro de `persistence`. Cada tabla con un único DAO.

### Bloque 7 — Testing

- [ ] Tests viven **solo** en `persistence/src/test` y `services/src/test` — nunca en `webapp/` ni `models/`.
- [ ] Todos los tests son JUnit 5: grep `org.junit.Test` (JUnit 4) → debe dar 0.
- [ ] Sin `Mockito.verify(` ni `Mockito.spy(` en tests (grep). Tampoco `AtomicReference`+`doAnswer` reimplementando verify.
- [ ] Tests de DAO: `@Rollback @Transactional @ExtendWith(SpringExtension.class) @ContextConfiguration(classes = TestConfiguration.class)`; fixtures de lectura desde `populator.sql`; asserts de write con `JdbcTestUtils.countRowsInTableWhere(...)`. **No** usan `@Sql`.
- [ ] Tests de write de Hibernate llaman `em.flush()` antes del assert (si no, el cambio queda en el first-level cache y el assert falsea).
- [ ] Tests de Service usan `@ExtendWith(MockitoExtension.class)` + `@Mock` + `@InjectMocks`.
- [ ] Cobertura: cada service con lógica real tiene tests; cada DAO tiene tests. Happy y unhappy paths (`assertThrows`).

### Bloque 8 — Seguridad

- [ ] `WebAuthConfig` usa `SecurityFilterChain` (no `WebSecurityConfigurerAdapter` deprecated).
- [ ] `CurrentUserAdvice` expone `@ModelAttribute("loggedUser")`.
- [ ] `rememberMeKey` via `@Value("${rememberme.key}")`, no hardcodeado.
- [ ] `SecurityContextHolder` solo en `webapp.auth` y `CurrentUserAdvice` (grep en services/, persistence/ y controllers).
- [ ] Ownership **declarativo en la capa web**: `@PreAuthorize` en el controller respaldado por access handlers (`ProductAccessHandler`/`ReportAccessHandler`/`RentAccessHandler` en `webapp.auth`); cero `@PreAuthorize` en services; el service no tira `ForbiddenException` como gate primario (ver `docs/security.md` §Ownership). Chequeo integrado (ex skill `/ownership-audit`): todo endpoint que recibe un ID de recurso tiene su `@PreAuthorize` o su matcher en `WebAuthConfig` — nunca un `if` manual en el controller.

### Bloque 9 — Logging

- [ ] Cero `System.out.println` / `printStackTrace()` fuera de tests.
- [ ] SLF4J con `{}` placeholder, no concatenación con `+`.
- [ ] `logback.xml` configurado con nivel `INFO` o `WARN` por default.

### Bloque 10 — Sprint actual

Detectar el sprint actual (hoy es **Sprint 6**):
1. Mirar `0_Plans/sprint-6/00-index.md` (o `0_Plans/sprint-<N>/00-index.md` para el sprint en curso) y las indicaciones del corrector en `PAW_Obsidian/wiki/sources/sprint-<N>-indicaciones.md` si existen.
2. Buscar en `PAW_Directives.md` la sección de novedades del sprint en curso.
3. Si no hay marcador claro o no hay roadmap del sprint, preguntar al usuario y degradar con gracia.
4. Aplicar las reglas específicas del sprint en curso.
   - *Ejemplo histórico (Sprint 2, solo de referencia):* `ProductStatus` (catálogo solo `ACTIVE`), `RentStatus` con 9 valores, `payment_image_id`, paginación+filtros+búsqueda con 3 forms, locale del email desde `user.preferredLanguage`.

### Bloque 11 — Build y tests

A menos que `$ARGUMENTS` contenga `--skip-tests`:

```bash
mvn clean compile -q           # debe compilar sin warnings
mvn test -q                     # todos los tests verdes
```

Si falla: reportar el error con el archivo/línea y parar (no seguir con blocks posteriores).

### Bloque 12 — Git sanity

```bash
git status                     # ¿hay cambios sin commitear?
git log --oneline -10          # últimos commits coherentes
```

- [ ] No hay archivos sensibles (`.env`, credentials, `target/`, `.idea/`, `.DS_Store`) en el árbol.
- [ ] El `.gitignore` está actualizado.

## Formato de reporte

Mostrar progreso por bloque con checks. Al final, resumen:

```
🎯 Pre-Delivery Report — Sprint X

✅ Bloque 1 — Maven              (8/8)
✅ Bloque 2 — Spring Config      (6/6)
⚠️  Bloque 3 — DI                (3/4)
   ❌ UserServiceImpl.java:42 — `new EmailHelper()` en vez de @Autowired
...

📊 Totales
  ✅ 45 checks OK
  ⚠️  3 checks warning
  ❌ 2 checks críticos → arreglar ANTES de entregar

🔥 Prioridad de fixes
1. [CRITICAL] persistence/schema.sql (test) no tiene la columna `payment_image_id`
2. [CRITICAL] ProductController.delete sin ownership check
3. [WARNING]  3 keys i18n faltan en messages_en.properties
```

Si todo verde:

```
✅ LISTO PARA ENTREGAR — 50/50 checks pasaron. mvn compile OK. mvn test OK.
```

## Notas

- Si el proyecto no compila, DETENETE y reportalo primero. Todo lo demás pasa a segundo plano.
- Los chequeos de XSS (`${var}` crudo fuera de `<c:out>`/`<c:url>`/`<spring:message>`/`<form:*>`/`<sec:*>` en Bloque 5) y de ownership declarativo (Bloque 8) están **integrados** en este checklist — las ex-skills `/xss-scan` y `/ownership-audit` fueron absorbidas acá (archivo en `.claude/skills-archived/`). `/i18n-sync` sigue existiendo para el diff fino de keys; el Bloque 0 ya corre la paridad automática.
- Antes de reportar findings, cruzar con `0_Plans/audits/ADJUDICACIONES.md` (CSRF disabled es deliberado, `_es` vacío hereda, etc.) — no re-flagear lo adjudicado.
- Preguntar al usuario por el sprint si no podés detectarlo (afecta block 10).

## Opciones (opcional)

$ARGUMENTS


## Etapa de la cursada (JDBC vs JPA)

El Bloque 6 (Persistencia) se evalúa según la línea `ETAPA ACTUAL:` del CLAUDE.md / AGENTS.md del repo. Con `ETAPA ACTUAL: JDBC (Entrega 1)`: los checks JPA (LAZY/EAGER, 1+1, `em.flush()`, FK-entidad, paridad Flyway) NO aplican — en su lugar verificá: RowMapper estático compartido, SimpleJdbcInsert, un DAO por tabla, escape de LIKE, `java.sql.*` solo en persistence, y que el schema.sql esté al día. Con `JPA (Entrega 2+)` o sin declaración: Bloque 6 completo tal como está arriba. Con `SPA+REST (Entrega Final)`: sumá los checks de la API — resources sin lógica de negocio, DTOs sin campos sensibles, códigos/verbos correctos, ExceptionMappers cubriendo las excepciones de dominio, deep-linking (catch-all) funcionando, y las reglas JSP solo sobre las vistas legacy restantes (ver `etapas/entrega-final-spa-rest.md`).
