from app import passwords


def test_hash_and_verify_roundtrip():
    h = passwords.hash_password("supersecret")
    assert h.startswith("pbkdf2_sha256$")
    assert passwords.verify_password("supersecret", h) is True
    assert passwords.verify_password("wrong", h) is False


def test_salt_is_unique_per_hash():
    assert passwords.hash_password("same") != passwords.hash_password("same")


def test_verify_rejects_garbage():
    assert passwords.verify_password("x", "") is False
    assert passwords.verify_password("x", "not-a-valid-hash") is False
    assert passwords.verify_password("x", None) is False
