## Spring Security & Ownership

Spring Security secures the web layer using the ACL pattern (Roles, Resources, Permissions). Configuration lives in `webapp/src/main/java/.../config/WebAuthConfig.java`. The team uses the modern `SecurityFilterChain` API, **not** the deprecated `WebSecurityConfigurerAdapter`.

### web.xml integration

Two pieces are required:

```xml
<!-- 1. Register WebAuthConfig alongside WebConfig -->
<context-param>
    <param-name>contextConfigLocation</param-name>
    <param-value>
        ar.edu.itba.paw.webapp.config.WebConfig,
        ar.edu.itba.paw.webapp.config.WebAuthConfig,
    </param-value>
</context-param>

<!-- 2. DelegatingFilterProxy intercepts all requests -->
<filter>
    <filter-name>springSecurityFilterChain</filter-name>
    <filter-class>org.springframework.web.filter.DelegatingFilterProxy</filter-class>
</filter>
<filter-mapping>
    <filter-name>springSecurityFilterChain</filter-name>
    <url-pattern>/*</url-pattern>
</filter-mapping>
```

### WebAuthConfig — pattern

- Use `@EnableWebSecurity` + `@Bean SecurityFilterChain filterChain(HttpSecurity http)`.
- Inject `UserDetailsService` (the standard Spring interface) by type — Spring resolves it to the project's implementation in `webapp.auth`.
- **The order of `requestMatchers` matters — first match wins.** All public matchers must be declared **before** `anyRequest().hasRole("USER")` (or the equivalent default rule). Putting a permissive rule like `/**.permitAll()` before a restrictive one is a security bug.
- `accessDeniedPage("/error/403")` routes 403s to `ErrorController.forbidden()`.
- `formLogin` configures `usernameParameter("email")` and `passwordParameter("password")`; the login form posts to `/login`.
- Static assets (`/css/**`, `/js/**`, `/assets/**`, `/images/**`, `/favicon.ico`, `/error/**`, `/.well-known/**`) are `permitAll()`.

### CSRF — disabled on purpose (NOT a finding)

`WebAuthConfig.filterChain` disables CSRF: `WebAuthConfig.java:142` → `.csrf(AbstractHttpConfigurer::disable)`. **This is deliberate and is the cátedra-shown pattern**, not a vulnerability to fix:

- The course material disables CSRF explicitly — `wiki/concepts/spring-security.md:102` (`.csrf(csrf -> csrf.disable())`) and `wiki/sources/clase-5-spring-security-logging.md:107` (`.and().csrf().disable();`).
- It is the standing team decision for this project; the `pawserver` deploy runs this way.

**Do not re-flag CSRF disabled as a finding.** Any audit, `/corrector-eyes`, or `/gp` pass that surfaces "CSRF disabled → habilitar CSRF" is a **false-positive** here — close it citing this section. (Historical note: `0_Plans/audits/ad-hoc/admin-panel-and-deactivation-audit.md` A-SEC1 raised it as ALTA and cited `docs/correcciones-cohorte.md §3.1`; that citation is **inexact** — `correcciones-cohorte.md` does not mention CSRF — so A-SEC1 is discarded.)

### Role naming

- Role names **must** be prefixed with `ROLE_` in `GrantedAuthority` (e.g., `new SimpleGrantedAuthority("ROLE_USER")`).
- `hasRole("USER")` automatically expects `ROLE_USER` — Spring strips the prefix when evaluating.
- A user can have multiple roles (it's a `Collection<GrantedAuthority>`).

### `UserDetailsService` + `AuthUser` (project pattern)

Located in `ar.edu.itba.paw.webapp.auth`. Implements the standard `org.springframework.security.core.userdetails.UserDetailsService`. Wraps the domain `User` in `AuthUser` (extends Spring's `User` `UserDetails`) so the domain object is recoverable when needed.

Rules:
- Annotate `loadUserByUsername` with `@Transactional(readOnly = true)` — login should not open a write transaction.
- If `user.getPassword() == null/empty`, throw `UsernameNotFoundException` (rejects guest-stub accounts that haven't completed registration).
- **Controllers MUST NOT depend on `AuthUser` directly.** They receive the domain `User` via `@ModelAttribute("loggedUser")` (see below). `AuthUser` is an implementation detail of the `auth` package.

### Accessing the logged-in user from controllers

**Convention: use `@ModelAttribute("loggedUser") final User loggedUser`.** Do NOT use `@AuthenticationPrincipal`, do NOT call `SecurityContextHolder` from controllers, do NOT call it from services.

The user is resolved exactly once by `CurrentUserAdvice`:

```java
@ControllerAdvice(basePackages = "ar.edu.itba.paw.webapp.controller")
public class CurrentUserAdvice {
    private final UserService userService;

    @ModelAttribute("loggedUser")
    public User loggedUser() {
        final Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth == null || !auth.isAuthenticated() || "anonymousUser".equals(auth.getName())) {
            return null;
        }
        return userService.findByEmail(auth.getName()).orElse(null);
    }
}
```

This makes `loggedUser` available:
- As a method parameter in any controller (`@ModelAttribute("loggedUser") final User loggedUser`).
- As `${loggedUser}` in any JSP.

`basePackages` scopes the advice to controller-handled requests so it does not run in test or service contexts.

**Why this and not `@AuthenticationPrincipal AuthUser`?** Decoupling: controllers see only the domain `User`. If the auth strategy changes, only `CurrentUserAdvice` needs to change.

### `SecurityContextHolder` — strict placement rule

| Layer | Allowed? |
|---|---|
| Controllers | NO — receive the user as `@ModelAttribute` parameter |
| Services | NO — receive `userId` / `User` as method parameter |
| `webapp.auth` package | YES (e.g., the success handler, custom filters) |
| `@ControllerAdvice` (`CurrentUserAdvice`) | YES — single source of truth |

The cátedra penalizes `SecurityContextHolder` usage in services or sprinkled across controllers as inconsistency / layer violation.

### Ownership — declarative at the web boundary

Verifying the role is **not enough**. If a user can access a resource that belongs to another user, that's a security bug even if the role is correct. The cátedra requires the ownership **decision** to be **declarative at the web layer** (`@PreAuthorize` on the controller, or a rule in `WebAuthConfig`) and **never** inside a service. Services may answer ownership *queries* (e.g. `isProvider`) but must not throw `ForbiddenException` as the primary gate.

All per-resource access control uses **`@PreAuthorize` on the controller method**, backed by access-handler beans in `webapp.auth` (`ProductAccessHandler`, `ReportAccessHandler`, `RentAccessHandler`). Method security is enabled by `@EnableMethodSecurity(prePostEnabled = true)` on `WebAuthConfig`.

The Maven compiler is configured with `<parameters>true</parameters>` in the parent and module `maven-compiler-plugin` declarations. This keeps Java method parameter names in the compiled bytecode, so Spring Security SpEL expressions such as `#id`, `#productId`, `#reportId`, and `#rentId` resolve from the actual controller parameter names instead of depending on debug local-variable metadata.

```java
// Controller — declarative.
@PreAuthorize("@productAccessHandler.isOwner(authentication, #id)")
@RequestMapping(value = "/products/{id}/edit", method = RequestMethod.GET)
public ModelAndView editForm(@PathVariable("id") final Long id) {
    final Product product = productService.getProductDetail(id);   // load only — no userId, no ownership check
    ...
}
```

```java
// webapp.auth — the handler answers an ownership question; the DECISION is the @PreAuthorize
@Component
public class ProductAccessHandler {
    public boolean isOwner(final Authentication auth, final Long productId) {
        final Long userId = AuthSupport.resolveUserId(auth);
        if (userId == null || productId == null) return false;
        try {
            return productService.getProductById(productId).getProviderId().equals(userId);
        } catch (final ResourceNotFoundException e) { return false; }
    }
}
```

Rent endpoints follow the same pattern via `RentAccessHandler` (`canCreateRent`, `canAccessAsProvider/Renter/Participant`). `RentAccessHandler` delegates to ownership *queries* on `RentService` (`isProvider`, `isRenter`, `isParticipant`) — these stay in the service because they return a boolean fact, not an authorization decision.

The controller never branches on ownership and the service never throws `ForbiddenException` for it; `@PreAuthorize` returns 403, mapped by `GlobalExceptionHandler`. The service still loads the resource with `getProductById` / `getProductDetail` / `findById`, which throws `ResourceNotFoundException` (404) when it does not exist.

#### Why the web layer owns this check

- The cátedra grades service-level ownership decisions as a layer violation (TP1 + TP2 reincidente). Authorization belongs at the web boundary.
- Keeps the service focused on business rules (state machine, dates, duplicates) — anything that reaches it is assumed already authorized.
- One declarative place per resource: the `@PreAuthorize` SpEL (or the `WebAuthConfig` matcher), backed by a single access-handler bean.

### Exception convention for ownership

| Exception | Where it lives | HTTP mapping |
|---|---|---|
| `ResourceNotFoundException` | `service-contracts` → `ar.edu.itba.paw.services.exceptions` | 404 |
| `ForbiddenException` | `service-contracts` → `ar.edu.itba.paw.services.exceptions` | 403 |

Both are plain `RuntimeException`s (no `@ResponseStatus` on the exception class — the mapping lives in `GlobalExceptionHandler`). Living in `service-contracts` lets services, DAOs and controllers reference them without violating the dependency direction.

**404 vs 403 disclosure rule:** when a user tries to access another user's resource, return **403** (do **not** leak whether the resource exists by returning 404 in some cases and 403 in others). The cátedra has flagged the inconsistency.

### `<sec:authorize>` in JSPs (vs `c:if + role string`)

```jsp
<%-- WRONG — magic string + duplicates the ACL --%>
<c:if test="${loggedUser.role == 'ADMIN'}">
    <a href="/admin">Panel</a>
</c:if>

<%-- RIGHT — uses the same WebAuthConfig rules --%>
<sec:authorize access="hasRole('ADMIN')">
    <a href="<c:url value='/admin'/>">Panel</a>
</sec:authorize>

<%-- Or by URL — respects the antMatchers / requestMatchers exactly --%>
<sec:authorize url="/admin">
    <a href="<c:url value='/admin'/>">Panel</a>
</sec:authorize>
```

### ACL — where each rule lives

Every access rule is declarative at the web layer. There are exactly two homes (never duplicated for the same endpoint):

- **Coarse rules** (public matchers, `/admin/**` → `hasRole("ADMIN")`, `anyRequest().hasAnyRole("USER","ADMIN")`) → `WebAuthConfig.filterChain(...)`.
- **Per-resource access** (ownership for products, reports, rents) → `@PreAuthorize` on the controller method, backed by `ProductAccessHandler` / `ReportAccessHandler` / `RentAccessHandler`. Enabled by `@EnableMethodSecurity(prePostEnabled = true)` on `WebAuthConfig`.

Rules:
- **Never** put `@PreAuthorize` in a **service** — zero tolerance (cátedra-graded, reincidente TP1→TP2). Method security applies only to controllers.
- **Never** gate the *same* endpoint in both `WebAuthConfig` and `@PreAuthorize` — pick one per endpoint.
- A service may expose ownership *queries* (`isProvider`, `isOwner`) consumed by an access-handler bean — that is a data fact, not an authorization decision, so it is allowed.

### `POST /logout` — handled by Spring Security

**Do not** define a controller method for `POST /logout`. Spring Security wires it via `.logout(logout -> logout.logoutUrl("/logout").logoutSuccessUrl("/login"))`. Defining your own endpoint is a cátedra-graded error.

### `accountNonLocked` — use it for soft account lock

If the project ever needs to disable / lock users, use the `UserDetails` flags (`accountNonLocked`, `enabled`, `accountNonExpired`, `credentialsNonExpired`) rather than checking a column manually in every controller. Spring Security blocks login automatically when those flags are false.

### Anti-patterns flagged by the cátedra

- Manual ownership checks in controllers (`if (loggedUser.getId() != resource.getOwnerId())`).
- `if (loggedUser != null)` everywhere instead of letting the matchers in `WebAuthConfig` enforce authentication.
- Gating the **same** endpoint twice (a `WebAuthConfig` matcher **and** a `@PreAuthorize`) — one home per endpoint.
- `@PreAuthorize` on a **service** method — authorization belongs on the controller only.
- Ownership **decisions** (throwing `ForbiddenException`) inside a service instead of declaratively at the web layer.
- Custom `POST /logout` endpoint.
- `SecurityContextHolder` in service or sprinkled across controllers.
- Returning 404 for forbidden resources (and 403 for not-found ones).
- `WebSecurity` bean annotated as `@Service` instead of `@Component` (wrong stereotype).
