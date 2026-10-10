from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class Room:
    id: str
    slug: str
    title: str
    tier: str
    commands: List[str]
    mission: str
    hint: str
    salt: str
    hash: str
    path: Path = field(default_factory=Path)

    @property
    def image_tag(self) -> str:
        return f"linux-ctf-level{self.id}:latest"

    @property
    def container_name(self) -> str:
        return f"linux-ctf-room-{self.id}"

    @property
    def containerfile_path(self) -> Path:
        return self.path / "Containerfile"

    @property
    def setup_script_path(self) -> Path:
        return self.path / "setup.sh"

    @property
    def metadata_path(self) -> Path:
        return self.path / "metadata.json"
