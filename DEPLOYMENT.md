# Despliegue de Flowdesk

Esta guía prepara una versión de prueba sin modificar `main` ni `dev`. La rama de trabajo es
`preview/fullstack`.

## 1. Backend y PostgreSQL en Railway

1. Crear un proyecto vacío en Railway.
2. Agregar una base PostgreSQL administrada.
3. Agregar un servicio desde el repositorio `PauuuAlv/flowdesk`.
4. Seleccionar la rama `preview/fullstack`.
5. Configurar **Root Directory** como `/backend`.
6. Railway detectará `backend/Dockerfile`. El servidor escucha el puerto asignado mediante
   la variable `PORT`.
7. Configurar el healthcheck en `/health` y generar un dominio público.

Variables requeridas en el servicio backend:

```text
SQLALCHEMY_DATABASE_URL=<referencia a DATABASE_URL de PostgreSQL>
JWT_SECRET_KEY=<valor aleatorio largo y secreto>
SUPERADMIN_EMAIL=<correo de administración para el ambiente de prueba>
SUPERADMIN_PASSWORD=<contraseña segura exclusiva del ambiente de prueba>
CORS_ORIGINS=["https://DOMINIO-DE-VERCEL"]
FRONTEND_URL=https://DOMINIO-DE-VERCEL
```

No copies `.env` a Railway ni publiques credenciales en Git. Las variables se capturan en el
panel de Railway.

Antes del primer inicio funcional, ejecutar en el servicio backend:

```text
alembic upgrade head
python -m app.scripts.seed_superadmin
```

Ambos comandos deben ejecutarse con las variables de Railway disponibles. El seed es idempotente:
si el superadministrador ya existe, no lo crea nuevamente.

## 2. Frontend en Vercel

La URL pública del backend debe existir antes de conectar el frontend.

1. Importar el mismo repositorio en Vercel.
2. Seleccionar la rama `preview/fullstack` para el ambiente de prueba.
3. Configurar **Root Directory** como `frontend/app`.
4. Usar `npm run build` como comando de compilación.
5. Usar `dist/app/browser` como directorio de salida.
6. Configurar el enrutamiento SPA y la comunicación con la URL pública de Railway.

El paso 6 se completará cuando Railway entregue el dominio real. Así evitamos guardar una URL
inventada o temporal directamente en el código.

## 3. Validación antes de integrar

- Confirmar `GET /health` en Railway.
- Probar inicio de sesión del superadministrador.
- Crear una empresa y generar una invitación.
- Aceptar la invitación y acceder al panel del tenant.
- Probar renovación y expiración de sesión.
- Probar recarga directa de las rutas de Angular.
- Confirmar que las credenciales y tokens no estén versionados.

Una vez validado el ambiente de prueba, se revisarán los cambios antes de llevarlos primero a
`dev` y posteriormente a `main`.
