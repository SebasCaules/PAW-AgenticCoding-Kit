## Anti-patterns — Errores recurrentes castigados por el corrector

Lista compilada de las devoluciones de **TP1 (27+ grupos)** y **TP2 (32 grupos, dos correctores)** disponibles en `~/Desktop/ITBA/26-1C/PAW/PAW_Obsidian/wiki/sources/` (`devolucion-tp1.md`, `devolucion-tp1-nuestra.md`, `devolucion-tp1-referencia-15-grupos.md`, `correcciones-segunda-entrega.md`). Los items marcados como **error grave** o **error conceptual grave** descontaron nota de forma directa. Tratar esta lista como checklist negativo: nada de esto debe quedar en el código antes de entregar.

> **Reincidencia = penalización doble.** Cualquier finding marcado en TP1 que reaparezca en TP2 recibe el comentario `"Esto ya se marcó en la primer entrega"` y baja nota más fuerte. Cruzar siempre contra `devolucion-tp1-nuestra.md` antes de cerrar una entrega.

### Severidad: trampas TP2 (Hibernate / JPA) — nuevas, alta prioridad

#### `@Async` accediendo a relaciones lazy sin materializar — **error conceptual grave**
Un método `@Async` corre en otro thread, la sesión Hibernate del request original ya no está. Acceder a una relación lazy (`booking.getUser().getName()`) tira `LazyInitializationException` o trae datos parciales en silencio. **Fix:** materializar antes (`entity.getRelacion().getId()` fuerza la carga) o resolver con `JOIN FETCH` en el DAO. Detectado en corrector B grupos 2, 3, 5. **Trampa nueva del TP2.**

#### Paginación con relaciones sin modelo 1+1 — **error conceptual grave**
Para listas paginadas con `@ManyToOne`/`@OneToMany`: primera query devuelve los IDs paginados, segunda query con `JOIN FETCH ... WHERE id IN (...)` rehidrata. Sin esto, Hibernate puede traer la tabla entera y paginar in-memory. Detectado en muchos grupos en TP2. Ver `wiki/concepts/hibernate-jpa.md` y `docs/pagination-and-search.md`.

#### `FetchType.EAGER` en cascada — **error conceptual grave**
Una `@ManyToOne(fetch = EAGER)` en `Product` apuntando a `User` que también tiene `@OneToMany(fetch = EAGER)` a `Image` significa que una página de 20 productos dispara ~120 queries. Default obligatorio: **`Lazy`** en cualquier relación. `EAGER` solo justificado y con comentario que explique por qué. Casos grupos 1, 3, 4, 10, 11, 14, 16 (corrector A) + 4, 11, 14 (corrector B).

#### Foreign keys mapeadas con `Long xId` en lugar de la entidad
Mapear con `@ManyToOne Product product` no con `Long productId` pelado. Sin FK explícita Hibernate no genera JOINs y la BD pierde integridad referencial. Marcado como "Error conceptual grave" en grupo 3 corrector A y grupo 6 corrector B.

#### `.size()` sobre colección lazy materializa la colección completa
Si solo necesitás el conteo, query `COUNT(*)` separada. Si es derivado de la entidad, `@Formula("(SELECT COUNT(*) FROM ...)")`. Especialmente grave si la colección puede crecer sin límite (comentarios, likes, imágenes).

#### Contador modificado por varios DAOs en lugar de `@Formula`
Si la entidad tiene un campo "cantidad de X" que dos DAOs incrementan/decrementan, eliminar el campo y reemplazar por `@Formula`. Evita consistencia manual entre DAOs. Marcado en grupo 7 corrector B y grupo 13 corrector B.

#### Errores de precedencia en SQL/HQL con `OR`/`AND` sin paréntesis
`WHERE a AND b AND c OR d` evalúa como `(a AND b AND c) OR d` — filtra mal y fuga datos. Caso real en grupo 5 corrector B: `WHERE v.publicationStatus = 'ACTIVE' AND v.stock > 0 AND v.genre = :g OR v.sellerId = :sellerId` trae cualquier vinilo del seller, ignorando active y stock. **Paréntesis explícitos siempre.**

#### Tests de Hibernate sin `em.flush()` antes del assert
Sin `flush()`, los writes quedan en el first-level cache y `JdbcTestUtils.countRowsInTableWhere(...)` lee la BD subyacente y el assert pasa con BD vacía. Marcado en grupo 5 corrector B.

#### Cron job sin flag idempotente que reenvía la misma notificación
Caso real grupo 2 corrector B: `remindUpcomingBookingsCronJob` con loop infinito mandó infinitos mails al mismo usuario. Marcar el flag (`reminderSent`) en la misma transacción que el envío, filtrar por él en la próxima ejecución.

### Severidad: error conceptual grave

#### XSS — imprimir datos de usuario sin `<c:out>`
Imprimir `${user.name}`, `${product.description}`, `${review.comment}` directamente. Solucionar con `<c:out value="${...}"/>` (escapa `<`, `>`, `"`, `'`, `&`). Ver `docs/views-and-jsp.md`.

#### Lógica de negocio en controllers
Controllers deben coordinar (recibir request → llamar al service → devolver vista). NO deben:
- validar reglas de negocio (esto va en form validators o services);
- llamar a múltiples services para ensamblar un resultado (mover la orquestación al service);
- hacer try-catch de excepciones de negocio (usar `GlobalExceptionHandler`);
- decidir qué precio aplica, deduplicar entidades, resolver conflictos;
- tener acceso a la BD;
- instanciar objetos de dominio (eso viene de la capa de persistencia).

#### Tests con `Mockito.verify()` o `Mockito.spy()`
Validan **implementación**, no comportamiento. Si refactorizás el internals, el test rompe aunque el resultado sea correcto. Validar con `Assertions.*` sobre el valor de retorno. Excepción mínima: cuando el efecto secundario **es** el contrato observable (ej. un service de notificaciones cuyo único trabajo es despachar un mail) — incluso ahí, preferí volver el método `boolean` y assertar el resultado.

#### Tests no unitarios (usar otro método de la misma clase para preparar / verificar)
Un test de `update` que llama `findById` después para verificar el cambio depende de que `findById` también funcione. Cualquier fallo en `findById` ensucia el test de `update`. En persistencia: usar `JdbcTestUtils.countRowsInTableWhere(...)`. En service: assertar el valor de retorno. Ver `docs/testing.md`.

#### N+1 queries / JOINs en Java
Iterar `productIds.stream().map(id -> dao.findById(id))` en un loop, o pedir 1000 registros y filtrar en memoria. Resolver en una única consulta SQL con `JOIN` o `WHERE id IN (...)`. Ver `docs/guidelines.md` (Data Access & Performance).

#### Validación de ownership manual en controllers
`if (product.getProviderId() != loggedUser.getId())` en el controller. Mover a un método del service (`findOwnedByX(id, userId)`) que tira `ForbiddenException`. Ver `docs/security.md`.

#### Servicios referenciando recursos de la capa webapp
Un `EmailServiceImpl` (módulo `services`) que conoce paths de templates en `webapp/WEB-INF/`. Viola la dirección de dependencias (`webapp` → `services`). Pasar los textos resueltos como parámetros, o mover la resolución de templates a un componente de `webapp`.

#### Loguear a nivel `DEBUG` o `INFO` en producción
Si `logback.xml` (prod) está en DEBUG/INFO, los logs explotan en volumen. Producción debe ser `WARN` o más alto, con un logger específico para `ar.edu.itba` en `INFO` (logs de la app). Override en dev con `-Dar.edu.itba.log.level=DEBUG`. Ver `docs/logging.md`.

#### No tener tests
Es un requerimiento del enunciado. La cobertura mínima esperada cubre tanto la capa de servicios como la de persistencia, con happy paths y unhappy paths.

#### `@Transactional` ausente en métodos de servicio que escriben
Cualquier método público de service que mute estado (insert / update / delete, transición de estado, envío de mail con persistencia) debe tener `@Transactional`. Lecturas: `@Transactional(readOnly = true)`. Ver `docs/architecture.md` (Transaction Management).

#### Spring Security con orden de matchers incorrecto
`anyRequest().authenticated()` antes que rutas más restrictivas → las rutas restrictivas quedan apenas autenticadas. **First match wins**. Las rutas públicas se declaran primero, las protegidas después, y `anyRequest()` siempre al final. Ver `docs/security.md`.

#### Tests de persistencia sin `@Rollback` ni assertion de DB
Un test que hace `dao.create(...)` sin assertar `JdbcTestUtils.countRowsInTable(...)` no verifica nada. Y si no rollbackea, contamina los siguientes tests.

#### Loguear a archivos genéricos del contenedor
Sin un `FileAppender` propio en `logback.xml`, los logs caen en `catalina.out` / `localhost.log` mezclados con todas las apps del Tomcat. El equipo debe escribir a archivos **únicos del proyecto** (`paw-2026a-10.YYYY-MM-DD.log`) en una ruta accesible. Ver `docs/logging.md` (Cátedra directives — logging checklist).

### Findings específicos de nuestro TP1 (Grupo 10) — NO reincidir

Cada caso nominal está documentado en **`docs/correcciones-cohorte.md` §2.1** con el fix concreto: controllers con lógica de dominio (`DashboardController.computeReviewableRentIds`, `CatalogController.parseCategoryFilters`, `ImageController.detectContentType`, `CatalogController.buildFilterQueryString`), `RowMapper` duplicado en `ReviewJdbcDao`, tests con `AtomicReference + doAnswer`, `@RequestMapping` sin `method=`, `commons-fileupload` con versión hardcodeada, `aria-label` sin i18n, etc. La cátedra los va a buscar activamente en TP2 — reincidencia = penalización doble.

### Severidad: error grave

#### Hardcodear credenciales en el repo
Mailing, DB, Gmail, etc. Todo va por `application.properties` (no commiteado) o por variables de entorno con `@Value("${...}")`.

#### URLs hardcodeadas en código
`String baseUrl = "http://pawserver.it.itba.edu.ar/paw-2025a-01/"`. Usar `@Value("${app.base-url}")` y dejarlo en `application.properties`.

#### Usar el locale del actor para mails (no del destinatario)
`LocaleContextHolder.getLocale()` devuelve el locale del **usuario que disparó la acción**, no del destinatario del mail. Si A reserva el producto de B, el mail a B se manda en el idioma de A. Usar `recipient.getPreferredLanguage()` (o un default) y pasarlo al `EmailService`. Ver `docs/views-and-jsp.md` (sección i18n) y `docs/logging.md` (sección Async + ThreadLocal).

#### Definir `POST /logout` manualmente
Lo maneja Spring Security. Solo configurar en `WebAuthConfig`:
```java
.logout(l -> l.logoutUrl("/logout").logoutSuccessUrl("/login"))
```

#### `<c:url>` ausente
Hardcodear `/css/...` o `/products/123` rompe la app cuando se sirve detrás de un context path (`/paw-2026a-10/...`). Ver `docs/views-and-jsp.md`.

#### Versiones de dependencias en poms hijos
Las versiones viven **solo** en el pom padre (`<dependencyManagement>`). Hijos declaran `<groupId>` + `<artifactId>` y nada más. Sobreescribir versiones de Java desde un pom hijo es especialmente grave (visto en grupos donde `models` tenía Java 17 y el padre 21).

#### Schema SQL en el módulo equivocado
`schema.sql` y migraciones Flyway viven en `persistence/src/main/resources/`. **No** en `webapp/`. Es un detalle del DAO.

#### `rememberMeKey` hardcodeada / débil
La key del remember-me filter va externa (`@Value("${app.security.rememberme.key}")` o equivalente) y robusta (≥32 bytes aleatorios). Hardcodearla compromete el "recordarme" de toda la app para siempre. Marcado en muchos grupos (G4, G6, G8, G10, G11 del TP1 referencia).

#### Stereotype incorrecto para beans de seguridad
Un bean de configuración de seguridad (`WebSecurity`, helpers de filtros) va con `@Component`, no con `@Service`. `@Service` indica lógica de negocio.

#### `hsqldb` con scope `compile` en `webapp/pom.xml`
Siempre `test`. Si llega al WAR final, la app levanta dependencias de testing en producción.

#### Validator acoplado a un form específico
Un `PasswordMatcher` que hace `if (form instanceof RegisterForm) { ... }` es imposible de reutilizar para `ResetPasswordForm`, `ChangePasswordForm`, etc. **Fix:** definir una interfaz (ej. `PasswordsMatching { getPassword(); getConfirmPassword(); }`); todos los forms que aplican la implementan, el validator opera contra la interfaz.

#### `lang="es"` hardcodeado en `<html>`
Debe respetar el locale activo: `lang="${pageContext.response.locale}"` o equivalente. Hardcodearlo rompe accesibilidad y screen readers cuando el usuario cambia de idioma.

#### `java.sql.*` fuera de `persistence`
`java.sql.Date`, `java.sql.Timestamp` en `models` o `services` viola la división de capas — el modelo no debe conocer detalles de SQL. Usar `java.time.*` (`LocalDate`, `LocalDateTime`, `Instant`) en todo el proyecto, y hacer la conversión a `java.sql.*` solo en el DAO si la API de Spring JDBC lo requiere.

#### Una tabla modificada por más de un DAO
Cada tabla de la BD tiene un único DAO responsable. Si `ClubJDBCDao` actualiza la tabla `users`, eso pertenece a `UserDao`. Romper esta regla ensucia los tests, viola SRP y causa bugs cuando la lógica de update se duplica.

#### Loguear con `+` en vez de `{}` (parameterized SLF4J)
```java
LOGGER.debug("user=" + user); // construye el string aunque DEBUG esté off
LOGGER.debug("user={}", user); // lazy — solo si DEBUG está habilitado
```

#### `Optional` como campo o parámetro
`Optional` es solo para retorno de funciones. Como campo no se serializa bien, como parámetro genera APIs ambiguas (`Optional<X>` vs `X` con `null`). Usar `null` para campos opcionales y exponerlos por getter como `Optional.ofNullable(...)`.

#### `Optional.get()` sin verificar
Llamar `.get()` sin `isPresent()` o `orElseThrow(...)` lanza `NoSuchElementException`. Usar `orElseThrow(() -> new ResourceNotFoundException(...))`.

#### Uso inconsistente de "no existe"
Mezclar `null`, `Optional.empty()`, excepciones, `id = -1` para representar ausencia. Elegir **una sola** convención y mantenerla:
- Retorno de `findBy...`: `Optional.empty()`.
- Campo opcional del modelo: `null`.
- Servicio: `orElseThrow(ResourceNotFoundException::new)` cuando el caller espera presencia.

#### Boxed primitives sin necesidad
`Integer`/`Long`/`Boolean` cuando `null` no tiene significado de negocio. Auto-unboxing tira NPE silencioso. Usar primitivos (`int`, `long`, `boolean`) en esos casos.

#### Magic strings/numbers
Días de la semana como `String[]`, `orderBy = "price_asc"`, MIME types como literales, tamaños de página hardcodeados, "secciones" como strings. Usar enums o constantes con `private static final` declarado en el lugar correcto (no replicado por DAO/controller/JSP).

#### Auto-unboxing peligroso
Pasar `null` a un método que recibe `int`/`long` (porque vino como `Integer`/`Long`). Validar antes o usar primitivos.

#### Modelos del dominio mutables / con setters
Los modelos viven en `models` con constructor-only. Sin setters. Si una operación cambia el modelo, devuelve uno nuevo o el DAO retorna la versión actualizada. Ver `docs/architecture.md` (Coding Style).

#### Modelos instanciados en controllers/services
Los objetos de dominio nacen en la capa de persistencia (a partir de un `RowMapper` o devueltos por un `SimpleJdbcInsert`). Para updates, pasar parámetros sueltos al service, no instanciar `new Product(...)` en el controller. Si necesitás un agregado para pasar datos, usá un DTO/form.

#### Listas mutables pasadas por referencia entre capas
Un controller que recibe una lista y le hace `add` o reordena viola encapsulamiento. Los services devuelven listas inmutables o copias.

#### `CharacterEncodingFilter` configurado por bean **y** en `web.xml`
Si ya está en `web.xml`, no agregar un bean redundante. La duplicación confunde la config y suele indicar que nadie revisó el `web.xml` original.

#### Spring stereotype incorrecto
`@Service` para clases que no son lógica de negocio (ej., un bean de seguridad debe ser `@Component`). El estereotipo no es decorativo: indica el rol semántico.

#### Endpoints de modificación con `@RequestParam` cuando el ID es identidad de la entidad
`POST /productos?id=5` es semánticamente raro — el `id` identifica la entidad, debería ser `@PathVariable` (`POST /productos/5`). Reservar `@RequestParam` para filtros y opciones (`?sort=price&page=2`).

#### `@PathVariable` sin nombre explícito
```java
public void m(@PathVariable Long id) // depende de compilar con -parameters
public void m(@PathVariable("id") Long id) // robusto y explícito
```
Spring tiene un fallback que mira el debug info, pero no se garantiza con cualquier setup de compilación.

#### Métodos de interfaz con `public`
Las interfaces ya son `public` por definición; declarar los métodos con `public` es ruido. Importante por estilo, no por corrección.

#### Pushear archivos de IDE / configs vacíos / artifacts
`webapp.iml`, carpeta `bin/`, `out/`, `.vscode`, `target/`, `PVS-Studio/`, configuraciones vacías, tests comentados. Limpiar el `.gitignore` y revisar antes de cada commit.

#### Tests con preconditions insertadas vía `JdbcTemplate.update(...)` cuando hay `populator.sql`
Si hay un `populator.sql`, los tests de **lectura** no insertan. Los tests de escritura crean preconditions con `JdbcTemplate` directo (no a través del DAO bajo test). Ver `docs/testing.md`.

#### `schema.sql` vacío
Si la app tiene tablas, el `schema.sql` no puede estar vacío. Era pedido explícitamente por enunciado.

### Severidad: estilo / mejorable (sin penalización directa, pero recomendado)

#### Inyectar DAO en validators
Inyectar **services** en validators, no DAOs. El validator es un cliente del service como cualquier otro. Ver `docs/forms-and-validation.md`.

#### Tests sin cubrir paths de error
Solo happy paths. Usar `Assertions.assertThrows` para validar excepciones.

#### Try/catch para loggear y relanzar
```java
try { ... } catch (Exception e) { logger.error(...); throw e; } // ruido
```
Si solo querés loggear y relanzar, configurar el handler central. Si querés agregar contexto, lanzar una excepción específica.

#### `try/catch (Exception e)` genérico
Catchear `Exception` solo para evitar caer es ocultar bugs. Catchear la excepción específica esperada.

#### DTOs sin builder ni `.fromModel()` / `.toDTO()`
Cuando el controller arma DTOs con seteo manual de cada campo, la lectura sufre. Un método estático `Dto.fromModel(model)` o un builder mejora.

#### Mezcla de inglés/español en nombres
`buscarConFiltros` + `findByEmail` en la misma interfaz. Decidir un idioma y mantenerlo.

#### `snake_case` o `PascalCase` en nombres de método
Java es `camelCase`. Paquetes en lowercase. Nombres de método en `camelCase`.

#### Modificadores de acceso omitidos
Default package-private es raramente lo que se quiere. Declarar `public`/`private`/`protected` siempre. Ver `docs/guidelines.md`.

#### `static` faltante en clases utilitarias / RowMappers
RowMappers son `private static final RowMapper<T>`. Clases `Utils` con métodos estáticos no deberían ser instanciables (constructor privado). Effective Java item 4.

#### `[]` en lugar de `List<T>`
Effective Java item 28 — preferir `List` sobre arrays en APIs.

#### `@Async` + `@Transactional` en el mismo bean sin BD
Si el bean no toca la BD (ej. `EmailService` solo manda mails), `@Transactional` no agrega nada y confunde. Quitar.

#### Tests dentro de `services/test` sin mockear las llamadas al DAO
Si no mockeás los DAOs, no es un test de service unitario — es de integración por accidente.

#### Dependencias de Spring Boot en proyecto Spring 5
`spring-boot-starter-mail`, `spring-boot-starter-thymeleaf` y cualquier `spring-boot-*` rompen la convención del proyecto (Spring 5 + WAR + JSP). Usar el módulo Spring 5 equivalente (`spring-context-support` para mail, etc.). Ver `docs/setup.md` (Dependencies — Spring 5 only, NO Spring Boot).

#### Faltar `messages_es.properties`
Aunque el `messages.properties` por defecto esté en español, `messages_es.properties` debe existir (puede estar vacío) para dejar explícito que el locale `es` está soportado. Las claves faltantes se resuelven por herencia. Ver `docs/views-and-jsp.md`.

#### `System.out.println` / `e.printStackTrace()` para loguear
Salida estándar no respeta niveles, no rolla, no se filtra y termina en archivos genéricos del contenedor. Siempre `LOGGER.<level>(...)` de SLF4J.

#### Prefijos manuales en cada `LOGGER.<level>(...)`
Concatenar timestamp/thread/sessionId en cada log es ruido. Configurar el `<encoder><pattern>` en `logback.xml` una sola vez. Ver `docs/logging.md` (Cátedra directives — logging checklist).

#### `FileAppender` sin rolling policy
Sin `RollingFileAppender` + `TimeBasedRollingPolicy` y `maxHistory`, los logs crecen sin límite hasta llenar el disco. Pensar la ruta de logs en deploy: nombre con prefijo del proyecto, ubicación accesible al equipo.

#### Clase utilitaria instanciable
`public class Utils { public static String x() {...} }` — sin constructor privado, alguien la puede instanciar por error. Constructor `private` y clase `final`. Ver `docs/guidelines.md` (Utility classes — non-instantiable).

### Checklist negativo rápido (pre-entrega)

- [ ] No hay `${var}` con datos de usuario sin `<c:out>`.
- [ ] No hay `<% ... %>` ni `<%= ... %>` en JSPs.
- [ ] No hay lógica de negocio en controllers.
- [ ] No hay try-catch de excepciones de negocio en controllers.
- [ ] No hay `Mockito.verify()` ni `Mockito.spy()`.
- [ ] No hay tests de persistencia sin `JdbcTestUtils.countRowsInTable*`.
- [ ] No hay tests que llamen a otro método del DAO/service en la sección de Arrange o Assert (ver `docs/testing.md`).
- [ ] No hay `LIKE` con input sin escapar `%` y `_`.
- [ ] No hay loops `findById` (N+1).
- [ ] No hay `@Transactional` en DAOs ni controllers.
- [ ] No hay `@Transactional` faltante en métodos de service que escriben.
- [ ] No hay `@Transactional(readOnly = true)` faltante en métodos de service que solo leen.
- [ ] No hay `SecurityContextHolder` fuera de `webapp.auth` o `CurrentUserAdvice`.
- [ ] No hay validación de ownership en controllers.
- [ ] No hay role checks con magic strings en JSP (`<sec:authorize>` en lugar de `c:if`).
- [ ] No hay `<c:url>` ausente en links / recursos estáticos.
- [ ] No hay textos hardcodeados en JSP / controller / service.
- [ ] `messages_es.properties` existe (puede estar vacío y heredar del default).
- [ ] No hay dependencias `spring-boot-*` (mail, thymeleaf, etc.) — proyecto es Spring 5.
- [ ] No hay `System.out.println` / `e.printStackTrace()` — siempre `LOGGER.<level>(...)`.
- [ ] No hay logs a `DEBUG`/`INFO` en el `logback.xml` de prod.
- [ ] No hay logs a archivos genéricos (`catalina.out`, `localhost.log`) — `FileAppender` propio del proyecto.
- [ ] El `FileAppender` es `RollingFileAppender` con `maxHistory` razonable.
- [ ] No hay clases utilitarias instanciables — constructor `private`, clase `final`.
- [ ] No hay credenciales hardcodeadas.
- [ ] No hay URL base hardcodeada — usar `@Value("${app.base-url}")`.
- [ ] No hay versiones en poms hijos.
- [ ] No hay `schema.sql` fuera de `persistence`.
- [ ] No hay `java.sql.*` fuera de `persistence`.
- [ ] No hay magic strings / magic numbers — enums o constantes.
- [ ] No hay `Optional` como campo / parámetro — solo retorno.
- [ ] No hay `Optional.get()` sin verificar.
- [ ] No hay boxed primitives donde `null` no significa nada.
- [ ] No hay `@PathVariable` sin nombre explícito.
- [ ] No hay `POST /logout` controller.
- [ ] No hay loggers concatenando con `+` (siempre `{}`).
- [ ] No hay logs de DEBUG/INFO en `logback.xml` de producción (root level WARN).
- [ ] No hay PII en logs (sin nombres, apellidos, direcciones, CBU, tokens, passwords).
- [ ] No hay archivos basura commiteados (`bin/`, `out/`, `.iml`, `.vscode`).
- [ ] No hay tests comentados.
- [ ] El locale de los mails es el del **destinatario**, no del actor.

> Checklist extendido (trampas TP2 + findings nominales del Grupo 10): ver `docs/correcciones-cohorte.md` §5.