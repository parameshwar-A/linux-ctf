#!/usr/bin/env bash
# ==============================================================================
# Linux CTF - Player / Lab Runner Utility (Base Repo)
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

DOCKER_USER="${DOCKER_USER:-paramesh273}"

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
        test_tok=$(python3 -c "import secrets; print(secrets.token_hex(16))")
        test_flag="FLAG{l${room_num}_${test_tok}}"
        secret_name="ctf-flag-${room_num}-${test_tok:0:8}"

        echo -n "$test_flag" | podman secret create "$secret_name" - >/dev/null 2>&1

        trap 'podman secret rm "$secret_name" >/dev/null 2>&1 || true' EXIT

        podman run --rm -it \
            --name "linux-ctf-room-${room_num}" \
            --hostname "ctf-room${room_num}" \
            --network none \
            --cap-drop ALL \
            --cap-add CHOWN,DAC_OVERRIDE,FOWNER,SETUID,SETGID \
            --security-opt no-new-privileges \
            --pids-limit 256 \
            --memory 512m --memory-swap 512m \
            --cpus 1.0 \
            --ulimit nofile=1024:1024 \
            --ulimit fsize=104857600:104857600 \
            --secret "${secret_name},target=ctf_flag,mode=0400" \
            "$tag"

        podman secret rm "$secret_name" >/dev/null 2>&1 || true
        trap - EXIT
        ;;
    clean)
        echo "[*] Cleaning up linux-ctf containers and secrets..."
        podman ps -a --filter "name=linux-ctf-*" --format "{{.ID}}" | xargs -r podman rm -f
        podman secret ls --format "{{.Name}}" | grep -E '^ctf-flag-' | xargs -r podman secret rm 2>/dev/null || true
        echo "[+] Cleaned up active containers and secrets."
        ;;
    clean-room|clean-image)
        room_num=$(normalize_room "${1:-01}")
        tag="linux-ctf-level${room_num}:latest"
        cname="linux-ctf-room-${room_num}"
        echo "[*] Cleaning Room ${room_num} (container: $cname, image: $tag)..."
        podman rm -f "$cname" 2>/dev/null || true
        podman rmi -f "$tag" 2>/dev/null || true
        podman secret ls --format "{{.Name}}" | grep -E "^ctf-flag-${room_num}-" | xargs -r podman secret rm 2>/dev/null || true
        echo "[+] Room ${room_num} cleaned."
        ;;
    clean-rooms|clean-images)
        echo "[*] Cleaning up all room containers, images, and secrets..."
        podman ps -a --filter "name=linux-ctf-*" --format "{{.ID}}" | xargs -r podman rm -f
        podman images --filter "reference=*linux-ctf-level*" --format "{{.ID}}" | xargs -r podman rmi -f
        podman secret ls --format "{{.Name}}" | grep -E '^ctf-flag-' | xargs -r podman secret rm 2>/dev/null || true
        echo "[+] All room containers, images, and secrets removed."
        ;;
    *)
        usage
        ;;
esac
