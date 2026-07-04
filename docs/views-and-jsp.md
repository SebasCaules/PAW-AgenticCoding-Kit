## Views, JSP, JSTL & i18n

Todas las vistas viven en `webapp/src/main/webapp/WEB-INF/views/`. Los custom tag files en `webapp/src/main/webapp/WEB-INF/tags/`. El frontend usa Bootstrap 5 + custom CSS en `webapp/src/main/webapp/css/`.

### Reglas absolutas

1. **NUNCA** usar scriptlets (`<% %>`) ni expresiones Java (`<%= %>`). Solo JSTL + EL (`${...}`).
2. **NUNCA** imprimir datos del usuario / DB con `${var}` directo — siempre `<c:out>` para escapar HTML.
3. **NUNCA** hardcodear paths de recursos estáticos ni URLs internas — siempre `<c:url>`.
4. **NUNCA** hardcodear textos visibles al usuario — siempre `<spring:message>`.
5. **NUNCA** chequear roles con `c:if + magic strings` (`${user.role == 'ADMIN'}`) — usar `<sec:authorize>`.
6. **NUNCA** poner lógica de negocio en JSP (filtrar, ordenar, deduplicar, decidir precios, resolver fallback, etc.). Ver `docs/domain-and-layering.md`.

### Taglibs requeridas (al inicio de cada JSP que las use)

```jsp
<%@ taglib prefix="c"      uri="http://java.sun.com/jsp/jstl/core" %>
<%@ taglib prefix="spring" uri="http://www.springframework.org/tags" %>
<%@ taglib prefix="form"   uri="http://www.springframework.org/tags/form" %>
<%@ taglib prefix="sec"    uri="http://www.springframework.org/security/tags" %>
```

### XSS — `<c:out>` obligatorio

Imprimir `${user.name}` o `${product.description}` directo permite a un atacante inyectar `<script>...`. **Todo** valor que provenga de la DB o del usuario debe imprimirse con `<c:out>`:

```jsp
<%-- VULNERABLE — XSS --%>
<p>${user.name}</p>
<h1>${product.title}</h1>

<%-- SEGURO — escapa entidades HTML --%>
<c:out value="${user.name}" />
<c:out value="${product.title}" />
```

`<c:out>` convierte `<`, `>`, `"`, `'`, `&` en sus entidades HTML, neutralizando scripts.

Valores **seguros** sin `<c:out>` (controlados por la app, no por el usuario):
- URLs generadas con `<c:url>`
- Números enteros / decimales
- Booleanos
- Valores de enums controlados por el código

Esta regla aplica también a **mensajes de error** que pueden incluir input del usuario, atributos `alt` de imágenes y atributos `title`.

### `<c:url>` para todos los recursos y URLs

```jsp
<%-- MAL: rompe cuando la app no está en el root context --%>
<link rel="stylesheet" href="/css/style.css" />
<a href="/products/${id}">Ver</a>

<%-- BIEN --%>
<c:url value="/css/style.css" var="cssPath" />
<link rel="stylesheet" href="${cssPath}" />

<c:url value="/products/${id}" var="productUrl" />
<a href="${productUrl}">Ver</a>
```

`<c:url>` aplica el context path correcto y encoda parámetros. Imprescindible cuando la app se sirve detrás de un context (`/paw-2026a-10/`).

`<c:url>` con parámetros:

```jsp
<c:url value="/catalog" var="catalogUrl">
    <c:param name="location" value="${location}" />
    <c:param name="page" value="${p}" />
</c:url>
<a href="${catalogUrl}">Página ${p}</a>
```

### Forms con Spring Form Taglib

`modelAttribute` debe coincidir **exactamente** con el `@ModelAttribute` del controller:

```jsp
<c:url value="/publish" var="postPath" />
<form:form modelAttribute="publishProductForm" action="${postPath}" method="post"
           enctype="multipart/form-data">
    <form:label path="title">Título</form:label>
    <form:input path="title" />
    <form:errors path="title" cssClass="formError" element="p" />

    <button type="submit">Publicar</button>
</form:form>
```

- `<form:errors>` permite customizar el elemento HTML (`element="p"`), la clase CSS (`cssClass`) y el inline style.
- Para validación cross-field (a nivel de form completo) que se ata a un campo, ver `docs/forms-and-validation.md`.

### `<sec:authorize>` — control de acceso en la vista

No hacer chequeos manuales con `c:if` — usar la taglib de Spring Security para que la regla la evalúe el ACL de `WebAuthConfig` y no haya divergencias:

```jsp
<%-- MAL: magic string + lógica duplicada con WebAuthConfig --%>
<c:if test="${loggedUser.role == 'ADMIN'}">
    <a href="/admin">Panel</a>
</c:if>

<%-- BIEN: respeta exactamente las reglas del SecurityFilterChain --%>
<sec:authorize access="hasRole('ADMIN')">
    <a href="<c:url value='/admin'/>">Panel</a>
</sec:authorize>

<%-- También se puede chequear por URL (respeta los matchers de WebAuthConfig) --%>
<sec:authorize url="/admin">
    <a href="<c:url value='/admin'/>">Panel</a>
</sec:authorize>

<%-- Mostrar nombre del usuario logueado --%>
<sec:authentication property="name" />
```

**Regla:** si el ocultado/mostrado de un elemento depende de "puede o no acceder a esta ruta", usar `<sec:authorize url="...">`. Es lo más robusto porque las reglas viven en un único lugar (`WebAuthConfig`).

### i18n — `<spring:message>`

Todos los textos visibles al usuario van por `MessageSource`. Archivos en `webapp/src/main/resources/i18n/`:

```
messages.properties       (default — el proyecto usa español como default)
messages_en.properties
messages_es.properties
messages_fr.properties
```

**Jerarquía de resolución** (Spring busca el más específico primero):

```
messages_en_US.properties → messages_en.properties → messages.properties
```

Uso en JSP:

```jsp
<%-- mensaje simple --%>
<h1><spring:message code="landing.title" /></h1>

<%-- con argumentos posicionales (placeholders {0}, {1}) --%>
<spring:message code="user.greeting" arguments="${user.username}" />

<%-- como atributo HTML — usar var --%>
<spring:message code="form.submit" var="submitLabel" />
<input type="submit" value="${submitLabel}" />
```

Mensajes de validación JSR-303: las claves de los archivos siguen la jerarquía de Bean Validation. Ver `docs/forms-and-validation.md` para el detalle.

#### Pluralización (una sola clave, sin `c:choose`)

Para evitar dos claves separadas (`x.single`/`x.many`) seleccionadas a mano en la vista, se colapsa en **una sola clave** que `MessageFormat` resuelve según el número.

> ⚠️ **OJO — ICU `plural` NO funciona en este proyecto.** El `MessageSource` es un `ReloadableResourceBundleMessageSource` pelado (ver `WebConfig.messageSource()`), que usa `java.text.MessageFormat`. `java.text.MessageFormat` soporta los tipos `number`/`date`/`time`/`choice`, **pero no `plural`/`select`** (eso es ICU4J, que **no** está en el classpath). Una clave como `{0, plural, one{...} other{...}}` tira `IllegalArgumentException: unknown format type` en runtime y rompe la página. Usar `choice`, no `plural`.

**Forma soportada — `choice` (el número va embebido y se repite por rama):**

```properties
# {0} se reformatea recursivamente dentro de la rama elegida
catalog.count={0,choice,0#{0} productos encontrados|1#1 producto encontrado|1<{0} productos encontrados}
```

```jsp
<%-- el arg DEBE ir solo (no en lista separada por coma) para que llegue como Number a ChoiceFormat --%>
<spring:message code="catalog.count" var="catalogCountText" arguments="${page.totalCount}"/>
<paw:page-header title="${heading}" countText="${catalogCountText}"/>
```

Renderiza "1 producto encontrado" / "5 productos encontrados" automáticamente, sin `<c:choose>` ni ternario.

Sutilezas de `ChoiceFormat`:
- Límites ascendentes: `0#` (≥0), `1#` (=1), `1<` (>1). Cubrir el `0#` si el cero es posible.
- **El arg tiene que ser un número.** `<spring:message arguments="${a},${b}">` parte el string por coma → todo llega como `String` → `ChoiceFormat` (que compara contra límites numéricos) falla. Por eso, si necesitás el plural dentro de un mensaje compuesto, resolvé la frase con su propia clave `choice` (arg único `arguments="${n}"`, que se preserva como `Number`) y **inyectá el string resultante** en el mensaje padre — no embebas el `choice` con el número viniendo de una lista por coma. Ej.: `catalog.days={0,choice,1#{0} día|1<{0} días}` → se resuelve aparte y se pasa como `{2}` a `catalog.dateRange.pill={0} - {1} · {2}`.
- Para palabra sola (número renderizado en otro elemento), usar `choice` sin `{0}` en las ramas: `{0,choice,1#reporte|1<reportes}`.

> Si en el futuro se quiere el `plural`/`select` de ICU de verdad (reglas de plural por locale: `few`/`many` para fr/pl/ru, etc.), hay que agregar la dependencia `com.ibm.icu:icu4j` (al `<dependencyManagement>` del pom padre) y un `MessageSource` custom ICU-backed que reemplace al `ReloadableResourceBundleMessageSource`. Mientras eso no exista, **`choice` es la única forma que funciona**.

#### Reglas de i18n

- **NO** dejar textos hardcodeados en JSPs. Si hay un string visible, debe vivir en `messages*.properties`.
- **NO** dejar textos hardcodeados en controllers ni services. Si el mensaje termina en la UI, va por `MessageSource`.
- **NO** internacionalizar a medias: símbolos de moneda, atributos `alt` de imágenes, `title` y `aria-label` también requieren clave de mensaje.
- **`messages_es.properties` debe existir, aunque esté vacío.** Convención del equipo: el archivo por idioma soportado siempre presente, aun si el default `messages.properties` ya está en español. Las claves que falten en `messages_es.properties` se resuelven automáticamente vía herencia desde `messages.properties` (jerarquía: `messages_es_AR` → `messages_es` → `messages`). Dejarlo vacío evita duplicar todas las claves y deja explícito que el locale `es` está soportado.
- **Mails** usan el `preferredLanguage` del **destinatario**, no `LocaleContextHolder.getLocale()`. Ver `docs/anti-patterns.md` y `docs/security.md` (sección "Async + ThreadLocal").

### Custom tag files

Las páginas usan ~30 custom tags definidos en `WEB-INF/tags/` (navbar, footer, product-card, calendar, modal, etc.). Cuando hay una pieza de UI reutilizable con parámetros, crear un tag file en lugar de copiar JSP. Si solo hay estructura repetida sin parámetros, un `<%@ include file="..." %>` también es válido — los tags no son un Golden Hammer.

### Custom Tag Library (SimpleTag) — para lógica de presentación reusable

Cuando los built-in no alcanzan, crear un tag con `SimpleTag`:

```java
public class MyTag extends SimpleTagSupport {
    @Override
    public void doTag() throws JspException, IOException {
        getJspContext().getOut().write("...");
    }
}
```

Más TLD en `WEB-INF/`. Esta opción es para presentación (ej. formateo). **No** para lógica de negocio.

### EL quick reference

```
${user.name}           → propiedad simple
${user.address.city}   → propiedad anidada
${products[0]}         → colección indexada por índice
${user.age >= 18}      → operación relacional
${empty list}          → true si null, "" o colección vacía
```

Operadores: `+`, `-`, `*`, `/`, `%`, `==`, `!=`, `<`, `>`, `&&`, `||`, `!`, `empty`.

### Copy-to-clipboard — usar SIEMPRE el helper HTTP-safe

**El deploy de la cátedra (`pawserver`) se sirve por HTTP, no HTTPS.** La async Clipboard API (`navigator.clipboard`) **solo existe en un secure context** (HTTPS o `localhost`): en producción es `undefined` y cualquier código que la llame directo falla en silencio (el botón "Copiar" no copia nada). Esto aplica a **todo** lo que copie texto: link de compartir, email/CBU del provider, email del renter, etc.

Regla: **nunca** llamar `navigator.clipboard` directo desde una vista o un JS de feature. Copiar **siempre** a través del helper compartido `window.pawCopyToClipboard(text, onCopied)` definido en **`webapp/src/main/webapp/assets/js/clipboard-copy.js`** (cargado global en `head.jsp`). El helper intenta la Clipboard API solo si `window.isSecureContext`, y si no, cae al fallback legacy `document.execCommand('copy')` — que sí funciona sobre HTTP.

```js
// MAL — se rompe en el deploy HTTP (navigator.clipboard es undefined)
navigator.clipboard.writeText(shareUrl).then(flashCopied);

// BIEN — único punto de copia, con fallback HTTP
window.pawCopyToClipboard(shareUrl, flashCopied);
```

Es **single source of truth**: el link de compartir (`detail.jsp`), el copy de emails/CBU (`rent-action-panel.tag`) y el copy de `.is-copyable` (`rent-manage.js`) usan todos este helper. Si agregás una nueva acción de copiar, reusalo — no reimplementes el branch `navigator.clipboard`/`execCommand` inline.

### Formateo de fechas — función EL `pawfn:fmtDateTime` / `pawfn:fmtDate`

El proyecto **no** formatea fechas con string-hacks en el JSP (`fn:replace(fn:substring(x, 0, 16), 'T', ' ')` sobre el `toString()` de un `LocalDateTime`): es frágil, deja formato ISO y duplica el patrón en cada vista. **Tampoco** se formatea en el modelo/DTO (un getter `getXDisplay()` en `models`/`service-contracts` es un formateo de presentación viviendo en la capa equivocada — además roza el antipattern cátedra "modelos con fechas formateadas como `String`"). El formateo es **responsabilidad de la vista** y vive en `webapp`:

- **Helper único en `webapp`:** `ar.edu.itba.paw.webapp.util.DisplayFormat` (`final` + constructor `private`, no instanciable). Expone `fmtDateTime(TemporalAccessor)` → `dd/MM/yyyy HH:mm` y `fmtDate(TemporalAccessor)` → `dd/MM/yyyy`, ambos null-safe (devuelven `""`). Toma `TemporalAccessor` para que **una sola** función sirva `LocalDate` y `LocalDateTime` (las funciones EL no se pueden sobrecargar).
- **Expuesto como función EL** vía `webapp/src/main/webapp/WEB-INF/paw-functions.tld` (prefijo `pawfn`, uri `http://itba.edu.ar/paw/functions`).
- **El modelo/DTO solo expone el getter temporal crudo** (`getCreatedAt()` → `LocalDateTime`, la fuente de verdad). El JSP formatea con la función EL sobre ese getter.

```jsp
<%@ taglib prefix="pawfn" uri="http://itba.edu.ar/paw/functions" %>

<%-- MAL — string-hack sobre el toString() ISO --%>
<c:set var="createdDisplay" value="${fn:replace(fn:substring(report.createdAt, 0, 16), 'T', ' ')}"/>

<%-- MAL — formateo en el modelo (getter de presentación en models/service-contracts) --%>
<c:out value="${report.createdAtDisplay}"/>

<%-- BIEN — función EL de la capa view sobre el getter temporal crudo --%>
<c:out value="${pawfn:fmtDateTime(report.createdAt)}"/>   <%-- dd/MM/yyyy HH:mm --%>
<c:out value="${pawfn:fmtDate(pause.blockFrom)}"/>        <%-- dd/MM/yyyy (LocalDate o LocalDateTime) --%>
```

Usado en `admin/*` y `my-listings/*` (reports, actions, report-detail), `pauses/manage.jsp`, y los tags `review-card`/`admin-report-item`. Es el único punto de formato de fechas — si agregás una fecha visible, reusá `pawfn`, no reintroduzcas `fn:substring` ni un getter `getXDisplay()`.

> Nota: patrón de formato fijo (`dd/MM/yyyy`), no locale-aware. Si en el futuro se necesita formato por locale, parametrizar `DisplayFormat` — hoy fuera de scope.

### Antipatterns en JSP que el corrector castiga

- Imprimir `${var}` con datos del usuario sin `<c:out>` → **XSS, error grave**.
- Hardcodear `/css/...` en lugar de `<c:url>`.
- Hardcodear `${pageContext.request.contextPath}/...` en lugar de `<c:url>` (es la opción "menos mala" pero `<c:url>` es la canónica).
- Hardcodear textos visibles en lugar de `<spring:message>`.
- Chequear roles con `c:if + magic string` en lugar de `<sec:authorize>`.
- Concatenar valores en JSP (`<h3>${var1}${var2}</h3>`) en lugar de interpolar con un mensaje i18n parametrizado.
- Faltar `messages_es.properties` (aunque esté vacío) — el archivo por idioma soportado siempre va presente y hereda del default.
- Modelos/DTOs que formatean fechas: ya sea **almacenándolas** como `String` (perdiendo el tipo temporal), exponiendo getters de presentación `getXDisplay()` en `models`/`service-contracts`, o dispersando string-hacks (`fn:substring`/`fn:replace`) por cada vista. El tipo crudo (`LocalDate`/`LocalDateTime`) es la única fuente de verdad en el modelo; el formato de presentación vive en la vista, vía `pawfn:fmtDateTime`/`pawfn:fmtDate` (ver "Formateo de fechas").
- Filtrar / ordenar / deduplicar colecciones en el JSP — pertenece al service.
- Llamar `navigator.clipboard` directo para copiar texto — se rompe en el deploy HTTP. Usar `window.pawCopyToClipboard` (ver "Copy-to-clipboard — usar SIEMPRE el helper HTTP-safe").