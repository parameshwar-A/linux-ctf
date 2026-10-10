from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from linux_ctf.models import Room

logger = logging.getLogger(__name__)


def find_project_root() -> Path:
    """Finds the root directory containing the rooms/ folder."""
    current = Path(__file__).resolve().parent
    for parent in [current, *current.parents]:
        if (parent / "rooms").is_dir() and (parent / "common").is_dir():
            return parent
    return Path.cwd()


class RoomRegistry:
    def __init__(self, rooms_dir: Optional[Path] = None):
        self.project_root = find_project_root()
        self.rooms_dir = rooms_dir or (self.project_root / "rooms")
        self._rooms: Dict[str, Room] = {}
        self.load_rooms()

    def load_rooms(self) -> None:
        """Discovers and parses all room metadata from rooms/ or bundled manifest."""
        self._rooms.clear()

        # Try loading from local rooms/ directory (author / dev mode)
        if self.rooms_dir.exists():
            for room_path in sorted(self.rooms_dir.glob("level*")):
                if not room_path.is_dir():
                    continue

                metadata_file = room_path / "metadata.json"
                if not metadata_file.is_file():
                    continue

                try:
                    with open(metadata_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    room = Room(
                        id=str(data.get("id", "")).zfill(2),
                        slug=data.get("slug", room_path.name),
                        title=data.get("title", "Untitled Room"),
                        tier=data.get("tier", "Beginner"),
                        commands=data.get("commands", []),
                        mission=data.get("mission", ""),
                        hint=data.get("hint", ""),
                        salt=data.get("salt", ""),
                        hash=data.get("hash", ""),
                        path=room_path,
                    )
                    self._rooms[room.id] = room
                except Exception as e:
                    logger.error(f"Failed to load room at {room_path}: {e}")

        # If no rooms loaded from filesystem, fallback to bundled curriculum manifest
        if not self._rooms:
            manifest = Path(__file__).resolve().parent.parent / "data" / "rooms.json"
            if manifest.is_file():
                try:
                    with open(manifest, "r", encoding="utf-8") as f:
                        items = json.load(f)
                    for data in items:
                        room = Room(
                            id=str(data.get("id", "")).zfill(2),
                            slug=data.get("slug", f"level{data.get('id', '')}"),
                            title=data.get("title", "Untitled Room"),
                            tier=data.get("tier", "Beginner"),
                            commands=data.get("commands", []),
                            mission=data.get("mission", ""),
                            hint=data.get("hint", ""),
                            salt="",
                            hash="",
                            path=Path(""),
                        )
                        self._rooms[room.id] = room
                except Exception as e:
                    logger.error(f"Failed to load bundled manifest at {manifest}: {e}")

    def list_rooms(self) -> List[Room]:
        """Returns all loaded rooms sorted by ID."""
        return sorted(self._rooms.values(), key=lambda r: int(r.id) if r.id.isdigit() else 999)

    def get_room(self, identifier: str) -> Optional[Room]:
        """Fetches room by ID or slug (e.g., '01', '1', 'level01')."""
        clean_id = identifier.strip().lower()
        if clean_id.startswith("level"):
            clean_id = clean_id[5:]
        if clean_id.isdigit():
            clean_id = clean_id.zfill(2)

        if clean_id in self._rooms:
            return self._rooms[clean_id]

        for room in self._rooms.values():
            if room.slug.lower() == identifier.lower():
                return room
        return None
