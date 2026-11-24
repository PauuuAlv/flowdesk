import unittest

from pydantic import ValidationError

from app.schemas.auth import ChangePasswordRequest, RegisterRequest, ResetPasswordRequest
from app.schemas.platform_admin import (
    AcceptPlatformInvitationRequest,
    ChangePlatformPasswordRequest,
    PlatformResetPasswordRequest,
)

STRONG = "Segura#2026"
# Cada una incumple exactamente una regla.
WEAK = ["Cort#1", "minuscula#2026", "MAYUSCULA#2026", "SinNumero#", "SinSimbolo2026"]

# (esquema, datos base sin la contraseña, campo de la contraseña)
CASES = [
    (RegisterRequest, {"token": "t"}, "password"),
    (ResetPasswordRequest, {"token": "t"}, "new_password"),
    (ChangePasswordRequest, {"current_password": "x"}, "new_password"),
    (AcceptPlatformInvitationRequest, {"token": "t"}, "password"),
    (PlatformResetPasswordRequest, {"token": "t"}, "new_password"),
    (ChangePlatformPasswordRequest, {"current_password": "x"}, "new_password"),
]


class PasswordPolicyContractTests(unittest.TestCase):
    """Toda contraseña que se define en el backend (invitación, recuperación o
    cambio con sesión) exige las mismas reglas que valida el frontend."""

    def test_every_password_schema_accepts_a_strong_password(self):
        for schema, base, field in CASES:
            with self.subTest(schema=schema.__name__):
                schema(**base, **{field: STRONG})

    def test_every_password_schema_rejects_weak_passwords(self):
        for schema, base, field in CASES:
            for weak in WEAK:
                with self.subTest(schema=schema.__name__, password=weak):
                    with self.assertRaises(ValidationError):
                        schema(**base, **{field: weak})


if __name__ == "__main__":
    unittest.main()
