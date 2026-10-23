from __future__ import annotations
import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass


@dataclass
class SessionSecret:
    room_id: str
    flag: str
    salt: str
    expected_hash: str
    created_at: float = 0.0

    def verify(self, submitted_flag: str) -> bool:
        clean_input = submitted_flag.strip()
        salted_str = f"{clean_input}::{self.salt}"
        computed_hash = hashlib.sha256(salted_str.encode("utf-8")).hexdigest()
        return hmac.compare_digest(computed_hash.lower(), self.expected_hash.lower())


def generate_session_secret(room_id: str) -> SessionSecret:
    """Generates an ephemeral, cryptographically random flag and salted hash."""
    clean_id = str(room_id).zfill(2)
    token = secrets.token_hex(16)
    flag = f"FLAG{{l{clean_id}_{token}}}"
    salt = secrets.token_hex(16)
    salted_str = f"{flag}::{salt}"
    expected_hash = hashlib.sha256(salted_str.encode("utf-8")).hexdigest()

    return SessionSecret(
        room_id=clean_id,
        flag=flag,
        salt=salt,
        expected_hash=expected_hash,
        created_at=time.time(),
    )
