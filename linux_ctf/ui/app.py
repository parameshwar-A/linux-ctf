from __future__ import annotations
from pathlib import Path
from typing import List, Optional
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, Grid
from textual.widgets import Button, Footer, Header, Label, ListItem, ListView, ProgressBar, Static

from linux_ctf.models import Room
from linux_ctf.engine.rooms import RoomRegistry
from linux_ctf.engine.podman import PodmanEngine, PodmanError
from linux_ctf.engine.progress import ProgressTracker
from linux_ctf.ui.screens.submit_modal import SubmitModal
from linux_ctf.ui.screens.confirm_modal import ConfirmCleanModal


class RoomListItem(ListItem):
    """Custom list item representing a challenge room with completion and readiness badges."""

    def __init__(self, room: Room, is_done: bool, is_ready: bool, is_running: bool) -> None:
        super().__init__()
        self.room = room
        self.is_done = is_done
        self.is_ready = is_ready
        self.container_running = is_running

    def compose(self) -> ComposeResult:
        if self.container_running:
            container_status = "[RUNNING]"
            container_badge = "badge-running"
        elif self.is_ready:
            container_status = "[READY]"
            container_badge = "badge-ready"
        else:
            container_status = "[NOT PULLED]"
            container_badge = "badge-unbuilt"

        if self.is_done:
            title_text = f"[{self.room.id}] [SOLVED] {self.room.title}"
            title_class = "room-title-solved"
        else:
            title_text = f"[{self.room.id}] {self.room.title}"
            title_class = "room-title-pending"

        with Vertical(classes="room-item-box"):
            yield Label(title_text, classes=f"room-label {title_class}")
            yield Label(f"  {container_status}", classes=f"room-badge {container_badge}")


class LinuxCTFApp(App):
    """Modern Terminal User Interface for Linux CTF with Live Progress and Completion Tracking."""

    CSS_PATH = "styles.tcss"
    TITLE = "LINUX CTF :: Activity-Based Linux Command Mastery"
    SUB_TITLE = "Learn Linux Commands by Hunting Flags in Rootless Containers"
    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "refresh_all", "Refresh", show=True),
        Binding("p", "pull_room", "Pull", show=True),
        Binding("e", "enter_room", "Enter", show=True),
        Binding("c", "clean_room", "Clean Room", show=True),
        Binding("h", "toggle_hint", "Hint", show=True),
        Binding("s", "submit_flag", "Submit Flag", show=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.registry = RoomRegistry()
        self.engine = PodmanEngine()
        self.tracker = ProgressTracker()
        self.rooms: List[Room] = self.registry.list_rooms()
        self.selected_room: Optional[Room] = self.rooms[0] if self.rooms else None
        self.hint_revealed: bool = False

    def _create_room_item(self, room: Room) -> RoomListItem:
        is_ready = self.engine.is_image_ready(room)
        is_running = self.engine.is_container_running(room.container_name)
        is_done = self.tracker.is_completed(room.id)
        return RoomListItem(room, is_done=is_done, is_ready=is_ready, is_running=is_running)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True, icon="")
        with Container(id="main-container"):
            # Left Sidebar
            with Vertical(id="sidebar"):
                yield Label("CHALLENGE ROOMS", id="sidebar-title")
                yield Label("Solved: 0/15 (0%)", id="sidebar-stats-label")
                total_rooms = max(len(self.rooms), 1)
                yield ProgressBar(total=total_rooms, show_eta=False, id="sidebar-progress-bar")
                items = [self._create_room_item(r) for r in self.rooms]
                yield ListView(*items, id="rooms-list")

            # Right Main Content Area
            with Vertical(id="content"):
                with Vertical(id="room-header"):
                    yield Label("ROOM OVERVIEW", id="room-title")
                    yield Label("Select a room to begin", id="room-meta")

                # Action Toolbar (Single compact row)
                with Grid(id="toolbar"):
                    yield Button("Pull", id="btn-pull")
                    yield Button("Enter", id="btn-enter")
                    yield Button("Clean", id="btn-clean")
                    yield Button("Show Hint", id="btn-hint")
                    yield Button("Submit", id="btn-submit")

                # Dedicated Pull Progress Status Box (visible during active image pull)
                with Vertical(id="pull-progress-box"):
                    yield Label("Pulling container image...", id="pull-status-label")
                    yield ProgressBar(total=100, show_eta=False, id="pull-progress-bar")

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
        # Update overall stats in sidebar
        total_count = len(self.rooms)
        stats = self.tracker.get_summary(total_count)
        try:
            stats_label = self.query_one("#sidebar-stats-label", Label)
            stats_label.update(
                f"Solved: [bold green]{stats['completed']}/{stats['total']}[/bold green] ([cyan]{stats['percent']}%[/cyan])"
            )
            prog_bar = self.query_one("#sidebar-progress-bar", ProgressBar)
            prog_bar.update(progress=stats["completed"])
        except Exception:
            pass

        if not self.selected_room:
            return

        room = self.selected_room
        is_ready = self.engine.is_image_ready(room)
        is_running = self.engine.is_container_running(room.container_name)
        is_done = self.tracker.is_completed(room.id)

        # Clear, instant intimation of status without requiring clicks
        if is_running:
            img_badge = "[bold cyan][RUNNING][/bold cyan]"
            status_desc = "[bold cyan]Active Container Session[/bold cyan]"
        elif is_ready:
            img_badge = "[bold green][IMAGE READY][/bold green]"
            status_desc = "[bold green]Ready To Play (Cached Locally)[/bold green]"
        else:
            img_badge = "[bold yellow][NEEDS PULL][/bold yellow]"
            status_desc = "[bold yellow]Not Downloaded (Click 'Pull' or press 'p')[/bold yellow]"

        comp_badge = "[bold green][COMPLETED][/bold green]" if is_done else "[dim][NOT SOLVED][/dim]"

        # Update Header
        self.query_one("#room-title", Label).update(
            f"[bold cyan]ROOM {room.id} : {room.title.upper()}[/bold cyan]  {img_badge}  {comp_badge}"
        )
        self.query_one("#room-meta", Label).update(
            f"Tier: [white]{room.tier}[/white]  |  Image: [dim]{self.engine.get_image_tag(room)}[/dim]  |  Status: {status_desc}"
        )

        # Update Button cues
        try:
            btn_enter = self.query_one("#btn-enter", Button)
            btn_pull = self.query_one("#btn-pull", Button)
            if is_ready:
                btn_enter.label = "Enter Lab"
                btn_enter.set_class(True, "ready-btn")
                btn_pull.label = "Re-pull"
                btn_pull.set_class(False, "needed-btn")
            else:
                btn_enter.label = "Enter"
                btn_enter.set_class(False, "ready-btn")
                btn_pull.label = "Pull Image"
                btn_pull.set_class(True, "needed-btn")
        except Exception:
            pass

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
        self.engine.refresh_cache()
        self.refresh_room_list()
        self.update_content_view()
        self.notify("Refreshed all room statuses.", title="Linux CTF")

    @work(exclusive=True, thread=True)
    def action_pull_room(self) -> None:
        if not self.selected_room:
            return

        room = self.selected_room
        remote_tag = self.engine.get_image_tag(room)

        # Show the progress box and update button label
        def show_progress_start() -> None:
            try:
                box = self.query_one("#pull-progress-box", Vertical)
                box.set_class(True, "active")
                label = self.query_one("#pull-status-label", Label)
                label.update(f"[*] Starting download of {remote_tag} from Docker Hub...")
                bar = self.query_one("#pull-progress-bar", ProgressBar)
                bar.update(progress=5)
                btn = self.query_one("#btn-pull", Button)
                btn.disabled = True
                btn.label = "Pulling..."
            except Exception:
                pass

        self.app.call_from_thread(show_progress_start)

        def on_stream_progress(msg: str, pct: float) -> None:
            def update_ui() -> None:
                try:
                    label = self.query_one("#pull-status-label", Label)
                    label.update(f"[*] {msg[:75]}")
                    bar = self.query_one("#pull-progress-bar", ProgressBar)
                    bar.update(progress=pct)
                except Exception:
                    pass
            self.app.call_from_thread(update_ui)

        success, msg = self.engine.pull_room_image(room, progress_callback=on_stream_progress)

        def show_progress_end() -> None:
            try:
                btn = self.query_one("#btn-pull", Button)
                btn.disabled = False
                btn.label = "Re-pull"
                label = self.query_one("#pull-status-label", Label)
                bar = self.query_one("#pull-progress-bar", ProgressBar)
                if success:
                    label.update(f"[bold green][+] Image {remote_tag} is READY! Click 'Enter Lab' (or 'e') to begin.[/bold green]")
                    bar.update(progress=100)
                else:
                    label.update(f"[bold red][-] Pull failed: {msg[:70]}[/bold red]")
            except Exception:
                pass

        self.app.call_from_thread(show_progress_end)
        self.app.call_from_thread(self.action_refresh_all)

    action_build_room = action_pull_room

    def action_enter_room(self) -> None:
        if not self.selected_room:
            return

        room = self.selected_room

        # Strict check: Block entering if not ready/pulled
        if not self.engine.is_image_ready(room):
            self.notify(
                f"Room {room.id} is NOT READY!\nPlease pull it first using the [Pull Image] button (or 'p').",
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

        room = self.selected_room

        def handle_submit(solved: bool) -> None:
            self.refresh_room_list()
            self.update_content_view()
            if solved:
                self.notify(
                    f"Room {room.id} ({room.title}) marked as COMPLETED!",
                    title="Room Solved",
                    severity="information",
                )

        self.push_screen(SubmitModal(room, self.engine, self.tracker), handle_submit)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id in ("btn-pull", "btn-build"):
            self.action_pull_room()
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
