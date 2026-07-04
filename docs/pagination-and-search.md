## Pagination, Filters & Search

The catalog combines three independent concerns: **searchbar**, **filters**, and **pagination**. They are three separate forms but **each must preserve the state of the other two**.

### State rules

| User action | Expected behavior |
|---|---|
| Changes a filter | Reset page to 1; keep search query |
| Changes the search | Reset page to 1; keep filters |
| Changes the page | Keep filters and search |
| Reloads the page | Land on the same state (page is in the URL) |

**Pagination always lives in the URL.** Never store the current page only in JS state — refreshing the browser should bring the user back to the same view.

### Query parameter validation (GET)

These are **GET** requests. They are not Spring forms, so `@Valid` does not apply. Validate query parameters **manually in the controller**:

- Page out of range → clamp to nearest valid page (1 or `totalPages`).
- Page negative or non-numeric → fall back to page 1 (do not 500).
- Filter value not in the enum → ignore the filter (do not 500).
- Empty / missing query → treat as no search.

Example:

```java
@GetMapping("/catalog")
public ModelAndView catalog(
        @RequestParam(defaultValue = "") String query,
        @RequestParam(required = false) String location,
        @RequestParam(defaultValue = "1") int page) {

    // Decode location safely — invalid values are ignored, not 500
    Location loc = null;
    if (location != null && !location.isBlank()) {
        try { loc = Location.valueOf(location.toUpperCase()); }
        catch (IllegalArgumentException ignored) { /* invalid filter — ignore */ }
    }

    int totalPages = productService.getPageCount(query, loc);
    if (page < 1) page = 1;
    if (totalPages > 0 && page > totalPages) page = totalPages;

    ModelAndView mav = new ModelAndView("catalog/catalog");
    mav.addObject("products", productService.findFiltered(query, loc, page));
    mav.addObject("currentPage", page);
    mav.addObject("totalPages", totalPages);
    mav.addObject("query", query);
    mav.addObject("location", location);
    return mav;
}
```

The cátedra has explicitly flagged groups whose `pag=-1` produced a 500 — clamp instead of crash.

### Recommended approach: hidden fields in each form

A single GET form per concern, each preserving the other states via `<input type="hidden">`. This keeps JS off the critical path and lets us reuse Spring validators when needed.

```jsp
<%-- Search form --%>
<form method="get" action="<c:url value='/catalog'/>">
    <input type="text" name="query" value="<c:out value='${query}'/>"/>
    <input type="hidden" name="location" value="<c:out value='${location}'/>"/>
    <input type="hidden" name="page" value="1"/> <%-- reset to 1 on new search --%>
    <button type="submit">Buscar</button>
</form>

<%-- Filter form --%>
<form method="get" action="<c:url value='/catalog'/>">
    <input type="hidden" name="query" value="<c:out value='${query}'/>"/>
    <input type="hidden" name="page" value="1"/> <%-- reset to 1 on filter change --%>
    <select name="location" onchange="this.form.submit()">
        <option value="">Todas</option>
        <c:forEach var="loc" items="${locations}">
            <option value="${loc.name()}"
                <c:if test="${loc.name() == location}">selected</c:if>>
                <c:out value="${loc.displayName}"/>
            </option>
        </c:forEach>
    </select>
</form>

<%-- Pagination links — preserve filters + query --%>
<c:if test="${totalPages > 1}">
    <c:forEach begin="1" end="${totalPages}" var="p">
        <c:url value="/catalog" var="pageUrl">
            <c:param name="query" value="${query}"/>
            <c:param name="location" value="${location}"/>
            <c:param name="page" value="${p}"/>
        </c:url>
        <a href="${pageUrl}" <c:if test="${p == currentPage}">class="active"</c:if>>
            <c:out value="${p}"/>
        </a>
    </c:forEach>
</c:if>
```

The JS-only approach (manage state in JS, reload with computed query string) is permitted but discouraged: you lose Spring server-side validators and bloat the JS layer.

### Filters as query params, not path variables

Convention from Sprint 2 onward: filters and locations live in **query params**, not path variables.

```
NO  /catalog/bariloche
SI  /catalog?location=BARILOCHE&query=skis&page=1
```

Reasons: a single endpoint serves all filter combinations; optional filters are trivial; the same controller handles search + filter + page.

### Catalog visibility — only `ACTIVE` products

The DAO that powers the catalog **must filter by `status = 'ACTIVE'`**. Paused/deleted products are not listed even if they still exist in the table. This is a domain invariant — see `docs/domain-and-layering.md`.

```sql
WHERE status = 'ACTIVE'
  AND (title ILIKE ? OR description ILIKE ?)
  AND (location = ? OR ? IS NULL)
LIMIT ? OFFSET ?
```

### `LIKE` — escape `%` and `_`

When the search query is interpolated into a `LIKE` clause, `%` and `_` are wildcards in SQL. If a user searches for "50%" or "name_with_underscore", **escape** them in the service / DAO. The cátedra has flagged groups that didn't.

A canonical escape: `value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")` and append `ESCAPE '\\'` to the SQL.

### Multiple paginations on one page

If a single page has more than one paginated list (e.g., "my products" + "my rents"), use **distinct query param names** per concern (`productPage`, `rentPage`) so changing one does not reset the other.

### Pagination metadata in the model

When the service returns a `Page<T>` with `pageNumber`, `pageSize`, `totalCount`, and `content`, expose all of them to the view. JSPs need:
- `currentPage` to highlight the active link
- `totalPages` to render the page list
- `pageSize` if the user can change it (otherwise it's a constant)

### Where the page clamp lives — one rule

The page clamp (`page < 1 → 1`, `page > lastPage → lastPage`) and the `ceil(totalCount / pageSize)`
formula have a single home. The rule:

> **The clamp lives wherever the `totalCount` is computed, and it runs exactly once.**

In practice every paginated **DAO** method computes its own `COUNT` and then fetches the page, so the
DAO clamps internally — count → clamp → fetch in one pass, returning a fully-correct `Page` whose
`getPageNumber()` is the clamped value. `ProductJpaDao.findByCriteria` is the canonical shape; all
paginated DAOs follow it. Consequences:

- An out-of-range page (`?page=999`) returns the **last page** with content, never an empty ghost page.
- The **service never clamps and never re-queries** for pagination — it forwards the raw `pageNumber` and
  trusts the clamped `Page`. (A service computes a separate `COUNT` only when it needs that number for
  something *other* than clamping — e.g. the per-category dashboard badge counts — never to clamp.)
- The **controller never clamps** either; `@RequestParam` validation only stops a `500` (non-numeric →
  fall back to a default), the DAO does the range clamp.

The shared maths lives in `ar.edu.itba.paw.models.Pagination` (`lastPage` / `clamp`) — a non-instantiable
utility reused by every DAO and by `Page.getTotalPages()`, so the formula is never duplicated. Never
re-implement `Math.min(Math.max(...))` or `ceil(total/size)` inline.

#### Both bounds belong to the DAO — the service does not even normalize `page < 1`

`Pagination.clamp` is `Math.min(Math.max(requestedPage, 1), lastPage(total, size))` — it already pins the
**lower** bound (`page < 1 → 1`) **and** the upper bound (`page > lastPage → lastPage`) in one call. Every
paginated DAO calls it, so the lower-bound clamp is **not** a separate concern the service has to cover.

A common misread is "the DAO only does the *upper*-bound clamp, so the service still has to floor `page`
at 1". That is wrong: there is **one** clamp, it lives in the DAO, and it does both ends. The service must
forward `criteria.getPageNumber()` **untouched**. Do not pre-normalize the page in the service (or the
controller) with any of these idioms — they are redundant with `Pagination.clamp`, they re-implement the
floor `Pagination` already owns, and they drift in spelling across the codebase:

```java
// WRONG — the service re-implements the lower-bound floor the DAO's Pagination.clamp already does
final int page = Math.max(criteria.getPageNumber(), 1);
final int page = criteria.getPageNumber() < 1 ? 1 : criteria.getPageNumber();
final int page = pageNumber >= 1 ? pageNumber : 1;
final int page = normalizePageNumber(raw.getPageNumber());   // private helper doing the same floor

// RIGHT — forward the raw page number; the DAO clamps both bounds via Pagination.clamp
return dao.findByCriteria(criteria.toBuilder().pageSize(PAGE_SIZE).build());
```

The service still owns its **page-size policy** (`.pageSize(PAGE_SIZE)`) and any **query normalization**
(trim/blank-to-null) — those are not the clamp. It just stops touching `pageNumber`. If you ever need the
floor/ceiling outside a DAO, call `Pagination.clamp` / `Pagination.lastPage`; never hand-roll
`Math.max(page, 1)` or `ceil(total/size)`.

> Tests: a service test must **not** assert that the service hands the DAO a floored page (e.g.
> `argThat(c -> c.getPageNumber() == 1)` after passing `0`). That asserts the floor lives in the service —
> the exact thing this rule forbids — and is also testing implementation via the mock. The clamp is covered
> by the DAO pagination tests (scenarios 4 and 8 in `docs/testing.md`); the service test asserts only its
> own contributions (page size, returned content, query normalization).

### Anti-patterns flagged by the cátedra

- `pag=-1` returns 500 (no clamp).
- `pag=999` shows page 7 with empty results instead of clamping or redirecting to 1.
- Search input is unescaped → injects `%`/`_` into `LIKE`.
- Pagination only in JS state → refreshing the browser jumps back to page 1.
- Changing a filter does not reset the page → user lands on an empty page 5 of a now-shorter list.
- Multiple paginations sharing the same `page` query param.
- Filter form deletes the search query when submitted.
- Listing all 1000 records and filtering in Java instead of in SQL.
- Doing JOINs in Java (`for` loop calling `findById`) — N+1 queries.
- Magic numbers for page size hardcoded across DAOs / controllers / JSPs (use a `private static final int DEFAULT_PAGE_SIZE = ...` in the service or a `@Value`).
- Service (or controller) flooring the page with `Math.max(page, 1)` / `page < 1 ? 1` / a `normalizePageNumber` helper. The clamp is one call (`Pagination.clamp`) and it lives in the DAO — both bounds, including `< 1`. The service forwards the raw `pageNumber`.