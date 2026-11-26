"""Contratos de Web Push: claves VAPID, cifrado RFC 8291 y limpieza de suscripciones."""
import base64
import json
import os
import unittest
from unittest.mock import MagicMock, patch

import http_ece
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from jose import jwt

from app.core.config import settings
from app.scripts.generate_vapid_keys import generate_vapid_keys
from app.services import web_push


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class FakeBrowser:
    """Simula las claves que genera `pushManager.subscribe()` en el navegador."""

    def __init__(self):
        self.private_key = ec.generate_private_key(ec.SECP256R1())
        self.auth = os.urandom(16)
        public = self.private_key.public_key().public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
        self.subscription = MagicMock(
            id="sub-1",
            endpoint="https://push.example.test/send/abc123",
            p256dh=_b64url(public),
            auth=_b64url(self.auth),
            failure_count=0,
        )

    def decrypt(self, body: bytes) -> dict:
        plaintext = http_ece.decrypt(body, private_key=self.private_key, auth_secret=self.auth,
            version="aes128gcm")
        return json.loads(plaintext)


class WebPushTests(unittest.TestCase):
    def setUp(self):
        self.previous = (settings.VAPID_PUBLIC_KEY, settings.VAPID_PRIVATE_KEY, settings.VAPID_SUBJECT)
        settings.VAPID_PUBLIC_KEY, settings.VAPID_PRIVATE_KEY = generate_vapid_keys()
        settings.VAPID_SUBJECT = "mailto:soporte@example.com"
        self.browser = FakeBrowser()
        self.db = MagicMock()

    def tearDown(self):
        settings.VAPID_PUBLIC_KEY, settings.VAPID_PRIVATE_KEY, settings.VAPID_SUBJECT = self.previous

    def _send(self, status_code: int):
        response = MagicMock(status_code=status_code, text="", headers={})
        with patch("pywebpush.requests.post", return_value=response) as post:
            outcome = web_push.send_to_subscription(self.db, self.browser.subscription,
                {"title": "Actividad vencida", "body": "Llamar a ACME", "url": "/panel/actividades"},
                urgency="high")
        return outcome, post

    def test_generated_vapid_keys_have_web_push_format(self):
        public_key, private_key = generate_vapid_keys()
        self.assertEqual(len(_b64url_decode(public_key)), 65)
        self.assertEqual(_b64url_decode(public_key)[0], 0x04)
        self.assertEqual(len(_b64url_decode(private_key)), 32)

    def test_payload_is_encrypted_for_the_browser_and_signed_with_vapid(self):
        outcome, post = self._send(201)
        self.assertEqual(outcome, "delivered")
        self.assertEqual(self.browser.subscription.failure_count, 0)

        args, kwargs = post.call_args
        self.assertEqual(args[0], self.browser.subscription.endpoint)
        headers = kwargs["headers"]
        self.assertEqual(headers["content-encoding"], "aes128gcm")
        self.assertEqual(headers["Urgency"], "high")
        self.assertEqual(headers["ttl"], str(settings.PUSH_TTL_SECONDS))

        # El navegador (y solo él) puede descifrar el contenido.
        self.assertEqual(self.browser.decrypt(kwargs["data"])["body"], "Llamar a ACME")

        # Cabecera VAPID: vapid t=<JWT ES256>, k=<clave pública del servidor>.
        authorization = headers["authorization"]
        self.assertTrue(authorization.startswith("vapid t="))
        token = authorization.split("t=", 1)[1].split(",", 1)[0]
        key = authorization.split("k=", 1)[1].strip()
        self.assertEqual(key, settings.VAPID_PUBLIC_KEY)
        claims = jwt.get_unverified_claims(token)
        self.assertEqual(claims["aud"], "https://push.example.test")
        self.assertEqual(claims["sub"], "mailto:soporte@example.com")
        self.assertEqual(jwt.get_unverified_header(token)["alg"], "ES256")

    def test_expired_subscription_is_removed(self):
        outcome, _ = self._send(410)
        self.assertEqual(outcome, "removed")
        self.db.delete.assert_called_once_with(self.browser.subscription)

    def test_temporary_failure_is_counted(self):
        outcome, _ = self._send(500)
        self.assertEqual(outcome, "failed")
        self.assertEqual(self.browser.subscription.failure_count, 1)
        self.db.delete.assert_not_called()

    def test_nothing_is_sent_without_vapid_keys(self):
        settings.VAPID_PRIVATE_KEY = None
        with patch("pywebpush.requests.post") as post:
            outcome = web_push.send_to_subscription(self.db, self.browser.subscription, {"title": "x"})
        self.assertEqual(outcome, "failed")
        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
