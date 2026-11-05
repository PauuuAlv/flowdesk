# flowdesk_backend
Backend de Flowdesk, un CRM desarollado para ARMsystem con FastAPI y postgreSQL

## Correo transaccional

Los endpoints dependen del contrato `EmailService`, por lo que no conocen al
proveedor final. Mientras se define si producción utilizará Resend o Amazon SES,
el valor predeterminado es:

```env
EMAIL_PROVIDER=development
EMAIL_FROM_ADDRESS=no-reply@flowdesk.local
EMAIL_FROM_NAME=Flowdesk
```

Para enviar correos mediante Gmail SMTP, activa la verificación en dos pasos y
crea una contraseña de aplicación. La contraseña principal de Google no se usa:

```env
EMAIL_PROVIDER=smtp
EMAIL_FROM_ADDRESS=flowdesk03@gmail.com
EMAIL_FROM_NAME=Flowdesk
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=flowdesk03@gmail.com
SMTP_PASSWORD=<contraseña-de-aplicación>
SMTP_USE_TLS=true
```

`SMTP_PASSWORD` es un secreto: debe existir solo en `.env` o en las variables
protegidas del proveedor de despliegue y nunca debe subirse al repositorio.

En servicios que bloquean los puertos SMTP, como el plan gratuito de Render, se
puede utilizar la API HTTPS de Resend:

```env
EMAIL_PROVIDER=resend
EMAIL_FROM_ADDRESS=no-reply@flowdesk.armsystem.com.mx
EMAIL_FROM_NAME=Flowdesk
RESEND_API_KEY=<clave-con-permiso-solo-de-envío>
RESEND_API_URL=https://api.resend.com/emails
```

El dominio del remitente debe estar verificado en Resend. `RESEND_API_KEY` debe
guardarse únicamente como secreto local o del proveedor de despliegue.

En modo `development` no se envía ningún correo. Los enlaces de invitación y
recuperación se escriben en los logs del backend para poder probarlos localmente:

```powershell
docker compose logs -f backend
```

Las claves reales del futuro proveedor deberán configurarse únicamente como
variables de entorno y nunca guardarse en Git.
