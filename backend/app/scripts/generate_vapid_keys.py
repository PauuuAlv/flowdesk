"""Genera un par de claves VAPID (ECDSA P-256) para Web Push.

    python -m app.scripts.generate_vapid_keys

Copia las dos líneas al `.env` (o a las variables del proveedor). La clave
privada es secreta; la pública se entrega al navegador. Si cambias el par,
las suscripciones existentes dejan de funcionar y cada usuario debe volver a
activar las notificaciones.
"""
import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def generate_vapid_keys() -> tuple[str, str]:
    """Devuelve (pública, privada) en base64url sin relleno.

    Pública: punto sin comprimir de 65 bytes (applicationServerKey del navegador).
    Privada: escalar de 32 bytes (formato aceptado por pywebpush/py_vapid).
    """
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_bytes = private_key.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    private_bytes = private_key.private_numbers().private_value.to_bytes(32, "big")
    return _b64url(public_bytes), _b64url(private_bytes)


if __name__ == "__main__":
    public_key, private_key = generate_vapid_keys()
    print(f"VAPID_PUBLIC_KEY={public_key}")
    print(f"VAPID_PRIVATE_KEY={private_key}")
