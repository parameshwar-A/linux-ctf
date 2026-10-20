import unittest
import tempfile
from pathlib import Path
from linux_ctf.engine.progress import ProgressTracker


class TestProgressTracker(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.progress_file = Path(self.temp_dir.name) / "progress.json"
        self.tracker = ProgressTracker(progress_file=self.progress_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_initial_state(self):
        self.assertEqual(self.tracker.get_completed_ids(), set())
        self.assertEqual(self.tracker.get_completed_count(), 0)
        self.assertFalse(self.tracker.is_completed("01"))
        summary = self.tracker.get_summary(total_rooms=15)
        self.assertEqual(summary["completed"], 0)
        self.assertEqual(summary["total"], 15)
        self.assertEqual(summary["percent"], 0.0)

    def test_mark_and_persist(self):
        self.tracker.mark_completed("01", "The Awakening")
        self.assertTrue(self.tracker.is_completed("01"))
        self.assertEqual(self.tracker.get_completed_count(), 1)
        self.assertIn("01", self.tracker.get_completed_ids())

        # Load fresh instance pointing to same file
        reloaded = ProgressTracker(progress_file=self.progress_file)
        self.assertTrue(reloaded.is_completed("01"))
        entry = reloaded.get_room_status("01")
        self.assertEqual(entry["title"], "The Awakening")
        self.assertIn("completed_at", entry)

    def test_reset(self):
        self.tracker.mark_completed("01", "Room 1")
        self.tracker.mark_completed("02", "Room 2")
        self.assertEqual(self.tracker.get_completed_count(), 2)

        self.tracker.reset_room("01")
        self.assertFalse(self.tracker.is_completed("01"))
        self.assertTrue(self.tracker.is_completed("02"))
        self.assertEqual(self.tracker.get_completed_count(), 1)

        self.tracker.reset_all()
        self.assertEqual(self.tracker.get_completed_count(), 0)


if __name__ == "__main__":
    unittest.main()
