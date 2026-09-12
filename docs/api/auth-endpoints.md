# Flowdesk API — Endpoints de Autenticación (Sprint 1)

## Tabla resumen

| Método | Endpoint | Quién lo usa | Requiere token | Para qué sirve |
|---|---|---|---|---|
| POST | `/api/platform-admin/auth/login` | ArmSystem (superadmin) | No | Login del PlatformAdmin |
| POST | `/api/platform-admin/tenants` | ArmSystem (superadmin) | Sí (PlatformAdmin) | Crear una empresa (tenant) nueva + su primer admin invitado |
| POST | `/api/auth/register` | Cualquier usuario invitado | No | Aceptar una invitación: define contraseña y activa la cuenta |
| POST | `/api/auth/login` | Usuario ya activo | No | Iniciar sesión normal |
| POST | `/api/auth/refresh` | Usuario ya logueado | No (usa refresh_token) | Renovar el access_token sin volver a pedir contraseña |
| GET | `/api/auth/me` | Usuario logueado | Sí (User) | Saber quién soy, mi rol, mi tenant |
| POST | `/api/users/invite` | Admin de un tenant | Sí (User, role=admin) | Invitar a alguien más dentro de tu propio tenant |
| POST | `/api/auth/forgot-password` | Cualquiera | No | Pedir un link para resetear contraseña |
| POST | `/api/auth/reset-password` | Quien tenga el link | No (usa token del link) | Definir una contraseña nueva |
| GET | `/health` | Nadie en particular | No | Confirmar que el backend está vivo |

---

## POST /api/platform-admin/auth/login

**Para qué sirve:** el superadmin de ArmSystem inicia sesión. Es un sistema de login completamente separado del de los usuarios normales.

**Pasos:**
1. Body: `{ "email": "admin@armsystem.com", "password": "..." }`
2. Ejecutar.
3. Guarda el `access_token` de la respuesta — lo vas a necesitar para el siguiente endpoint.

---

## POST /api/platform-admin/tenants

**Para qué sirve:** crea una empresa cliente nueva (tenant) y, de una vez, su primer usuario administrador (queda invitado, sin contraseña todavía).

**Pasos:**
1. Botón **Authorize** (candado) → pega `Bearer <access_token del superadmin>`.
2. Body:
```json
{
  "name": "Nombre de la empresa",
  "slug": "nombre-unico-url",
  "admin_email": "admin@laempresa.com",
  "admin_full_name": "Nombre del admin"
}
```
3. Ejecutar. La respuesta trae `dev_invitation_link` — cópialo, ahí viene el token que usa el siguiente endpoint.
4. Nota: `slug` debe ser único; si lo repites, da `409 Conflict`.

---

## POST /api/auth/register

**Para qué sirve:** el usuario invitado (el admin del tenant, o cualquiera invitado después) usa el link que recibió para definir su contraseña por primera vez. Al terminar, ya queda logueado (regresa tokens).

**Pasos:**
1. Del `dev_invitation_link` (algo como `http://localhost/accept-invite?token=XXXXX`), copia **solo** el valor después de `token=` — no la URL completa.
2. Body:
```json
{ "token": "XXXXX", "password": "unaPasswordDe8CaracteresOMas" }
```
3. Ejecutar. Guarda el `access_token`/`refresh_token` de la respuesta.
4. El token de invitación es de un solo uso: si lo vuelves a usar, da `400 Bad Request`.

---

## POST /api/auth/login

**Para qué sirve:** login normal para cualquier usuario ya activo (ya pasó por `/register` alguna vez).

**Pasos:**
1. Body: `{ "email": "...", "password": "..." }`
2. Ejecutar.
3. Si el usuario todavía está "invited" (no ha aceptado su invitación) o la contraseña está mal, da `401` con el mismo mensaje genérico en ambos casos (por seguridad, no revela cuál fue el problema).

---

## POST /api/auth/refresh

**Para qué sirve:** cuando el `access_token` expira (30 min), en vez de pedirle la contraseña de nuevo al usuario, el frontend manda el `refresh_token` (dura 7 días) y recibe un `access_token` nuevo.

**Pasos:**
1. Body: `{ "refresh_token": "el-que-guardaste-del-login" }`
2. Ejecutar. Recibes un `access_token` nuevo (el `refresh_token` se regresa igual, no cambia — no hay rotación todavía, ver nota de deuda técnica en el código).

---

## GET /api/auth/me

**Para qué sirve:** saber quién soy con solo mi token — el frontend lo usa típicamente al cargar la app, para mostrar tu nombre/rol y decidir qué mostrar en pantalla.

**Pasos:**
1. Botón **Authorize** → pega `Bearer <access_token>` de cualquier usuario activo.
2. Ejecutar (sin body). Regresa `id`, `tenant_id`, `email`, `full_name`, `role`, `status`.

---

## POST /api/users/invite

**Para qué sirve:** un admin de un tenant invita a alguien más dentro de **su propio** tenant (nunca de otro — el `tenant_id` sale del token, no del body).

**Pasos:**
1. Botón **Authorize** → pega `Bearer <access_token>` de un usuario con `role: "admin"`.
2. Body:
```json
{ "email": "nuevo@laempresa.com", "full_name": "Nombre", "role": "member" }
```
3. Ejecutar. Recibes `dev_invitation_link` para esa persona — con eso puede usar `/api/auth/register` igual que el primer admin.
4. Si el email ya existe en ese tenant, da `409 Conflict`. Si quien llama no es admin, da `403 Forbidden`.

---

## POST /api/auth/forgot-password

**Para qué sirve:** el usuario olvidó su contraseña y pide un link para resetearla.

**Pasos:**
1. Body: `{ "email": "..." }`
2. Ejecutar. Siempre responde el mismo mensaje genérico, exista o no el email (por seguridad).
3. Revisa `docker logs flowdesk-backend-1 --tail 5` — ahí aparece la línea `[DEV] Password reset link for ...` con el link (todavía no se envía por correo real).
4. Copia el token de esa URL (después de `token=`).

---

## POST /api/auth/reset-password

**Para qué sirve:** con el token del paso anterior, define una contraseña nueva.

**Pasos:**
1. Body: `{ "token": "el-del-log", "new_password": "unaNuevaDe8CaracteresOMas" }`
2. Ejecutar.
3. El token es de un solo uso y expira en 2 horas (`RESET_PASSWORD_TOKEN_EXPIRE_HOURS`).
4. Confirma con `/api/auth/login` usando la contraseña nueva.

---

## GET /health

**Para qué sirve:** confirmar que el backend está corriendo. No requiere nada, no hace nada de negocio — solo lo usa Docker/nginx/tú para monitoreo.

**Pasos:**
1. Ejecutar sin body ni auth.
2. Responde `{ "status": "ok" }`.