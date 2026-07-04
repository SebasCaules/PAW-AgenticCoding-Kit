---
name: smoke
description: Chequeo rápido de sanidad del proyecto (< 2 min, determinístico) — paridad i18n de los 4 bundles, versiones Flyway duplicadas, balance de tags JSTL en JSPs, y test-compile de todos los módulos. Usar antes de commit/push/entrega, después de un merge, o cuando el usuario pida "chequeo rápido" / "está todo sano". NO arregla nada — solo reporta.
argument-hint: [opcional: "i18n" | "flyway" | "jsp" para correr un solo check, o "--no-compile" para saltear el test-compile]
allowed-tools: [Read, Glob, Grep, Bash]
---

Corrés el smoke check del proyecto **Rent The Slopes**. Es un chequeo de SANIDAD, no una auditoría: rápido, determinístico, sin agentes.

## Regla dura

**Este skill NO arregla nada.** Reporta el estado y termina. Los fixes se hacen después, con confirmación del usuario — nunca en la misma pasada.

## Proceso

1. **Checks determinísticos** (segundos):
   ```bash
   python3 .claude/scripts/paw_checks.py all
   ```
   Si el usuario pasó un check puntual como argumento (`i18n`/`flyway`/`jsp`), correr solo ese.
   - `i18n`: paridad de keys entre `messages.properties` (default) y `_en`/`_fr` (`_es` hereda y puede estar vacío) + keys huérfanas.
   - `flyway`: versiones `V<nro>` duplicadas en `db/migration/` (rompen el boot) + warning si el `schema.sql` de test quedó más viejo que la última migración.
   - `jsp`: balance de `c:if`/`c:forEach`/`c:choose`/`c:when`/`c:otherwise`/`form:form` en views y tags (un tag desbalanceado = 500 en runtime que `mvn test` no atrapa).

2. **Test-compile de todos los módulos** (~1-2 min, saltear si pasaron `--no-compile`):
   ```bash
   mvn -q -pl webapp -am test-compile
   ```
   Compila main + tests de todos los módulos sin correr los tests.

3. **Si hubo cambios en `db/migration/` desde el último commit** (mirar `git status` / `git diff --name-only HEAD`):
   recordar la paridad del schema HSQLDB (`persistence/src/test/resources/schema.sql`, regla de `docs/testing.md`) y **emitir al usuario** el comando de boot para verificación real — NUNCA correrlo vos (regla del proyecto):
   ```
   cd webapp && mvn jetty:run
   ```

4. **Reporte final** — tabla compacta:

   | Check | Estado | Detalle |
   |---|---|---|
   | i18n | ✅/❌ | keys faltantes/huérfanas (si hay) |
   | flyway | ✅/❌/⚠️ | duplicados / warning de schema |
   | jsp | ✅/❌ | archivos con tags desbalanceados |
   | test-compile | ✅/❌ | primer error si falla |

   Si TODO da ✅: decirlo en una línea y terminar. Si algo da ❌: listar los problemas con archivo y detalle, y preguntar si arreglás — no arreglar de una.

## Contexto

Este skill existe porque "tests verdes ≠ la app anda" (cluster C7 de `0_Plans/claude-harness/AUDIT_friccion-sesiones-claude.md`): HSQLDB no ejercita Flyway ni PostgreSQL, y las keys i18n cojas y los JSPs desbalanceados solo explotan en runtime. `/pre-delivery` invoca estos mismos checks como fase 0.
