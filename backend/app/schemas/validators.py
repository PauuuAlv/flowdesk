import re


def validate_password_strength(password: str) -> str:
    """Lanza ValueError si no cumple; Pydantic convierte eso en un 422
    automáticamente con un mensaje claro para el frontend."""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one number")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\/;'`~]", password):
        raise ValueError("Password must contain at least one special character")
    return password
