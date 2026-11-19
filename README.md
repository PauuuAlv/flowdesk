# Flowdesk

Flowdesk es un CRM SaaS multiempresa para administrar clientes, oportunidades,
actividades, productos, cotizaciones, usuarios, roles y configuración comercial
desde una sola plataforma.

## Tecnologías

- Angular 20 para la aplicación web.
- FastAPI 0.115 para la API REST.
- PostgreSQL 16 para persistencia.
- Nginx como puerta de entrada en el entorno Docker.
- Docker Compose para el ambiente local.
- Vercel y Render para la vista previa publicada.

## Estructura

```text
flowdesk/
├── backend/       API, modelos, migraciones y pruebas
├── frontend/      aplicación Angular
├── nginx/         configuración del proxy inverso
├── docs/          contratos y documentación técnica
├── compose.yml   servicios del entorno local
└── render.yaml   infraestructura de vista previa
```

## Módulos disponibles

- Autenticación, recuperación de contraseña e invitaciones.
- Administración SaaS de empresas, planes y suscripciones.
- Usuarios, roles y permisos por empresa.
- Dashboard comercial.
- Clientes y oportunidades.
- Actividades de seguimiento.
- Productos y servicios.
- Cotizaciones con exportación a PDF.
- Configuración de empresa y perfil.

## Desarrollo local

### Requisitos

- Docker Desktop.
- Git.

### Configuración

1. Copiar `.env.example` como `.env`.
2. Sustituir los valores de ejemplo por credenciales exclusivamente locales.
3. Iniciar el ambiente desde la raíz:

```powershell
docker compose up --build
```

La aplicación queda disponible en `http://localhost`.

| Recurso | Dirección |
| --- | --- |
| Aplicación | `http://localhost` |
| Estado de la API | `http://localhost/health` |
| Swagger | `http://localhost/docs` |

## Pruebas

Backend:

```powershell
docker compose exec -T backend pytest -q
```

Frontend:

```powershell
cd frontend/app
npm test -- --watch=false
npm run build
```

## Seguridad

- Las cuentas se activan mediante invitaciones personales y de un solo uso.
- El aislamiento de información se realiza por `tenant_id` obtenido del token.
- Los permisos se validan tanto en el frontend como en la API.
- Los secretos se configuran mediante variables de entorno.
- Los archivos `.env`, datos locales y dependencias no se versionan.

## Documentación

- [Contrato de autenticación](docs/api/auth-endpoints.md)
- [Configuración de despliegue](DEPLOYMENT.md)
- [Backend](backend/README.md)
- [Frontend](frontend/app/README.md)
