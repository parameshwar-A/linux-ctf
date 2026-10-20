from __future__ import annotations
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Callable, List, Optional, Tuple
from linux_ctf.models import Room
from linux_ctf.engine.rooms import find_project_root
from linux_ctf.engine.secrets import SessionSecret, generate_session_secret

logger = logging.getLogger(__name__)


class PodmanError(Exception):
    pass


class PodmanEngine:
    def __init__(self, project_root: Optional[Path] = None, registry_prefix: Optional[str] = None):
        self.project_root = project_root or find_project_root()
        self.registry_prefix = registry_prefix if registry_prefix is not None else os.environ.get("LINUX_CTF_REGISTRY", "docker.io/paramesh273")
        self.active_sessions: dict[str, SessionSecret] = {}
        self._cached_images: Optional[Set[str]] = None
        self._cached_running_containers: Optional[Set[str]] = None
        self._ensure_podman_installed()

    def _ensure_podman_installed(self) -> None:
        if not shutil.which("podman"):
            raise PodmanError(
                "Podman is not installed or not found in system PATH. "
                "Please install podman to run Linux CTF labs."
            )

    def refresh_cache(self) -> None:
        """Fetches all local images and running container names in fast batch queries."""
        images: Set[str] = set()
        try:
            res = subprocess.run(
                ["podman", "images", "--format", "{{.Repository}}:{{.Tag}}"],
                capture_output=True,
                text=True,
            )
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    entry = line.strip()
                    if entry and entry != "<none>:<none>":
                        images.add(entry)
                        if entry.startswith("localhost/"):
                            images.add(entry[10:])
                        elif entry.startswith("docker.io/"):
                            images.add(entry[10:])
                            parts = entry[10:].split("/")
                            if len(parts) > 1:
                                images.add(parts[-1])
        except Exception as e:
            logger.debug(f"Error refreshing image cache: {e}")
        self._cached_images = images

        running: Set[str] = set()
        try:
            res = subprocess.run(
                ["podman", "ps", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
            )
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    name = line.strip()
                    if name:
                        running.add(name)
        except Exception as e:
            logger.debug(f"Error refreshing container cache: {e}")
        self._cached_running_containers = running

    def clear_cache(self) -> None:
        """Invalidates cached images and container lists."""
        self._cached_images = None
        self._cached_running_containers = None

    def get_image_tag(self, room: Room) -> str:
        """Returns the full image tag, incorporating remote registry prefix if set."""
        if self.registry_prefix:
            return f"{self.registry_prefix.rstrip('/')}/linux-ctf-level{room.id}:latest"
        return room.image_tag

    def is_image_built(self, image_tag: str) -> bool:
        """Checks if an image exists locally in podman storage (fast cached lookup)."""
        if self._cached_images is None:
            self.refresh_cache()

        clean_tag = image_tag.strip()
        if self._cached_images is not None:
            if clean_tag in self._cached_images:
                return True
            if f"localhost/{clean_tag}" in self._cached_images:
                return True
            if clean_tag.startswith("docker.io/") and clean_tag[10:] in self._cached_images:
                return True
            if f"docker.io/{clean_tag}" in self._cached_images:
                return True
            return False

        res = subprocess.run(
            ["podman", "image", "exists", image_tag],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return res.returncode == 0

    def get_room_image_tags(self, room: Room) -> List[str]:
        """Finds all tags and repository entries currently in local Podman storage for this room."""
        if self._cached_images is None:
            self.refresh_cache()

        tags = set()
        room_patterns = [
            f"linux-ctf-level{room.id}",
            f"linux-ctf-{room.slug}",
        ]
        if self._cached_images is not None:
            for entry in self._cached_images:
                repo = entry.split(":")[0]
                for pat in room_patterns:
                    if repo == pat or repo.endswith(f"/{pat}"):
                        tags.add(entry)
                        break

        remote_tag = self.get_image_tag(room)
        candidate_tags = [
            room.image_tag,
            f"localhost/{room.image_tag}",
            f"localhost/linux-ctf-{room.slug}:latest",
            f"linux-ctf-{room.slug}:latest",
            remote_tag,
            f"docker.io/{remote_tag}" if not remote_tag.startswith("docker.io/") else remote_tag,
            remote_tag.replace("docker.io/", "") if remote_tag.startswith("docker.io/") else remote_tag,
        ]
        for t in candidate_tags:
            if self.is_image_built(t):
                tags.add(t)

        return sorted(list(tags))

    def is_image_ready(self, room: Room) -> bool:
        """Checks if room image exists locally under any valid local or registry tag."""
        if self._cached_images is None:
            self.refresh_cache()

        remote_tag = self.get_image_tag(room)
        candidate_tags = [
            room.image_tag,
            f"localhost/{room.image_tag}",
            remote_tag,
            f"docker.io/{remote_tag}" if not remote_tag.startswith("docker.io/") else remote_tag,
            remote_tag.replace("docker.io/", "") if remote_tag.startswith("docker.io/") else remote_tag,
        ]
        if any(self.is_image_built(t) for t in candidate_tags):
            return True
        return len(self.get_room_image_tags(room)) > 0

    def pull_room_image(
        self, room: Room, progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> Tuple[bool, str]:
        """Pulls a pre-built room image from Docker Hub or configured registry with live progress."""
        remote_tag = self.get_image_tag(room)
        logger.info(f"Pulling image {remote_tag}...")

        if progress_callback:
            progress_callback(f"Connecting to registry for {remote_tag}...", 10.0)

        proc = subprocess.Popen(
            ["podman", "pull", remote_tag],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        output_lines: List[str] = []
        progress = 15.0

        if proc.stdout:
            for line in iter(proc.stdout.readline, ""):
                if not line:
                    break
                clean_line = line.strip()
                output_lines.append(clean_line)
                if progress_callback and clean_line:
                    if "Trying to pull" in clean_line:
                        progress = 20.0
                    elif "Getting image source" in clean_line:
                        progress = 30.0
                    elif "Copying blob" in clean_line:
                        progress = min(progress + 15.0, 85.0)
                    elif "Copying config" in clean_line:
                        progress = 88.0
                    elif "Writing manifest" in clean_line:
                        progress = 95.0
                    progress_callback(clean_line, progress)

            proc.stdout.close()

        ret = proc.wait()
        if ret == 0:
            # Also tag as local alias for offline consistency
            subprocess.run(
                ["podman", "tag", remote_tag, room.image_tag],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.run(
                ["podman", "tag", remote_tag, f"localhost/{room.image_tag}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if progress_callback:
                progress_callback(f"Image {remote_tag} is READY!", 100.0)
            self.refresh_cache()
            return True, f"Image {remote_tag} pulled successfully."

        full_output = "\n".join(output_lines)
        return False, full_output

    def is_container_running(self, container_name: str) -> bool:
        """Checks if a container is currently active (fast cached lookup)."""
        if self._cached_running_containers is None:
            self.refresh_cache()

        if self._cached_running_containers is not None:
            return container_name in self._cached_running_containers

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
        self.refresh_cache()
        return res.returncode == 0

    def clean_room(self, room: Room) -> Tuple[bool, str]:
        """Stops any running container and removes all local and pulled images for the room."""
        if self.is_container_running(room.container_name):
            self.stop_container(room.container_name)
        subprocess.run(
            ["podman", "rm", "-f", room.container_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        tags_to_remove = self.get_room_image_tags(room)
        if not tags_to_remove:
            return True, f"Room {room.id} is already cleaned (no images found)."

        res = subprocess.run(
            ["podman", "rmi", "-f"] + tags_to_remove,
            capture_output=True,
            text=True,
        )
        self.refresh_cache()
        success = (res.returncode == 0) or not self.is_image_ready(room)
        return success, res.stdout + res.stderr

    delete_room_image = clean_room

    def clean_all_rooms(self, rooms: List[Room]) -> Tuple[int, List[str]]:
        """Cleans up all rooms (stops containers and removes all local and pulled images)."""
        removed_count = 0
        messages = []
        for room in rooms:
            if self.is_image_ready(room) or self.is_container_running(room.container_name):
                success, msg = self.clean_room(room)
                if success:
                    removed_count += 1
                    messages.append(f"Cleaned Room {room.id}")
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
                    f"Room {room.id} is NOT ready! Please pull it first using 'pull {room.id}'."
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
        ret = subprocess.run(cmd).returncode
        self.refresh_cache()
        return ret

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
                    f"Room {room.id} image is not pulled yet. "
                    f"Please make it ready first using: pull {room.id}"
                )

        secret = generate_session_secret(room.id)
        self.active_sessions[room.id] = secret
        if secret.verify(flag):
            return True, "[+] [SUCCESS] FLAG ACCEPTED! Room Completed!"
        return False, "[-] [INCORRECT] Keep exploring and check man pages!"
