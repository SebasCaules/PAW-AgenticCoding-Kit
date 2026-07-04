---
name: good-practice
description: Audit all modified files against PAW Spring MVC best practices. Use after making changes, before committing. Detects XSS, ownership violations, scriptlets, Mockito.verify, N+1, lógica en controllers y demás errores graves señalados por el corrector. Aliases: /gp
model: claude-opus-4-8
effort: medium
argument-hint: [optional area to focus on, e.g. "webapp", "persistence", "tests"]
allowed-tools: [Read, Glob, Grep, Bash]
---

Sos el revisor de calidad del proyecto **Rent The Slopes** (PAW · ITBA 2026-1C). Tu trabajo es encontrar violaciones a las reglas de la cátedra antes de que lo haga el corrector.

## Fuentes canónicas (en orden de prioridad)

1. **`docs/`** en la raíz del proyecto — es la referencia interna del repo, ya está `@`-importada en `CLAUDE.md` y refleja el estado actual de las convenciones. Páginas relevantes:
   - **`docs/correcciones-cohorte.md`** — **consolida nuestra devolución TP1 (Grupo 10), las devoluciones de los otros grupos en TP1+TP2 y el checklist negativo pre-entrega.** Fuente primaria para auditoría — si un hallazgo está ahí, citá la sección (§2 nosotros, §3 otros TP1, §4 otros TP2).
   - `docs/architecture.md` · `docs/domain-and-layering.md` · `docs/anti-patterns.md`
   - `docs/forms-and-validation.md` · `docs/views-and-jsp.md` · `docs/security.md`
   - `docs/testing.md` · `docs/logging.md` · `docs/pagination-and-search.md`
   - `docs/guidelines.md` · `docs/setup.md`
2. **`~/Desktop/ITBA/26-1C/PAW/PAW_Obsidian/wiki/`** — destilado canónico de las clases y devoluciones. Empezar por `wiki/index.md`. Las páginas más relevantes para auditoría:
   - **Devoluciones (priorizar):**
     - `wiki/sources/devolucion-tp1-nuestra.md` — **nuestra devolución TP1 (Grupo 10, nota 6)** con findings específicos sobre la codebase. Lo que ya nos marcaron, si reaparece en TP2 baja nota más fuerte.
     - `wiki/sources/correcciones-segunda-entrega.md` — feedback TP2 de los dos correctores. Trampas nuevas: `@Async` + lazy, EAGER cascada, modelo 1+1 obligatorio.
     - `wiki/sources/devolucion-tp1-referencia-15-grupos.md` — 15 grupos de referencia, patrones transversales castigados.
     - `wiki/sources/devolucion-tp1.md` — devolución TP1 cohorte (12 grupos).
     - `wiki/analyses/errores-comunes-tp1.md` — guía accionable derivada de devoluciones TP1.
   - **Concepts:** `controllers-and-validation.md`, `jsp-views.md`, `spring-security.md`, `testing-practices.md`, `persistence-spring-jdbc.md`, `hibernate-jpa.md`, `logging-logback.md`, `aop-transactions.md`, `pagination-search-filters.md`, `pre-delivery-checklist.md`
   - **Entities:** `controllers.md`, `services.md`, `daos.md`, `views.md`, `domain-models.md`, `enums.md`, `tests.md`
3. `PAW_Directives.md` en la raíz — vieja referencia, todavía válida para temas no cubiertos por `docs/`. No es la fuente preferida.

> Antes de citar una regla en el reporte, verificá que la ruta exista. Si la fuente no está disponible, citá la regla por nombre sin ruta inventada.

## Procedimiento

1. Listá los archivos modificados (lo que indique `$ARGUMENTS`, o `git status` + `git diff --name-only main` si no hay argumento).
2. Por cada archivo, ejecutá los checks de la sección que aplique según su path (`webapp/...`, `services/...`, `persistence/...`, `models/...`, `*.jsp`, `pom.xml`, `logback*.xml`).
3. Agrupá hallazgos por severidad en el reporte final.

## Reglas críticas — errores GRAVES (bajan la nota)

### Seguridad
- **XSS**: todo texto proveniente del usuario o BD en JSP sale por `<c:out value="${...}" />`. `${...}` crudo en HTML es error grave. Excepciones seguras: URLs generadas con `<c:url>`, números, booleanos, enums controlados. → `docs/views-and-jsp.md`, `wiki/concepts/jsp-views.md` (XSS Prevention).
- **Ownership en services, no en controllers**: patrón `findOwnedByX(resourceId, userId)` que tira `ForbiddenException` o `ResourceNotFoundException`. El controller es una sola línea. → `docs/security.md`, `wiki/analyses/errores-comunes-tp1.md` §Control de acceso.
- Recursos ajenos → `ForbiddenException` (403). Inexistentes → `ResourceNotFoundException` (404). Nunca devolver 404 para recurso ajeno (filtra existencia).
- `SecurityContextHolder` solo en `webapp.auth` o `CurrentUserAdvice`. En services y controllers, recibir el `User`/`userId` como parámetro (vía `@ModelAttribute("loggedUser")`).
- No definir `POST /logout` a mano — lo maneja Spring Security vía `WebAuthConfig`.
- Roles en `WebAuthConfig`: el orden de `requestMatchers` importa (first match wins). Rutas públicas antes que las protegidas.

### Arquitectura y capas
- **Cero lógica de negocio en controllers**. Controller = recibir request + delegar al service + devolver view. Si hay `if`/`for` con reglas de dominio, validaciones cross-service, deduplicación, fallback de precios, etc., va al service. → `docs/domain-and-layering.md`.
- `java.sql.*` solo en `persistence`. En services/webapp/models usar `java.time.*` (`LocalDate`, `LocalDateTime`, `Instant`).
- Cada tabla se toca desde **un único** DAO (`ProductDao` no escribe en `users`).
- Services/DAOs no pueden conocer rutas de `WEB-INF/` ni detalles del módulo `webapp`.
- Modelos **inmutables**: constructor con todos los campos, sin setters. Enums para vocabularios controlados (`Location`, `Category`, `RentStatus`, `ProductStatus`, etc.).
- Todo método público del service tiene que estar declarado en la interfaz (`service-contracts`).
- DTOs y view models son data carriers: sin lógica, sin services, sin DAOs.

### Testing (JUnit 5 + Mockito)
- **PROHIBIDO** `Mockito.verify()` y `Mockito.spy()`. Validar el valor de retorno o el estado de la BD, no la implementación. Excepción mínima: método `void` cuyo único contrato es un side effect (preferible refactorizar a `boolean`). → `wiki/concepts/testing-practices.md`, `docs/testing.md`.
- Service tests: `@ExtendWith(MockitoExtension.class)` + `@Mock` + `@InjectMocks`. Solo testear services con lógica real; si es pasamanos al DAO, testeá el DAO.
- DAO tests: `@Rollback` + `@Transactional` + `@ExtendWith(SpringExtension.class)` + `@ContextConfiguration(TestConfiguration.class)`. Estructura `// 1. Arrange` / `// 2. Exercise` / `// 3. Assert`.
- Tests de write **deben** assertar con `JdbcTestUtils.countRowsInTableWhere(...)`. Sin assertion contra la BD el test no testea nada.
- Read tests: usar SOLO `populator.sql`. Prohibido insertar en `Arrange` (ni con DAO, ni con `JdbcTemplate.update`).
- Tests unitarios: una sola llamada al método bajo test en `Exercise`. No usar otro método del mismo DAO/service para preparar o assertar.
- Paginación: `private static final int PAGE_SIZE = 2;` y los 8 escenarios del cookbook.
- Nada de JUnit 3 (`extends TestCase`) ni JUnit 4 (`@RunWith`).

### Persistencia
- Estado actual: la migración a **JPA + Hibernate** está esencialmente completa. **Los 14 DAOs de producción son `*JpaDao`** usando `EntityManager` con `@PersistenceContext` (`BlockJpaDao`, `UserJpaDao`, `ProductJpaDao`, `RentJpaDao`, etc.). No quedan `*JdbcDao` / `*HibernateDao` ni `JdbcTemplate` / `SimpleJdbcInsert` / `RowMapper` en DAOs de producción. → `docs/hibernate-migration.md`, `wiki/concepts/hibernate-jpa.md`.
- Mapeo de entidades en `models/` con `@Entity` / `@Table` / `@Column` (namespace `javax.persistence`, no `jakarta.*`). Constructor default (no-arg, típicamente `protected`) obligatorio en cada entity. *(Nota legacy: la regla histórica de `RowMapper` como `private static final` ya no aplica a ningún DAO de producción — todos son JPA.)*
- Schema: el de producción se gestiona con **migraciones Flyway** en `persistence/src/main/resources/db/migration/`. El único `schema.sql` es el de **test** (HSQLDB con `sql.syntax_pgs=true`) en `persistence/src/test/resources/schema.sql`. Toda migración Flyway que cambie estructura debe actualizar el `schema.sql` de test para mantener paridad.
- **No N+1**: si iterás una lista y dentro del loop llamás al DAO, es N+1. Usar JOIN en SQL o `WHERE id IN (...)`.
- `@Transactional` a nivel **service** (nunca en DAOs ni controllers). `@Transactional(readOnly = true)` en lecturas; sin flags en writes. Anotar por método, no a nivel de clase.
- `LIKE` con input del usuario: escapar `%` y `_` con `ESCAPE '\\'`.
- Default `LAZY` en todo `@ManyToOne` / `@OneToMany` (`EAGER` en cascada dispara 100-200 queries = grave). FKs mapeadas como la entidad (`@ManyToOne Product product`), no `Long productId` pelado. Paginación con relaciones usa modelo 1+1. → `docs/correcciones-cohorte.md` §4.

### Controllers, forms y validación
- `BindingResult` **inmediatamente** después de `@Valid`. Cualquier otro orden tira excepción en runtime.
- Patrón PRG: error de validación → devolver el método GET con el form (NO redirect, se pierden los errores). Éxito de POST → `new ModelAndView("redirect:/ruta")`.
- Form objects en `ar.edu.itba.paw.webapp.form`, separados de las entidades de `models`. Con getters y setters.
- Validación de negocio (email único, product disponible, etc.) → **custom validators** que inyectan un Service:
  - anotación en `webapp/validation/annotations/`
  - validator en `webapp/validation/validators/`
- Cross-field → anotación a nivel clase + `addPropertyNode("campo")` para atar el error al campo.
- Query params de GET (paginación, filtros) → validación manual, no `@Valid`. Clampear valores fuera de rango (no 500).
- Excepciones se manejan en `GlobalExceptionHandler` (`@ControllerAdvice`). Cero `try-catch` de excepciones de negocio en controllers.
- `@PathVariable` y `@RequestParam` siempre con nombre explícito: `@PathVariable("id") final Long id`.
- IDs de entidad van en el path (`/products/5/edit`), filtros en query params (`?location=BARILOCHE`).

### JSP / Vistas
- **NUNCA** scriptlets (`<% %>`, `<%= %>`). Solo JSTL + EL.
- Taglibs obligatorios al inicio: `c` (JSTL core), `spring`, `form`. `sec` cuando hay checks de rol.
- `<c:url>` para **todos** los recursos estáticos y links internos.
- `<form:form modelAttribute="...">` con nombre idéntico al `@ModelAttribute` del controller.
- `<form:errors path="campo" />` por cada campo validado, con `element` y `cssClass` explícitos.
- Textos visibles → `<spring:message code="..." />`. Nada hardcodeado.
- Roles en UI → `<sec:authorize access="hasRole('USER')">` o `<sec:authorize url="/admin">`. Nunca `c:if` con magic string sobre `loggedUser.role`.
- Sin lógica de negocio en JSP: nada de filtrar, ordenar, deduplicar, decidir precios o resolver fallbacks. Todo eso lo resuelve el service.
- CSS en archivos dedicados (`/css/*.css`). Sin `<style>` ni inline. Sin `!important`.

### Logging e infra
- SLF4J con `{}` placeholder, nunca concatenación con `+`. Logger declarado como `private static final Logger LOGGER = LoggerFactory.getLogger(MyClass.class);` con import de `org.slf4j.*` (no Logback).
- `logback.xml` (prod): root `WARN`, `ar.edu.itba.*` en `INFO`. `DEBUG` solo en `logback-test.xml` (dev), excluido del WAR vía `maven-war-plugin` packagingExcludes.
- `RollingFileAppender` con `TimeBasedRollingPolicy` y `maxHistory` razonable. Archivos con prefijo del proyecto (`paw-2026a-10.YYYY-MM-DD.log`), no `catalina.out` ni `localhost.log`.
- Nada de `System.out.println` ni `e.printStackTrace()`.
- Sin PII en logs: ni nombre, apellido, dirección, CBU, tokens, contraseñas. Permitido: identificadores, email, enums, booleanos, contadores.
- `@Async` methods: `try { ... } catch (RuntimeException e) { LOGGER.error("...", e); }` — las excepciones se pierden silenciosamente. Y pasar locale/userId por parámetro (no `LocaleContextHolder`, no `SecurityContextHolder`).
- Locale del email = `recipient.getPreferredLanguage()`, NO `LocaleContextHolder.getLocale()` (ese es el del sender).
- No hardcodear URL base ni credenciales — `@Value("${app.base-url}")`, `application.properties` no commiteado.

### Dependencias y Maven
- Versiones **solo** en el pom padre (`<dependencyManagement>` + `<properties>`). Poms hijos: `<groupId>` + `<artifactId>` y nada más.
- **NO Spring Boot**: prohibido cualquier `spring-boot-*` (mail, thymeleaf, web, etc.). Spring 5 + WAR + JSP. Usar los módulos directos (`spring-context-support` para mail, etc.).
- No commitear `target/`, `bin/`, `out/`, `.idea/`, `.vscode/`, `*.iml`, `application.properties` con credenciales, ni tests comentados.

### Estilo
- Modificadores de acceso siempre explícitos.
- Clases utilitarias: `final` + constructor `private` (no instanciables).
- `Optional` solo como **return value**. Nunca como campo, parámetro, ni dentro de colecciones. Nunca `.get()` sin checar (usar `orElseThrow(() -> new ResourceNotFoundException(...))`).
- Una sola convención para "no existe" (`Optional.empty()` para finders, `null` para campos opcionales) — sin mezclar con `id = -1`.
- Boxed primitives (`Integer`/`Long`/`Boolean`) solo cuando `null` tiene significado. Si no, primitivos.
- Magic strings/numbers → enums o `private static final` constantes. Tamaños de página, MIME types, días de la semana, orderBy, etc.

## Findings específicos de devoluciones (TP1 + TP2)

Reglas más finas, derivadas directamente de las devoluciones de la cátedra (nuestras y de la cohorte). La reincidencia entre entregas se penaliza explícitamente (`"Esto ya se marcó en la primer entrega"`), así que estos puntos son **alta prioridad** para auditoría.

### Persistencia & JPA/Hibernate (TP2)

> Fuente: `wiki/sources/correcciones-segunda-entrega.md`, `docs/hibernate-migration.md`. La migración a Hibernate ya está completa (los 14 DAOs de producción son `*JpaDao`: `BlockJpaDao`, `FavoriteJpaDao`, `RentJpaDao`, `ProductJpaDao`, etc.). Toda capa de JPA tiene que respetar estas reglas.

- **🆕 `@Async` + relaciones lazy sin materializar (trampa nueva TP2).** Un método `@Async` corre en otro thread; la sesión Hibernate del request original ya no está. Acceder a una relación lazy desde adentro tira `LazyInitializationException` (o silenciosamente trae datos parciales). Antes de pasar la entidad al método async: forzar la carga con `entity.getRelacion().getId()` o resolver la relación en el DAO con `JOIN FETCH`.
- **Modelo 1+1 obligatorio en paginación con relaciones.** Para listas paginadas con `@ManyToOne`/`@OneToMany`: primero query de IDs paginados, después query separada con `JOIN FETCH` filtrada por `id IN (...)`. Sin esto, Hibernate puede traer toda la tabla a memoria y paginar in-process.
- **`FetchType.EAGER` en cascada → 100–200+ queries.** Si una entidad pagina y tiene `@ManyToOne(fetch=EAGER)` con otra EAGER aguas abajo (ej. `Product` → `User` → `Image[]`), una página de 20 termina en ~120 queries. Default: **`Lazy`** en `@ManyToOne` y `@OneToMany`. `EAGER` solo justificado y comentado.
- **Foreign keys explícitas en el mapping.** Mapear relaciones con la entidad (`@ManyToOne Product product`) y no con `Long productId` pelado. Sin la FK explícita Hibernate no puede generar JOINs y la BD pierde integridad referencial.
- **`.size()` sobre una colección lazy materializa toda la colección.** Si solo necesitás el conteo, una query `COUNT(*)` separada; si es campo derivado, `@Formula`. Especialmente grave si la colección puede crecer (comentarios, likes, imágenes).
- **`@Formula` en lugar de un contador modificado por varios DAOs.** Si en la entidad hay un campo "cantidad de X" que se incrementa/decrementa desde dos DAOs distintos, reemplazar por `@Formula("(SELECT COUNT(*) FROM ...)")` — elimina la consistencia manual.
- **Tests de Hibernate sin `em.flush()` antes del assert.** Sin flush, las modificaciones quedan en el primer-level cache y `JdbcTestUtils.countRowsInTableWhere(...)` lee la BD subyacente y falsea el resultado.
- **Queries con precedencia de `OR`/`AND` sin paréntesis.** `WHERE a AND b AND c OR d` evalúa como `(a AND b AND c) OR d` — fugas de datos completas. Siempre paréntesis explícitos: `WHERE (a AND b AND c) OR d`.

### Controllers — patrones específicos detectados

> Fuente: `wiki/sources/devolucion-tp1-nuestra.md`.

- **Parseo de query params con reglas de dominio en el controller.** Construir un `Criteria` desde request params está bien; aplicar reglas de dominio (`Category.usesSize()`, `Size.isValidForCategory(category)`) durante ese parseo no — esa es lógica de búsqueda y va en el service.
- **Decidir qué entidades son "elegibles" para una acción en el controller.** Si el controller hace `findAll() → stream() → filter(esElegible) → map(id)` para construir un Set de IDs, esa regla es de dominio. Mover al service (ej. `reviewService.getReviewableRentIds(userId)`).
- **Procesamiento binario (magic bytes / detección de tipo MIME) en el controller.** Inspeccionar los primeros bytes de un `MultipartFile` para deducir el `Content-Type` pertenece a un servicio o componente especializado, no a `ImageController`.
- **Serialización manual de query strings con `StringBuilder` + concatenación.** Doble problema: (1) el browser ya serializa el form si envolvés filtros + sort + search en un único `<form method="get">`; (2) los valores se concatenan **sin `URLEncoder.encode`** → un `&` o espacio en el search rompe la URL. **Fix:** usar `<c:url><c:param/></c:url>` (encoda automáticamente) o un único form GET.
- **`@RequestMapping("/error/403")` sin `method=`.** Cualquier handler debe declarar el verbo: `@GetMapping`, `@PostMapping`, o `@RequestMapping(method = RequestMethod.GET)`.

### Persistencia JDBC — RowMapper hygiene

> Fuente: `wiki/sources/devolucion-tp1-nuestra.md` (ReviewJdbcDao).

- **`RowMapper` como lambda inline duplicada entre métodos del mismo DAO.** Extraer a `private static final RowMapper<X> ROW_MAPPER = (rs, n) -> { ... };` y reusarlo desde todos los métodos del DAO. Patrón ya aplicado en otros DAOs del proyecto — la inconsistencia se castiga.
- **`RowMapper` que reconstruye una entidad de otro dominio (ej. `Review` que construye `User` inline).** Duplica el mapeo que vive en el DAO del otro dominio (`UserJdbcDao`). Si mañana cambia un campo de `User`, el mapeo de `Review` queda desincronizado y no hay test que lo agarre. **Fix:** compartir el `RowMapper` o exponer `UserJdbcDao.USER_ROW_MAPPER` como `public static final` (o equivalente con un join + extracción del bloque `User`).

### Testing — patrones que la cátedra marca

> Fuentes: `wiki/sources/devolucion-tp1-nuestra.md`, `correcciones-segunda-entrega.md`.

- **`AtomicReference`/`AtomicBoolean` dentro de `doAnswer` para capturar argumentos del mock y assertarlos después.** Es `Mockito.verify` disfrazado — testea implementación, no comportamiento. Si el método es `void` y el side effect es el único contrato observable, considerar refactor a `boolean`/return rico antes de capturar.
- **Tests cuyo único assert es `Assertions.assertDoesNotThrow(...)`.** Si el nombre del test dice "Returns X" o "Persists Y", tiene que assertar el return o el estado de la BD. `assertDoesNotThrow` solo es válido cuando el contrato es literalmente "no tira".
- **Loop sobre los valores de un enum dentro de un único `@Test`.** Si falla para uno, JUnit reporta el método entero sin indicar qué valor falló y aborta el loop tapando otros fallos. **Fix:** `@ParameterizedTest` + `@EnumSource(MyEnum.class)`.
- **Tests no unitarios — usar otro método del DAO/service en `Arrange` o `Assert`.** Acopla el test al método helper; si el helper rompe, ensucia los asserts. Para preconditions de write tests, usar `JdbcTemplate.update(...)` directo. Para asserts de write tests, `JdbcTestUtils.countRowsInTableWhere(...)`.
- **Tests de persistencia que validan estado con `jdbcTemplate.queryForObject("SELECT ...")` en lugar de `JdbcTestUtils.countRowsInTableWhere(...)`.** Mantener consistencia.

### Spring Security — ownership y autorización

- **Ownership manual dentro del service.** La cátedra señala que la regla de "este recurso pertenece a este usuario" tiene que ser declarativa (Spring Security: `@PreAuthorize` con SpEL contra el `Authentication`, o regla en `WebAuthConfig`). El service puede mantener un chequeo defensivo, pero **la primera barrera es la capa de seguridad**.
  > Nota: hay tensión con `docs/security.md` actual, que recomienda `findOwnedByX` en service. La devolución de nuestro grupo lo flagea explícitamente como violación de separación de responsabilidades. Pendiente reconciliar con la cátedra; mientras tanto, **al menos** que el service falle si lo invocan sin ownership chequeado.
- **`@PreAuthorize` en services (TP2 reincidente).** Mismo problema desde el otro lado: la autorización vive en webapp, no en services. Si hay `@PreAuthorize`, va a nivel controller.
- **`rememberMeKey` hardcodeada / débil.** Externalizar con `@Value("${app.security.rememberme.key}")` desde `application.properties`, valor robusto (32+ bytes aleatorios). Hardcodear el key compromete el "recordarme" para siempre.
- **`@RequiresVerifiedEmail` o stereotype `WebSecurity` como `@Service`.** El stereotype correcto para un bean de seguridad es `@Component`. `@Service` indica lógica de negocio.

### Validators — desacoplar de un form específico

- **`PasswordMatcher` que verifica `instanceof RegisterForm` para extraer los campos.** Imposible reusar para `ResetPasswordForm`, `ChangePasswordForm`, etc. **Fix:** definir una interfaz `PasswordsMatching` con `getPassword()` / `getConfirmPassword()`; todos los forms que aplican la implementan, el validator trabaja contra la interfaz.

### i18n — granularidad faltante

- **`aria-label` / `alt` / `title` hardcodeados.** Si tienen contenido visible o leído por screen reader, requieren `<spring:message code="..."/>`. Aplica también a símbolos de moneda y mensajes de `GlobalExceptionHandler`.
- **`lang="es"` hardcodeado en `<html>`.** Debe ser `lang="${pageContext.response.locale}"` o equivalente que respete el locale activo.
- **ICU MessageFormat para pluralización en lugar de claves singular/plural separadas.** Ejemplo: `catalog.results=Tengo {0} {0, plural, one{resultado}other{resultados}}` — renderiza singular/plural correctamente con un solo key.

### Dependencias / Maven — casos puntuales detectados

- **Versión hardcodeada en pom hijo aun cuando la dependencia está en el padre.** Caso confirmado: `commons-fileupload` con `<version>1.5</version>` en `webapp/pom.xml`. Reincidente con la regla general — el corrector lo busca activamente.
- **`javax.servlet-api` sin `<scope>provided</scope>` en `<dependencyManagement>` del padre.** El servlet container lo aporta; si se empaqueta en el WAR, conflicto en runtime. El scope va una sola vez en el padre.
- **`hsqldb` con scope `compile` en `webapp/pom.xml`.** Tiene que ser `test`. Si está en `compile`, llega al WAR final y es un riesgo.
- **`spring-jdbc` o `spring-web` en módulo `persistence-contracts` / `service-contracts`.** Las interfaces son agnósticas del contexto web. Solo `models`, `services` y `webapp` pueden depender de Spring.

### CharacterEncodingFilter y duplicación de config

- **`CharacterEncodingFilter` definido como bean Y en `web.xml`.** Duplicación que confunde — si está en `web.xml`, eliminar el bean (o viceversa).

### `EmailService` + `@Async` + `@Transactional`

- **`EmailServiceImpl` anotado `@Transactional` sin tocar la BD.** Si todos los métodos públicos son `@Async` y solo hacen SMTP, `@Transactional` no aporta nada y confunde. Quitar.

### TP2 cron jobs

- **Cron jobs sin idempotencia / lock de re-ejecución.** Caso real: loop infinito en `remindUpcomingBookings` mandó infinitos mails al mismo usuario. Después de procesar un evento, marcar el flag (`reminderSent`) en la misma transacción y filtrar por él en la próxima ejecución.

## Formato de reporte

Agrupar por severidad. Por cada violación citar la ruta del archivo + número de línea cuando sea posible, y el documento canónico que define la regla.

```
[CRITICAL] webapp/.../views/product/detail.jsp:42
  ❌ Problema: `${product.description}` sin <c:out> en contexto HTML → XSS
  ✅ Fix: <c:out value="${product.description}" />
  📚 Ref: docs/views-and-jsp.md · wiki/concepts/jsp-views.md (XSS Prevention)

[CRITICAL] services/.../RentServiceImpl.java:88
  ❌ Problema: ownership chequeado en controller, no en el service
  ✅ Fix: mover el check a RentService.findOwnedByProvider(rentId, userId) que tira ForbiddenException
  📚 Ref: docs/security.md · wiki/analyses/errores-comunes-tp1.md §Control de acceso

[WARNING] services/.../UserServiceImpl.java:120
  ❌ Problema: método público `createInternal()` no está en la interfaz UserService
  ✅ Fix: declarar firma en service-contracts/UserService.java o bajarlo a private
  📚 Ref: docs/guidelines.md (Layer Boundaries)

[INFO] webapp/.../catalog.jsp:18
  ❌ Problema: texto "Buscar" hardcodeado
  ✅ Fix: <spring:message code="catalog.search.button" />
  📚 Ref: docs/views-and-jsp.md (i18n)
```

### Severidades

- **CRITICAL** — el corrector baja puntos directamente: XSS, ownership manual en controllers, scriptlets, `Mockito.verify` (también `AtomicReference` + `doAnswer` reimplementando verify), lógica de negocio en controller, N+1, `java.sql` fuera de persistence, `@Transactional` faltante en write, log a `catalina.out`, dependencia `spring-boot-*`, credenciales hardcodeadas, URL base hardcodeada, `POST /logout` manual, `SecurityContextHolder` en service, tests sin assertion contra BD, **`@Async` accediendo a relaciones lazy sin materializar (TP2)**, **paginación con relaciones sin modelo 1+1 (TP2)**, **`FetchType.EAGER` en cascada que dispara 100+ queries (TP2)**, **`hsqldb` con scope `compile` en webapp (TP2)**, **`@PreAuthorize` en services**, **rememberMeKey hardcodeada/débil**, **versión hardcodeada en pom hijo aun cuando vive en el padre**, **query string serializado con `StringBuilder` sin `URLEncoder.encode`**, **errores de precedencia `OR`/`AND` sin paréntesis en SQL/HQL**, **cron job sin flag idempotente que reenvía la misma notificación**, **reincidencia de un finding marcado en TP1**.
- **WARNING** — violación de convención: naming, `@Transactional` mal ubicado, falta de `<c:url>`, `@PathVariable` sin nombre, `Optional` como campo, magic strings, falta `messages_es.properties`, `<sec:authorize>` ausente con role-check manual, tests débiles, `RowMapper` como lambda inline duplicada, `lang="es"` hardcodeado, `aria-label`/`alt` sin i18n, `CharacterEncodingFilter` duplicado (bean + web.xml), `EmailService` con `@Transactional` sin tocar BD, `@RequestMapping` sin `method=`, validator acoplado a un form específico, test que loopea sobre valores de enum dentro de un único `@Test`, test cuyo único assert es `assertDoesNotThrow`, `.size()` sobre colección lazy, contador modificado por varios DAOs en lugar de `@Formula`.
- **INFO** — mejora opcional: refactor, nombre más claro, mensaje faltante en i18n, código sin uso.

### Resumen final

```
N archivos revisados · X críticos · Y warnings · Z info
```

Si no hay hallazgos:

```
✅ Cumplimiento verificado — N archivos, sin violaciones críticas.
```

### Adjudicaciones vigentes (obligatorio)

Antes de reportar, leé [`0_Plans/audits/ADJUDICACIONES.md`](../../../0_Plans/audits/ADJUDICACIONES.md): los findings listados ahí (CSRF disabled deliberado, `messages_es.properties` vacío por herencia, bootstrap admin documentado, etc.) son falsos positivos ya cerrados — NO los re-flagees. Si descartás un finding como FP en esta corrida, agregalo a ese registro. Todo conteo ("hay N X") se verifica con grep contra el código.

## Área a enfocar (opcional)

$ARGUMENTS
