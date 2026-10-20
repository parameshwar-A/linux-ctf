import unittest
import argparse
from io import StringIO
import sys
from unittest.mock import patch
import os
import tempfile
from pathlib import Path
from linux_ctf.engine.rooms import RoomRegistry
from linux_ctf.engine.podman import PodmanEngine
from linux_ctf.engine.secrets import generate_session_secret
from linux_ctf.cli import cmd_list, cmd_show, cmd_verify


class TestLinuxCTFCLI(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.progress_file = Path(self.temp_dir.name) / "progress.json"
        self.env_patch = patch.dict(os.environ, {"LINUX_CTF_PROGRESS_FILE": str(self.progress_file)})
        self.env_patch.start()
        self.registry = RoomRegistry()
        self.engine = PodmanEngine()

    def tearDown(self):
        self.env_patch.stop()
        self.temp_dir.cleanup()

    def test_cli_list(self):
        args = argparse.Namespace()
        with patch("sys.stdout", new=StringIO()) as fake_out:
            code = cmd_list(self.registry, self.engine, args)
            output = fake_out.getvalue()
            self.assertEqual(code, 0)
            self.assertIn("LINUX CTF - AVAILABLE ROOMS", output)
            self.assertIn("01", output)
            self.assertIn("02", output)

    def test_cli_show(self):
        # Valid room
        args = argparse.Namespace(room_id="01")
        with patch("sys.stdout", new=StringIO()) as fake_out:
            code = cmd_show(self.registry, self.engine, args)
            output = fake_out.getvalue()
            self.assertEqual(code, 0)
            self.assertIn("ROOM 01", output)
            self.assertIn("Mission:", output)

        # Non-existent room
        args_bad = argparse.Namespace(room_id="999")
        with patch("sys.stdout", new=StringIO()) as fake_out:
            code = cmd_show(self.registry, self.engine, args_bad)
            output = fake_out.getvalue()
            self.assertEqual(code, 1)
            self.assertIn("not found", output)

    @patch.object(PodmanEngine, "is_image_ready", return_value=True)
    @patch.object(PodmanEngine, "test_flag_against_container")
    def test_cli_verify(self, mock_test, mock_ready):
        r1 = self.registry.get_room("01")
        secret = generate_session_secret(r1.id)
        self.engine.active_sessions[r1.id] = secret

        # Test valid flag
        mock_test.return_value = (True, "[+] SUCCESS! FLAG ACCEPTED!")
        args_good = argparse.Namespace(room_id="01", flag=secret.flag)
        with patch("sys.stdout", new=StringIO()) as fake_out:
            code = cmd_verify(self.registry, self.engine, args_good)
            output = fake_out.getvalue()
            self.assertEqual(code, 0)
            self.assertIn("ACCEPTED", output)

        # Test invalid flag
        mock_test.return_value = (False, "[-] INCORRECT FLAG! Keep exploring...")
        args_bad = argparse.Namespace(room_id="01", flag="FLAG{invalid_flag}")
        with patch("sys.stdout", new=StringIO()) as fake_out:
            code = cmd_verify(self.registry, self.engine, args_bad)
            output = fake_out.getvalue()
            self.assertEqual(code, 1)
            self.assertIn("INCORRECT", output)


if __name__ == "__main__":
    unittest.main()
