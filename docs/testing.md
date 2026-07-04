## Testing Practices

### Dónde viven los tests

Los tests **solo** pueden existir en dos módulos:

- `persistence/src/test/` — tests de DAOs contra HSQLDB en memoria.
- `services/src/test/` — tests de servicios con Mockito.

**Nunca** crear tests en `webapp/` ni en `models/`. Si existe un `*Test.java` o un `*Test.class` en esos módulos, debe eliminarse. Los artefactos compilados stale en `target/` también deben limpiarse con `mvn clean`.

---

### General

- All tests use **JUnit 5** (`junit-jupiter-api`).
- All tests follow **AAA structure**:
  1. `// 1. Arrange`
  2. `// 2. Exercise`
  3. `// 3. Assert`
- Naming: `test<MethodName>When<Condition>Returns<ExpectedOutcome>`
- e.g. `testFindByIdWhenUserExistsReturnsUser`, `testFindByIdWhenUserDoesNotExistReturnsEmptyOptional`
- Every test must be unitary: it exercises exactly one public method of the class under test. Do **not** call another method of the same DAO/service to prepare data or assert the result.

### Persistence Tests 

- Located in `persistence/src/test/`
-  Each test class is annotated with `@Transactional` + `@Rollback` so every test runs in isolation and leaves no state behind.
- Use **HSQLDB** in-memory database with `sql.syntax_pgs=true` (partial PostgreSQL syntax compatibility)
- `TestConfiguration.java` wires up the in-memory `DataSource`, a `DataSourceTransactionManager`, and a `DataSourceInitializer` that runs `schema.sql`
- Tests load this config with `@ExtendWith(SpringExtension.class)` + `@ContextConfiguration(classes = TestConfiguration.class)`
- Use `JdbcTestUtils.countRowsInTable(jdbcTemplate, "table")` to assert DB state

#### Class Setup
```java
@Rollback
@Transactional
@ExtendWith(SpringExtension.class)
@ContextConfiguration(classes = TestConfiguration.class)
public class SomeDaoTest {
    @Autowired private SomeDao dao;
    @Autowired private DataSource dataSource;
    private JdbcTemplate jdbcTemplate;

    @BeforeEach
    public void setUp() {
        jdbcTemplate = new JdbcTemplate(dataSource);
    }
}
```

#### Test Structure (AAA)
Same three-step comment structure:
1. `// 1. Arrange` — declare input values as `final` constants using placeholder strings like `"[USERNAME]"` and `"[PASSWORD]"`; emails are the exception and must be lowercase real-looking values without brackets, e.g. `"new-user@example.com"`
2. `// 2. Exercise` — call the DAO method, store result in `final` variable
3. `// 3. Assert` — validate returned objects with `Assertions.*`; for persisted write state, use `JdbcTestUtils.countRowsInTableWhere(jdbcTemplate, TABLE_CONSTANT, "condition")`

#### Unit Boundaries

- A persistence test must call only the DAO method being tested in the `Exercise` section.
- Do **not** use another method of the same DAO in `Arrange` or `Assert`. For example, `testUpdateAvailability` must not call `findById`, `getAvailabilityFrom`, or `getAvailabilityTo` to verify the update.
- When a DAO write method (create **or** update) persists multiple columns, every test for that method must assert **all** persisted columns in `Assert`. Do not split part of the assertion into a separate test that exercises the same DAO method. For example, a `createBlock` test that sets `block_from`, `block_to` and `product_id` must include all three in the `JdbcTestUtils.countRowsInTableWhere` condition — omitting any column means the test passes even if that column was never written.
- For write-method tests, assert persisted state with `JdbcTestUtils.countRowsInTableWhere(...)`.
- Hibernate/JPA DAO tests that perform writes must call `em.flush()` after the DAO method and before any `JdbcTestUtils` assertion, so the assertion reads the real DB state instead of pending first-level-cache changes.
- When a write-method test persists explicit values declared in `Arrange`, the `Assert` condition must compare the stored columns to those exact values; do not weaken the check to `IS NOT NULL` unless the method intentionally generates an unpredictable value.
- When a DAO method returns a complete collection or map, declare the full expected collection/map in `Arrange` and compare it exactly in `Assert`. Do not assert only `size()` plus `contains(...)`, because that can miss unexpected extra or missing values.
- When a DAO method returns a `Page`, assert both the pagination metadata and the page `content`. If the order is deterministic, declare the expected ordered content IDs/values in `Arrange` and compare them exactly to `result.getContent()`.
- Page sizes used by persistence tests must be declared as class constants and set to `private static final int PAGE_SIZE = 2;` for pagination tests. Reuse that constant in Arrange, Exercise, and Assert instead of hardcoding numeric page-size literals.
- Do **not** use `jdbcTemplate.queryForObject("SELECT ...")` in the `Assert` section of persistence tests. A persistence write assertion should be phrased as "there is exactly one row matching this persisted state".
- Table names used in `JdbcTestUtils` calls must be class constants, e.g. `private static final String USERS_TABLE = "users";`, and reused instead of hardcoding the table string repeatedly.
- Persistence tests that build SQL conditions with string literals must use a local helper equivalent to `private String sqlString(final String value) { return "'" + value.replace("'", "''") + "'"; }`; do not concatenate raw quoted values like `"status = '" + status + "'"`.
- If a value is passed to the method under test in `Exercise`, declare it in `Arrange`. This includes negative lookup values such as non-existent IDs, emails, verification tokens, and reset tokens; do not inline them in the method call.
- For each `findBy...` method that has positive and negative tests, keep the `WhenExists` test first and the `WhenNotExists` test immediately below it.
- **Every** test (read **and** write) relies exclusively on the dataset in `persistence/src/test/resources/populator.sql`. Every required row, token, status, timestamp, relationship, and snapshot column for the scenario — including write-method preconditions — must already be prepared there.
- **Never insert or update in the `Arrange` section.** No `JdbcTemplate.update(...)`, `INSERT`s, or helper writes are allowed in `Arrange`, not even to seed a write-method precondition. If the scenario needs a record/column/state that does not exist yet, **add it to `populator.sql`** and reference it by id from the test — do not create it inside the test.
- The only write a persistence test performs is the call to the DAO method under test, in `Exercise`.
- When a new write-precondition fixture would change existing count/pagination assertions, make it invisible to those queries (e.g. a `DELETED` product, like the existing `Fixture ...` rows). To set an extra column without touching the shared `INSERT` column list, add a dedicated `UPDATE ... WHERE id = ...` right after the row in `populator.sql` (this is how the admin-invite / snapshot fixtures are seeded).

#### Pagination Tests

- To keep pagination tests simple and avoid inflating `populator.sql`, use `private static final int PAGE_SIZE = 2;` in pagination tests.
- Every paginated DAO method **clamps an out-of-range page to `[1, lastPage]` in a single query** (it
  already has the `COUNT`, so it fixes the offset before the ids query — see `ProductJpaDao.findByCriteria`
  as the canonical shape, and the `Pagination` helper in `models`). A page past the end therefore returns
  the **last page** with its content, never an empty ghost page, and the service never re-queries. The
  clamp lives in exactly one place per query: whoever owns the `totalCount`. For a single-method paginated
  DAO that is the DAO; a service only clamps when it is the one that computed the count for another reason
  (it does not, today — every paginated DAO clamps internally). See `docs/pagination-and-search.md`.
- For each paginated DAO method, cover these 8 scenarios:
  1. First page, no filters, no matches: returns empty content.
  2. First page, no filters, with matches: returns matching content.
  3. Second page, no filters, with matches and total matches greater than `PAGE_SIZE`: returns remaining content.
  4. Second page, no filters, with matches but total matches less than or equal to `PAGE_SIZE` (out of range): **clamps to the last page** and returns its content (not empty).
  5. First page, with filters, no matches: returns empty content.
  6. First page, with filters, with matches: returns matching content.
  7. Second page, with filters, with matches and total filtered matches greater than `PAGE_SIZE`: returns remaining filtered content.
  8. Second page, with filters, with matches but total filtered matches less than or equal to `PAGE_SIZE` (out of range): **clamps to the last page** and returns its content (not empty).
- In every pagination scenario, assert all pagination metadata (`pageNumber`, `pageSize`, `totalCount`) and exact ordered content IDs. For the clamp scenarios (4 and 8) the asserted `pageNumber` is the **clamped last page**, not the requested out-of-range page.

#### Read Operations (find, get, search, etc.)

- Tests for read-only methods **MUST NOT insert or update data manually**.
- These tests must rely exclusively on the dataset defined in `populator.sql`, which must already contain all required records and column values for the read scenario.

#### Populator Domain Fixtures

- Every product inserted in `persistence/src/test/resources/populator.sql` must have at least one default price row in the same file.
- A default price row has `price_from` before the current date and `price_to = NULL`. Prefer a stable old date such as `2020-01-01`.
- Do not add fixtures for impossible product states such as "product without price", "product with only special prices", or "product with only expired prices".
- If a DAO test needs a negative lookup with no price rows, use a non-existent product ID instead of creating an invalid product fixture.

##### Rationale

- Avoids data duplication across tests  
- Ensures consistency and predictability  
- Uses a known and controlled dataset  
- Leverages automatic reset via `@Transactional` + `@Rollback`  

##### Rules

- The `Arrange` section should be empty or limited to declaring inputs that reference existing data
- Do not use helpers like `insertUser()` or `insertActiveProductWithDefaults()` in read tests
- Do not use `JdbcTemplate.update(...)`, manual inserts, or any other table mutation in read tests
- All IDs must correspond to records defined in `populator.sql`
- Define constants in the test class that match those IDs

##### Incorrect Example

```java
@Test
public void testFindByProviderPaginatedWhenFirstPage() {
    // 1. Arrange — 13 active products; page 1 of size 12 should return 12
    final Long userId = insertUser();
    for (int i = 0; i < 13; i++) {
        insertActiveProductWithDefaults(userId);
    }

    // 2. Exercise
    final Page<Product> result = productDao.findByProvider(userId, 1, 12);

    // 3. Assert
    Assertions.assertEquals(13L, result.getTotalCount());
    Assertions.assertEquals(12, result.getContent().size());
    Assertions.assertEquals(1, result.getPageNumber());
    Assertions.assertEquals(12, result.getPageSize());
}
```

##### Correct Approach
Use a provider and products already defined in populator.sql
Ensure that dataset already covers pagination scenarios (e.g., > pageSize items)

```java
@Test
public void testFindByProviderPaginatedWhenFirstPage() {
    // 1. Arrange
    // No inserts — using data from populator.sql

    final long providerId = PROVIDER_ID_WITH_MANY_PRODUCTS;

    // 2. Exercise
    final Page<Product> result = productDao.findByProvider(providerId, 1, 12);

    // 3. Assert
    Assertions.assertEquals(EXPECTED_TOTAL_PRODUCTS, result.getTotalCount());
    Assertions.assertEquals(12, result.getContent().size());
    Assertions.assertEquals(1, result.getPageNumber());
    Assertions.assertEquals(12, result.getPageSize());
}
```


### Service Tests

- Located in `services/src/test/`
- Use **Mockito** (`mockito-core`, `mockito-junit-jupiter`) to mock DAO interfaces (no Spring context)
- `@InjectMocks` for the class under test
- `@Mock` for every dependency

```java
@ExtendWith(MockitoExtension.class)
public class SomeServiceTest {
    @Mock private SomeDao someDao;
    @InjectMocks private SomeServiceImpl someService;
    // ...
}
```

#### Test Structure (AAA)
Every test must follow this exact three-step comment structure:
1. `// 1. Arrange` — set up mocks with `Mockito.when(...).thenReturn(...)`
2. `// 2. Exercise` — call the method under test, store result in `final` variable
3. `// 3. Assert` — validate with `Assertions.*`

#### Rules
- **No `Mockito.verify`** — behavior is validated exclusively through `Assertions.*`
- All result variables must be `final`
- Use `Mockito.anyString()` / `Mockito.anyLong()` etc. for wildcard argument matching
- Mocks that should return a specific value use `thenReturn(value)`; mocks that should return empty use `thenReturn(Optional.empty())`

---

### Why no `Mockito.verify` / `Mockito.spy`

The cátedra has flagged this as **error conceptual grave** in multiple sprints. The reasoning:

- `verify(dao).create(args)` and `spy(...)` validate that a specific *method* was called with specific arguments. That is testing the **implementation**, not the **observable behavior**.
- If the implementation is refactored (e.g., the service starts caching, batches calls, or delegates to a helper), the test breaks even though the externally observable behavior is unchanged.
- The right alternative: assert the **return value** of the service method or the **persisted state** of the DB.

```java
// WRONG — validates implementation
Mockito.verify(mailService, Mockito.times(1)).sendWelcome(Mockito.any());

// RIGHT — validates observable behavior
final Optional<User> created = userService.register("john@example.com", "pass");
Assertions.assertTrue(created.isPresent());
Assertions.assertEquals("john@example.com", created.get().getEmail());
```

The narrow exception is when the method is **`void`** and the side effect is the only observable contract (e.g., a notification dispatcher whose only contract is to send a mail). Even then, the recommended fix is to refactor the method to return `boolean` (or richer info) so the test can assert the return value.

### What to test in services

The cátedra rule, repeated through Sprint 2:

> Test services **only when they have business logic**. If a service method is a passthrough to a DAO, do not write a service test — write the DAO test instead.

Apply to every service:
- Lots of validation, branching, mapping → test thoroughly with Mockito.
- Single-line `return dao.findById(id);` → no service test needed (the DAO test covers it).

### Required test coverage

> All flows that touch the database must have tests — happy paths AND unhappy paths.

For each service method that mutates state:
- One test for the happy path.
- One test per business rule that can reject the input (validation failure, wrong state, ownership violation, etc.).
- The unhappy paths assert the thrown exception with `Assertions.assertThrows(...)`.

### JUnit version

**JUnit 5 only.** The cátedra rejects JUnit 3 (`extends TestCase`) and JUnit 4 (`@RunWith`). The course slides reference JUnit 4 patterns; convert them to JUnit 5:

| JUnit 4 | JUnit 5 |
|---|---|
| `@RunWith(MockitoJUnitRunner.class)` | `@ExtendWith(MockitoExtension.class)` |
| `@RunWith(SpringJUnit4ClassRunner.class)` | `@ExtendWith(SpringExtension.class)` |
| `@Before` | `@BeforeEach` |
| `@After` | `@AfterEach` |
| `@BeforeClass` | `@BeforeAll` (must be `static`) |
| `org.junit.Assert.*` | `org.junit.jupiter.api.Assertions.*` |
| `org.junit.Test` | `org.junit.jupiter.api.Test` |
| `assertThat` from Hamcrest | `Assertions.*` (no Hamcrest dep) |

### `assertEquals` on domain objects requires `equals()`

If you do `Assertions.assertEquals(expectedUser, actualUser)` without overriding `equals()`/`hashCode()` on the domain class, you are comparing identity — the assertion always fails. Either override `equals` on the immutable model or assert field-by-field.

### Service test setup boilerplate

```java
@ExtendWith(MockitoExtension.class)
public class SomeServiceTest {
    @Mock private SomeDao someDao;
    @Mock private OtherService otherService;     // services depend on services, not DAOs of other domains

    @InjectMocks private SomeServiceImpl someService;
}
```

`@InjectMocks` creates the service and injects the mocks declared as `@Mock` in the test. Any constructor parameter that does not have a matching `@Mock` will be left null.

### Service tests do not load Spring context

No `@ContextConfiguration`, no `application.properties`, no `@Value` resolution. If a service depends on `@Value` configuration, set it manually in the test (`ReflectionTestUtils.setField(...)` or expose it via constructor).

### Strict stubs and `lenient()`

By default `MockitoExtension` runs in `STRICT_STUBS` mode — every `when(...).thenReturn(...)` must be used by the test, otherwise the test fails. If a stub is needed in some tests but not all (e.g., shared `@BeforeEach` setup), wrap it with `Mockito.lenient().when(...)`. Avoid lenient stubs as the default — they hide stale code.

### Don't mix Mockito and real Spring beans in service tests

If a test loads `@ContextConfiguration` and also uses `@Mock`/`@InjectMocks`, beans get resolved through Spring and Mockito injects nothing. Pick one strategy per test class.

---

### Persistence test — `populator.sql`

**Every** test — read **and** write — relies exclusively on the dataset defined in `persistence/src/test/resources/populator.sql`. The cátedra-graded rule: **no inserts or updates in the `Arrange` section**. If a scenario (a read fixture **or** a write-method precondition) needs a record/column/state that is not there yet, **add it to `populator.sql`** and reference it by id — do not seed it with `JdbcTemplate.update(...)` / `INSERT` inside the test.

To keep a new write-precondition fixture from changing existing count/pagination assertions, make it invisible to those queries (e.g. a `DELETED` product, like the existing `Fixture ...` rows). When you need an extra column on the fixture but don't want to touch the shared `INSERT` column list, set it with a dedicated `UPDATE ... WHERE id = ...` next to the row in `populator.sql` (the admin-invite stubs and the `status_before_review` snapshot fixture are seeded this way).

### `populator.sql` invariants

- Every `Product` row has at least one default `Price` row in the same file (`price_from` before today, `price_to = NULL`). Use a stable old date like `2020-01-01`.
- `CLOTHING` / `FOOTWEAR` products always have a non-null `size` matching the category.
- `EQUIPMENT` / `ACCESSORIES` products always have `size = NULL`.
- Do not create domain-impossible fixtures (product without price, helmet with size, etc.).

When you add a new column with a NOT NULL constraint to a table, update `populator.sql` so existing rows are still valid.

### Schema parity

Every Flyway migration that changes structure or constraints must also update `persistence/src/test/resources/schema.sql` so HSQLDB matches PostgreSQL after the migration runs. The two files are not the same syntax (HSQLDB uses `INTEGER GENERATED BY DEFAULT AS IDENTITY`, PostgreSQL uses `SERIAL`), but the resulting schemas must be functionally equivalent.

### Anti-patterns the cátedra has called out

- Persistence tests with no DB-state assertion (`dao.create(...)` followed by no `JdbcTestUtils` check). Test always passes — useless.
- Service tests with no mocks (DAO calls hit nothing → NPE in real code).
- Tests that insert preconditions through the DAO under test (couples the test to the method being tested).
- Persistence tests that use `jdbcTemplate.queryForObject("SELECT ...")` to verify the persisted state. Use `JdbcTestUtils.countRowsInTableWhere(...)` instead.
- Helper methods like `insertUser()` / `createActiveProduct()` used in read tests. Read tests must rely on `populator.sql`.
- Tests with multiple calls to the class under test in a single `@Test` (more than one Exercise step).
- Tests that share mutable state via class fields without `@BeforeEach` reset.
- Pagination tests that hardcode page sizes — use `private static final int PAGE_SIZE = 2;`.
- Tests asserting only `result.size()` + `result.contains(...)` — declare the full expected collection and compare exactly. The size+contains pair misses unexpected extras.

---

### Cátedra directives — testing checklist

Reglas explícitas de la cátedra. Casi todas tienen su sección detallada arriba; este bloque las junta para repaso rápido antes de entregar.

- **Hay que tener tests unitarios en services y DAOs.** Ambas capas: persistencia con `JdbcTestUtils` y servicios con Mockito sobre las interfaces de DAO.
- **Cobertura suficiente en los tests complejos.** Cuando un método tiene varias ramas (validaciones, ownership, transiciones de estado, errores), cubrir cada rama con un test. Happy path **y** unhappy paths. Ver "Required test coverage".
- **Si el service solo llama al DAO y nada más, NO se testea.** El test del DAO ya cubre el comportamiento. Solo se testean métodos de service que tienen lógica propia (validación, branching, mapeo, orquestación). Ver "What to test in services".
- **Tests unitarios, no de integración.** Cada test ejercita un único método público. No usar otro método del mismo DAO/service para preparar datos o assertar el resultado. Persistencia → `JdbcTestUtils` y populator. Servicios → Mockito sobre interfaces.
- **(IMPORTANTE) En persistencia, todo test que escribe DEBE validar que la BD efectivamente cambió.** Después de `dao.create(...)`, `dao.update(...)`, `dao.delete(...)` siempre va un `JdbcTestUtils.countRowsInTableWhere(jdbcTemplate, TABLE, "condicion exacta")`. Un test de write sin assertion contra la BD pasa siempre y no testea nada — la cátedra lo marca como **error grave**.
- **Ningún test sin asserts.** Si el `Exercise` no termina en uno o más `Assertions.*` (o `assertThrows`), el test es ruido. La cátedra lo marca explícitamente.
- **Nunca `Mockito.verify` ni `Mockito.spy`.** Testean implementación, no comportamiento — si el service refactorea (cachea, batchea, delega), el test rompe aunque el comportamiento observable no haya cambiado. Lo correcto es assertar el **valor de retorno** del método o el **estado persistido**.
- **Métodos `void` son los más difíciles de testear.** Antes de pelearse con `verify` para validar un `void`, preguntarse: **¿tiene sentido que sea `void`?**. Casi siempre conviene cambiar la firma a `boolean` (o devolver el objeto creado / un resultado más rico) para poder assertar el retorno. Esto pasa especialmente en services. Ver "Why no `Mockito.verify` / `Mockito.spy`".
