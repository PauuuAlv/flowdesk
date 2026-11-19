# Frontend de Flowdesk

Aplicación web de Flowdesk desarrollada con Angular 20 y componentes
independientes. Consume la API mediante rutas relativas bajo `/api` para
funcionar de la misma manera en Docker y en los ambientes publicados.

## Funcionalidades

- Inicio de sesión para usuarios y superadministradores.
- Activación de cuentas por invitación.
- Recuperación y restablecimiento de contraseña.
- Navegación protegida por sesión y permisos.
- Paneles de administración SaaS y operación por empresa.
- Interfaces responsivas para los módulos comerciales.

## Ejecución local

Desde `frontend/app`:

```powershell
npm install
npm start
```

El servidor de desarrollo utiliza `proxy.conf.json` para dirigir `/api` al
backend local.

## Comandos

```powershell
# Pruebas unitarias
npm test -- --watch=false

# Compilación de producción
npm run build
```

## Organización

- `core/models`: contratos TypeScript.
- `core/services`: comunicación con la API y manejo de sesión.
- `core/guards`: protección de rutas por autenticación y permisos.
- `core/interceptors`: incorporación del token en las peticiones.
- `features`: pantallas agrupadas por dominio funcional.
- `layout`: estructura de navegación del panel de empresa.
