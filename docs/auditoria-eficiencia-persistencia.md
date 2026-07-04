# Auditoria de eficiencia de la capa de persistencia

Fecha: 2026-06-09

## Resumen ejecutivo

La capa de persistencia esta bastante mejor que una implementacion JPA ingenua: usa asociaciones `LAZY`, evita traer BLOBs para listados, aplica paginacion 1+1 en catalogo/rentas/reportes, usa `JOIN FETCH` solo para relaciones necesarias y ya tiene algunos indices de FK agregados en `V44__add_fk_indexes.sql`.

Las mejoras mas relevantes no pasan por reescribir toda la capa, sino por ajustar consultas calientes e indices compuestos. Los puntos con mayor retorno son:

1. Agregar indices compuestos alineados con `WHERE + ORDER BY` de rentas, catalogo, reportes, precios y bloques.
2. Cambiar algunos `COUNT(*) > 0` por consultas tipo `EXISTS`/`SELECT 1 LIMIT 1`.
3. Mover agregaciones de estadisticas que hoy traen filas a memoria hacia SQL.
4. Revisar el costo del ordenamiento/filtro por rating en catalogo, porque usa subqueries correlacionadas por producto.
5. Reducir duplicacion entre query de `COUNT` y query de IDs para evitar drift y facilitar optimizaciones futuras.

## Hallazgos y fixes sugeridos

### A1 - Falta de indices compuestos para las consultas mas frecuentes

**Impacto:** Alto. Con mas datos, los indices simples existentes ayudan, pero varias consultas filtran por varias columnas y ordenan por otra. PostgreSQL puede terminar combinando indices o haciendo scans/sorts evitables.

**Evidencia:**

- `ProductJpaDao.findByProvider(...)` filtra por `provider_id`, `status`, opcionalmente `category`, y ordena por `id ASC` (`persistence/src/main/java/ar/edu/itba/paw/persistence/ProductJpaDao.java:181-208`).
- `RentJpaDao.getRentsAsRenter(...)` filtra por `renter_id`, `status` y ordena `id DESC` (`persistence/src/main/java/ar/edu/itba/paw/persistence/RentJpaDao.java:197-215`).
- `RentJpaDao.getRentsAsProvider(...)` filtra por `products.provider_id`, `rents.status` y ordena `r.id DESC` (`persistence/src/main/java/ar/edu/itba/paw/persistence/RentJpaDao.java:232-253`).
- Catalogo filtra `products.status`, `location_id`, `category`, `gender`, `condition`, `title`, disponibilidad via `blocks`, y siempre junta con precio efectivo (`persistence/src/main/java/ar/edu/itba/paw/persistence/ProductJpaDao.java:614-655`).
- Los indices actuales de FK son simples: `rents(product_id)`, `reviews(rent_id)`, `products(provider_id)`, `prices(product_id)` (`persistence/src/main/resources/db/migration/V44__add_fk_indexes.sql:11-14`).

**Fix sugerido:**

Crear una migracion nueva con indices compuestos, midiendo con `EXPLAIN ANALYZE` en PostgreSQL antes/despues:

```sql
CREATE INDEX IF NOT EXISTS idx_products_provider_status_id
    ON products (provider_id, status, id);

CREATE INDEX IF NOT EXISTS idx_products_catalog_status_location_category_id
    ON products (status, location_id, category, id);

CREATE INDEX IF NOT EXISTS idx_rents_renter_status_id_desc
    ON rents (renter_id, status, id DESC);

CREATE INDEX IF NOT EXISTS idx_rents_product_status_id_desc
    ON rents (product_id, status, id DESC);

CREATE INDEX IF NOT EXISTS idx_blocks_product_range
    ON blocks (product_id, block_from, block_to);

CREATE INDEX IF NOT EXISTS idx_prices_product_effective
    ON prices (product_id, price_from, price_to, inserted_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_reports_product_created_id_desc
    ON reports (product_id, created_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_reports_status_created_id_desc
    ON reports (status, created_at DESC, id DESC);
```

Para el dashboard de proveedor de rentas, evaluar tambien:

```sql
CREATE INDEX IF NOT EXISTS idx_products_provider_id_id
    ON products (provider_id, id);
```

### A2 - `COUNT(*)` usado como existencia en conflicto de rentas

**Impacto:** Medio/Alto. En `hasConflictingRent`, la consulta cuenta todos los conflictos cuando solo necesita saber si existe uno. En productos con historial grande, esto hace trabajo innecesario justo en el flujo critico de reserva.

**Evidencia:** `RentJpaDao.hasConflictingRent(...)` usa `SELECT COUNT(r)` y compara `> 0` (`persistence/src/main/java/ar/edu/itba/paw/persistence/RentJpaDao.java:57-69`).

**Fix sugerido:**

Cambiar a `SELECT 1` con `setMaxResults(1)`:

```java
return !em.createQuery(
        "SELECT 1 FROM Rent r " +
        "WHERE r.product.id = :productId " +
        "AND r.status NOT IN :excluded " +
        "AND r.block.blockFrom <= :endDate " +
        "AND r.block.blockTo >= :startDate",
        Integer.class)
        .setParameter("productId", productId)
        .setParameter("excluded", List.of(RentStatus.CANCELLED, RentStatus.PAYMENT_CANCELLED))
        .setParameter("endDate", endDate)
        .setParameter("startDate", startDate)
        .setMaxResults(1)
        .getResultList()
        .isEmpty();
```

Complementarlo con `idx_rents_product_status_id_desc` e `idx_blocks_product_range`.

### A3 - Estadisticas de rentas agregan en memoria

**Impacto:** Medio. Las estadisticas por producto pueden degradar cuando un producto acumula muchas rentas finalizadas.

**Evidencia:**

- `sumRevenueByProductPerMonth(...)` trae `blockTo,totalPrice` y agrupa por mes en Java (`persistence/src/main/java/ar/edu/itba/paw/persistence/RentJpaDao.java:440-454`).
- `findMonthsWithCompletedRents(...)` trae todas las fechas y deduplica en Java (`persistence/src/main/java/ar/edu/itba/paw/persistence/RentJpaDao.java:458-468`).
- `countRepeatRenters(...)` trae todos los renters repetidos y usa `.size()` (`persistence/src/main/java/ar/edu/itba/paw/persistence/RentJpaDao.java:522-531`).

**Fix sugerido:**

Mover las agregaciones a SQL nativo PostgreSQL en produccion:

```sql
SELECT date_trunc('month', b.block_to) AS month, SUM(r.total_price)
FROM rents r
JOIN blocks b ON b.id = r.block_id
WHERE r.product_id = :pid
  AND r.status IN (:statuses)
  AND b.block_to >= :since
GROUP BY date_trunc('month', b.block_to)
ORDER BY month;
```

```sql
SELECT COUNT(*)
FROM (
  SELECT r.renter_id
  FROM rents r
  WHERE r.product_id = :pid
    AND r.status IN (:statuses)
  GROUP BY r.renter_id
  HAVING COUNT(*) >= 2
) repeated;
```

Si se mantiene compatibilidad HSQLDB para tests, dejar fallback JPQL o cubrir estas queries con tests de integracion PostgreSQL.

### A4 - Ordenamiento y filtro por rating en catalogo usa subquery correlacionada

**Impacto:** Medio/Alto segun volumen. El catalogo ordena o filtra por rating con una subquery que calcula `AVG` por producto. Esto puede ser caro porque se evalua contra muchos candidatos antes de paginar.

**Evidencia:** `AVG_RATING_SUBQUERY` se usa en `ORDER BY` para `RATING` y en `WHERE` para `minRating` (`persistence/src/main/java/ar/edu/itba/paw/persistence/ProductJpaDao.java:600-605` y `persistence/src/main/java/ar/edu/itba/paw/persistence/ProductJpaDao.java:652-654`). Para hidratar cards, el servicio ya usa batch aggregation (`ReviewJpaDao.findRatingSummariesByProductIds`, `persistence/src/main/java/ar/edu/itba/paw/persistence/ReviewJpaDao.java:137-164`).

**Fix sugerido:**

Crear una vista materializada o tabla de resumen `product_rating_summary(product_id, avg_rating, review_count)` mantenida al crear review/respuesta, o una vista normal si el volumen todavia es bajo. Luego el catalogo puede hacer:

```sql
LEFT JOIN product_rating_summary rs ON rs.product_id = p.id
...
ORDER BY COALESCE(rs.avg_rating, 0) DESC, p.id ASC
```

Esto evita recalcular ratings por cada busqueda y permite indexar `avg_rating` si el ordenamiento por rating se vuelve frecuente.

### A5 - Precio efectivo usa subquery por producto; conviene indexar y considerar normalizacion

**Impacto:** Medio. `EFFECTIVE_PRICE_JOIN` resuelve la fila vigente con una subquery correlacionada por producto. Es correcto y evita overcount, pero depende mucho de un buen indice.

**Evidencia:** `EFFECTIVE_PRICE_JOIN` selecciona `prices` por `product_id`, rango de fecha y orden de precedencia (`persistence/src/main/java/ar/edu/itba/paw/persistence/ProductJpaDao.java:40-44`). Se usa tanto para `COUNT` como para IDs del catalogo (`persistence/src/main/java/ar/edu/itba/paw/persistence/ProductJpaDao.java:421-436`) y en ordenamiento por total (`persistence/src/main/java/ar/edu/itba/paw/persistence/ProductJpaDao.java:512-536`).

**Fix sugerido:**

Minimo: agregar `idx_prices_product_effective`.

Mejora mayor: mantener una columna/tabla auxiliar de precio vigente por producto para el catalogo sin rango de fechas. Para rangos arbitrarios, la CTE con `generate_series` sigue siendo razonable, pero deberia medirse con rangos largos.

### A6 - `COUNT` e IDs duplican la logica de filtros en catalogo

**Impacto:** Medio. No es un bug hoy, pero aumenta el costo de cada busqueda: toda pagina ejecuta `COUNT`, luego query de IDs, luego hidratacion. Ademas, cualquier cambio en `where/order` debe mantenerse sincronizado.

**Evidencia:** `ProductJpaDao.findByCriteria(CatalogCriteria)` ejecuta `COUNT(*)` y luego `SELECT p.id` con el mismo join/where (`persistence/src/main/java/ar/edu/itba/paw/persistence/ProductJpaDao.java:421-445`). La variante `TOTAL_PRICE` repite el patron (`persistence/src/main/java/ar/edu/itba/paw/persistence/ProductJpaDao.java:512-554`).

**Fix sugerido:**

Para paginas de catalogo donde no sea imprescindible mostrar total exacto, considerar paginacion "slice": pedir `pageSize + 1` IDs y deducir `hasNext`. Si UX requiere total exacto, mantener el `COUNT` pero encapsular mejor la construccion de filtros y medir si conviene cachear counts por criterio frecuente.

### A7 - `ReviewJpaDao.findByProductId` pagina con `JOIN FETCH` directo

**Impacto:** Bajo/Medio. En este caso los `JOIN FETCH` son ManyToOne y no multiplican filas, asi que no hay el problema clasico de paginar colecciones. Aun asi, no clampa pagina fuera de rango y no usa el patron 1+1 que si se usa en reportes.

**Evidencia:** `findByProductId` hace `COUNT`, luego query paginada con `JOIN FETCH r.rent`, `rent2.renter`, `rent2.product` (`persistence/src/main/java/ar/edu/itba/paw/persistence/ReviewJpaDao.java:34-51`).

**Fix sugerido:**

No es urgente. Si se observan paginas vacias por `page` fuera de rango o se agregan mas relaciones, alinear con reportes: IDs paginados, fetch por IDs, y luego `hydrateImageIds`.

### A8 - Busquedas con `LOWER(col) LIKE '%term%'` no aprovechan btree

**Impacto:** Medio si crece el numero de usuarios/productos/reportes. Btree no ayuda con contains case-insensitive.

**Evidencia:**

- `UserJpaDao.searchPaginated` filtra `LOWER(email/name/surname) LIKE :pattern`.
- `ProductJpaDao` filtra `LOWER(p.title) LIKE ...` en catalogo y my-listings.
- `ReportJpaDao.findByCriteria` filtra por producto/reporter con `LOWER(...) LIKE`.

**Fix sugerido:**

En PostgreSQL, habilitar `pg_trgm` y crear indices GIN para busquedas contains:

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_users_email_trgm
    ON users USING gin (lower(email) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_users_name_trgm
    ON users USING gin (lower(name) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_users_surname_trgm
    ON users USING gin (lower(surname) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_products_title_trgm
    ON products USING gin (lower(title) gin_trgm_ops);
```

Si no se quiere depender de extension PostgreSQL, mantenerlo como mejora futura y aceptar scans para datasets chicos.

### A9 - Algunos flujos de servicio hacen varias lecturas secuenciales por aggregate

**Impacto:** Bajo/Medio. La hidratacion esta bien batch-eada para listados, pero los detalles de producto hacen varias consultas: shell, price bundle, imagenes, pickup spots, rating.

**Evidencia:** `ProductServiceImpl.getProductDetail(...)` arma el agregado con multiples servicios: producto, precios, imagenes, spots y rating (`services/src/main/java/ar/edu/itba/paw/services/ProductServiceImpl.java:140-148`).

**Fix sugerido:**

Para pagina de detalle no es necesariamente un problema. Solo optimizar si aparece en profiling. Si hace falta, crear un read-model DAO especifico de detalle que traiga producto+provider+location+rating en una query y deje imagenes/precios como batch id-only.

## Buenas practicas ya presentes

- Las entidades usan `FetchType.LAZY` en relaciones principales, evitando eager loading accidental.
- Los listados evitan BLOBs: imagenes se hidratan como IDs desde tablas puente.
- El catalogo usa paginacion 1+1: IDs primero, `JOIN FETCH` despues.
- Reportes ya usan patron 1+1 y `JOIN FETCH` para evitar N+1.
- Hay locks pesimistas en flujos donde importa la concurrencia, como reserva de producto y orden de imagenes.
- Se agregaron indices simples para FKs criticas en `V44__add_fk_indexes.sql`.

## Plan recomendado de fixes

1. Agregar migracion de indices compuestos para rentas, productos, bloques, precios y reportes.
2. Cambiar `hasConflictingRent` de `COUNT` a existencia con `setMaxResults(1)`.
3. Mover agregaciones de estadisticas de rentas a SQL nativo o vistas.
4. Medir catalogo con `EXPLAIN ANALYZE`, especialmente `RATING`, `TOTAL_PRICE` y filtros por fecha.
5. Si rating se usa mucho para ordenar/filtrar, crear resumen materializado por producto.
6. Evaluar `pg_trgm` para busquedas textuales si el dataset supera algunos miles de filas.

## Consultas a medir con `EXPLAIN ANALYZE`

- Catalogo sin fecha, orden por precio.
- Catalogo con fecha y orden por total.
- Catalogo con orden por rating y `minRating`.
- Mis publicaciones filtradas por estado/categoria/query.
- Dashboard de rentas como renter/provider.
- Reportes por estado y por producto.
- Estadisticas de producto con muchas rentas finalizadas.

