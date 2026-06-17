import base64
import hashlib
import hmac
import os


_PBKDF2_ROUNDS = 200_000


def _b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64d(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


def _derive_key(master_key: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256",
        master_key.encode("utf-8"),
        salt,
        _PBKDF2_ROUNDS,
        dklen=32,
    )


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        block = hmac.new(
            key,
            nonce + counter.to_bytes(4, "big"),
            hashlib.sha256,
        ).digest()
        out.extend(block)
        counter += 1
    return bytes(out[:length])


def _xor_bytes(left: bytes, right: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(left, right))


def encrypt_secret(plain_text: str, master_key: str) -> str:
    if not isinstance(plain_text, str) or plain_text == "":
        raise ValueError("plain_text must be a non-empty string")
    if not isinstance(master_key, str) or master_key == "":
        raise ValueError("master_key must be a non-empty string")

    salt = os.urandom(16)
    nonce = os.urandom(16)
    key = _derive_key(master_key, salt)
    raw = plain_text.encode("utf-8")
    cipher = _xor_bytes(raw, _keystream(key, nonce, len(raw)))
    mac = hmac.new(key, b"v1" + salt + nonce + cipher, hashlib.sha256).digest()
    return f"v1.{_b64e(salt)}.{_b64e(nonce)}.{_b64e(cipher)}.{_b64e(mac)}"


def decrypt_secret(cipher_text: str, master_key: str) -> str:
    if not isinstance(cipher_text, str) or cipher_text == "":
        raise ValueError("cipher_text must be a non-empty string")
    if not isinstance(master_key, str) or master_key == "":
        raise ValueError("master_key must be a non-empty string")

    parts = cipher_text.split(".")
    if len(parts) != 5 or parts[0] != "v1":
        raise ValueError("invalid encrypted format")

    salt = _b64d(parts[1])
    nonce = _b64d(parts[2])
    cipher = _b64d(parts[3])
    mac = _b64d(parts[4])
    key = _derive_key(master_key, salt)
    expected = hmac.new(key, b"v1" + salt + nonce + cipher, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expected):
        raise ValueError("invalid master key or corrupted encrypted value")
    raw = _xor_bytes(cipher, _keystream(key, nonce, len(cipher)))
    return raw.decode("utf-8")


def resolve_secret(name: str, value: str) -> str:
    env_override = os.getenv(name, "").strip()
    if env_override:
        return env_override

    if isinstance(value, str) and value.startswith("ENC(") and value.endswith(")"):
        encrypted = value[4:-1]
        master_key = os.getenv("TRADING_MASTER_KEY", "").strip()
        if not master_key:
            raise RuntimeError(
                f"{name} is encrypted but TRADING_MASTER_KEY is not set."
            )
        return decrypt_secret(encrypted, master_key)
    return value
