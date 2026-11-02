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

En modo `development` no se envía ningún correo. Los enlaces de invitación y
recuperación se escriben en los logs del backend para poder probarlos localmente:

```powershell
docker compose logs -f backend
```

Las claves reales del futuro proveedor deberán configurarse únicamente como
variables de entorno y nunca guardarse en Git.
