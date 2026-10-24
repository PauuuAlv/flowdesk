# Despliegue de Flowdesk

Esta guía prepara una versión de prueba sin modificar `main` ni `dev`. La rama de trabajo es
`preview/fullstack`.

En desarrollo local, PostgreSQL se publica en el puerto `5433` para no interferir con el proyecto
Urbanik, que utiliza `5432`. Dentro de la red de Docker, Flowdesk continúa conectándose a
`postgres:5432`.

## 1. Backend y PostgreSQL en Render

El archivo `render.yaml` de la raíz define un Blueprint con:

- PostgreSQL 16 gratuito llamado `flowdesk-preview-db`;
- servicio Docker gratuito llamado `flowdesk-preview-api`;
- región `ohio` para ambos servicios;
- rama `preview/fullstack`;
- directorio raíz `backend`;
- healthcheck `/health`;
- conexión automática entre FastAPI y PostgreSQL.

Pasos:

1. En Render, crear un **Blueprint** desde `PauuuAlv/flowdesk`.
2. Seleccionar la rama `preview/fullstack` y el archivo `render.yaml`.
3. Capturar las variables marcadas como secretas.
4. Revisar que ambos recursos utilicen el plan gratuito antes de confirmar.

Variables requeridas en el servicio backend:

```text
SUPERADMIN_EMAIL=<correo de administración para el ambiente de prueba>
SUPERADMIN_PASSWORD=<contraseña segura exclusiva del ambiente de prueba>
CORS_ORIGINS=["https://DOMINIO-DE-VERCEL"]
FRONTEND_URL=https://DOMINIO-DE-VERCEL
```

La conexión de la base y `JWT_SECRET_KEY` se generan automáticamente. No copies `.env` a Render
ni publiques credenciales en Git. Las demás variables se capturan en el panel de Render.

El contenedor ejecuta automáticamente `alembic upgrade head` y el seed idempotente antes de iniciar
FastAPI. Si el superadministrador ya existe, no lo crea nuevamente.

El plan gratuito de PostgreSQL en Render expira 30 días después de crearse, no incluye respaldos y
es exclusivamente para esta vista previa. Para conservar datos reales debe actualizarse a un plan
de pago antes del vencimiento.

## 2. Frontend en Vercel

La URL pública del backend debe existir antes de conectar el frontend.

1. Importar el mismo repositorio en Vercel.
2. Seleccionar la rama `preview/fullstack` para el ambiente de prueba.
3. Configurar **Root Directory** como `frontend/app`.
4. La configuración de `frontend/app/vercel.ts` establece automáticamente:
   - comando de compilación: `npm run build`;
   - directorio de salida: `dist/app/browser`;
   - enrutamiento de Angular para permitir recargas en rutas internas;
   - proxy de `/api/*` hacia el backend.
5. Crear la variable `FLOWDESK_BACKEND_URL` con el origen público de Render, sin `/api` y sin
   diagonal final. Ejemplo: `https://flowdesk-preview-api.onrender.com`.

Mientras `FLOWDESK_BACKEND_URL` no esté configurada, Vercel utilizará el dominio reservado
`https://backend-pendiente.invalid`. Las pantallas y rutas de Angular se pueden revisar, pero las
operaciones que llaman a la API fallarán de forma esperada hasta colocar la URL real.

## 3. Validación antes de integrar

- Confirmar `GET /health` en Render.
- Probar inicio de sesión del superadministrador.
- Crear una empresa y generar una invitación.
- Aceptar la invitación y acceder al panel del tenant.
- Probar renovación y expiración de sesión.
- Probar recarga directa de las rutas de Angular.
- Confirmar que las credenciales y tokens no estén versionados.

Una vez validado el ambiente de prueba, se revisarán los cambios antes de llevarlos primero a
`dev` y posteriormente a `main`.
