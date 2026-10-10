from __future__ import annotations
from pathlib import Path
from typing import List, Optional
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, Grid
from textual.widgets import Button, Footer, Header, Label, ListItem, ListView, Static

from linux_ctf.models import Room
from linux_ctf.engine.rooms import RoomRegistry
from linux_ctf.engine.podman import PodmanEngine, PodmanError
from linux_ctf.ui.screens.submit_modal import SubmitModal
from linux_ctf.ui.screens.confirm_modal import ConfirmCleanModal


class RoomListItem(ListItem):
    """Custom list item representing a challenge room."""

    def __init__(self, room: Room, status_text: str, badge_class: str) -> None:
        super().__init__()
        self.room = room
        self.status_text = status_text
        self.badge_class = badge_class

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label(f"[{self.room.id}] {self.room.title}", classes="room-label")
            yield Label(f" {self.status_text}", classes=self.badge_class)


class LinuxCTFApp(App):
    """Modern Terminal User Interface for Linux CTF."""

    CSS_PATH = "styles.tcss"
    TITLE = "LINUX CTF :: Activity-Based Linux Command Mastery"
    SUB_TITLE = "Learn Linux Commands by Hunting Flags in Rootless Containers"
    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "refresh_all", "Refresh", show=True),
        Binding("b", "build_room", "Build", show=True),
        Binding("e", "enter_room", "Enter", show=True),
        Binding("c", "clean_room", "Clean Room", show=True),
        Binding("h", "toggle_hint", "Hint", show=True),
        Binding("s", "submit_flag", "Submit Flag", show=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.registry = RoomRegistry()
        self.engine = PodmanEngine()
        self.rooms: List[Room] = self.registry.list_rooms()
        self.selected_room: Optional[Room] = self.rooms[0] if self.rooms else None
        self.hint_revealed: bool = False

    def _create_room_item(self, room: Room) -> RoomListItem:
        is_built = self.engine.is_image_built(room.image_tag)
        is_running = self.engine.is_container_running(room.container_name)

        if is_running:
            status = "[RUNNING]"
            badge = "badge-running"
        elif is_built:
            status = "[READY]"
            badge = "badge-ready"
        else:
            status = "[NOT BUILT]"
            badge = "badge-unbuilt"

        return RoomListItem(room, status, badge)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True, icon="")
        with Container(id="main-container"):
            # Left Sidebar
            with Vertical(id="sidebar"):
                yield Label("CHALLENGE ROOMS", id="sidebar-title")
                items = [self._create_room_item(r) for r in self.rooms]
                yield ListView(*items, id="rooms-list")

            # Right Main Content Area
            with Vertical(id="content"):
                with Vertical(id="room-header"):
                    yield Label("ROOM OVERVIEW", id="room-title")
                    yield Label("Select a room to begin", id="room-meta")

                # Action Toolbar (Single compact row)
                with Grid(id="toolbar"):
                    yield Button("Build", id="btn-build")
                    yield Button("Enter", id="btn-enter")
                    yield Button("Clean", id="btn-clean")
                    yield Button("Show Hint", id="btn-hint")
                    yield Button("Submit", id="btn-submit")

                with Vertical(classes="info-card"):
                    yield Label("TARGET COMMANDS", classes="card-title")
                    yield Label("", id="commands-chips")

                with Vertical(classes="info-card"):
                    yield Label("MISSION BRIEFING", classes="card-title")
                    yield Static("", id="mission-text")

                with Vertical(classes="info-card"):
                    yield Label("HINTS & MANUAL PAGES", classes="card-title")
                    yield Static("", id="hint-box")

        yield Footer()

    def on_mount(self) -> None:
        room_list = self.query_one("#rooms-list", ListView)
        if self.rooms:
            room_list.index = 0
            self.selected_room = self.rooms[0]
            room_list.focus()
        self.update_content_view()

    def refresh_room_list(self) -> None:
        self.registry.load_rooms()
        self.rooms = self.registry.list_rooms()
        room_list = self.query_one("#rooms-list", ListView)
        room_list.clear()

        for room in self.rooms:
            room_list.append(self._create_room_item(room))

        if self.rooms:
            # Maintain current selection or default to first
            current_id = self.selected_room.id if self.selected_room else self.rooms[0].id
            for idx, r in enumerate(self.rooms):
                if r.id == current_id:
                    room_list.index = idx
                    self.selected_room = r
                    break

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item and isinstance(event.item, RoomListItem):
            self.select_room(event.item.room)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item and isinstance(event.item, RoomListItem):
            self.select_room(event.item.room)

    def select_room(self, room: Room) -> None:
        self.selected_room = room
        self.hint_revealed = False
        self.update_content_view()

    def update_content_view(self) -> None:
        if not self.selected_room:
            return

        room = self.selected_room
        is_built = self.engine.is_image_built(room.image_tag)
        is_running = self.engine.is_container_running(room.container_name)

        if is_running:
            status_desc = "[bold cyan][RUNNING][/bold cyan] Active"
        elif is_built:
            status_desc = "[bold green][READY][/bold green] Ready to enter"
        else:
            status_desc = "[bold yellow][NOT BUILT][/bold yellow] Click [Build] or press 'b'"

        # Update Header
        self.query_one("#room-title", Label).update(
            f"[bold cyan]ROOM {room.id} : {room.title.upper()}[/bold cyan]"
        )
        self.query_one("#room-meta", Label).update(
            f"Tier: [white]{room.tier}[/white]  |  Image: [dim]{room.image_tag}[/dim]  |  Status: {status_desc}"
        )

        # Update Commands Chips (Use rich pill badges)
        chips = "  ".join([f"[bold black on yellow]  {cmd}  [/bold black on yellow]" for cmd in room.commands])
        self.query_one("#commands-chips", Label).update(chips)

        # Update Mission Text
        self.query_one("#mission-text", Static).update(
            f"[bold white]{room.mission}[/bold white]"
        )

        # Update Hint Card and Button Label
        hint_widget = self.query_one("#hint-box", Static)
        try:
            hint_btn = self.query_one("#btn-hint", Button)
        except Exception:
            hint_btn = None

        if self.hint_revealed:
            hint_widget.update(f"HINT: [bold yellow]{room.hint}[/bold yellow]")
            hint_widget.add_class("revealed")
            if hint_btn:
                hint_btn.label = "Hide Hint"
        else:
            hint_widget.update("[dim]Hint is hidden. Click '[bold]Show Hint[/bold]' above or press '[bold]h[/bold]' to reveal.[/dim]")
            hint_widget.remove_class("revealed")
            if hint_btn:
                hint_btn.label = "Show Hint"

    def action_toggle_hint(self) -> None:
        self.hint_revealed = not self.hint_revealed
        self.update_content_view()

    def action_refresh_all(self) -> None:
        self.refresh_room_list()
        self.update_content_view()
        self.notify("Refreshed all room statuses.", title="Linux CTF")

    @work(exclusive=True, thread=True)
    def action_build_room(self) -> None:
        if not self.selected_room:
            return

        room = self.selected_room
        base_built = self.engine.is_image_built("linux-ctf-base:latest")

        if not base_built:
            self.notify(
                "Building base image for the first time. This may take ~1 to 2 minutes...",
                title="Building Base Sandbox",
                severity="information",
                timeout=8,
            )
        else:
            self.notify(
                f"Building challenge layer for Room {room.id} (takes ~3 to 5 seconds)...",
                title=f"Building Room {room.id}",
                severity="information",
                timeout=4,
            )

        success, msg = self.engine.build_room_image(room)
        if success:
            self.notify(
                f"Room {room.id} ({room.title}) is built and READY!",
                title="Build Success",
                severity="information",
            )
        else:
            self.notify(
                f"Build failed for Room {room.id}:\n{msg[:150]}",
                title="Build Error",
                severity="error",
                timeout=10,
            )

        self.app.call_from_thread(self.action_refresh_all)

    def action_enter_room(self) -> None:
        if not self.selected_room:
            return

        room = self.selected_room

        # Strict check: Block entering if not ready/built
        if not self.engine.is_image_built(room.image_tag):
            self.notify(
                f"Room {room.id} is NOT READY!\nPlease build it first using the [Build] button (or 'b').",
                title="Room Not Ready",
                severity="warning",
                timeout=6,
            )
            return

        # Suspend TUI and give full terminal control to podman interactive session
        with self.suspend():
            try:
                self.engine.start_interactive_session(room)
            except PodmanError as e:
                print(f"Error launching room: {e}")

        # Upon user typing 'exit', resume TUI and refresh status
        self.refresh_room_list()
        self.update_content_view()

    def action_clean_room(self) -> None:
        if not self.selected_room:
            return

        room = self.selected_room

        def handle_confirm(confirmed: bool) -> None:
            if confirmed:
                success, msg = self.engine.clean_room(room)
                if success:
                    self.notify(
                        f"Room {room.id} cleaned successfully.",
                        title="Room Cleaned",
                        severity="information",
                    )
                else:
                    self.notify(
                        f"Clean error: {msg}",
                        title="Error",
                        severity="error",
                    )
                self.refresh_room_list()
                self.update_content_view()

        self.push_screen(ConfirmCleanModal(room), handle_confirm)

    def action_submit_flag(self) -> None:
        if not self.selected_room:
            return

        self.push_screen(SubmitModal(self.selected_room, self.engine))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "btn-build":
            self.action_build_room()
        elif button_id == "btn-enter":
            self.action_enter_room()
        elif button_id == "btn-clean":
            self.action_clean_room()
        elif button_id == "btn-hint":
            self.action_toggle_hint()
        elif button_id == "btn-submit":
            self.action_submit_flag()


def run_app() -> None:
    app = LinuxCTFApp()
    app.run()


if __name__ == "__main__":
    run_app()
