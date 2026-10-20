#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
import sys

# Support running directly: `python linux_ctf/cli.py` or `./linux_ctf/cli.py`
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from linux_ctf.engine.rooms import RoomRegistry
from linux_ctf.engine.podman import PodmanEngine, PodmanError
from linux_ctf.engine.progress import ProgressTracker

# ANSI Colors
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_CYAN = "\033[1;36m"
C_GREEN = "\033[1;32m"
C_YELLOW = "\033[1;33m"
C_RED = "\033[1;31m"
C_GRAY = "\033[0;90m"


def cmd_list(registry: RoomRegistry, engine: PodmanEngine, args: argparse.Namespace) -> int:
    rooms = registry.list_rooms()
    if not rooms:
        print(f"{C_YELLOW}[!] No rooms found in rooms/ directory.{C_RESET}")
        return 0

    tracker = ProgressTracker()
    print(f"\n{C_CYAN}{C_BOLD}=== LINUX CTF - AVAILABLE ROOMS ==={C_RESET}")
    print(f"{'ID':<4} {'ROOM TITLE':<25} {'TIER':<10} {'STATUS':<14} {'PROGRESS'}")
    print("-" * 68)

    for room in rooms:
        is_ready = engine.is_image_ready(room)
        is_running = engine.is_container_running(room.container_name)
        is_done = tracker.is_completed(room.id)

        if is_running:
            status = f"{C_GREEN}RUNNING{C_RESET}"
        elif is_ready:
            status = f"{C_CYAN}READY{C_RESET}"
        else:
            status = f"{C_GRAY}NOT PULLED{C_RESET}"

        if is_done:
            progress_str = f"{C_GREEN}COMPLETED{C_RESET}"
        else:
            progress_str = f"{C_GRAY}PENDING{C_RESET}"

        print(f"{room.id:<4} {room.title:<25} {room.tier:<10} {status:<23} {progress_str}")

    print("-" * 68)
    stats = tracker.get_summary(len(rooms))
    print(f"Total Rooms: {len(rooms)} | Completed: {stats['completed']}/{stats['total']} ({stats['percent']}%)\n")
    return 0


def cmd_show(registry: RoomRegistry, engine: PodmanEngine, args: argparse.Namespace) -> int:
    room = registry.get_room(args.room_id)
    if not room:
        print(f"{C_RED}[-] Room '{args.room_id}' not found.{C_RESET}")
        return 1

    is_ready = engine.is_image_ready(room)
    is_running = engine.is_container_running(room.container_name)

    tracker = ProgressTracker()
    is_done = tracker.is_completed(room.id)
    progress_desc = f"{C_GREEN}COMPLETED (Replayable){C_RESET}" if is_done else f"{C_YELLOW}PENDING (Not Solved){C_RESET}"

    print(f"\n{C_CYAN}{C_BOLD}======================================================================{C_RESET}")
    print(f"  {C_BOLD}[ ROOM {room.id} ]: {room.title.upper()}{C_RESET}")
    print(f"{C_CYAN}======================================================================{C_RESET}")
    print(f"  {C_YELLOW}Tier:{C_RESET}       {room.tier}")
    print(f"  {C_YELLOW}Progress:{C_RESET}   {progress_desc}")
    print(f"  {C_YELLOW}Container:{C_RESET}  {engine.get_image_tag(room)} ({'Ready' if is_ready else 'Not pulled'})")
    print(f"  {C_YELLOW}Active:{C_RESET}     {'Yes' if is_running else 'No'}")
    print(f"  {C_YELLOW}Mission:{C_RESET}    {room.mission}")
    print(f"  {C_YELLOW}Hint:{C_RESET}       {room.hint}")
    print(f"{C_CYAN}----------------------------------------------------------------------{C_RESET}")
    print(f"  {C_GREEN}Launch Lab:{C_RESET} python3 -m linux_ctf.cli enter {room.id}")
    print(f"{C_CYAN}======================================================================{C_RESET}\n")
    return 0


def cmd_pull(registry: RoomRegistry, engine: PodmanEngine, args: argparse.Namespace) -> int:
    room = registry.get_room(args.room_id)
    if not room:
        print(f"{C_RED}[-] Room '{args.room_id}' not found.{C_RESET}")
        return 1

    remote_tag = engine.get_image_tag(room)
    print(f"\n{C_YELLOW}[*] Pulling Room {room.id} image ({remote_tag})...{C_RESET}")
    success, output = engine.pull_room_image(room)
    if success:
        print(f"{C_GREEN}[+] Room {room.id} image pulled successfully and is READY!{C_RESET}")
        print(f"{C_GREEN}[+] Enter room anytime with: python3 -m linux_ctf.cli enter {room.id}{C_RESET}\n")
        return 0
    else:
        print(f"{C_RED}[-] Pull failed:\n{output}{C_RESET}\n")
        return 1


cmd_build = cmd_pull


def cmd_enter(registry: RoomRegistry, engine: PodmanEngine, args: argparse.Namespace) -> int:
    room = registry.get_room(args.room_id)
    if not room:
        print(f"{C_RED}[-] Room '{args.room_id}' not found.{C_RESET}")
        return 1

    if not engine.is_image_ready(room):
        print(f"\n{C_RED}[!] Room {room.id} is NOT READY!{C_RESET}")
        print(f"{C_YELLOW}[*] You must pull the room image before entering:{C_RESET}")
        print(f"    {C_CYAN}python3 -m linux_ctf.cli pull {room.id}{C_RESET}\n")
        return 1

    print(f"{C_GREEN}[*] Launching interactive session for Room {room.id}: {room.title}...{C_RESET}")
    try:
        return engine.start_interactive_session(room)
    except PodmanError as e:
        print(f"{C_RED}[-] Error: {e}{C_RESET}")
        return 1


def cmd_stop(registry: RoomRegistry, engine: PodmanEngine, args: argparse.Namespace) -> int:
    room = registry.get_room(args.room_id)
    if not room:
        print(f"{C_RED}[-] Room '{args.room_id}' not found.{C_RESET}")
        return 1

    print(f"{C_YELLOW}[*] Stopping container {room.container_name}...{C_RESET}")
    engine.stop_container(room.container_name)
    print(f"{C_GREEN}[+] Container stopped.{C_RESET}")
    return 0


def cmd_clean_room(registry: RoomRegistry, engine: PodmanEngine, args: argparse.Namespace) -> int:
    if getattr(args, "all", False):
        rooms = registry.list_rooms()
        print(f"{C_YELLOW}[*] Cleaning up all built rooms (stopping containers and removing images)...{C_RESET}")
        count, msgs = engine.clean_all_rooms(rooms)
        for msg in msgs:
            print(f"  {msg}")
        print(f"{C_GREEN}[+] Successfully cleaned {count} room(s).{C_RESET}")
        return 0

    if not args.room_id:
        print(f"{C_RED}[-] Please specify a room ID to clean, or use --all{C_RESET}")
        return 1

    room = registry.get_room(args.room_id)
    if not room:
        print(f"{C_RED}[-] Room '{args.room_id}' not found.{C_RESET}")
        return 1

    if not engine.is_image_ready(room) and not engine.is_container_running(room.container_name):
        print(f"{C_YELLOW}[*] Room {room.id} is already clean (no container or image found).{C_RESET}")
        return 0

    print(f"{C_YELLOW}[*] Cleaning Room {room.id} (stopping active container and removing all local & pulled images)...{C_RESET}")
    success, output = engine.clean_room(room)
    if success:
        print(f"{C_GREEN}[+] Room {room.id} cleaned successfully.{C_RESET}")
        return 0
    else:
        print(f"{C_RED}[-] Failed to clean room:\n{output}{C_RESET}")
        return 1


def cmd_verify(registry: RoomRegistry, engine: PodmanEngine, args: argparse.Namespace) -> int:
    room = registry.get_room(args.room_id)
    if not room:
        print(f"{C_RED}[-] Room '{args.room_id}' not found.{C_RESET}")
        return 1

    if not engine.is_image_ready(room):
        print(f"{C_RED}[!] Room {room.id} image is not pulled yet. Please pull it first:{C_RESET}")
        print(f"    {C_CYAN}python3 -m linux_ctf.cli pull {room.id}{C_RESET}")
        return 1

    print(f"{C_YELLOW}[*] Testing flag against Room {room.id}...{C_RESET}")
    success, output = engine.test_flag_against_container(room, args.flag)
    print(output)
    if success:
        tracker = ProgressTracker()
        tracker.mark_completed(room.id, room.title)
        print(f"\n{C_GREEN}[+] Progress Recorded: Room {room.id} marked as COMPLETED!{C_RESET}\n")
    return 0 if success else 1


def cmd_reset_progress(registry: RoomRegistry, args: argparse.Namespace) -> int:
    tracker = ProgressTracker()
    if getattr(args, "room_id", None):
        room = registry.get_room(args.room_id)
        if not room:
            print(f"{C_RED}[-] Room '{args.room_id}' not found.{C_RESET}")
            return 1
        tracker.reset_room(room.id)
        print(f"{C_GREEN}[+] Progress reset for Room {room.id} ({room.title}).{C_RESET}")
    else:
        tracker.reset_all()
        print(f"{C_GREEN}[+] All progress records have been reset to 0.{C_RESET}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="linux-ctf",
        description="Linux CTF - Containerized Activity-Based Command Line Game Engine",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    sub_list = subparsers.add_parser("list", help="List all available rooms and their statuses")

    # show
    sub_show = subparsers.add_parser("show", help="Display details for a specific room")
    sub_show.add_argument("room_id", help="Room identifier (e.g. 01, level01)")

    # pull (and alias build)
    sub_pull = subparsers.add_parser("pull", aliases=["build"], help="Pull the container image for a room from Docker Hub")
    sub_pull.add_argument("room_id", help="Room identifier (e.g. 01, level01)")

    # enter / start
    sub_enter = subparsers.add_parser("enter", help="Start or attach to an interactive room container")
    sub_enter.add_argument("room_id", help="Room identifier (e.g. 01, level01)")

    # stop
    sub_stop = subparsers.add_parser("stop", help="Stop a running room container")
    sub_stop.add_argument("room_id", help="Room identifier (e.g. 01, level01)")

    # clean-room (and aliases clean-image, clean-all, clean)
    sub_clean = subparsers.add_parser(
        "clean-room",
        aliases=["clean-image", "clean-all", "clean"],
        help="Stop and remove container and image for a room (or use clean-all / --all)",
    )
    sub_clean.add_argument("room_id", nargs="?", default=None, help="Room identifier (e.g. 01, level01)")
    sub_clean.add_argument("--all", action="store_true", help="Clean all built rooms")

    # verify
    sub_verify = subparsers.add_parser("verify", help="Test a flag value non-interactively")
    sub_verify.add_argument("room_id", help="Room identifier (e.g. 01, level01)")
    sub_verify.add_argument("flag", help="Flag string to test (e.g. FLAG{...})")

    # reset-progress
    sub_reset = subparsers.add_parser("reset-progress", help="Reset local CTF progress (all or specific room)")
    sub_reset.add_argument("room_id", nargs="?", default=None, help="Optional room ID to reset (e.g. 01)")

    # tui
    sub_tui = subparsers.add_parser("tui", help="Launch the interactive Terminal User Interface (TUI)")

    # If no arguments provided, default to tui
    if len(sys.argv) == 1:
        from linux_ctf.ui.app import run_app
        run_app()
        return 0

    args = parser.parse_args()

    try:
        registry = RoomRegistry()
        engine = PodmanEngine()
    except PodmanError as e:
        print(f"{C_RED}[!] {e}{C_RESET}")
        return 1

    if args.command == "tui":
        from linux_ctf.ui.app import run_app
        run_app()
        return 0
    elif args.command == "list":
        return cmd_list(registry, engine, args)
    elif args.command == "show":
        return cmd_show(registry, engine, args)
    elif args.command in ("pull", "build"):
        return cmd_pull(registry, engine, args)
    elif args.command == "enter":
        return cmd_enter(registry, engine, args)
    elif args.command == "stop":
        return cmd_stop(registry, engine, args)
    elif args.command in ("clean-room", "clean-image", "clean-all", "clean"):
        if args.command in ("clean-all", "clean") and not args.room_id:
            setattr(args, "all", True)
        return cmd_clean_room(registry, engine, args)
    elif args.command == "verify":
        return cmd_verify(registry, engine, args)
    elif args.command == "reset-progress":
        return cmd_reset_progress(registry, args)

    return 0


if __name__ == "__main__":
    sys.exit(main())



