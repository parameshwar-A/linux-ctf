#!/usr/bin/env bash
# ==============================================================================
# Linux CTF - Player / Lab Runner Utility (Base Repo)
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

DOCKER_USER="${DOCKER_USER:-paramesh}"

usage() {
    echo "Linux CTF - Lab Runner"
    echo "Usage: $0 [command] [args]"
    echo ""
    echo "Commands:"
    echo "  pull <room_id> [username]   Pull room image from Docker Hub"
    echo "  pull-all [username]         Pull all room images from Docker Hub"
    echo "  run <room_id>               Launch interactive session in the room container"
    echo "  clean-room <id>             Clean up a room (stop container and remove image)"
    echo "  clean-rooms                 Clean up all room containers and images"
    echo "  clean                       Remove lingering CTF containers"
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
    pull)
        room_num=$(normalize_room "${1:-01}")
        user="${2:-$DOCKER_USER}"
        remote_tag="docker.io/${user}/linux-ctf-level${room_num}:latest"
        echo "[*] Pulling ${remote_tag} from Docker Hub..."
        podman pull "$remote_tag"
        podman tag "$remote_tag" "linux-ctf-level${room_num}:latest"
        echo "[+] Successfully pulled Room ${room_num}."
        ;;
    pull-all)
        user="${1:-$DOCKER_USER}"
        echo "[*] Pulling all rooms from Docker Hub (${user})..."
        for i in {1..15}; do
            rnum=$(printf "%02d" "$i")
            remote_tag="docker.io/${user}/linux-ctf-level${rnum}:latest"
            if podman pull "$remote_tag" 2>/dev/null; then
                podman tag "$remote_tag" "linux-ctf-level${rnum}:latest"
                echo "[+] Pulled Room ${rnum}."
            fi
        done
        echo "[+] Pull complete."
        ;;
    run)
        room_num=$(normalize_room "${1:-01}")
        tag="linux-ctf-level${room_num}:latest"
        if ! podman image exists "$tag"; then
            echo "[-] Room level${room_num} image is not present locally!"
            echo "[*] Please pull the image first by running:"
            echo "    $0 pull ${room_num}"
            exit 1
        fi
        echo "[*] Entering room level${room_num} with dynamic session secret..."
        test_flag="FLAG{l${room_num}_interactive_$(head -c 4 /dev/urandom | xxd -p)}"
        test_salt="$(head -c 8 /dev/urandom | xxd -p)"
        test_hash=$(echo -n "${test_flag}::${test_salt}" | sha256sum | cut -d' ' -f1)

        podman run --rm -it \
            --name "linux-ctf-room-${room_num}" \
            --hostname "ctf-room${room_num}" \
            -e CTF_FLAG="$test_flag" \
            -e CTF_SALT="$test_salt" \
            -e CTF_HASH="$test_hash" \
            "$tag"
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
