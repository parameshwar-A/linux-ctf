from __future__ import annotations
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static
from linux_ctf.models import Room
from linux_ctf.engine.podman import PodmanEngine
from linux_ctf.engine.progress import ProgressTracker


class SubmitModal(ModalScreen[bool]):
    """Modal dialog for testing and submitting a flag."""

    def __init__(self, room: Room, engine: PodmanEngine, tracker: Optional[ProgressTracker] = None) -> None:
        super().__init__()
        self.room = room
        self.engine = engine
        self.tracker = tracker or ProgressTracker()
        self.is_solved: bool = False

    def compose(self) -> ComposeResult:
        with Container(id="modal-dialog"):
            yield Label(f"SUBMIT FLAG - ROOM {self.room.id}", id="modal-title")
            yield Static(
                f"Enter the flag found in '{self.room.title}':",
                id="modal-msg",
            )
            yield Input(placeholder="FLAG{...}", id="flag-input")
            yield Label("", id="feedback-label")
            with Horizontal(id="modal-buttons"):
                yield Button("Submit", variant="success", id="btn-modal-submit")
                yield Button("Close", variant="default", id="btn-modal-close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-modal-close":
            self.dismiss(self.is_solved)
        elif event.button.id == "btn-modal-submit":
            self.submit_flag()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.submit_flag()

    def submit_flag(self) -> None:
        flag_input = self.query_one("#flag-input", Input)
        feedback = self.query_one("#feedback-label", Label)
        val = flag_input.value.strip()

        if not val:
            feedback.update("[-] Please enter a flag first!")
            feedback.set_class(True, "error-text")
            return

        if not self.engine.is_image_ready(self.room):
            feedback.update("[-] Room image is not pulled yet! Please pull it first using [Pull].")
            feedback.set_class(True, "error-text")
            return

        feedback.update("[*] Verifying flag against hardened validator...")
        feedback.set_class(False, "error-text")
        feedback.set_class(False, "success-text")

        # Test flag non-interactively
        success, msg = self.engine.test_flag_against_container(self.room, val)
        if success:
            self.is_solved = True
            self.tracker.mark_completed(self.room.id, self.room.title)
            feedback.update("[+] [SUCCESS] FLAG ACCEPTED! Room Completed & Recorded!")
            feedback.set_class(True, "success-text")
            feedback.set_class(False, "error-text")

            # Immediately refresh underlying app widgets without waiting for room click
            if hasattr(self.app, "refresh_room_list"):
                self.app.refresh_room_list()
            if hasattr(self.app, "update_content_view"):
                self.app.update_content_view()
        else:
            feedback.update("[-] [INCORRECT] Keep exploring and check man pages!")
            feedback.set_class(True, "error-text")
            feedback.set_class(False, "success-text")
