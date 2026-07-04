
## Logging

The app uses **SLF4J + Logback** (config in `webapp/src/main/resources/logback.xml`). Default level for `ar.edu.itba.*` is `INFO`; override in dev with `-Dar.edu.itba.log.level=DEBUG`.

### When to add a logger

Every new `*ServiceImpl` method that mutates state, transitions a state machine, sends an email, issues a token, or rejects a business rule **must** include a log line. Pure read methods (`findById`, `getX`, etc.) generally do not need logs unless they implement non-trivial logic worth tracing.

Declare the logger as:

```java
private static final Logger LOGGER = LoggerFactory.getLogger(MyServiceImpl.class);
```

### Log levels

Pick the level by **what the event means**, not by how interesting it feels:

| Level | Use for |
|---|---|
| `INFO` | Successful mutations, state transitions, scheduled jobs starting/finishing, emails sent, tokens issued. The default for "something happened that an admin would want to see in the file." |
| `WARN` | Business rules rejected (ownership violation, invalid state transition, validation failure, cooldown hit). The operation didn't crash but it didn't proceed either. |
| `ERROR` | Unexpected failures with stack trace (`LOGGER.error("...", e)`). Especially important inside `@Async` methods where exceptions otherwise vanish. |
| `DEBUG` | Verbose tracing only useful in dev. Keep these rare — most events should be `INFO` or above. |

### What NEVER to log (PII)

The following must **never** appear in any log message, even partially:

- User name, surname, address
- CBU
- Verification or password-reset tokens (or any fragment of them)
- Passwords (raw or hashed)

What **is** allowed:

- Identifiers: `userId`, `productId`, `rentId`, `blockId`, `imageId`
- User email (decided as acceptable for this project)
- Enum values (`RentStatus`, `Category`, `ProductStatus`, etc.)
- Booleans / counts / amounts / currency codes

### Message format

Use SLF4J parameterized logging — never string concatenation.

```java
// Good
LOGGER.info("Rent transitioned rentId={} {} -> {}", rentId, expected, next);

// Bad
LOGGER.info("Rent transitioned rentId=" + rentId + " " + expected + " -> " + next);
```

Conventional shape: a short verb-led summary, then `key=value` pairs for the relevant identifiers.

### Async methods

Methods annotated `@Async` swallow exceptions silently. Wrap the risky call in `try/catch (RuntimeException e)` and log at `ERROR` with the exception so SMTP/IO failures stay visible.


## Logging

La aplicación usa **SLF4J + Logback** para registrar lo que pasa en la capa de servicios.

### Configuración

`webapp/src/main/resources/logback.xml` define dos archivos rotativos en `webapp/logs/` y un appender de consola:

| Archivo | Contenido | Nivel |
|---|---|---|
| `paw-2026a-10.YYYY-MM-DD.log` | Eventos de la app (`ar.edu.itba.*`) | `INFO` |
| `paw-2026a-10-warnings.YYYY-MM-DD.log` | Logs de librerías externas | `WARN` |

- **Retención:** 7 días (rolling diario, los más viejos se borran solos).
- **Consola:** los logs de la app también salen por stdout cuando se corre con `mvn jetty:run`.
- **Override en dev:** `mvn jetty:run -Dar.edu.itba.log.level=DEBUG` baja el nivel para ver detalle fino sin tocar el XML.
- **Patrón:** cada entrada incluye fecha completa (`yyyy-MM-dd HH:mm:ss.SSS`), thread, nivel, logger y mensaje.

### Qué se loguea

Los `*ServiceImpl` registran tres tipos de eventos:

- **`INFO` — Mutaciones y cambios de estado.** Creaciones, ediciones, transiciones de `RentStatus`, envíos de email, emisión de tokens, etc. Suficiente para reconstruir qué pasó en una operación dada usando IDs.
- **`WARN` — Reglas de negocio rechazadas.** Ownership violation, transición de rent inválida, validación de size/category fallida, intento de favoritear producto propio, token de verificación inválido o expirado.
- **`ERROR` — Fallos inesperados.** Hoy cubre fallos de envío SMTP en `EmailServiceImpl` (antes se perdían silenciosamente porque `@Async` se come la excepción).

### Privacidad

Los logs **nunca** incluyen datos sensibles del usuario:

- Sin nombre ni apellido
- Sin dirección ni CBU
- Sin tokens (verificación de email, reset de contraseña)
- Sin contraseñas (ni hasheadas)

Solo se registran identificadores (`userId`, `productId`, `rentId`, etc.) y el email del usuario cuando es relevante para el evento.

---

### Logger declaration — always SLF4J

Import only from SLF4J (the facade). Never import directly from Logback — that couples the code to the implementation.

```java
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

private static final Logger LOGGER = LoggerFactory.getLogger(MyClass.class);
```

`Logger` and `LoggerFactory` are in `org.slf4j`. If the IDE auto-imports from Logback, fix it.

### Parameterized logging — `{}` not `+`

```java
// GOOD — parameterized; lazy if level is disabled
LOGGER.info("Rent transitioned rentId={} {} -> {}", rentId, expected, next);

// BAD — string concatenation runs even if INFO is disabled
LOGGER.info("Rent transitioned rentId=" + rentId);

// GOOD — exception with message
LOGGER.error("SMTP send failed for rentId={}", rentId, ex);   // last arg is Throwable
```

For expensive arguments, use the supplier-based API to defer evaluation:

```java
LOGGER.atDebug()
      .addKeyValue("user", () -> userService.findById(userId))   // only invoked if DEBUG is on
      .log("loading user");
```

### Dev vs prod Logback configs

Logback resolves config files in this order: `logback-test.xml` → `logback.xml`. The project uses both:

| File | Location | Used when | Output | Level |
|---|---|---|---|---|
| `logback-test.xml` | `webapp/src/main/resources` | Dev (`mvn jetty:run` from CLI/IDE) | Console | DEBUG |
| `logback.xml` | `webapp/src/main/resources` | Prod (WAR deployed in Tomcat) | Rolling files in `webapp/logs/` | WARN root, INFO `ar.edu.itba.*` |

`maven-war-plugin` excludes `logback-test.xml` from the packaged WAR:

```xml
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-war-plugin</artifactId>
    <configuration>
        <packagingExcludes>**/logback-test.xml</packagingExcludes>
    </configuration>
</plugin>
```

Without this exclusion the dev DEBUG config leaks into production and the cátedra penalizes "logging at DEBUG/INFO in prod" as **error grave**.

### Logger hierarchy & `additivity`

Production config uses two appenders for two file streams:

- Root logger (`<root level="WARN">`) → `warnings.YYYY-MM-DD.log` (external library noise).
- `ar.edu.itba` logger (`<logger name="ar.edu.itba" level="INFO" additivity="false">`) → `paw.YYYY-MM-DD.log` (app events).

The `additivity="false"` flag is critical: without it, every log emitted under `ar.edu.itba.*` is also propagated to the root, producing duplicate entries in the warnings file. Always set `additivity="false"` on a child logger that has its own appender.

### Async methods — exceptions vanish silently

Spring's `@Async` runs the method on a different thread. **Exceptions are not propagated to the caller.** SMTP failures and IO errors disappear unless you catch and log them inside the method:

```java
@Async
public void sendRentRequestEmail(...) {
    try {
        // smtp work
    } catch (final RuntimeException e) {
        LOGGER.error("SMTP send failed rentId={} renterEmail={}", rentId, recipient, e);
    }
}
```

Without the try/catch, a misconfigured SMTP host fails silently and you only notice when users complain.

### `@Async` and `ThreadLocal`

`SecurityContextHolder` and `LocaleContextHolder` use `ThreadLocal`. They are **empty** in the async thread:

```java
@Async
public void sendRentRequestEmail(...) {
    Locale.getDefault();                          // app default — NOT the user's
    LocaleContextHolder.getLocale();              // app default — NOT the request's
    SecurityContextHolder.getContext().getAuthentication();  // null
}
```

Solution: pass the relevant data (locale, recipient, userId) as **explicit method parameters**. Resolve them in the controller (where ThreadLocal still has the request data) and forward them.

This is also why mails should use `recipient.getPreferredLanguage()` — the recipient's configured locale travels via the `User` entity, while `LocaleContextHolder` would still hold the request locale of whoever triggered the action (which is wrong by definition: A reserves B's product, B's mail should be in B's language).

### `@Scheduled` and multi-instance deployments

`@Scheduled` runs **on every JVM** that has the bean. In a single-server deployment (current case) that's fine. For multi-instance, use a shared lock (Quartz with JDBC store, ShedLock, etc.) so the job runs once per scheduled tick.

Add `@EnableScheduling` to `WebConfig` to enable.

### What an INFO log line should look like

Conventional shape: a short verb-led summary, then `key=value` pairs for the relevant identifiers. Easy to grep, easy to diff.

```java
LOGGER.info("Rent created rentId={} productId={} renterId={}", rent.getId(), productId, renterId);
LOGGER.info("Rent transitioned rentId={} {} -> {}", rentId, oldStatus, newStatus);
LOGGER.info("Email sent to recipient={} subject=\"{}\" rentId={}", recipientEmail, subject, rentId);
LOGGER.warn("Ownership violation rentId={} userId={}", rentId, callerId);
LOGGER.error("SMTP send failed rentId={}", rentId, e);
```

### Do not catch-and-log just to rethrow

```java
// noise — the message adds nothing the propagation wouldn't already give
try {
    risky();
} catch (Exception e) {
    LOGGER.error("error in risky", e);
    throw e;
}
```

Only catch if you can handle the exception or add context. Otherwise let it propagate and let `GlobalExceptionHandler` produce the response.

### Anti-patterns flagged by the cátedra

- Logging at DEBUG or INFO in `logback.xml` (prod). Root must be WARN; `ar.edu.itba` may be INFO.
- `System.out.println` and `e.printStackTrace()` instead of a logger.
- Logging without configuring `logback.xml` at all → logs end up in `catalina.out` / `localhost.log` mixed with everything else.
- String concatenation in log calls (`LOGGER.info("user=" + user)`).
- PII in logs (name, surname, address, CBU, tokens, passwords).
- Missing `additivity="false"` causing duplicate entries.
- `@Async` methods without try/catch + `ERROR` log — silent SMTP failures.
- Importing `Logger` from Logback instead of SLF4J.

---

### Cátedra directives — logging checklist

Reglas explícitas de la cátedra. Este bloque las junta para pre-entrega.

- **No loguear a nivel `DEBUG` en prod.** Es excesivo y satura los archivos. En `logback.xml` (prod): `root` en `WARN`, `ar.edu.itba.*` en `INFO`. `DEBUG` solo en `logback-test.xml` (dev), excluido del WAR. Ver "Dev vs prod Logback configs".
- **No loguear a archivos genéricos del contenedor (ERROR CONCEPTUAL GRAVE).** Nunca dejar que los logs caigan en `catalina.out`, `localhost.log`, `stdout` del servidor o cualquier archivo compartido entre todas las apps del Tomcat. El equipo debe tener archivos **únicos del proyecto** (ej. `paw-2026a-10.YYYY-MM-DD.log`, `paw-2026a-10-warnings.YYYY-MM-DD.log` en `webapp/logs/`). Sin `logback.xml` configurando un `FileAppender` propio, los logs se mezclan con los de otras apps y son imposibles de auditar — la cátedra lo marca como **error conceptual grave**.
- **Nunca usar salida estándar para loguear.** Prohibido `System.out.println`, `System.err.println` y `e.printStackTrace()`. Siempre `LOGGER.<level>(...)` de SLF4J. La salida estándar no respeta niveles, no rolla, no se filtra y termina en archivos genéricos del contenedor.
- **Prefijos / metadata en el template, no en cada llamada.** Cosas como timestamp, thread, logger name, nivel, sessionId, MDC keys → se configuran **una vez** en el `<encoder><pattern>` del `logback.xml`. NO concatenarlos manualmente en cada `LOGGER.info("...")`.

  ```xml
  <!-- BIEN — prefijo en el pattern -->
  <encoder>
      <pattern>%d{yyyy-MM-dd HH:mm:ss.SSS} [%thread] %-5level %logger{36} - %msg%n</pattern>
  </encoder>
  ```

  ```java
  // MAL — prefijo manual en cada log
  LOGGER.info("[" + new Date() + "] [" + Thread.currentThread().getName() + "] Rent created rentId=" + id);

  // BIEN — el pattern ya pone fecha y thread; el log solo dice qué pasó
  LOGGER.info("Rent created rentId={}", id);
  ```

- **Rolling appender obligatorio para no acumular logs infinitos.** El `FileAppender` debe ser `RollingFileAppender` con `TimeBasedRollingPolicy` (rotación diaria) o `SizeAndTimeBasedRollingPolicy`, y un `maxHistory` razonable (ej. 7-30 días) para que los archivos viejos se borren solos. Pensar el deploy: la ubicación (`webapp/logs/`, `/var/log/paw-2026a-10/`, etc.) tiene que ser **fácilmente accesible** al equipo en el server real, con permisos de lectura, y los nombres deben llevar el prefijo del proyecto para distinguirlos de otros despliegues.

  ```xml
  <appender name="APP_FILE" class="ch.qos.logback.core.rolling.RollingFileAppender">
      <file>${LOG_DIR}/paw-2026a-10.log</file>
      <rollingPolicy class="ch.qos.logback.core.rolling.TimeBasedRollingPolicy">
          <fileNamePattern>${LOG_DIR}/paw-2026a-10.%d{yyyy-MM-dd}.log</fileNamePattern>
          <maxHistory>7</maxHistory>
      </rollingPolicy>
      <encoder>
          <pattern>%d{yyyy-MM-dd HH:mm:ss.SSS} [%thread] %-5level %logger{36} - %msg%n</pattern>
      </encoder>
  </appender>
  ```
