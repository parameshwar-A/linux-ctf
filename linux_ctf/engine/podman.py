from __future__ import annotations
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple
from linux_ctf.models import Room
from linux_ctf.engine.rooms import find_project_root
from linux_ctf.engine.secrets import SessionSecret, generate_session_secret

logger = logging.getLogger(__name__)


class PodmanError(Exception):
    pass


class PodmanEngine:
    def __init__(self, project_root: Optional[Path] = None, registry_prefix: Optional[str] = None):
        self.project_root = project_root or find_project_root()
        self.registry_prefix = registry_prefix if registry_prefix is not None else os.environ.get("LINUX_CTF_REGISTRY", "docker.io/paramesh")
        self.active_sessions: dict[str, SessionSecret] = {}
        self._ensure_podman_installed()

    def _ensure_podman_installed(self) -> None:
        if not shutil.which("podman"):
            raise PodmanError(
                "Podman is not installed or not found in system PATH. "
                "Please install podman to run Linux CTF labs."
            )

    def get_image_tag(self, room: Room) -> str:
        """Returns the full image tag, incorporating remote registry prefix if set."""
        if self.registry_prefix:
            return f"{self.registry_prefix.rstrip('/')}/linux-ctf-level{room.id}:latest"
        return room.image_tag

    def is_image_built(self, image_tag: str) -> bool:
        """Checks if an image exists locally in podman storage."""
        res = subprocess.run(
            ["podman", "image", "exists", image_tag],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return res.returncode == 0

    def is_image_ready(self, room: Room) -> bool:
        """Checks if room image exists locally either under local tag or registry tag."""
        return self.is_image_built(room.image_tag) or self.is_image_built(self.get_image_tag(room))

    def pull_room_image(self, room: Room) -> Tuple[bool, str]:
        """Pulls a pre-built room image from Docker Hub or configured registry."""
        remote_tag = self.get_image_tag(room)
        logger.info(f"Pulling image {remote_tag}...")
        res = subprocess.run(["podman", "pull", remote_tag], capture_output=True, text=True)
        if res.returncode == 0:
            # Also tag as local alias for offline consistency
            subprocess.run(["podman", "tag", remote_tag, room.image_tag], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, f"Image {remote_tag} pulled successfully."
        return False, res.stdout + res.stderr

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
        image_tag = self.get_image_tag(room)
        if not self.is_image_built(image_tag):
            if self.is_image_built(room.image_tag):
                image_tag = room.image_tag
            else:
                raise PodmanError(
                    f"Room {room.id} is NOT ready! Please build or pull it first."
                )

        # Stop existing instance if lingering
        if self.is_container_running(room.container_name):
            self.stop_container(room.container_name)

        # Generate ephemeral dynamic session secret for this run
        secret = generate_session_secret(room.id)
        self.active_sessions[room.id] = secret

        cmd = [
            "podman",
            "run",
            "--rm",
            "-it",
            "--name",
            room.container_name,
            "--hostname",
            f"ctf-room{room.id}",
            "-e",
            f"CTF_FLAG={secret.flag}",
            "-e",
            f"CTF_SALT={secret.salt}",
            "-e",
            f"CTF_HASH={secret.expected_hash}",
            image_tag,
        ]
        # Direct terminal pass-through (stdin/stdout/stderr connected to host tty)
        return subprocess.run(cmd).returncode

    def test_flag_against_container(self, room: Room, flag: str) -> Tuple[bool, str]:
        """Tests flag validity against active session or in-container validator."""
        # Fast path: check against active session in memory
        active = self.active_sessions.get(room.id)
        if active:
            if active.verify(flag):
                return True, "[+] [SUCCESS] FLAG ACCEPTED! Room Completed!"
            else:
                return False, "[-] [INCORRECT] Keep exploring and check man pages!"

        # Fallback if testing non-interactively without active session
        image_tag = self.get_image_tag(room)
        if not self.is_image_built(image_tag):
            if self.is_image_built(room.image_tag):
                image_tag = room.image_tag
            else:
                return False, (
                    f"Room {room.id} image is not built yet. "
                    f"Please make it ready first using: build {room.id}"
                )

        secret = generate_session_secret(room.id)
        self.active_sessions[room.id] = secret
        if secret.verify(flag):
            return True, "[+] [SUCCESS] FLAG ACCEPTED! Room Completed!"
        return False, "[-] [INCORRECT] Keep exploring and check man pages!"
