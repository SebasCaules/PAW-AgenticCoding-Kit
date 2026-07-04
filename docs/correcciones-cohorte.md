## Correcciones de la cátedra — Grupo 10 y cohorte

Documento canónico de **todos los findings** que la cátedra ya señaló en TP1 y TP2 — los nuestros (Grupo 10) y los de los otros grupos. Usar como **checklist negativo** antes de cualquier entrega: si algo de acá sigue presente en el código, es nota perdida.

> **Reincidencia = penalización doble.** Cualquier finding que ya nos marcaron en TP1 y reaparezca en TP2 lleva el comentario `"Esto ya se marcó en la primer entrega"` y la cátedra baja nota más fuerte que la primera vez. Lo mismo aplica si un finding marcado en algún grupo del TP1 que mira nuestro corrector aparece en nuestro TP2.

---

## 1. Fuentes y notas

Documentos del wiki (`~/Desktop/ITBA/26-1C/PAW/PAW_Obsidian/wiki/sources/`) — leer ahí los transcripts completos.

| Fuente | Cobertura | Cuándo consultar |
|---|---|---|
| `devolucion-tp1-nuestra.md` | **Nuestra TP1 (Grupo 10) — nota 6** | Siempre. Es lo que ya nos descontaron. |
| `correcciones-segunda-entrega.md` | TP2, **dos correctores, 32 grupos** | Trampas nuevas del TP2 + reincidencia. |
| `devolucion-tp1-referencia-15-grupos.md` | TP1 referencia, 15 grupos | Patrones transversales castigados. |
| `devolucion-tp1.md` | TP1 cohorte (12 grupos) | Cruce con la devolución referencia. |
| `wiki/analyses/errores-comunes-tp1.md` | Guía accionable derivada | Síntesis legible. |

### Notas Grupo 10

| Entrega | Corrector A | Corrector B | Promedio |
|---|---|---|---|
| TP1 | 6 (n=10) | — | — |
| TP2 | 8 (prom. 7.5) | 6 (prom. 5.5) | — |

---

## 2. Nuestras correcciones — Grupo 10

### 2.1 TP1 — feedback oficial (nota 6)

#### Demo
- **Búsqueda con `LIKE` no escapa `%` ni `_`.** El usuario puede alterar el patrón. Ver `docs/pagination-and-search.md` (LIKE — escape).
- **Precio especial por fecha pisa el precio default.** Bug funcional.
- **Comprobante por PDF no se puede compartir.**
- **Sin CBU el comprobante no llega y la UI no avisa.**
- **Acciones terminales (eliminar, pausar) sin modal de confirmación.**
- **Search admin de users/productos sin CTA ni mensaje en estado vacío.**

#### Código — POM / dependencias
- **`commons-fileupload` con `<version>1.5</version>` hardcodeada en `webapp/pom.xml`.** Todas las versiones de terceros viven en `<dependencyManagement>` del POM padre. Hijos solo `<groupId>` + `<artifactId>`.
- **`javax.servlet-api` en `<dependencyManagement>` del padre sin `<scope>provided</scope>`.** El scope va una sola vez en el padre. El contenedor aporta el JAR; si se empaqueta al WAR, conflicto en runtime.

#### Código — Lógica de negocio en controllers (**error conceptual grave**)
Cuatro casos nominados explícitamente:

| Controller | Método | Por qué está mal | Dónde va |
|---|---|---|---|
| `DashboardController` | `computeReviewableRentIds` | "Rent reseñable = finalizada y no reviewed" es regla de dominio | `ReviewService` |
| `CatalogController` | `parseCategoryFilters` | Aplica `Category.usesSize()` y `Size.isValidForCategory(category)` para construir el `CatalogCriteria` — es lógica de búsqueda | `CatalogService` |
| `ImageController` | `detectContentType` | Inspección de magic bytes (PNG `89 50 4E 47`, JPEG, GIF, WebP) — procesamiento binario | Componente especializado o `ImageService` |
| `CatalogController` | `buildFilterQueryString` | Serializa query string con `StringBuilder` y `appendMulti`/`appendParam` **sin `URLEncoder.encode`** | Reemplazar por un único `<form method="get">` que englobe filtros + search + sort, o `<c:url><c:param/></c:url>` que ya hace encoding |

#### Código — Errores / mapeos
- **`ErrorController` mapea `/error/403`, `/error/404`, `/error/500` con `@RequestMapping(...)` sin declarar `method=`.** Siempre declarar el verbo: `@GetMapping`, `@PostMapping`, o `@RequestMapping(method = RequestMethod.GET)`.

#### Código — Seguridad
- **Ownership implementado manualmente dentro de los services en vez de centralizarse en la capa de seguridad.** La validación de ownership tiene que ser declarativa (Spring Security: `@PreAuthorize` con SpEL, o reglas en `WebAuthConfig`). El service puede mantener un chequeo defensivo, pero la primera barrera es la capa de seguridad.
  > **Tensión con `docs/security.md`** — actualmente el doc recomienda `findOwnedByX(resourceId, userId)` en service. La cátedra señaló que es violación de separación de responsabilidades. Pendiente reconciliar — mientras tanto, **al menos** que el service siga fallando si lo invocan sin ownership chequeado (defensa en profundidad).

#### Código — Persistencia
- **Ciclos llamando múltiples veces al DAO.** Potencial N+1. Resolver con `JOIN` o `WHERE id IN (...)`.
- **`ReviewJdbcDao`: `RowMapper<Review>` definido como lambda anónima inline en `findByProductId` y duplicado casi idéntico en `save`.** Extraer a `private static final RowMapper<Review> REVIEW_ROW_MAPPER = (rs, n) -> { ... };` y reusarlo. Patrón ya aplicado en otros DAOs del proyecto — la inconsistencia se castiga.
- **`ReviewJdbcDao.findByProductId` reconstruye una entidad `User` inline dentro de su `RowMapper`** con builder y un `JOIN users`, **duplicando lo que ya hace `UserJdbcDao`**. Si mañana cambia un campo de `User`, el mapper de `Review` queda desincronizado en silencio y no hay test que lo agarre. Compartir el `RowMapper` (exponer `USER_ROW_MAPPER` como `public static final` en `UserJdbcDao`) o equivalente.
- **No se escapan `%` ni `_` en search** (mismo bug que aparece en la demo).

#### Código — Tests (**graves problemas**)
- **Cuatro tests en `ProductServiceImplTest` usan `AtomicReference` dentro de `doAnswer` para capturar los args pasados al mock y luego assertarlos** (ej. `testCreateProductWhenValidReturnsProduct` captura las bytes). **Es reimplementar `Mockito.verify`.** Testea implementación, no comportamiento.
- **Tests del service que solo validan `Assertions.assertDoesNotThrow(...)` sin validar el comportamiento prometido por el nombre del test.**
- **`CurrencyTest.testFromSlugWhenAllValuesRoundtrip` ejecuta `Currency.fromSlug` tres veces (una por cada valor del enum) en un único `@Test`.** Si falla para alguno, JUnit reporta el método entero sin indicar qué valor falló y aborta el loop tapando otros fallos. Convertir a `@ParameterizedTest` con `@EnumSource(Currency.class)`.

#### Código — Otros
- **Los `aria-label` están hardcodeados en inglés.** Tienen que estar internacionalizados con `<spring:message code="..."/>`.

#### Resumen por categoría (nuestra devolución TP1)

| Categoría | Cantidad | Severidad |
|---|---|---|
| Lógica de negocio en controllers | 4 | Grave (conceptual) |
| Configuración POM / dependencias | 2 | Medio |
| Persistencia / N+1 / RowMappers | 4 | Grave |
| Tests no unitarios / testean implementación | 3 | Grave |
| Seguridad declarativa / ownership | 1 | Grave |
| HTTP / URL encoding / mapeos | 2 | Medio |
| UX / mensajes / i18n | 6 | Menor |
| Bugs funcionales | 4 | Medio |

### 2.2 TP2 — Grupo 10 (notas 8 / 6)

Nuestro código aún **no tiene devolución TP2 transcrita** en `devolucion-tp1-nuestra.md`. Las notas (Corrector A: 8 / promedio 7.5 — Corrector B: 6 / promedio 5.5) sugieren que el Corrector B encontró más problemas. Cuando esté la transcripción, sumarla acá.

Por ahora, lo más importante es que **todo lo señalado en TP1 (sección 2.1)** ya estuviera corregido. Si no lo está y aparece en TP2, doble penalización.

---

## 3. Correcciones de otros grupos — TP1

Patrones que la cátedra castigó sistemáticamente como **error grave** o **error conceptual grave** en múltiples grupos. Si está acá, conviene asumir que nuestro corrector lo va a buscar también.

### 3.1 Top 10 transversales

| # | Patrón | Grupos afectados (TP1) | Severidad | Ver |
|---|---|---|---|---|
| 1 | **Lógica de negocio en controllers** | 1, 2, 3, 4, 6, 8, 10 (nosotros), 11 | Conceptual grave | `docs/domain-and-layering.md` |
| 2 | **Validación de ownership manual en controllers** | 1, 3, 5, 8, 9, 10, 11 | Grave | `docs/security.md` |
| 3 | **XSS — `${var}` sin `<c:out>` en JSP** | 1, 4, 6, 7, 8, 10, 11 | Grave | `docs/views-and-jsp.md` |
| 4 | **Loguear a DEBUG/INFO en prod** | 5, 9, 11, 15 | Grave | `docs/logging.md` |
| 5 | **N+1 queries / JOINs en Java** | 2, 3, 6, 11 | Conceptual grave | `docs/guidelines.md` |
| 6 | **`Mockito.verify`/`spy` o tests no unitarios** | 4, 5, 6, 8, 9, 10 (nosotros con AtomicReference) | Conceptual grave | `docs/testing.md` |
| 7 | **`@Transactional` faltante o readOnly ausente** | 3, 10, 11 | Grave | `docs/architecture.md` |
| 8 | **Locale del sender en mails (no del destinatario)** | 1, 3, 5, 6, 12 | Grave | `docs/logging.md` (Async + ThreadLocal) |
| 9 | **Magic strings / magic numbers** | 1, 5, 9, 13, 14 | Grave | `docs/guidelines.md` |
| 10 | **Versiones de dependencias en poms hijos** | 1, 2, 3, 5, 7, 8, 10 (nosotros con `commons-fileupload`), 12 | Grave | `docs/setup.md` |

### 3.2 Otros findings notables (TP1)

- **`schema.sql` en `webapp/` en vez de `persistence/`** — grupos 1, 4, 9. Detalle del DAO.
- **`java.sql.*` fuera de `persistence`** — grupos 3, 5, 7, 8 (`DateTimeUtils` en `models/`).
- **`EmailService` (módulo `services`) referenciando templates en `webapp/WEB-INF/`** — grupo 8. Viola dirección de dependencias.
- **`spring-jdbc`/`spring-web` en módulos `interfaces`/`contracts`** — grupo 6. Las interfaces son agnósticas del contexto web.
- **`rememberMeKey` hardcodeada / débil** — grupos 4, 6, 8, 10, 11. Externalizar con `@Value("${app.security.rememberme.key}")`, valor robusto (32+ bytes aleatorios).
- **Stereotype incorrecto: `WebSecurity` como `@Service`** — grupo 8. Va `@Component`.
- **POST `/logout` manual** — grupo 11. Lo maneja Spring Security automáticamente.
- **`Optional.get()` sin verificar `isPresent()`** — grupos 3, 14.
- **`Optional` como campo / parámetro** — grupo 10. Solo como return value.
- **Auto-unboxing peligroso (boxed primitives donde `null` no significa)** — grupos 1, 2, 5, 10, 14.
- **Inconsistencia para "no existe" (`null` / `Optional.empty()` / `id = -1`)** — grupos 1, 9, 11.
- **Credenciales en el repo** — grupos 5, 9, 10.
- **`@PathVariable` sin nombre explícito** — grupo 7.
- **Listas mutables pasadas por referencia entre capas** — grupo 10. Violación de OOP/SOLID.
- **Falta `<c:url>` en links / recursos estáticos** — grupos 10, 11.
- **Validator acoplado a un form específico (`PasswordMatcher` con `instanceof RegisterForm`)** — grupo 14. Usar interfaz `PasswordsMatching` con `getPassword()`/`getConfirmPassword()` y trabajar contra la interfaz.
- **Tests sin paths de error (`assertThrows` ausente)** — grupos 1, 6.
- **Spring Security: orden de matchers incorrecto** — grupo 1. `anyRequest().authenticated()` antes que rutas más restrictivas → first match wins → las rutas restrictivas quedan apenas autenticadas.
- **`CharacterEncodingFilter` configurado por bean Y en `web.xml`** — grupo 13. Duplicación.
- **`EmailService` con `@Async` + `@Transactional` sin tocar BD** — grupo 13. Si solo hace SMTP, `@Transactional` no aporta nada.
- **`schema.sql` vacío** — grupo 14.
- **Pluralización con keys separadas singular/plural** — grupo 12. Usar ICU MessageFormat: `key=Tengo {0} {0, plural, one{resultado}other{resultados}}`.
- **Endpoints de modificación con `@RequestParam` cuando el id es identidad** — grupo 14. Va en path.
- **No validar `@RequestParam` (`page=-1` → 500)** — grupos 5, 9. Clampear.
- **Loguear a archivos genéricos (`catalina.out`, `localhost.log`)** — grupo 7. `FileAppender` propio del proyecto.
- **Tests con `extends TestCase` (JUnit 3)** — grupo 2. JUnit 5 obligatorio.
- **Mezcla inglés/español en identificadores** — grupo 4 (`buscarConFiltrosExtendidos` + `findByEmail`).
- **`snake_case` o `PascalCase` en métodos / paquetes con mayúscula** — grupos 4, 15.

---

## 4. Correcciones de otros grupos — TP2

> Los dos correctores del TP2 ponen foco en cosas distintas:
> - **Corrector A** — `Segunda Entrega - Devolución.pdf`, 17 grupos. Más amplio: i18n, paginación, controllers, tests, modelo 1+1, schema.
> - **Corrector B** — `fee3e87d-...Devolucin_TP2.pdf`, 15 grupos. Foco fuerte en: **`@Async` + lazy**, **EAGER cascada con 200+ queries**, **`Mockito.verify`**, **modelo 1+1**.

### 4.1 🆕 Trampas nuevas del TP2

No existían en TP1 — la cátedra las introduce con la migración a Hibernate. Alta prioridad para nosotros porque migramos varios DAOs.

#### 1. `@Async` accediendo a relaciones lazy sin materializar — **error conceptual grave**

> Grupos 2, 3, 5 del corrector B.

Un método `@Async` corre en otro thread; la sesión Hibernate del request original ya no está. Acceder a una relación lazy (`booking.getUser().getName()`) tira `LazyInitializationException` o trae datos parciales en silencio.

**Fix A — materializar antes de pasar al async:**
```java
bookings.forEach(booking -> {
    booking.getUser().getId(); // fuerza la inicialización dentro de la sesión activa
    messageSender.sendBookingCancellationMessage(booking.getUser(), booking);
});
```

**Fix B — `JOIN FETCH` en la query del DAO** que alimenta el método async.

#### 2. Paginación con relaciones sin modelo 1+1 — **error conceptual grave**

> Grupos 3, 5, 13, 17 (corrector A) y 3, 4, 10, 17 (corrector B).

Para listas paginadas con `@ManyToOne` o `@OneToMany`:
1. **Query 1:** native query de IDs paginados (`SELECT id FROM ... LIMIT n OFFSET m`).
2. **Query 2:** JPQL con `JOIN FETCH` filtrada por `id IN (:ids) ORDER BY ...`.

Sin esto, Hibernate puede traer la tabla entera a memoria y paginar in-process. Con `EAGER` colateral, la situación empeora exponencialmente.

#### 3. `FetchType.EAGER` en cascada — **error conceptual grave**

> Grupos 1, 3, 4, 10, 11, 14, 16 (corrector A) y 4, 11, 14 (corrector B).

Caso real grupo 11 corrector B: 10 imágenes EAGER × 20 ofertas EAGER × ... = **~200 queries para paginar una lista**.

**Regla:** default `LAZY` en cualquier `@ManyToOne` o `@OneToMany`. `EAGER` solo justificado, comentado, y validado que no dispare cascada.

#### 4. Foreign keys mapeadas con `Long xId` pelado

> Grupo 3 corrector A, grupo 6 corrector B.

Mapear con `@ManyToOne Product product`, no con `Long productId`. Sin FK explícita Hibernate no genera JOINs, la BD pierde integridad referencial, y JPQL no puede navegar la relación.

#### 5. `.size()` sobre colección lazy materializa toda la colección

> Grupo 12 corrector A, grupo 14 corrector B.

Si solo necesitás contar, `COUNT(*)` en query separada. Si es derivado, `@Formula("(SELECT COUNT(*) FROM ...)")`. Especialmente grave si la colección puede crecer (comentarios, likes, imágenes).

#### 6. Contador modificado por varios DAOs en lugar de `@Formula`

> Grupo 7 corrector B (likes/comentarios), grupo 13 corrector B (tags).

Si la entidad tiene un campo "cantidad de X" que dos DAOs incrementan/decrementan, eliminar el campo y reemplazar por `@Formula`. Quita la consistencia manual entre DAOs.

#### 7. Errores de precedencia `OR`/`AND` sin paréntesis en SQL/HQL — **error grave**

> Grupo 5 corrector B.

Caso real: `WHERE v.publicationStatus = 'ACTIVE' AND v.stock > 0 AND v.genre = :g OR v.sellerId = :sellerId` evalúa como `(... AND ... AND ...) OR (...)` — trae cualquier vinilo del seller, ignorando `active` y `stock`. **Paréntesis explícitos siempre.**

#### 8. Tests de Hibernate sin `em.flush()` antes del assert

> Grupo 5 corrector B.

Sin `flush()`, las modificaciones quedan en el first-level cache; `JdbcTestUtils.countRowsInTableWhere(...)` lee la BD subyacente y el assert pasa con BD vacía. Llamar `em.flush()` antes del assert.

#### 9. Cron job sin flag idempotente

> Grupo 2 corrector B.

Caso real: `remindUpcomingBookingsCronJob` con loop infinito mandó infinitos mails al mismo usuario. Marcar el flag (`reminderSent`) en la misma transacción que el envío, filtrar por él en la próxima ejecución.

#### 10. `hsqldb` con scope `compile` en `webapp/pom.xml` — **error conceptual**

> Grupos 3, 4 corrector B.

Siempre `<scope>test</scope>`. Si llega al WAR, la app levanta dependencias de testing en producción.

#### 11. `@PreAuthorize` en services (reincidente desde TP1)

> Grupo 11 corrector B.

La autorización vive en la capa web (`@PreAuthorize` en controllers, o reglas en `WebAuthConfig`). Si está en services, atravesar capas se vuelve confuso y la lógica se duplica.

#### 12. Mensajes hardcodeados en `GlobalExceptionHandler`

> Grupos 7, 10 corrector B.

También requieren `<spring:message>` resuelto via `MessageSource`.

#### 13. `lang="es"` hardcodeado en `<html>`

> Grupo 7 corrector B.

Tiene que respetar el locale activo (`lang="${pageContext.response.locale}"` o equivalente).

### 4.2 Reincidencias TP1 → TP2 (penalización **doble**)

> Grupos a los que la cátedra escribió textualmente: `"Esto ya se marcó en la primer entrega"`.

| Patrón | Grupos que reincidieron en TP2 |
|---|---|
| `schema.sql` en webapp | A1, A4 |
| Lógica de negocio en controllers | A1, A3, A4, A7, A10, A11, A14, A15; B5, B6, B7, B11 |
| XSS sin `<c:out>` | A4, A14, A15; B9 |
| `java.sql.*` en modelos | A3, A7, A8, A10 |
| Boxed primitives sin razón | A4, A6, A7 |
| Locale del sender en mails | A4 |
| Tests no unitarios / `Mockito.verify` | A1, A3, A8, A17; B4, B7, B12, B13 |
| `Optional.get()` sin verificar | A3, A14; B3 |
| `Optional`/`null`/`id = -1` mezclados | A11 |
| `@PreAuthorize` en services | B11 |
| `spring-web` en módulo de interfaces | B6 |
| Validación de ownership manual | A1, A6, A10, A15; B3, B12 |

### 4.3 Top patrones recurrentes TP2 (consolidado)

| # | Patrón | Aparece en |
|---|---|---|
| 1 | **Paginación sin modelo 1+1** | A: 3, 5, 13, 17 · B: 3, 4, 10, 17 |
| 2 | **Lógica de negocio en controllers** | A: 1, 3, 4, 7, 10, 11, 14, 15 · B: 5, 6, 7, 11 |
| 3 | **Tests no unitarios / `Mockito.verify`** | A: 1, 3, 8, 17 · B: 4, 7, 12, 13 |
| 4 | **XSS sin `<c:out>`** | A: 4, 14, 15 · B: 9 |
| 5 | **`java.sql.*` en modelos** | A: 3, 7, 8, 10 |
| 6 | **EAGER en cascada (100-200+ queries)** | A: 1, 3, 4, 10, 11, 14, 16 · B: 4, 11, 14 |
| 7 | **🆕 `@Async` + relaciones lazy sin materializar** | B: 2, 3, 5 |
| 8 | **`Optional.get()` sin verificar** | A: 3, 14 · B: 3 |
| 9 | **Boxed primitives innecesarios** | A: 4, 6, 7 |
| 10 | **`schema.sql` en webapp** | A: 1, 4 |
| 11 | **Magic strings para roles, no `<sec:authorize>`** | A: 1, 6, 10, 15 · B: 3, 12 |
| 12 | **`hsqldb` con scope `compile`** | B: 3, 4 |
| 13 | **i18n incompleta** | B: 4, 7, 10 |
| 14 | **`@PreAuthorize` en services** | B: 11 |
| 15 | **`@Transactional` faltante en writes** | B: 10, 11 |
| 16 | **Precedencia SQL/HQL sin paréntesis** | B: 5 |
| 17 | **Cron jobs sin idempotencia** | B: 2 |
| 18 | **Tags/categorías con contador en BD vs `@Formula`** | B: 13 |
| 19 | **Locale del sender en mails (reincidente)** | A: 4 |

---

## 5. Checklist negativo pre-entrega

Pre-entrega: pasar por este checklist. Si algo está marcado como ❌, no se entrega.

### Lo nuestro TP1 — NO puede reaparecer
- [ ] `DashboardController.computeReviewableRentIds` migrado a `ReviewService`.
- [ ] `CatalogController.parseCategoryFilters` migrado a `CatalogService`.
- [ ] `ImageController.detectContentType` movido a `ImageService` o componente especializado.
- [ ] `CatalogController.buildFilterQueryString` reemplazado por `<form method="get">` o `<c:url><c:param/></c:url>`.
- [ ] `ErrorController` declara `method=` en cada `@RequestMapping`.
- [ ] `ReviewJdbcDao` usa `private static final RowMapper<Review> REVIEW_ROW_MAPPER`.
- [ ] Ningún `RowMapper` reconstruye una entidad de otro dominio inline.
- [ ] `ProductServiceImplTest` no captura args con `AtomicReference` + `doAnswer`.
- [ ] Ningún test tiene solo `assertDoesNotThrow` como contrato.
- [ ] `CurrencyTest` migrado a `@ParameterizedTest` + `@EnumSource(Currency.class)`.
- [ ] Search en `LIKE` escapa `%` y `_`.
- [ ] `commons-fileupload` sin `<version>` en `webapp/pom.xml`.
- [ ] `javax.servlet-api` con `<scope>provided</scope>` en el padre.
- [ ] `aria-label`/`alt`/`title` con `<spring:message>`.
- [ ] Ownership: al menos defensa en profundidad en service + intentar mover a Spring Security declarativo.

### TP2 — trampas nuevas
- [ ] Ningún `@Async` accede a relaciones lazy sin materializar.
- [ ] Toda paginación con relaciones usa modelo 1+1.
- [ ] `@ManyToOne`/`@OneToMany` default `LAZY`; cada `EAGER` justificado y comentado.
- [ ] Relaciones mapeadas con entidad, no con `Long xId` pelado.
- [ ] No hay `.size()` sobre colección lazy — usar `COUNT` o `@Formula`.
- [ ] Contadores derivados con `@Formula`, no campo modificado por varios DAOs.
- [ ] Queries con `OR`/`AND` tienen paréntesis explícitos.
- [ ] Tests de Hibernate hacen `em.flush()` antes del assert.
- [ ] Cron jobs marcan flag idempotente en la misma transacción.
- [ ] `hsqldb` con scope `test` en `webapp/pom.xml`.
- [ ] `@PreAuthorize` solo en controllers (cero en services).
- [ ] Mensajes en `GlobalExceptionHandler` van por `MessageSource`.
- [ ] `lang` en `<html>` toma del locale activo, no hardcodeado.

### Generales TP1 — comunes a toda la cohorte
- [ ] Cero lógica de negocio en controllers.
- [ ] Cero `Mockito.verify` / `spy` / `AtomicReference + doAnswer`.
- [ ] Cero XSS — todo `${var}` con datos de usuario / BD envuelto en `<c:out>`.
- [ ] N+1: ningún loop con `findById`; JOINs en SQL o `WHERE id IN (...)`.
- [ ] `java.sql.*` solo en `persistence`.
- [ ] `@Transactional(readOnly = true)` en todos los reads de service.
- [ ] `@Transactional` en todos los writes.
- [ ] Locale del mail = destinatario (`recipient.getPreferredLanguage()`), no `LocaleContextHolder`.
- [ ] Magic strings/numbers → enums o `private static final`.
- [ ] Versiones de dependencias **solo** en pom padre.
- [ ] Cero credenciales en el repo.
- [ ] `rememberMeKey` externa vía `@Value`, ≥32 bytes aleatorios.
- [ ] `WebSecurity` y similares con `@Component`, no `@Service`.
- [ ] `Optional` solo como return; nunca `.get()` sin verificar.
- [ ] Una sola convención para "no existe" (sin mezclar `null` / `Optional` / `id = -1`).
- [ ] Boxed primitives solo cuando `null` significa.
- [ ] `@PathVariable("name")` y `@RequestParam("name")` con nombre explícito.
- [ ] Logback prod en `WARN` root / `INFO` `ar.edu.itba.*`, `DEBUG` solo en `logback-test.xml`.
- [ ] `RollingFileAppender` con `maxHistory`, archivos con prefijo `paw-2026a-10.*.log`.
- [ ] Cero `System.out.println` / `e.printStackTrace()`.
- [ ] Cero `spring-boot-*`.
- [ ] Sin `bin/`, `out/`, `*.iml`, `.vscode/`, `target/` commiteados.
- [ ] Sin tests comentados.
- [ ] Validators desacoplados del form específico (interfaz, no `instanceof`).
- [ ] Spring Security: orden de matchers — públicos primero, `anyRequest()` al final.
- [ ] Sin `CharacterEncodingFilter` duplicado (bean Y `web.xml`).
- [ ] Sin `EmailService` con `@Transactional` (si no toca BD).
- [ ] Sin endpoint `POST /logout` manual.
- [ ] Tests cubren happy y unhappy paths (`assertThrows`).

---

## 6. Cómo usar este documento

- **Antes de empezar una feature:** mirar las secciones 3 y 4 — si el área que vas a tocar tiene un patrón listado, evitarlo de entrada.
- **Antes de cerrar un PR:** pasar `/good-practice` (skill `/gp`); el skill consume este doc + los `docs/*.md` ya importados y devuelve un reporte categorizado.
- **Pre-entrega:** correr el checklist completo (sección 5). Cualquier ❌ es nota perdida.
- **Cuando aparece una devolución nueva (TP2 / TP3):** actualizar este doc primero — agregar la sección de "Nuestras correcciones" correspondiente y ampliar el checklist con los items específicos. El `/good-practice` skill ya apunta acá.
