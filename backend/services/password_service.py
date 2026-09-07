import base64
import hmac

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from werkzeug.security import check_password_hash, generate_password_hash


class PasswordService:
    """Use Werkzeug's maintained password implementation for new passwords.

    The legacy parser only exists for the deterministic Phase 2.2a fixtures,
    whose hashes were generated before the application had a password service.
    The cryptographic operation itself remains delegated to cryptography.
    """

    @staticmethod
    def hash_password(password: str) -> str:
        return generate_password_hash(password, method="scrypt")

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        if not isinstance(password, str) or not isinstance(password_hash, str):
            return False
        try:
            if password_hash.startswith("pbkdf2_sha256$"):
                return PasswordService._verify_legacy_fixture(password, password_hash)
            return check_password_hash(password_hash, password)
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _verify_legacy_fixture(password: str, encoded: str) -> bool:
        parts = encoded.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = base64.urlsafe_b64decode(parts[2] + "=" * (-len(parts[2]) % 4))
        expected = base64.urlsafe_b64decode(parts[3] + "=" * (-len(parts[3]) % 4))
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=len(expected),
            salt=salt,
            iterations=iterations,
        )
        derived = kdf.derive(password.encode("utf-8"))
        return hmac.compare_digest(derived, expected)
