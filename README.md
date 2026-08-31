# Flowdesk

CRM SaaS multiempresa para centralizar el ciclo comercial, operativo y financiero de ArmSystem.

## Estructura

- `frontend/`: aplicación Angular.
- `backend/`: API FastAPI.
- `nginx/`: proxy inverso para unificar frontend y API.
- `compose.yml`: PostgreSQL 16 Alpine, backend, frontend y Nginx.

## Desarrollo local con Docker

1. Copiar `.env.example` como `.env` y usar valores únicamente locales.
2. Iniciar Docker Desktop.
3. Ejecutar `docker compose up --build` desde la raíz.

Servicios expuestos mediante Nginx:

- Aplicación a través de Nginx: `http://localhost`
- Estado del backend: `http://localhost/api/health`
- Swagger: `http://localhost/docs`

El frontend, backend y PostgreSQL permanecen dentro de la red Docker y no publican sus puertos directamente en Windows.

No se deben subir archivos `.env`, credenciales, `node_modules`, cachés de Python ni datos locales de PostgreSQL.
