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

Servicios:

- Aplicación a través de Nginx: `http://localhost`
- Frontend directo: `http://localhost:4200`
- Backend directo: `http://localhost:8000/health`
- Swagger: `http://localhost/docs`

No se deben subir archivos `.env`, credenciales, `node_modules`, cachés de Python ni datos locales de PostgreSQL.
