from backend.services.password_service import PasswordService


def test_password_hash_uses_salted_maintained_algorithm():
    first = PasswordService.hash_password("correct horse battery staple")
    second = PasswordService.hash_password("correct horse battery staple")

    assert first.startswith("scrypt:")
    assert second.startswith("scrypt:")
    assert first != second
    assert first != "correct horse battery staple"


def test_password_verification_accepts_only_the_correct_password():
    password_hash = PasswordService.hash_password("correct horse battery staple")

    assert PasswordService.verify_password("correct horse battery staple", password_hash)
    assert not PasswordService.verify_password("wrong password", password_hash)


def test_password_verification_rejects_malformed_hashes():
    assert not PasswordService.verify_password("anything", "not-a-password-hash")
    assert not PasswordService.verify_password("anything", "pbkdf2_sha256$broken")
