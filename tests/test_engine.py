from pathlib import Path
import unittest
from linux_ctf.models import Room
from linux_ctf.engine.rooms import RoomRegistry
from linux_ctf.engine.podman import PodmanEngine, PodmanError
from linux_ctf.engine.secrets import generate_session_secret


class TestLinuxCTFEngine(unittest.TestCase):
    def setUp(self):
        self.registry = RoomRegistry()
        self.engine = PodmanEngine()

    def test_room_discovery(self):
        rooms = self.registry.list_rooms()
        self.assertGreaterEqual(len(rooms), 1)
        r1 = self.registry.get_room("01")
        self.assertIsNotNone(r1)
        self.assertEqual(r1.id, "01")
        self.assertIn("pwd", r1.commands)
        self.assertIn("ls", r1.commands)

    def test_room_normalization(self):
        self.assertEqual(self.registry.get_room("1").id, "01")
        self.assertEqual(self.registry.get_room("01").id, "01")
        self.assertEqual(self.registry.get_room("level01").id, "01")

    def test_unpulled_room_blocked_from_enter(self):
        dummy_room = Room(
            id="99",
            slug="level99",
            title="Nonexistent Room",
            tier="Beginner",
            commands=["ls"],
            mission="",
            hint="",
            salt="",
            hash="",
            path=Path("/tmp/nonexistent_level99"),
        )
        self.assertFalse(self.engine.is_image_ready(dummy_room))
        with self.assertRaises(PodmanError):
            self.engine.start_interactive_session(dummy_room)

    def test_image_readiness_and_registry_tag(self):
        r1 = self.registry.get_room("01")
        self.assertIn("paramesh273", self.engine.get_image_tag(r1))
        # Pull pre-built image as usual if not already present
        if not self.engine.is_image_ready(r1):
            success, msg = self.engine.pull_room_image(r1)
            self.assertTrue(success, f"Failed to pull image for room 01: {msg}")
        self.assertTrue(self.engine.is_image_ready(r1))

    def test_flag_verification(self):
        r1 = self.registry.get_room("01")
        if not self.engine.is_image_ready(r1):
            self.engine.pull_room_image(r1)

        secret = generate_session_secret(r1.id)
        self.engine.active_sessions[r1.id] = secret

        # Incorrect flag should fail
        ok, out = self.engine.test_flag_against_container(r1, "FLAG{bad_flag}")
        self.assertFalse(ok)
        self.assertIn("INCORRECT", out)

        # Correct flag should pass
        ok, out = self.engine.test_flag_against_container(r1, secret.flag)
        self.assertTrue(ok)
        self.assertIn("ACCEPTED", out)

    def test_flag_entropy(self):
        secret = generate_session_secret("01")
        # 16 bytes = 32 hex characters = 128 bits
        token_part = secret.flag.split("_")[1].rstrip("}")
        self.assertEqual(len(token_part), 32)
        self.assertEqual(len(secret.salt), 32)

    def test_registry_validation(self):
        # Valid registries
        pe1 = PodmanEngine(registry_prefix="docker.io/paramesh273")
        self.assertEqual(pe1.registry_prefix, "docker.io/paramesh273")
        pe2 = PodmanEngine(registry_prefix="quay.io/custom-org")
        self.assertEqual(pe2.registry_prefix, "quay.io/custom-org")

        # Invalid registries / option injection attempts
        malicious_inputs = [
            "--authfile=/etc/shadow",
            "docker.io/repo; rm -rf /",
            "docker.io/repo`touch /tmp/hacked`",
            "invalid prefix with spaces",
        ]
        for bad in malicious_inputs:
            with self.assertRaises(PodmanError):
                PodmanEngine(registry_prefix=bad)

    def test_test_flag_fallback_without_active_session(self):
        r1 = self.registry.get_room("01")
        self.engine.active_sessions.pop(r1.id, None)
        ok, msg = self.engine.test_flag_against_container(r1, "FLAG{any}")
        self.assertFalse(ok)
        self.assertIn("No active session found", msg)


if __name__ == "__main__":
    unittest.main()
