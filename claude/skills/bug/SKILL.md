---
name: bug
description: Ledger de bugs del proyecto en 0_Plans/BUGS.md — registra un bug reportado por el usuario (síntoma verbatim, superficie, intentos fallidos, estado) o actualiza uno existente si es re-reporte. Usar cuando el usuario reporta un síntoma/bug, cuando dice "sigue pasando X", o al fixear un bug para marcarlo FIXED. Un bug se describe UNA sola vez.
argument-hint: [descripción del bug, o "fixed BUG-NN <hash>" para cerrar uno]
allowed-tools: [Read, Glob, Grep, Edit, Write, Bash]
---

Mantenés el ledger de bugs de **Rent The Slopes** en `0_Plans/BUGS.md`. Existe porque el mismo bug llegó a re-tipearse 3-4 veces en sesiones distintas (cluster C10 de `0_Plans/claude-harness/AUDIT_friccion-sesiones-claude.md`) — cada re-reporte perdía los intentos fallidos anteriores.

## Proceso

1. **Leer `0_Plans/BUGS.md`** completo.

2. **Detectar si es re-reporte:** buscar en el ledger por keywords del síntoma (superficie, URL, mensaje de error). Si hay un bug ABIERTO/EN CURSO que matchea:
   - **NO pedir al usuario que re-explique.** Actualizar esa fila: sumar el nuevo dato/intento fallido a la columna "Intentos fallidos" y decirle al usuario qué se probó ya (para no repetir un fix que no anduvo).
   - Los intentos fallidos previos son la información más valiosa: si el fix anterior "no se ve", primero sospechar edit perdido / `target/` stale / sesión paralela (patrón real del audit) antes de re-diagnosticar de cero.

3. **Si es nuevo:** asignar el próximo `BUG-NN`, agregar fila con:
   - **Síntoma**: verbatim del usuario (citarlo, no parafrasearlo — es lo que él va a volver a escribir si re-reporta).
   - **Superficie**: URL/JSP/flujo concreto.
   - **Intentos fallidos**: vacío al crear; se va llenando.
   - **Estado**: `ABIERTO`.

4. **Al fixear** (o si invocan `fixed BUG-NN <hash>`): estado → `FIXED` + hash del commit. Si un bug se descarta (era dato de la BD dev, no código), estado → `DESCARTADO` + motivo en una frase.

5. Mantener la tabla ordenada por ID. No borrar filas nunca — el historial de DESCARTADOS también evita re-investigaciones.

## Regla para toda sesión de fix (aunque no invoquen este skill)

Si el usuario reporta un síntoma que suena conocido, grep en `0_Plans/BUGS.md` ANTES de diagnosticar. Está en las "Reglas operativas de sesión" de `CLAUDE.md`.
