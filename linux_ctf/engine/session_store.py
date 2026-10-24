from __future__ import annotations
import json
import os
from pathlib import Path
import re
from typing import Optional
from linux_ctf.engine.secrets import SessionSecret


def get_default_sessions_dir() -> Path:
    """Returns the default directory for local session secret persistence."""
    custom = os.environ.get("LINUX_CTF_SESSIONS_DIR")
    if custom:
        return Path(custom)

    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        base_dir = Path(xdg_config) / "linux_ctf" / "sessions"
    else:
        base_dir = Path.home() / ".config" / "linux_ctf" / "sessions"

    return base_dir


class SessionStore:
    """Securely persists session tokens locally to enable offline CLI flag verification."""

    def __init__(self, sessions_dir: Optional[Path] = None):
        self.sessions_dir = sessions_dir or get_default_sessions_dir()
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        try:
            self.sessions_dir.mkdir(parents=True, exist_ok=True)
            # Restrict directory permissions to owner only (0700)
            os.chmod(self.sessions_dir, 0o700)
        except Exception:
            pass

    def _get_path(self, room_id: str) -> Path:
        raw_id = str(room_id).lower().replace("level", "").strip()
        clean_id = re.sub(r"[^0-9a-zA-Z_-]", "", raw_id).zfill(2)
        target = (self.sessions_dir / f"{clean_id}.json").resolve()
        if self.sessions_dir.resolve() not in target.parents:
            raise ValueError(f"Path traversal detected in room_id: {room_id!r}")
        return target

    def save(self, secret: SessionSecret) -> None:
        """Saves session secret to owner-only 0600 file."""
        self._ensure_dir()
        file_path = self._get_path(secret.room_id)
        temp_path = file_path.with_suffix(".tmp")
        data = {
            "room_id": secret.room_id,
            "salt": secret.salt,
            "expected_hash": secret.expected_hash,
            "created_at": secret.created_at,
        }
        try:
            fd = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            temp_path.replace(file_path)
        except Exception:
            pass

    def get(self, room_id: str) -> Optional[SessionSecret]:
        """Loads session secret for room if present."""
        file_path = self._get_path(room_id)
        if not file_path.is_file():
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return SessionSecret(
                room_id=data["room_id"],
                flag=data.get("flag", ""),
                salt=data["salt"],
                expected_hash=data["expected_hash"],
                created_at=data.get("created_at", 0.0),
            )
        except Exception:
            return None

    def remove(self, room_id: str) -> bool:
        """Removes session file for room."""
        file_path = self._get_path(room_id)
        try:
            if file_path.is_file():
                file_path.unlink()
                return True
        except Exception:
            pass
        return False

    def clear(self) -> None:
        """Clears all session files."""
        try:
            if self.sessions_dir.is_dir():
                for f in self.sessions_dir.glob("*.json"):
                    f.unlink()
        except Exception:
            pass
