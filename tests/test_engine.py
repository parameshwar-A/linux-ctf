from pathlib import Path
import unittest
from linux_ctf.models import Room
from linux_ctf.engine.rooms import RoomRegistry
from linux_ctf.engine.podman import PodmanEngine, PodmanError


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

    def test_unbuilt_room_blocked_from_enter(self):
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
        self.assertFalse(self.engine.is_image_built(dummy_room.image_tag))
        with self.assertRaises(PodmanError):
            self.engine.start_interactive_session(dummy_room)

    def test_image_build_and_cleanup(self):
        r1 = self.registry.get_room("01")
        self.assertTrue(self.engine.is_image_built("linux-ctf-base:latest"))

        # Ensure r1 image exists
        if not self.engine.is_image_built(r1.image_tag):
            ok, msg = self.engine.build_room_image(r1)
            self.assertTrue(ok)

        self.assertTrue(self.engine.is_image_built(r1.image_tag))

        # Test cleaning room
        ok, msg = self.engine.clean_room(r1)
        self.assertTrue(ok)
        self.assertFalse(self.engine.is_image_built(r1.image_tag))

        # Rebuild room image
        ok, msg = self.engine.build_room_image(r1)
        self.assertTrue(ok)
        self.assertTrue(self.engine.is_image_built(r1.image_tag))

    def test_flag_verification(self):
        from linux_ctf.engine.secrets import generate_session_secret

        r1 = self.registry.get_room("01")
        if not self.engine.is_image_built(r1.image_tag):
            self.engine.build_room_image(r1)

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


if __name__ == "__main__":
    unittest.main()
