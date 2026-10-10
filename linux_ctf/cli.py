#!/usr/bin/env python3
from __future__ import annotations
import argparse
import sys
from linux_ctf.engine.rooms import RoomRegistry
from linux_ctf.engine.podman import PodmanEngine, PodmanError

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

    print(f"\n{C_CYAN}{C_BOLD}=== LINUX CTF - AVAILABLE ROOMS ==={C_RESET}")
    print(f"{'ID':<4} {'ROOM TITLE':<25} {'TIER':<10} {'STATUS':<12} {'COMMANDS'}")
    print("-" * 75)

    for room in rooms:
        is_built = engine.is_image_built(room.image_tag)
        is_running = engine.is_container_running(room.container_name)

        if is_running:
            status = f"{C_GREEN}RUNNING{C_RESET}"
        elif is_built:
            status = f"{C_CYAN}READY{C_RESET}"
        else:
            status = f"{C_GRAY}NOT BUILT{C_RESET}"

        cmds = ", ".join(room.commands)
        print(f"{room.id:<4} {room.title:<25} {room.tier:<10} {status:<21} {cmds}")

    print("-" * 75)
    print(f"Total Rooms: {len(rooms)}\n")
    return 0


def cmd_show(registry: RoomRegistry, engine: PodmanEngine, args: argparse.Namespace) -> int:
    room = registry.get_room(args.room_id)
    if not room:
        print(f"{C_RED}[-] Room '{args.room_id}' not found.{C_RESET}")
        return 1

    is_built = engine.is_image_built(room.image_tag)
    is_running = engine.is_container_running(room.container_name)

    print(f"\n{C_CYAN}{C_BOLD}======================================================================{C_RESET}")
    print(f"  {C_BOLD}[ ROOM {room.id} ]: {room.title.upper()}{C_RESET}")
    print(f"{C_CYAN}======================================================================{C_RESET}")
    print(f"  {C_YELLOW}Tier:{C_RESET}       {room.tier}")
    print(f"  {C_YELLOW}Commands:{C_RESET}   {', '.join(room.commands)}")
    print(f"  {C_YELLOW}Container:{C_RESET}  {room.image_tag} ({'Built' if is_built else 'Not built'})")
    print(f"  {C_YELLOW}Active:{C_RESET}     {'Yes' if is_running else 'No'}")
    print(f"  {C_YELLOW}Mission:{C_RESET}    {room.mission}")
    print(f"  {C_YELLOW}Hint:{C_RESET}       {room.hint}")
    print(f"{C_CYAN}----------------------------------------------------------------------{C_RESET}")
    print(f"  {C_GREEN}Launch Lab:{C_RESET} python3 -m linux_ctf.cli enter {room.id}")
    print(f"{C_CYAN}======================================================================{C_RESET}\n")
    return 0


def cmd_build(registry: RoomRegistry, engine: PodmanEngine, args: argparse.Namespace) -> int:
    room = registry.get_room(args.room_id)
    if not room:
        print(f"{C_RED}[-] Room '{args.room_id}' not found.{C_RESET}")
        return 1

    print(f"\n{C_YELLOW}[*] Preparing to build Room {room.id} ({room.image_tag})...{C_RESET}")
    if not engine.is_image_built("linux-ctf-base:latest"):
        print(f"{C_CYAN}[i] Notice: Base sandbox image is being built for the first time.")
        print(f"    This may take ~1 to 2 minutes while installing coreutils, gcc, and indexing man pages.")
        print(f"    Please wait...{C_RESET}")
    else:
        print(f"{C_CYAN}[i] Notice: Base image is ready. Building room challenge layer (takes ~3 to 5 seconds)...{C_RESET}")

    success, output = engine.build_room_image(room)
    if success:
        print(f"{C_GREEN}[+] Room {room.id} image built successfully and is READY!{C_RESET}")
        print(f"{C_GREEN}[+] Enter room anytime with: python3 -m linux_ctf.cli enter {room.id}{C_RESET}\n")
        return 0
    else:
        print(f"{C_RED}[-] Build failed:\n{output}{C_RESET}\n")
        return 1


def cmd_enter(registry: RoomRegistry, engine: PodmanEngine, args: argparse.Namespace) -> int:
    room = registry.get_room(args.room_id)
    if not room:
        print(f"{C_RED}[-] Room '{args.room_id}' not found.{C_RESET}")
        return 1

    if not engine.is_image_built(room.image_tag):
        print(f"\n{C_RED}[!] Room {room.id} is NOT READY!{C_RESET}")
        print(f"{C_YELLOW}[*] You must build the room image before entering:{C_RESET}")
        print(f"    {C_CYAN}python3 -m linux_ctf.cli build {room.id}{C_RESET}\n")
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

    if not engine.is_image_built(room.image_tag) and not engine.is_container_running(room.container_name):
        print(f"{C_YELLOW}[*] Room {room.id} is already clean (no container or image found).{C_RESET}")
        return 0

    print(f"{C_YELLOW}[*] Cleaning Room {room.id} (stopping active container and removing {room.image_tag})...{C_RESET}")
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

    if not engine.is_image_built(room.image_tag):
        print(f"{C_RED}[!] Room {room.id} image is not built yet. Please build it first:{C_RESET}")
        print(f"    {C_CYAN}python3 -m linux_ctf.cli build {room.id}{C_RESET}")
        return 1

    print(f"{C_YELLOW}[*] Testing flag against Room {room.id}...{C_RESET}")
    success, output = engine.test_flag_against_container(room, args.flag)
    print(output)
    return 0 if success else 1


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

    # build
    sub_build = subparsers.add_parser("build", help="Build the container image for a room")
    sub_build.add_argument("room_id", help="Room identifier (e.g. 01, level01)")

    # enter / start
    sub_enter = subparsers.add_parser("enter", help="Start or attach to an interactive room container")
    sub_enter.add_argument("room_id", help="Room identifier (e.g. 01, level01)")

    # stop
    sub_stop = subparsers.add_parser("stop", help="Stop a running room container")
    sub_stop.add_argument("room_id", help="Room identifier (e.g. 01, level01)")

    # clean-room (and alias clean-image)
    sub_clean = subparsers.add_parser("clean-room", aliases=["clean-image"], help="Stop and remove container and image for a room")
    sub_clean.add_argument("room_id", nargs="?", default=None, help="Room identifier (e.g. 01, level01)")
    sub_clean.add_argument("--all", action="store_true", help="Clean all built rooms")

    # verify
    sub_verify = subparsers.add_parser("verify", help="Test a flag value non-interactively")
    sub_verify.add_argument("room_id", help="Room identifier (e.g. 01, level01)")
    sub_verify.add_argument("flag", help="Flag string to test (e.g. FLAG{...})")

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
    elif args.command == "build":
        return cmd_build(registry, engine, args)
    elif args.command == "enter":
        return cmd_enter(registry, engine, args)
    elif args.command == "stop":
        return cmd_stop(registry, engine, args)
    elif args.command in ("clean-room", "clean-image"):
        return cmd_clean_room(registry, engine, args)
    elif args.command == "verify":
        return cmd_verify(registry, engine, args)

    return 0


if __name__ == "__main__":
    sys.exit(main())



