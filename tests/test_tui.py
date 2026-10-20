import unittest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
from textual.pilot import Pilot
from linux_ctf.ui.app import LinuxCTFApp
from linux_ctf.ui.screens.submit_modal import SubmitModal
from linux_ctf.ui.screens.confirm_modal import ConfirmCleanModal


class TestLinuxCTFTUI(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.progress_file = Path(self.temp_dir.name) / "progress.json"
        self.env_patch = patch.dict(os.environ, {"LINUX_CTF_PROGRESS_FILE": str(self.progress_file)})
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()
        self.temp_dir.cleanup()

    async def test_tui_app_lifecycle(self):
        app = LinuxCTFApp()
        async with app.run_test() as pilot:
            self.assertIsNotNone(app.selected_room)
            self.assertEqual(app.selected_room.id, "01")

            # Test hint toggle
            self.assertFalse(app.hint_revealed)
            app.action_toggle_hint()
            self.assertTrue(app.hint_revealed)

            # Test refresh
            app.action_refresh_all()
            self.assertGreaterEqual(len(app.rooms), 1)

    async def test_tui_navigation_and_hint(self):
        app = LinuxCTFApp()
        async with app.run_test() as pilot:
            list_view = app.query_one("#rooms-list")
            self.assertEqual(app.selected_room.id, "01")

            # Down arrow selects Room 02
            await pilot.press("down")
            await pilot.pause()
            self.assertEqual(app.selected_room.id, "02")

            # Up arrow selects Room 01
            await pilot.press("up")
            await pilot.pause()
            self.assertEqual(app.selected_room.id, "01")

            # Mouse click on Room 02
            if len(list_view.children) > 1:
                await pilot.click(list_view.children[1])
                await pilot.pause()
                self.assertEqual(app.selected_room.id, "02")

            # Click Hint Button to reveal
            hint_btn = app.query_one("#btn-hint")
            await pilot.click("#btn-hint")
            await pilot.pause()
            self.assertTrue(app.hint_revealed)
            self.assertIn("Hide Hint", str(hint_btn.label))

            # Click Hint Button again to hide
            await pilot.click("#btn-hint")
            await pilot.pause()
            self.assertFalse(app.hint_revealed)
            self.assertIn("Show Hint", str(hint_btn.label))

    async def test_tui_modals(self):
        app = LinuxCTFApp()
        async with app.run_test() as pilot:
            # Submit modal
            modal = SubmitModal(app.selected_room, app.engine)
            await app.push_screen(modal)
            await pilot.pause()
            app.pop_screen()
            await pilot.pause()

            # Confirm clean modal
            clean_modal = ConfirmCleanModal(app.selected_room)
            await app.push_screen(clean_modal)
            await pilot.pause()
            app.pop_screen()
            await pilot.pause()


if __name__ == "__main__":
    unittest.main()
