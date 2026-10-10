from __future__ import annotations
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple
from linux_ctf.models import Room
from linux_ctf.engine.rooms import find_project_root

logger = logging.getLogger(__name__)


class PodmanError(Exception):
    pass


class PodmanEngine:
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or find_project_root()
        self._ensure_podman_installed()

    def _ensure_podman_installed(self) -> None:
        if not shutil.which("podman"):
            raise PodmanError(
                "Podman is not installed or not found in system PATH. "
                "Please install podman to run Linux CTF labs."
            )

    def is_image_built(self, image_tag: str) -> bool:
        """Checks if an image exists locally in podman storage."""
        res = subprocess.run(
            ["podman", "image", "exists", image_tag],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return res.returncode == 0

    def build_base_image(self) -> Tuple[bool, str]:
        """Builds linux-ctf-base:latest from common/Containerfile.base."""
        containerfile = self.project_root / "common" / "Containerfile.base"
        if not containerfile.is_file():
            return False, f"Base containerfile not found at {containerfile}"

        cmd = [
            "podman",
            "build",
            "-t",
            "linux-ctf-base:latest",
            "-f",
            str(containerfile),
            str(self.project_root),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.returncode == 0, res.stdout + res.stderr

    def build_room_image(self, room: Room) -> Tuple[bool, str]:
        """Builds the container image for a specific room."""
        # Ensure base image exists first
        if not self.is_image_built("linux-ctf-base:latest"):
            logger.info("Base image not found. Building base image first...")
            success, msg = self.build_base_image()
            if not success:
                return False, f"Failed to build base image: {msg}"

        if not room.containerfile_path.is_file():
            return False, f"Containerfile missing for room {room.id} at {room.containerfile_path}"

        cmd = [
            "podman",
            "build",
            "-t",
            room.image_tag,
            "-f",
            str(room.containerfile_path),
            str(self.project_root),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.returncode == 0, res.stdout + res.stderr

    def is_container_running(self, container_name: str) -> bool:
        """Checks if a container is currently active."""
        res = subprocess.run(
            ["podman", "ps", "-q", "--filter", f"name=^{container_name}$"],
            capture_output=True,
            text=True,
        )
        return bool(res.stdout.strip())

    def stop_container(self, container_name: str) -> bool:
        """Forces container termination and removal."""
        res = subprocess.run(
            ["podman", "rm", "-f", container_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return res.returncode == 0

    def clean_room(self, room: Room) -> Tuple[bool, str]:
        """Stops any running container and removes the room's image (full room cleanup)."""
        if self.is_container_running(room.container_name):
            self.stop_container(room.container_name)

        if not self.is_image_built(room.image_tag):
            return True, f"Room {room.id} image ({room.image_tag}) is already cleaned."

        res = subprocess.run(
            ["podman", "rmi", "-f", room.image_tag],
            capture_output=True,
            text=True,
        )
        return res.returncode == 0, res.stdout + res.stderr

    delete_room_image = clean_room

    def clean_all_rooms(self, rooms: List[Room]) -> Tuple[int, List[str]]:
        """Cleans up all rooms (stops containers and removes images)."""
        removed_count = 0
        messages = []
        for room in rooms:
            if self.is_image_built(room.image_tag):
                success, msg = self.clean_room(room)
                if success:
                    removed_count += 1
                    messages.append(f"Cleaned Room {room.id} ({room.image_tag})")
                else:
                    messages.append(f"Failed to clean Room {room.id}: {msg}")
        return removed_count, messages

    delete_all_room_images = clean_all_rooms

    def start_interactive_session(self, room: Room) -> int:
        """Spawns an interactive PTY session directly connected to the user terminal."""
        if not self.is_image_built(room.image_tag):
            raise PodmanError(
                f"Room {room.id} is NOT built yet! Please make it ready first by running: "
                f"build {room.id}"
            )

        # Stop existing instance if lingering
        if self.is_container_running(room.container_name):
            self.stop_container(room.container_name)

        cmd = [
            "podman",
            "run",
            "--rm",
            "-it",
            "--name",
            room.container_name,
            "--hostname",
            f"ctf-room{room.id}",
            room.image_tag,
        ]
        # Direct terminal pass-through (stdin/stdout/stderr connected to host tty)
        return subprocess.run(cmd).returncode

    def test_flag_against_container(self, room: Room, flag: str) -> Tuple[bool, str]:
        """Tests flag validity non-interactively using the hardened in-container validator."""
        if not self.is_image_built(room.image_tag):
            return False, (
                f"Room {room.id} image is not built yet. "
                f"Please make it ready first using: build {room.id}"
            )

        cmd = [
            "podman",
            "run",
            "--rm",
            room.image_tag,
            "/usr/local/bin/submit-flag",
            flag,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        is_success = res.returncode == 0
        return is_success, res.stdout.strip()
