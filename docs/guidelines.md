## Data Access & Performance

Avoid N+1 query patterns.

Do not:
- fetch entities in a loop calling the DAO multiple times;
- load related data lazily via repeated queries.

Prefer:
- fetching all required data in a single query;
- joining necessary tables;
- returning fully usable data for the use case.

Controllers and services must be aware of query efficiency.

## Error Handling

Controllers must not use try-catch for business errors.

All exceptions must be handled via:
- @ControllerAdvice
- centralized exception handlers

Services throw domain exceptions.
Controllers do not handle them directly.

## Implementation Plans

All implementation plans must be saved under `0_Plans/` before starting any feature work. Never start implementing without a saved plan.

**Before creating a plan, read [`0_Plans/CATALOG.md`](../0_Plans/CATALOG.md).** That file is the single source of truth for:

- The rules for placement (no plans in the root of `0_Plans/` — every plan lives inside a topic folder).
- The current set of topic folders (`auth/`, `prices/`, `products/`, `rents/`, `reviews/`, `users/`, `ui-ux/`, `tests/persistence/`, `tests/services/`, `persistence/`, `cross-cutting/`, `audits/`).
- The naming convention (`plan_<slug>.md` for features/refactors, `fix-<slug>.md` for bug fixes, `prompt_<slug>.md` for reusable prompts).
- The expectation that every new plan is registered in `CATALOG.md` with its tipo and one-line description.

If no existing topic folder fits the plan, create a new one (lowercase, kebab-case) and add the corresponding section to `CATALOG.md` in the same change.

## CSS Guidelines

### Do NOT use `!important`
- Avoid using `!important` in CSS under any circumstances.
- It breaks the natural cascade and makes styles hard to override and maintain.

### Do NOT write CSS inside JSP files
- Do not include `<style>` tags or inline CSS inside JSPs.
- All styles must live in dedicated CSS files (e.g., `/css/components.css`, `/css/colors.css`).

### Preferred approach
- Use Bootstrap utility classes whenever possible.
- If custom styling is needed, define reusable classes in CSS files.
- Keep separation of concerns:
  - JSP → structure & content
  - CSS → styling

## Code Style Guidelines

### Entity references in APIs

Use a clear boundary between object construction and layer APIs:

- Constructors receive domain objects when they model object relationships, for example `new Rent(product, block, renter, ...)`.
- Public DAO and service methods receive ids for existing entity references, for example `createRent(productId, blockId, renterId, ...)`.
- DAO implementations may turn ids into persistence references internally (`em.getReference(...)`) before calling a constructor.
- Service implementations may call the owning service to resolve data managed by another aggregate; they must not inject another DAO directly.

This keeps method contracts stable and avoids passing partially loaded or stale domain objects across layers, while preserving expressive constructors inside the model.

### Access Modifiers

- Do not omit access modifiers (`public`, `private`, `protected`).
- Every class, method, and field must explicitly declare its visibility.
- Visibility must be intentional and consistent with usage:
  - Use `private` by default.
  - Use `public` only when the element is part of the external API.
  - Avoid package-private unless there is a clear and justified reason.

- Example:
  - DAOs should NOT be package-private if they are used by services.
  - Services should expose only the methods needed by controllers.

### Utility classes — non-instantiable

A utility class is a class with **only `static` members** (helpers, format functions, constants). It is never meant to be instantiated. Convention:

- All methods and fields are `static`.
- The class is `final` (no subclassing).
- A **`private` no-arg constructor** prevents accidental instantiation (and silences the implicit public default constructor).
- Optionally throw inside the constructor as a defensive measure if reflection is a concern.

```java
// RIGHT
public final class StringUtils {

    private StringUtils() {
        // utility class — not instantiable
    }

    public static String escape(final String input) { ... }
}

// WRONG — public default constructor, can be instantiated, can be subclassed
public class StringUtils {
    public static String escape(final String input) { ... }
}
```

The cátedra penalizes utility classes that can be instantiated as a code-style issue.

### Layer Boundaries

Each module is constrained in what it may import. Violations are cátedra-graded errors.

| Module | May import | Must NOT import |
|---|---|---|
| `models` | JDK only (`java.time.*`, `java.util.*`) | Anything Spring; `java.sql.*`; webapp; persistence |
| `persistence-contracts` | `models` | Spring infrastructure (`spring-jdbc`, `spring-web`); webapp |
| `persistence` | `persistence-contracts`, `models`, `spring-jdbc`, `java.sql.*` | webapp; service-contracts; services |
| `service-contracts` | `models`, exception types | Spring infrastructure; webapp |
| `services` | `service-contracts`, `persistence-contracts`, `models`, Spring annotations (`@Service`, `@Transactional`) | webapp templates; `webapp.controller`; persistence implementations |
| `webapp` | All of the above (interfaces only) — `service-contracts` (compile), `services` (runtime); `persistence-contracts` (compile), `persistence` (runtime); `models` | nothing more restrictive |

Specific bans:
- **No `java.sql.*` outside `persistence`.** Use `java.time.*` everywhere else (`LocalDate`, `LocalDateTime`, `Instant`). Conversion happens in the DAO.
- **No `schema.sql` / Flyway migrations outside `persistence`.** They are an implementation detail of the DAO.
- **No services referencing webapp resources.** A service in `services` may not look up template paths under `webapp/WEB-INF/`.
- **No DAO injected into a controller or validator.** Validators inject services (interfaces from `service-contracts`).
- **Each table has exactly one DAO.** If `ProductDao` writes to `users`, that is wrong — it belongs in `UserDao`.

### Magic Strings & Magic Numbers — use enums and constants

The cátedra penalizes magic literals in any layer. Use enums (`Location`, `Category`, `Currency`, `RentStatus`, `ProductStatus`, etc.) for controlled vocabularies and `private static final` constants for everything else.

```java
// WRONG
String orderBy = "price_asc";
int defaultPageSize = 12;
List<String> days = Arrays.asList("MONDAY", "TUESDAY", ...);

// RIGHT
OrderBy orderBy = OrderBy.PRICE_ASC;
private static final int DEFAULT_PAGE_SIZE = 12;
List<DayOfWeek> days = Arrays.asList(DayOfWeek.MONDAY, DayOfWeek.TUESDAY, ...);
```

Enum conventions in this project (see `docs/architecture.md`):
- `enum.name()` for persistence and HTTP — exact string in the DB.
- `enum.getMessageCode()` + `<spring:message>` for UI (never `getDisplayName()` — it returns hardcoded, untranslated text).

### `Optional` rules

`Optional` is for **return values only**. It must NOT appear:
- as a field of a class;
- as a method parameter;
- inside a collection (`List<Optional<X>>`);
- without being unwrapped before consumption.

Always use `orElseThrow(() -> new ResourceNotFoundException(...))` or `isPresent()` / `ifPresent()`. Never `.get()` without checking presence.

For optional fields of an immutable model:

```java
public class Event {
    private final String description;     // can be null

    public Optional<String> getDescription() {
        return Optional.ofNullable(description);
    }
}
```

### Representing absence — pick one strategy

Across the project, "this thing does not exist" must be expressed consistently:
- `findBy*` returns `Optional.empty()`;
- model fields hold `null` for "not provided" (and exposed via `Optional.ofNullable` getter);
- never use `id = -1` or magic sentinel values.

Mixing the three is a TP1-graded error. Pick one and propagate it.

### Boxed primitives only when `null` has meaning

Use `int`/`long`/`boolean` when the value is always present. Reach for `Integer`/`Long`/`Boolean` only when `null` carries semantic information ("not yet set", "optional"). Auto-unboxing a `null` boxed primitive throws `NullPointerException` silently.

### Naming conventions

- Java: `PascalCase` for types, `camelCase` for methods/fields, `UPPER_SNAKE_CASE` for constants.
- Packages: lowercase, no underscores, no camelCase.
- Pick one language for identifiers (Spanish or English) and stick to it. Mixing them in the same interface is a graded error.

### Repository hygiene

These should never be committed:

- IDE configuration: `.idea/`, `.vscode/`, `*.iml`, `bin/`, `out/`, `target/`, `webapp.iml`.
- Static-analysis caches: `PVS-Studio/`, `.sonar/`.
- Empty configuration files added by accident.
- Tests commented out (delete them or fix them).
- `application.properties` with credentials — use `application.example.properties` and gitignore the real one.
- Logs: `logs/`, `*.log`.

Maintain `.gitignore` accordingly. The `.gitignore` rule `.properties` (no prefix) does NOT match files ending in `.properties`; use `*.properties` if that's the intent.

### `@PathVariable` / `@RequestParam` — name your parameters

```java
// WRONG — relies on -parameters compilation flag
public ModelAndView m(@PathVariable Long id) { ... }

// RIGHT — robust, no compile-flag dependency
public ModelAndView m(@PathVariable("id") final Long id) { ... }
```

Spring has a fallback that reads the debug info, but it requires `-parameters` or unoptimized compilation. Always declare the name explicitly.

### Domain identity for entities

When a request modifies a specific resource, the resource ID belongs in the **path**, not in a query param:

```
POST /products/5/edit       (id = path variable — entity identity)
POST /catalog?location=BARILOCHE  (filter — query param)
```

Mixing them sends a confusing semantic signal.

### Externalize all configuration

Anything that varies between environments lives in `application.properties` and is consumed via `@Value`. Never hardcode:
- Base URL of the app (`app.base-url`).
- Mail credentials (`mail.username`, `mail.password`) and from address (`app.mail.from`).
- DB credentials (`db.url`, `db.username`, `db.password`).
- File-upload size limits (when overridable).

Do not commit a populated `application.properties`. Document the required keys in `application.example.properties` or `setup.md`.

### Excecption handling — pick the specific exception type

Catching `Exception` (without a specific type) hides real bugs. Catch the actual exception you can handle. If you cannot handle it, do not catch it — let `@ControllerAdvice` map it to the right HTTP response.

Wrapping risky calls only to log and rethrow is noise. Either:
- Add context by wrapping in a domain exception with a useful message; or
- Let the exception propagate and let the `GlobalExceptionHandler` (or async `try/catch` for `@Async`) deal with it.
