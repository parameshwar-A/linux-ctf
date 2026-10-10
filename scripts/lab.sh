#!/usr/bin/env bash
# Linux CTF - Developer / Lab Runner Utility

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

usage() {
    echo "Linux CTF - Lab Runner"
    echo "Usage: $0 [command] [args]"
    echo ""
    echo "Commands:"
    echo "  build-base          Build the shared base image (linux-ctf-base:latest)"
    echo "  build <room_id>     Build a specific room (e.g. 01, level01)"
    echo "  run <room_id>       Launch an interactive session in the room container"
    echo "  test <room_id>      Run automated validation test on a room"
    echo "  clean-room <id>     Clean up a room (stop container and remove image)"
    echo "  clean-rooms         Clean up all built rooms"
    echo "  clean               Remove lingering CTF containers"
    echo ""
    exit 1
}

normalize_room() {
    local raw="$1"
    raw="${raw#level}"
    printf "%02d" "$((10#$raw))"
}

cmd="${1:-}"
shift || true

case "$cmd" in
    build-base)
        echo "[*] Building linux-ctf-base:latest..."
        echo "[i] Notice: This may take ~1 to 2 minutes while downloading packages and indexing man pages. Please wait..."
        podman build -t linux-ctf-base:latest -f common/Containerfile.base .
        echo "[+] Base image built successfully."
        ;;
    build)
        room_num=$(normalize_room "${1:-01}")
        room_dir="rooms/level${room_num}"
        if [ ! -d "$room_dir" ]; then
            echo "[-] Room directory $room_dir does not exist."
            exit 1
        fi
        echo "[*] Building room level${room_num}..."
        if ! podman image exists "linux-ctf-base:latest"; then
            echo "[i] Notice: Base image missing. First-time build will take ~1 to 2 minutes. Please wait..."
        else
            echo "[i] Notice: Base image is ready. Building room challenge layer (takes ~3 to 5 seconds). Please wait..."
        fi
        podman build -t "linux-ctf-level${room_num}:latest" -f "${room_dir}/Containerfile" .
        echo "[+] Room level${room_num} built successfully and is READY."
        ;;
    run)
        room_num=$(normalize_room "${1:-01}")
        tag="linux-ctf-level${room_num}:latest"
        if ! podman image exists "$tag"; then
            echo "[-] Room level${room_num} is NOT ready!"
            echo "[*] Please build the room image first by running:"
            echo "    $0 build ${room_num}"
            exit 1
        fi
        echo "[*] Entering room level${room_num}..."
        podman run --rm -it \
            --name "linux-ctf-room-${room_num}" \
            --hostname "ctf-room${room_num}" \
            "$tag"
        ;;
    test)
        room_num=$(normalize_room "${1:-01}")
        tag="linux-ctf-level${room_num}:latest"
        metadata="rooms/level${room_num}/metadata.json"
        if [ ! -f "$metadata" ]; then
            echo "[-] Metadata file $metadata not found."
            exit 1
        fi
        if ! podman image exists "$tag"; then
            echo "[-] Room level${room_num} is not built yet. Please run: $0 build ${room_num}"
            exit 1
        fi
        flag=$(grep -o '"flag": *"[^"]*"' "$metadata" | cut -d'"' -f4)
        echo "[*] Testing room level${room_num} with flag: $flag"
        
        # Test wrong flag
        echo "[*] Testing INCORRECT flag..."
        podman run --rm "$tag" /usr/local/bin/submit-flag "FLAG{wrong_guess}" || true
        
        # Test correct flag
        echo "[*] Testing CORRECT flag..."
        podman run --rm "$tag" /usr/local/bin/submit-flag "$flag"
        echo "[+] Verification test passed!"
        ;;
    clean)
        echo "[*] Cleaning up linux-ctf containers..."
        podman ps -a --filter "name=linux-ctf-*" --format "{{.ID}}" | xargs -r podman rm -f
        echo "[+] Cleaned up active containers."
        ;;
    clean-room|clean-image)
        room_num=$(normalize_room "${1:-01}")
        tag="linux-ctf-level${room_num}:latest"
        cname="linux-ctf-room-${room_num}"
        echo "[*] Cleaning Room ${room_num} (container: $cname, image: $tag)..."
        podman rm -f "$cname" 2>/dev/null || true
        podman rmi -f "$tag" 2>/dev/null || true
        echo "[+] Room ${room_num} cleaned."
        ;;
    clean-rooms|clean-images)
        echo "[*] Cleaning up all room containers and images..."
        podman ps -a --filter "name=linux-ctf-*" --format "{{.ID}}" | xargs -r podman rm -f
        podman images --filter "reference=*linux-ctf-level*" --format "{{.ID}}" | xargs -r podman rmi -f
        echo "[+] All room containers and images removed."
        ;;
    *)
        usage
        ;;
esac
