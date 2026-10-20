from __future__ import annotations
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static
from linux_ctf.models import Room


class ConfirmCleanModal(ModalScreen[bool]):
    """Modal dialog for confirming clean-room action."""

    def __init__(self, room: Room) -> None:
        super().__init__()
        self.room = room

    def compose(self) -> ComposeResult:
        with Container(id="modal-dialog"):
            yield Label(f"CLEAN ROOM {self.room.id}?", id="modal-title")
            yield Static(
                f"This will stop any active container and remove all local and pulled images "
                f"for Room {self.room.id} (including localhost and docker.io tags) to free up storage.\n\n"
                f"Are you sure you want to clean this room?",
                id="modal-msg",
            )
            with Horizontal(id="modal-buttons"):
                yield Button("Yes, Clean", variant="error", id="btn-confirm-yes")
                yield Button("Cancel", variant="default", id="btn-confirm-no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-confirm-yes":
            self.dismiss(True)
        else:
            self.dismiss(False)
