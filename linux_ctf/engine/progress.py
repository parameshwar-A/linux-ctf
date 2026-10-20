from __future__ import annotations
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Set


def get_default_progress_path() -> Path:
    """Returns the default path to the local completion tracking file."""
    custom_path = os.environ.get("LINUX_CTF_PROGRESS_FILE")
    if custom_path:
        return Path(custom_path)

    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        base_dir = Path(xdg_config) / "linux_ctf"
    else:
        base_dir = Path.home() / ".config" / "linux_ctf"

    return base_dir / "progress.json"


class ProgressTracker:
    """Manages persistent room completion status for local Linux CTF play."""

    def __init__(self, storage_path: Optional[Path] = None, progress_file: Optional[Path] = None) -> None:
        self.storage_path = storage_path or progress_file or get_default_progress_path()
        self._data: Dict[str, Any] = self._load()

    def _normalize_id(self, room_id: str) -> str:
        clean = room_id.lower().replace("level", "").strip()
        try:
            return f"{int(clean):02d}"
        except ValueError:
            return room_id.strip()

    def _load(self) -> Dict[str, Any]:
        if not self.storage_path.exists():
            return {"version": 1, "completed_rooms": {}}
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    return {"version": 1, "completed_rooms": {}}
                if "completed_rooms" not in data:
                    data["completed_rooms"] = {}
                return data
        except Exception:
            return {"version": 1, "completed_rooms": {}}

    def _save(self) -> None:
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self.storage_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
            temp_path.replace(self.storage_path)
        except Exception:
            # Non-fatal if filesystem is temporarily read-only
            pass

    def is_completed(self, room_id: str) -> bool:
        """Returns True if the specified room has been successfully solved."""
        norm_id = self._normalize_id(room_id)
        return norm_id in self._data.get("completed_rooms", {})

    def mark_completed(self, room_id: str, title: str = "") -> bool:
        """Marks a room as completed with timestamp. Returns True if newly solved."""
        norm_id = self._normalize_id(room_id)
        completed = self._data.setdefault("completed_rooms", {})
        is_new = norm_id not in completed

        completed[norm_id] = {
            "completed_at": datetime.now().isoformat(),
            "title": title,
        }
        self._save()
        return is_new

    def get_completed_ids(self) -> Set[str]:
        """Returns set of all completed room IDs."""
        return set(self._data.get("completed_rooms", {}).keys())

    def get_completed_count(self) -> int:
        """Returns total count of completed rooms."""
        return len(self.get_completed_ids())

    def get_completion_date(self, room_id: str) -> Optional[str]:
        """Returns the ISO timestamp when the room was solved, or None."""
        norm_id = self._normalize_id(room_id)
        info = self._data.get("completed_rooms", {}).get(norm_id)
        return info.get("completed_at") if isinstance(info, dict) else None

    def get_room_status(self, room_id: str) -> Optional[Dict[str, Any]]:
        """Returns details of a completed room (completed_at, title), or None."""
        norm_id = self._normalize_id(room_id)
        info = self._data.get("completed_rooms", {}).get(norm_id)
        return dict(info) if isinstance(info, dict) else None

    def get_summary(self, total_rooms: int) -> Dict[str, Any]:
        """Returns a high-level completion statistics dictionary."""
        completed_count = self.get_completed_count()
        percent = (completed_count / total_rooms * 100.0) if total_rooms > 0 else 0.0
        return {
            "completed": completed_count,
            "total": total_rooms,
            "percent": round(percent, 1),
        }

    def reset_room(self, room_id: str) -> bool:
        """Clears completion state for a single room."""
        norm_id = self._normalize_id(room_id)
        completed = self._data.get("completed_rooms", {})
        if norm_id in completed:
            del completed[norm_id]
            self._save()
            return True
        return False

    def reset_all(self) -> None:
        """Clears all completion records."""
        self._data["completed_rooms"] = {}
        self._save()
