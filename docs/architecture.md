## Architecture

### Configuration & Bootstrapping

Spring is bootstrapped via `web.xml` which registers an `AnnotationConfigWebApplicationContext` pointing to `WebConfig.java`. The `DispatcherServlet` handles all requests (`/`).

`WebConfig` (`webapp/src/main/java/.../config/WebConfig.java`) is annotated with `@Configuration`, `@EnableWebMvc`, `@ComponentScan`, and `@PropertySource`. It defines all infrastructure beans:
- `ViewResolver` — resolves view names to `/WEB-INF/views/*.jsp`
- `DataSource` — reads `db.url`, `db.username`, `db.password` from `application.properties` via `@Value`
- `DataSourceInitializer` — runs `schema.sql` on startup to create/update tables
- `CommonsMultipartResolver` — handles file uploads (max 10 MB/file, 30 MB total)
- `MessageSource` — loads i18n messages from `classpath:i18n/messages`
- `LocalValidatorFactoryBean` — integrates Bean Validation with Spring MVC
- `PropertySourcesPlaceholderConfigurer` (static bean) — enables `@Value` resolution at startup

`@ComponentScan` covers `ar.edu.itba.paw.webapp.controller`, `ar.edu.itba.paw.services`, and `ar.edu.itba.paw.persistence` so all annotated beans in those packages are auto-detected.

### Coding Style

**Dependency Injection:** Constructor injection is preferred; field injection via `@Autowired` is also used. All service and DAO beans are Spring-managed (`@Service`, `@Repository`).

**Configuration:** Infrastructure is declared as `@Bean` methods inside `@Configuration` classes. There is no XML Spring config beyond `web.xml`.

**Persistence:** Progressive migration from JDBC to JPA/Hibernate is in flight. Newer DAOs use Hibernate via `EntityManager` (e.g., `ProductJpaDao`, `BlockJpaDao`, `PriceHibernateDao`, `FavoriteJpaDao`); legacy DAOs still use `JdbcTemplate` and `SimpleJdbcInsert` (e.g., `UserJdbcDao`, `RentJdbcDao`, `ImageJdbcDao`, `ReviewJdbcDao`). The HSQLDB test schema lives in `persistence/src/test/resources/schema.sql` and is applied via `DataSourceInitializer`; PostgreSQL prod schema is managed via Flyway migrations under `persistence/src/main/resources/db/migration/`.

**Models:** Domain objects are JPA-managed entities — Hibernate requires non-final fields and a no-arg constructor (typically `protected`), so the old "immutable, constructor-only" rule no longer holds at the field level. Public-API immutability is no longer a strict rule: setters are added where the service layer needs to mutate the entity, including hydrating `@Transient` derived fields (e.g., `Product.images`, `Product.effectivePrice`). The mutation surface should stay in the service layer; **controllers and views must not modify entity state directly**. Enums define controlled vocabularies: `Location`, `Category`, `Gender`, `Size`, `Condition`, `Currency`, `RentStatus`.

**Enum conventions:** Enums shown in the UI implement `HasMessageCode` and expose `getMessageCode()` (annotated `@Override`), resolved in JSP via `<spring:message code="${enum.messageCode}"/>` for real i18n. Enums that appear in URLs/forms also implement `HasSlug`. **Do not** add a `getDisplayName()` method — it returns hardcoded, untranslated text and is banned. For persistence and HTTP parameters, use `.name()` directly: it matches exactly the text stored in the database, so no lowercasing or other transformation is needed.

**Views:** JSP files in `webapp/src/main/webapp/WEB-INF/views/`. Custom JSP tag files in `WEB-INF/tags/` (navbar, modals, product cards, etc.).

**File uploads:** Images are stored as binary blobs in the `images` table and served via `ImageController`.

### Spring Security wiring

Spring Security lives in `webapp/src/main/java/.../config/WebAuthConfig.java` (registered alongside `WebConfig` in `web.xml`'s `contextConfigLocation`). It uses the modern `SecurityFilterChain` API, **not** the deprecated `WebSecurityConfigurerAdapter`. The `DelegatingFilterProxy` filter is mapped to `/*` in `web.xml`.

`UserDetailsService` (in `ar.edu.itba.paw.webapp.auth`) is injected by type. It looks up users via `UserService.findByEmail` and wraps them in `AuthUser` (an internal subclass of Spring's `User` that holds the domain `User`). Controllers never reference `AuthUser` directly — they consume the domain `User` exposed via `@ModelAttribute("loggedUser")` (see below).

For full detail on rules, ownership, and `<sec:authorize>`, see `docs/security.md`.

### `@ControllerAdvice` pair

The webapp uses **two** `@ControllerAdvice` classes with distinct responsibilities:

1. **`CurrentUserAdvice`** (`ar.edu.itba.paw.webapp.controller`) — `basePackages`-scoped to the controller package. Exposes the logged-in user as `@ModelAttribute("loggedUser") User loggedUser`. Resolves it once via `SecurityContextHolder` and `UserService.findByEmail`. Returns `null` for anonymous requests.

2. **`GlobalExceptionHandler`** — global. Maps domain exceptions and Spring exceptions to HTTP status codes and error views:

| Exception | Status | View |
|---|---|---|
| `ResourceNotFoundException` | 404 | `error/404` |
| `ForbiddenException` | 403 | `error/403` |
| `MethodArgumentTypeMismatchException` | 404 | `error/404` |
| `MaxUploadSizeExceededException`, `MultipartException` | 413 | `error/413` |
| `Exception` (catch-all) | 500 | `error/500` |

`ResourceNotFoundException` and `ForbiddenException` live in `service-contracts` under `ar.edu.itba.paw.services.exceptions`. They are plain `RuntimeException`s — the HTTP mapping lives in `GlobalExceptionHandler`, **not** as `@ResponseStatus` on the exception class.

### Transaction management

`@EnableTransactionManagement` is on `WebConfig`. The `PlatformTransactionManager` bean is a `DataSourceTransactionManager` wrapped around the project `DataSource`.

Convention:
- `@Transactional` lives only on **service classes** (or their methods). Never on DAOs, never on controllers.
- Read methods → `@Transactional(readOnly = true)`. Write methods → `@Transactional` (no flags).
- Annotate **per method** rather than at class level — makes intent (read vs write) visible per method.
- Service methods invoked by `@Async` need to be aware that `@Transactional` does not propagate the active transaction to the async thread. If the async method needs a transaction, annotate it explicitly.

### `@Async` and ThreadLocal pitfalls

Methods annotated `@Async` run in a different thread, so:
- `LocaleContextHolder.getLocale()` returns the default (often `en`), not the locale of the request that triggered it. Pass the recipient's locale as a parameter.
- `SecurityContextHolder` is empty unless explicitly propagated — pass the user (or `userId`) as a parameter.
- Exceptions thrown from `@Async` methods **vanish silently** unless you wrap the body in `try { ... } catch (RuntimeException e) { LOGGER.error("...", e); }`. Especially important for SMTP / IO calls.

### Email service

`EmailServiceImpl` uses `JavaMailSender` (Gmail SMTP, port 587, TLS). Configuration values come from `application.properties`:
- `app.base-url` — the public URL of the app (used to build links in mails). NEVER hardcode this.
- `app.mail.from` — the sender address.
- `mail.username` / `mail.password` — SMTP credentials.

Rules:
- Send mails with the **recipient's** preferred locale (`recipient.getPreferredLanguage()`), not `LocaleContextHolder.getLocale()`.
- Annotate the public methods with `@Async` so the request thread is not blocked by SMTP.
- Wrap the SMTP call in `try/catch (RuntimeException e)` and log `ERROR` so failures surface despite `@Async`.
- The `EmailService` lives in `services` and **must not** reference templates that live in `webapp/WEB-INF/`. Pass the resolved text as a parameter, or move template resolution to a `webapp` component.
