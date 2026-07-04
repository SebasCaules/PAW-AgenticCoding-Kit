## Technologies

### Backend
- Java 21
- Spring MVC 5.3.33 (`spring-webmvc`, `spring-context`)
- Spring JDBC 5.3.33 (`spring-jdbc`, `JdbcTemplate`, `SimpleJdbcInsert`)
- Bean Validation 2.0 (`javax.validation`) + Hibernate Validator 6.2.4

### Database
- PostgreSQL (production) via `postgresql` 42.2.5 driver
- HSQLDB 2.3.1 (in-memory, tests only; uses `sql.syntax_pgs=true` for PostgreSQL compatibility)
- Every Flyway migration that changes database structure or constraints must also update `persistence/src/test/resources/schema.sql` so the HSQLDB test schema matches the final migrated schema.

### Frontend
- JSP views with JSTL 1.2
- Custom JSP tag files (`WEB-INF/tags/`)
- Static resources: CSS and assets served via Spring's resource handler

### Build Tool
- Maven (multi-module, parent POM at project root)
- Jetty Maven Plugin 9.x for local development server (port 8080)

### Server
- Jetty (development): `cd webapp && mvn jetty:run`
- Packaged as a `.war` for deployment

## Prerequisites

- Java 21
- Maven 3.x
- PostgreSQL running locally with:
  - Database: `paw`
  - User: `pawdbuser`
  - Password: `pawdbsecret`
  - URL: `jdbc:postgresql://localhost/paw`

## Admin bootstrap (`admin.bootstrap.email`)

`AdminBootstrap` (`services`) promotes the user whose email matches the `admin.bootstrap.email`
property to `ROLE_ADMIN` so the very first admin can be created without a chicken-and-egg problem
(you need an admin to promote users, but there is no admin yet).

**Operational rule — empty it after the first deploy.** The bootstrap runs on **every** application
startup (`ContextRefreshedEvent`), not just the first one. So if that admin is later **demoted or
banned**, the next restart will silently **re-promote** them. After the initial deploy has created
the admin account, set `admin.bootstrap.email` to blank (or remove it) in `application.properties`
and leave it empty for the rest of the deployment's life. When blank, the bootstrap is skipped
(it logs `Admin bootstrap skipped`). Promote any further admins from the in-app admin panel
(`/admin/users`), not via this property.

## Build & Run Commands

All Maven commands must be run from the **project root** (`/Users/magaligonzalezporzio/paw-2026a-10`).

```bash
# Build entire project
mvn clean package

# Run the web application (Jetty, port 8080)
cd webapp && mvn jetty:run

# Run all tests
mvn test

# Run tests for a specific module
mvn test -pl persistence
mvn test -pl services

# Run a single test class
mvn test -pl persistence -Dtest=UserJdbcDaoTest
```

## Maven Module Structure

The root `pom.xml` declares all versions in `<dependencyManagement>`. Child modules inherit from it and do not re-declare versions.

| Module | Artifact | Purpose |
|--------|----------|---------|
| `models` | jar | Immutable domain objects and enums |
| `persistence-contracts` | jar | DAO interfaces |
| `persistence` | jar | JDBC DAO implementations (`JdbcTemplate`, `SimpleJdbcInsert`) |
| `service-contracts` | jar | Service interfaces |
| `services` | jar | Business logic implementations |
| `webapp` | war | Spring MVC controllers, JSP views, Spring config |

Dependency direction: `webapp` → `service-contracts` (compile) + `services` (runtime) → `persistence-contracts` (compile) + `persistence` (runtime) → `models`

### Dependency Management

Dependency versions, scopes, and types are centralized in the root `pom.xml` under `<dependencyManagement>`. Child modules declare dependencies with **only `<groupId>` and `<artifactId>`** — no `<version>`, `<scope>`, or `<type>`. Maven resolves all other attributes from the parent BOM.

This applies to every dependency, including sibling modules (`models`, `persistence-contracts`, `persistence`, `service-contracts`, `services`): they are declared in `<dependencyManagement>` of the root POM so children need only groupId+artifactId.

When adding a new dependency:
1. Add a `<property>` for the version in the root `pom.xml` `<properties>` block (e.g. `<foo.version>1.2.3</foo.version>`). Never hardcode a version literal directly inside `<dependencyManagement>`.
2. Add the full entry (groupId, artifactId, version via property, and scope if not `compile`) to `<dependencyManagement>` in the root `pom.xml`.
3. Reference it with only `<groupId>` and `<artifactId>` in the relevant child module's `pom.xml`.

**Never** declare `<version>`, `<scope>`, or `<type>` inside a child module's `<dependency>` block — these must live exclusively in the root `<dependencyManagement>`.

### Dependencies — Spring 5 only, NO Spring Boot

This project uses **Spring Framework 5** (classic `@Configuration` + `web.xml` + WAR). It is **not** a Spring Boot project. Do **not** add `spring-boot-*` dependencies — they pull a different lifecycle, embedded server, autoconfiguration, and starter conventions that are incompatible with the project setup. The cátedra penalizes their inclusion.

Banned dependencies (non-exhaustive):

- `spring-boot-starter-mail` — use `org.springframework:spring-context-support` + `JavaMailSender` directly.
- `spring-boot-starter-thymeleaf` — the project uses JSP/JSTL, not Thymeleaf. Adding it as a dependency on top of JSPs is an architectural inconsistency.
- Any other `spring-boot-starter-*` (web, security, data-jpa, validation, test, etc.).
- `spring-boot-autoconfigure`, `spring-boot-dependencies`.

Rule of thumb: if the artifactId starts with `spring-boot-`, it does not belong in this project. Use the equivalent Spring 5 module directly (`spring-webmvc`, `spring-jdbc`, `spring-security-web`, `spring-context-support`, etc.).
