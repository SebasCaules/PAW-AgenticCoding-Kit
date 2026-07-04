# Entrega Final — de JSP a SPA + REST API

La última etapa de PAW: el webapp Spring MVC + JSP se convierte en una **API REST** (JAX-RS/Jersey
sobre el mismo WAR) consumida por una **SPA** (React recomendado). Es la migración más grande de
la cursada y la que más decisiones de contrato tiene — **el contrato se cierra ANTES de escribir
código** (idealmente validado en consulta con la cátedra).

> Este doc es el destilado portable. El set completo de referencia (contrato resuelto, specs
> pantalla-por-pantalla y un runbook de 141 pasos atómicos) vive en el proyecto de origen bajo
> `0_Plans/rest-migration/final/` — si tenés acceso, empezá por su `README.md`.

## Declaración de etapa (pegala en tu CLAUDE.md / AGENTS.md)

```markdown
## Etapa de la cursada
ETAPA ACTUAL: SPA+REST (Entrega Final)
- Backend: API REST JAX-RS (Jersey) bajo /api/* en el mismo WAR; JSP solo como legacy en retirada.
- Auth: STATELESS con JWT (access + refresh) — se acabó la sesión de Spring Security.
- Front: SPA React (módulo Maven `frontend` integrado al WAR vía frontend-maven-plugin + Vite).
- Las reglas JSP (c:out, c:url, spring:message, sec:authorize) aplican SOLO a vistas legacy que
  sigan vivas; el código nuevo se audita con las reglas REST/SPA de este doc.
```

## Qué evalúa la cátedra en esta entrega

1. **Madurez REST del contrato**: sustantivos en las URIs (nunca verbos), verbos HTTP correctos
   (`GET` seguro/cacheable, `POST` crea, `PUT`/`PATCH` según semántica, `DELETE` idempotente),
   códigos correctos (201+`Location` al crear, 204 sin body, 400 validación, 401 vs 403, 404,
   409 conflicto de estado, 412/428 si usan concurrencia optimista).
2. **Hipermedia/links**: los DTOs exponen links (`self` + relaciones) en vez de IDs pelados
   anidados; el cliente navega por links, no construye URLs a mano.
3. **Paginación por headers**: `Link` (first/prev/next/last) + total (`X-Total-Count` o
   equivalente) — no metadata inventada en el body.
4. **Auth stateless**: JWT access + refresh; nada de `JSESSIONID`. El `SecurityContext` se puebla
   por filtro desde el token. Los access handlers / `@PreAuthorize` existentes se REUSAN.
5. **Content negotiation** y errores JSON uniformes (un `ErrorDto` estable; los `ExceptionMapper`
   reemplazan 1:1 al `GlobalExceptionHandler`).
6. **SPA real**: deep-linking (una URL pegada en el browser renderiza esa vista), estado en la URL
   (filtros/página/búsqueda — misma regla que la cursada JSP), i18n en el front (mismos locales),
   y build integrado al WAR (un solo artefacto deployable en el server de la cátedra).

## Orden de operaciones (olas espejo backend ⇄ front)

### Fase 0 — El contrato (papel, no código)
Inventariá TODOS los endpoints actuales (grep de `@RequestMapping`/`@GetMapping`... — verificá el
conteo contra código, no de memoria: en el proyecto de origen "eran ~70" y el recuento real dio
96). Definí: recursos y URIs, verbos, códigos, shape de DTOs y errores, paginación, auth y qué
preguntas quedan para la consulta. Esto es un doc en `0_Plans/`, revisable con la cátedra.

### Backend (sobre el WAR existente — JSP sigue andando mientras tanto)
- **B0 — Infra Jersey**: deps JAX-RS/Jersey en el pom padre, `ResourceConfig`, mapping `/api/*`
  en `web.xml` (el `DispatcherServlet`/JSP conviven hasta el final). Checkpoint: un `GET /api/ping`.
- **B1 — Auth stateless**: `JwtTokenService` + filtro que puebla el `SecurityContext`;
  `WebAuthConfig` a `STATELESS` para `/api/*` (entry point 401 JSON); login emite access+refresh;
  refresh rota tokens. Locale por `Accept-Language`.
- **B2 — Piezas transversales**: DTOs con `fromEntity(...)` + links (ocultan password/tokens/
  campos sensibles y cortan lazy), `ExceptionMapper`s por familia de excepción, Bean Validation
  en los resources, helper de paginación (headers `Link`).
- **B3 — Rollout por olas de recursos**: auth/users → products → rents → favoritos/gestión →
  admin/moderación. Cada ola: resources JAX-RS finos (la lógica sigue TODA en los services —
  la capa service no se toca), `curl` de checkpoint por endpoint.

### Front (módulo nuevo, integrado al build)
- **S-A — Andamiaje**: módulo Maven `frontend` con `frontend-maven-plugin` (node fijado), Vite
  (`base` = context path del deploy), el WAR empaqueta el build.
- **S-B — Cliente HTTP**: axios (o fetch wrapper) con interceptores: `Authorization: Bearer`,
  `Accept-Language`, refresh-on-401-and-retry, parser del header `Link`. TanStack Query (o
  equivalente) para cache/estado de servidor.
- **S-C — Auth + routing**: login/registro contra la API, guards por rol, deep-linking servido
  por el backend (catch-all a `index.html` para rutas no-API), estado-en-URL para filtros/página.
- **S-D — Migración pantalla por pantalla**, en el MISMO orden que las olas del backend: cada
  pantalla JSP → ruta React consumiendo los endpoints ya publicados. La JSP muere recién cuando
  su reemplazo está verificado.
- **S-E — Cierre**: i18n completo (mismos locales que la cursada), cache/file-revving de assets,
  tests del front (Vitest) — la cátedra los pide.

## Qué cambia respecto de la etapa JSP

| Tema | Cursada (JSP) | Final (SPA + REST) |
|---|---|---|
| XSS | `<c:out>` obligatorio | React escapa por default — prohibido `dangerouslySetInnerHTML` (es el nuevo `${var}` crudo) |
| URLs | `<c:url>` (context path) | `base` de Vite + cliente HTTP centralizado; nunca URLs hardcodeadas ni armadas a mano (navegar por links de la API) |
| i18n | `<spring:message>` + MessageSource | Catálogos en el front (i18next o equiv.), mismos locales; el backend solo localiza mensajes de error vía `Accept-Language` |
| Auth | Sesión + form login | JWT stateless: access+refresh, filtro propio, 401 JSON. `@PreAuthorize`/access handlers se reusan |
| Roles en la vista | `<sec:authorize>` | Guards de ruta + render condicional por rol del token — la autoridad REAL sigue siendo el backend |
| Errores | `GlobalExceptionHandler` → JSP de error | `ExceptionMapper`s → `ErrorDto` JSON; la SPA los muestra en el form/vista |
| Estado (filtros/página) | Query params + forms GET | **Igual**: estado en la URL de la SPA (la regla no cambia, cambia quién la implementa) |
| Validación | Bean Validation en forms MVC | Bean Validation en los resources (400 con detalle por campo) + validación de UX en el front (nunca como única barrera) |
| Tests | JUnit persistence/services | Los mismos (la capa service NO cambia) + tests del front |

## Trampas reales de esta migración

- **Romper la coexistencia**: el mapping `/api/*` mal hecho se come las JSP (o viceversa) — la
  cursada sigue demo-able durante toda la transición.
- **Lógica de negocio en los resources JAX-RS**: mismo pecado que en controllers MVC, misma
  penalización. El resource orquesta; el service decide.
- **DTO = entidad serializada**: expone password/tokens/CBU y explota con lazy. Siempre DTO
  explícito con `fromEntity`.
- **Deep links rotos**: F5 en `/products/5` da 404 si falta el catch-all a `index.html`.
- **El front "construye" URLs de la API a mano** en vez de seguir los links del contrato.
- **Auth a medias**: API stateless pero endpoints legacy aún por sesión → dos fuentes de verdad
  de identidad. Definí el corte y migrá el login primero.
- **i18n del backend olvidada**: los mensajes de error de la API también se localizan
  (`Accept-Language`) — los bundles no mueren, se reparten.

## Qué skills usar en esta etapa

`/plan` y `/impl` con la etapa declarada (el contrato y las olas son planes en `0_Plans/` como
siempre); `/gp` y `/corrector-eyes` auditan resources/DTOs con las reglas de arriba y las JSP
legacy con las de siempre; `/smoke` sigue válido para el backend (i18n de bundles backend,
Flyway, test-compile). Para el diseño de pantallas de la SPA, `/design` sirve como brief pero
recordá que genera JSP por defecto — pedile explícitamente React y pasale el design system.
