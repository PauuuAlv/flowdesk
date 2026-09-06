import hashlib
import secrets


def generate_raw_token() -> str:
    """El valor que se manda por correo. Nunca se guarda en la base tal cual."""
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    """Lo que sí se guarda en la base (invitation_token_hash / token_hash).
    SHA-256 es suficiente aquí (a diferencia de un password, un token de invitación
    ya tiene alta entropía por sí mismo — no necesita bcrypt/argon2)."""
    return hashlib.sha256(raw_token.encode()).hexdigest()
