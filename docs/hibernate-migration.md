# Reglas de Migración: JDBC → JPA/Hibernate

> Este archivo contiene las reglas que Claude Code debe seguir para migrar la capa de persistencia de JDBC a JPA con Hibernate. Basado en las notas de clase de PAW (ITBA).

---

## 1. Anotación de Entidades (modelos)

### Reglas base:

- Toda clase que se persiste en BD debe tener `@Entity`.
- Si el nombre de la tabla difiere del nombre de la clase, usar `@Table(name = "nombre_tabla")`.
- Siempre agregar un **constructor sin argumentos** (puede ser `protected` o package-private). Hibernate lo necesita para instanciar por reflection.
- Los atributos ya **no deben ser `final`**.
- No es necesario agregar setters para que Hibernate funcione; setea los valores por reflection.

### ID y secuencias:

```java
@Id
@GeneratedValue(strategy = GenerationType.SEQUENCE, generator = "users_seq")
@SequenceGenerator(name = "users_seq", sequenceName = "users_id_seq")
private Long id;
```

> Los IDs siempre deben ser `Long` (no `long` primitivo, no `Integer`). Si una query nativa devuelve IDs como `Number` en lugar de `Long`, convertir con `.stream().map(Number::longValue)`.

### Mapeo de columnas:

```java
@Column(name = "nombre_columna", length = 255, nullable = false, unique = true)
private String email;
```

Equivalencias con el schema SQL:
- `VARCHAR(255)` → `length = 255`
- `NOT NULL` → `nullable = false`
- `UNIQUE` → `unique = true`
- `TEXT` → `@Column(columnDefinition = "TEXT")`
- Columna opcional → `nullable = true` (default)

> Si el nombre del atributo Java coincide exactamente con el nombre de la columna en BD, se puede omitir `@Column` y usar el default de Hibernate.

---

## 2. Relaciones entre entidades

### Regla general: reemplazar IDs por objetos

**JDBC (antes):**
```java
private Long authorId;
```

**JPA (después):**
```java
@ManyToOne(fetch = FetchType.LAZY)
@JoinColumn(name = "author_id")
private User author;
```

> En JPA el mundo es de objetos. Los IDs son un detalle de implementación de la BD.

### Tipos de relaciones:

**`@ManyToOne`** — lado "muchos" (la tabla que tiene la FK):
```java
@ManyToOne(fetch = FetchType.LAZY)
@JoinColumn(name = "author_id")
private User author;
```

El atributo `optional` indica si la relación puede ser nula:
- `optional = false` → la FK es requerida (NOT NULL); la entidad no puede existir sin esa relación.
- `optional = true` → la FK puede ser nula; la relación es débil o no siempre existe.

```java
@ManyToOne(fetch = FetchType.LAZY, optional = false)  // createdBy: siempre requerido
private User createdBy;

@ManyToOne(fetch = FetchType.LAZY, optional = true)   // assignedTo: puede no estar asignado
private User assignedTo;
```

**`@OneToMany`** — lado "uno" (la entidad que tiene la lista):
```java
@OneToMany(mappedBy = "author", fetch = FetchType.LAZY, orphanRemoval = false)
private List<Issue> reportedIssues = new ArrayList<>();
```

- `mappedBy` apunta al **nombre del atributo Java** en la entidad del otro lado (no el nombre de columna).
- `orphanRemoval = true` solo si la entidad es débil (no puede existir sin la relación).
- Inicializar listas como `new ArrayList<>()` para evitar `NullPointerException` y para coherencia con la BD (preferir lista vacía a `null`).

**`@ManyToMany`** — usar tabla intermedia con las FKs, no modelar la tabla join como entidad.

### Fetch: SIEMPRE LAZY por defecto

```java
fetch = FetchType.LAZY   // ← usar esto salvo excepción muy justificada
fetch = FetchType.EAGER  // ← PROHIBIDO como default; genera N+1 y trae todo el grafo
```

> EAGER en colecciones provoca joins que traen demasiada data. Si se necesita la colección, cargarla explícitamente en el DAO.

---

## 3. Implementación de los DAOs

### Reemplazar `JdbcTemplate` + `RowMapper` por `EntityManager`:

```java
@Repository
public class UserJpaDao implements UserDao {

    @PersistenceContext
    private EntityManager em;

    // ...
}
```

- **No declarar el DAO como singleton con estado compartido.** Spring gestiona el `EntityManager` automáticamente (proxy por thread). El `@PersistenceContext` inyecta el EM correcto para cada hilo.
- Eliminar todos los `RowMapper`. El mapeo lo hace JPA.

### Operaciones CRUD:

**Create:**
```java
// Instanciar SIN id (lo genera la secuencia)
User user = new User(username, email, password);
em.persist(user);
return user;  // después de persist, el objeto ya tiene id
```

**Find por id:**
```java
return Optional.ofNullable(em.find(User.class, id));
```

**Find con query (JQL):**
```java
return em.createQuery("FROM User u WHERE u.email = :email", User.class)
         .setParameter("email", email)
         .getResultList()
         .stream().findFirst();
```

**Update:**
> **Ver sección 7 sobre dirty checking.** En muchos casos el update es implícito. Si se necesita un `merge` explícito:
```java
em.merge(user);
```

### JQL — reglas de escritura:

- Escribir en términos del **modelo Java**, no de tablas/columnas SQL.
- `FROM User u WHERE u.email = :email` (no `FROM users WHERE email = ?`)
- Se puede navegar el árbol de objetos: `u.author.username = :name`
- Para columnas nullable: `WHERE u.assignee IS NULL`

### JPQL vs SQL nativo — cuándo usar cada uno

**Regla: JPQL por defecto. SQL nativo solo cuando JPQL no puede expresar la query.**

JPQL puede navegar relaciones `@ManyToOne` con punto — Hibernate genera el JOIN automáticamente. No hace falta SQL nativo para hacer JOINs entre entidades mapeadas:

```java
// MAL — SQL nativo innecesario para un JOIN que JPQL ya resuelve solo:
em.createNativeQuery(
    "SELECT COUNT(*) FROM rents r JOIN blocks b ON b.id = r.block_id " +
    "WHERE r.product_id = ? AND b.block_from <= ?");

// BIEN — JPQL navega r.block.blockFrom y genera el JOIN:
em.createQuery(
    "SELECT COUNT(r) FROM Rent r " +
    "WHERE r.product.id = :productId AND r.block.blockFrom <= :endDate",
    Long.class);
```

**SQL nativo es necesario solo cuando:**
- Se obtienen IDs paginados en el patrón 1+1 (necesita `LIMIT`/`OFFSET` a nivel SQL para no traer toda la tabla a memoria).
- Se usan funciones específicas de la BD que JPQL no expone (`ILIKE`, expresiones con `CURRENT_DATE`, etc.).
- La query opera sobre tablas sin `@Entity` mapeada.

**No usar SQL nativo para:**
- JOINs entre entidades que ya tienen `@ManyToOne` — JPQL los genera al navegar.
- Filtros con `WHERE`, `COUNT`, `IN`, `NOT IN`, `ORDER BY`.
- Cualquier query expresable en términos del modelo de objetos.

### Firmas del DAO — objetos, no IDs

Los métodos de escritura del DAO deben recibir objetos de dominio, no IDs, cuando la entidad tiene la relación mapeada como `@ManyToOne`:

```java
// MAL — firma de era JDBC:
Rent createRent(Long productId, Long blockId, Long renterId, BigDecimal total, Currency currency);

// BIEN — firma JPA:
Rent createRent(Product product, Block block, User renter, BigDecimal total, Currency currency);
```

Si el caller (service) solo dispone de IDs en ese punto, carga los objetos antes de llamar al DAO. Si el service ya recibió el objeto de una capa superior (ej. `User loggedUser` del `@ModelAttribute` del controller), lo pasa directamente — no extrae el ID para que el DAO lo vuelva a convertir en objeto.

---

## 4. Sesión y `@Transactional`

### El problema del lazy fuera de transacción:

Si se intenta acceder a una colección lazy **fuera de un contexto transaccional**, Hibernate lanza `LazyInitializationException` porque ya liberó la sesión de BD.

**Solución correcta:** un filtro que mantenga la sesión abierta durante todo el request. **Ya está configurado** en `web.xml`:

```xml
<filter>
    <filter-name>openEntityManagerInViewFilter</filter-name>
    <filter-class>org.springframework.orm.jpa.support.OpenEntityManagerInViewFilter</filter-class>
</filter>
<filter-mapping>
    <filter-name>openEntityManagerInViewFilter</filter-name>
    <url-pattern>/*</url-pattern>
</filter-mapping>
```

No agregar ni modificar este filtro.

> ⚠️ **No resolver esto haciendo logs o accediendo a las colecciones dentro de `@Transactional` como workaround** — eso equivale a hacer fetch EAGER y anula la ventaja del lazy.

### Regla: los métodos de Service deben tener `@Transactional`:

```java
@Transactional
public User getUserById(long id) { ... }

@Transactional(readOnly = true)  // para operaciones de solo lectura
public List<Issue> findAll() { ... }
```

---

## 5. Dirty Checking — PELIGRO

Hibernate rastrea los objetos obtenidos de la BD dentro de un contexto transaccional. Si un objeto se modifica, **al finalizar la transacción Hibernate emite un UPDATE automático**, sin que el DAO haya llamado a ningún método de persistencia.

### Regla crítica:

> **⚠️ NO MODIFICAR ENTIDADES JPA EN FORMA DIRECTA dentro de contextos de escritura (`@Transactional` sin `readOnly=true`)**

**MAL — genera UPDATE no deseado:**
```java
@Transactional
public void doSomething(long userId) {
    User user = userDao.findById(userId);
    user.setUsername("nuevoNombre");  // ← dirty checking → UPDATE automático al salir
}
```

**BIEN — usar el DAO explícitamente o trabajar en readOnly:**
```java
@Transactional(readOnly = true)
public User getUser(long userId) {
    return userDao.findById(userId);
}
```

### Comportamiento de dirty checking sobre colecciones:

Cuando Hibernate persiste cambios en el **orden** de una colección `@OneToMany`, **borra todas las filas de la tabla de relación y las reinserta en el nuevo orden**. Esto se debe a que usa el `ROWID` de inserción para preservar el orden.

Consecuencias:
- Ordenar una lista en memoria dentro de un `@Transactional` dispara un DELETE masivo + N INSERTs al salir.
- Es correcto funcionalmente, pero puede ser costoso en performance con listas grandes.
- Es otro motivo para ser muy consciente de qué se hace con entidades dentro de contextos de escritura.

### `em.getReference()` para poblar FK sin buscar el objeto:

Cuando se necesita una FK pero no el objeto completo:
```java
User author = em.getReference(User.class, authorId);
// No ejecuta SELECT; crea un proxy con el id
issue.setAuthor(author);
```

---

## 6. Paginación — Patrón 1+1 Queries (OBLIGATORIO)

> **Regla de la cátedra:** todo método DAO que devuelve una `Page<T>` con entidades Hibernate **debe** usar el patrón 1+1. No existen excepciones, incluso cuando la entidad solo tiene relaciones `@ManyToOne`. La consistencia es obligatoria.

### Por qué el `JOIN FETCH` directo con `LIMIT/OFFSET` es un error

Cuando se mezcla `JOIN FETCH` con `setFirstResult`/`setMaxResults` en una sola query JPQL, Hibernate **no puede trasladar el `LIMIT/OFFSET` a SQL** porque un `JOIN` puede producir más filas que entidades (una entidad con 3 hijos produce 3 filas). Para paginar correctamente, Hibernate:

1. Emite la query **sin `LIMIT`** — trae toda la tabla a memoria.
2. Pagina en Java aplicando `firstResult` y `maxResults` sobre la colección en heap.

En producción, con miles de filas, esto es catastrófico. Hibernate también emite la advertencia:

```
HHH90003004: firstResult/maxResults specified with collection fetch; applying in memory!
```

Aunque la entidad solo tenga relaciones `@ManyToOne` (que no multiplican filas), **el patrón 1+1 es obligatorio por consistencia** — si en el futuro se agrega una relación `@OneToMany`, el bug aparece en silencio.

### El patrón 1+1 — estructura canónica

```java
@Override
public Page<MyEntity> findByCriteria(final MyCriteria criteria) {
    // --- Query de conteo ---
    final Long total = em.createQuery(
            "SELECT COUNT(e) FROM MyEntity e WHERE ...", Long.class)
            .setParameter(...)
            .getSingleResult();

    if (total == null || total == 0L) {
        return new Page<>(Collections.emptyList(), pageNumber, pageSize, 0L);
    }

    // --- Query 1: IDs paginados (LIMIT/OFFSET a nivel SQL) ---
    final List<Long> ids = em.createQuery(
            "SELECT e.id FROM MyEntity e WHERE ... ORDER BY e.createdAt DESC, e.id DESC",
            Long.class)
            .setParameter(...)
            .setFirstResult((pageNumber - 1) * pageSize)
            .setMaxResults(pageSize)
            .getResultList();

    if (ids.isEmpty()) {
        return new Page<>(Collections.emptyList(), pageNumber, pageSize, total);
    }

    // --- Query 2: hidratación por IDs (JOIN FETCH; sin LIMIT) ---
    final List<MyEntity> content = em.createQuery(
            "SELECT e FROM MyEntity e " +
            "JOIN FETCH e.relation1 " +
            "JOIN FETCH e.relation2 " +
            "WHERE e.id IN :ids " +
            "ORDER BY e.createdAt DESC, e.id DESC",
            MyEntity.class)
            .setParameter("ids", ids)
            .getResultList();

    return new Page<>(content, pageNumber, pageSize, total);
}
```

### Reglas de aplicación

| Regla | Detalle |
|---|---|
| El `ORDER BY` se repite en ambas queries | La query de IDs define la ventana de página; la de hidratación restaura el orden en memoria. |
| La query de IDs usa `setFirstResult` / `setMaxResults` | La de hidratación **nunca** los usa — trabaja sobre un conjunto ya acotado. |
| Guard antes de la query de hidratación | Si `ids.isEmpty()`, devolver `Page` vacía sin ejecutar la segunda query. |
| Guard antes de la query de IDs | Si `total == 0`, devolver `Page` vacía sin ejecutar ninguna query de datos. |
| La segunda query puede usar `JOIN FETCH` libremente | Ahora opera sobre un `IN (:ids)` acotado; no hay riesgo de traer toda la tabla. |
| SQL nativo vs JPQL para la primera query | La query de IDs puede ser JPQL o SQL nativo. Usar SQL nativo solo si la query requiere funciones de BD específicas o CTEs; en los demás casos JPQL es preferible. |

### Cuándo usar JPQL vs SQL nativo en la query de IDs

**Usar JPQL** (más legible, tipado, portátil con HSQLDB en tests):
```java
// JPQL navega relaciones con punto — no necesita JOIN explícito
em.createQuery(
    "SELECT r.id FROM Rent r WHERE r.renter.id = :uid AND r.status IN :statuses ORDER BY r.id DESC",
    Long.class)
```

**Usar SQL nativo** cuando JPQL no puede expresar la query (CTEs, `ILIKE`, `generate_series`, funciones de ventana):
```java
em.createNativeQuery(
    "SELECT p.id FROM products p " +
    "JOIN prices pr ON pr.product_id = p.id AND pr.price_from <= CURRENT_DATE ..." +
    "ORDER BY p.id DESC")
// SQL nativo devuelve Number/Object — convertir con ((Number) id).longValue()
```

### Caso especial: `findProductIdsByUser` en FavoriteJpaDao

`findProductIdsByUser` devuelve directamente `Page<Long>` (IDs de productos, no entidades). No hay segunda query de hidratación — los IDs ya son el resultado final. Aun así usa `setFirstResult`/`setMaxResults` sobre la query nativa, lo que es correcto: no hay `JOIN FETCH` de por medio, por lo que Hibernate traduce el `LIMIT/OFFSET` a SQL directamente.

### Anti-patrón — lo que NUNCA debe aparecer

```java
// MAL: JOIN FETCH con setFirstResult/setMaxResults en la misma query
em.createQuery(
    "SELECT e FROM MyEntity e JOIN FETCH e.relation WHERE ...",
    MyEntity.class)
.setFirstResult(offset)   // ← Hibernate pagina en memoria; puede traer toda la tabla
.setMaxResults(pageSize)
.getResultList();
```

### Inventario de métodos que cumplen el patrón (estado actual)

| DAO | Método | Query 1 | Query 2 |
|---|---|---|---|
| `ProductJpaDao` | `findByProvider(Long, int, int)` | Native SQL | `findByIdsOrdered` JPQL |
| `ProductJpaDao` | `findByProvider(Long, List, List, String, int, int)` | JPQL | `findByIdsOrdered` JPQL |
| `ProductJpaDao` | `findByCriteria(AdminProductCriteria)` | Native SQL | `findByIdsOrdered` JPQL |
| `ProductJpaDao` | `findByCriteria(CatalogCriteria)` | Native SQL | `findByIdsOrdered` JPQL |
| `ProductJpaDao` | `findPagedRentTotalsByCriteria` | Native SQL + CTEs | Devuelve proyección, sin entidades |
| `RentJpaDao` | `getRentsAsRenter` | Native SQL | `fetchByIds` JPQL |
| `RentJpaDao` | `getRentsAsProvider` | Native SQL | `fetchByIds` JPQL |
| `RentJpaDao` | `findDashboardRentsAsRenter` | Native SQL | `fetchByIds` JPQL |
| `RentJpaDao` | `findDashboardRentsAsProvider` | Native SQL | `fetchByIds` JPQL |
| `ReviewJpaDao` | `findByProductId` | JPQL | JPQL + `hydrateImageIds` |
| `AdminActionJpaDao` | `findByCriteria` | JPQL | JPQL con `JOIN FETCH` |
| `FavoriteJpaDao` | `findProductIdsByUser` | Native SQL | — (devuelve `Page<Long>`) |
| `ReportJpaDao` | `findByCriteria` | JPQL | JPQL con `JOIN FETCH` |
| `ReportJpaDao` | `findByProductId` | JPQL | JPQL con `JOIN FETCH` |
| `ReportJpaDao` | `findAwaitingProviderResponseByProviderId` | JPQL | JPQL con `JOIN FETCH` |
| `ProductViewJpaDao` | `findByUser` | JPQL | JPQL con `JOIN FETCH` |
| `UserJpaDao` | `searchPaginated` | Native SQL | JPQL |

---

## 7. Testing cuando las firmas del DAO cambian de `Long id` a objeto de dominio

Cuando un método de escritura del DAO pasa de recibir `Long productId` a `Product product`, todos los tests que llaman a ese método deben adaptarse. El principio que guía la adaptación es el mismo de siempre: **el test debe ser unitario respecto al DAO o servicio bajo prueba**, sin acoplarse a la implementación de otro DAO.

### Tests de DAO (`XxxJpaDaoTest`)

Aplica a cualquier objeto de dominio que antes se pasaba como `Long` y ahora se pasa como entidad: `Product`, `User`, `Block`, etc.

**El problema:** el test necesita una instancia del objeto de dominio para pasarla al DAO, pero instanciarla llamando a `otherDao.findById(...)` acopla el test — si ese DAO falla, el test del DAO bajo prueba también falla sin ser su culpable.

**La solución: `em.getReference`**

```java
@PersistenceContext
private EntityManager em;

@Test
public void testCreateBlockReturnsBlock() {
    // 1. Arrange
    final Product product = em.getReference(Product.class, POPULATOR_PRODUCT_ID);
    // No ejecuta SELECT; crea un proxy con el id.
    // El ID debe existir en populator.sql (cualquier entidad: Product, User, etc.).
    final LocalDate blockFrom = LocalDate.of(2026, 7, 1);
    final LocalDate blockTo   = LocalDate.of(2026, 7, 7);

    // 2. Exercise
    final Block result = blockDao.createBlock(blockFrom, blockTo, product);

    // 3. Assert — verificar TODAS las columnas escritas por el método
    Assertions.assertNotNull(result);
    Assertions.assertEquals(1, JdbcTestUtils.countRowsInTableWhere(jdbcTemplate, "blocks",
            "id = " + result.getId()
                    + " AND product_id = " + POPULATOR_PRODUCT_ID
                    + " AND block_from = " + sqlDate(blockFrom)
                    + " AND block_to = " + sqlDate(blockTo)));
}
```

> `em.getReference` crea un proxy Hibernate con el ID sin emitir ningún `SELECT`. El test sigue siendo unitario respecto al DAO bajo prueba. Si el ID no existiera en la BD, la constraint de FK fallaría al hacer `persist`, que es exactamente el error que interesa detectar.

**Acceder al ID del proxy en assertions:** dentro de la misma transacción, `result.getXyz().getId()` es seguro — Hibernate devuelve el ID del proxy sin emitir un SELECT adicional (el ID vive en el proxy mismo, no en los campos lazy). **Fuera de la transacción, no acceder a propiedades del proxy lazy excepto el ID.**

**No usar esto para Arrange:**
```java
// MAL — acopla el test del DAO bajo prueba al funcionamiento de otro DAO
final Product product = productDao.findById(POPULATOR_PRODUCT_ID).orElseThrow();
final User user       = userDao.findById(POPULATOR_USER_ID).orElseThrow();
```

### Tests de servicio (`XxxServiceImplTest`)

En tests de servicio, los objetos de dominio que son **parámetros de entrada** (no dependencias del servicio) se mockean con Mockito cuando su construcción real requeriría setup de JPA o constructores complejos.

```java
@Test
public void testCreateBlockWhenValidThenReturnsCreatedBlock() {
    // 1. Arrange
    final LocalDate from = LocalDate.of(2026, 6, 1);
    final LocalDate to   = LocalDate.of(2026, 6, 7);
    final Product product = Mockito.mock(Product.class);
    Mockito.when(product.getId()).thenReturn(42L);  // solo si el servicio llama product.getId() (ej. en el LOGGER)

    final Block expected = new Block(100L, from, to, product);
    Mockito.when(blockDao.createBlock(from, to, product)).thenReturn(expected);

    // 2. Exercise
    final Block result = blockService.createBlock(from, to, product);

    // 3. Assert
    Assertions.assertEquals(100L, result.getId());
    Assertions.assertEquals(42L, result.getProduct().getId());
}
```

**Por qué funciona el argument matching:** el `product` mockeado es el mismo objeto que el test pasa a `blockService.createBlock(...)`, que a su vez lo pasa a `blockDao.createBlock(...)`. Mockito lo empareja por identidad de referencia — no por `equals()`.

**Cuándo stubbear `xyz.getId()`:** solo si el servicio llama a ese método. Con `LOGGER.info("... {}", obj.getId())`, los argumentos son expresiones Java evaluadas **antes** de que el cuerpo de `info()` se ejecute — la JVM arma el array de varargs con los resultados y recién entonces SLF4J decide si el nivel está habilitado. Por lo tanto `obj.getId()` siempre se llama, independientemente del nivel de log configurado en el test. La única excepción es la API fluida con lambdas (`LOGGER.atInfo().addKeyValue("x", obj::getId).log(...)`) donde la evaluación sí es lazy. Como consecuencia, si el LOGGER statement se elimina en una refactorización futura, el stub quedaría sin usar y `STRICT_STUBS` lanzaría `UnnecessaryStubbingException` — señal de que el stub debe quitarse también.

### Checklist adicional para tests en la migración de firmas

- [ ] En tests de DAO (write): inyectar `@PersistenceContext EntityManager em` y usar `em.getReference(Entity.class, id)` para construir la referencia al objeto sin SELECT.
- [ ] En tests de DAO (read/find): las assertions `result.getXyz().getId()` son seguras dentro de la transacción (proxy ID no requiere SELECT).
- [ ] En tests de servicio: usar `Mockito.mock(DomainClass.class)` para objetos de dominio que son parámetros de entrada (no colaboradores con lógica).
- [ ] **No llamar a `otherDao.findById(...)` en el Arrange de un test de DAO** — viola la independencia del test.

---

## 8. Enums

```java
@Enumerated(EnumType.STRING)  // guardar el nombre del enum, no el ordinal
private Priority priority;
```

- Usar `EnumType.STRING` (legible en BD, tolerante a reordenar el enum).
- **Nunca cambiar los nombres de los valores del enum** una vez que hay datos en producción.
- No usar `EnumType.ORDINAL` (frágil: agregar un valor en el medio rompe todo).

---

## 9. Checklist de migración por archivo

Para cada `XxxJdbcDao` existente:

- [ ] Crear `XxxJpaDao` que implementa la misma interfaz `XxxDao`
- [ ] **Quitar `@Repository` del `XxxJdbcDao` anterior** para que Spring no encuentre dos candidatos para el mismo bean
- [ ] Inyectar `EntityManager` con `@PersistenceContext`
- [ ] Eliminar `JdbcTemplate` y `RowMapper`
- [ ] Reescribir cada método usando `em.find`, `em.persist`, `em.createQuery` (JQL)
- [ ] Verificar que los nombres de columnas en `@Column` coincidan con el schema actual
- [ ] Reemplazar todos los atributos `Long xyzId` por referencias al objeto (`@ManyToOne`)
- [ ] Agregar constructor sin argumentos en todos los modelos
- [ ] Quitar `final` de los atributos de los modelos
- [ ] Revisar que toda paginación use el patrón 1+1 queries con SQL nativo
- [ ] Revisar que todos los fetch sean LAZY excepto excepciones
- [ ] Reemplazar todo SQL nativo que pueda expresarse en JPQL (JOINs, WHERE, COUNT, IN) — ver sección "JPQL vs SQL nativo"
- [ ] Verificar que los métodos de escritura del DAO reciben objetos de dominio, no IDs primitivos