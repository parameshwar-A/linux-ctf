#!/usr/bin/env bash
# Linux CTF - In-Container Welcome Banner (MOTD)

# Colors
C_RESET="\033[0m"
C_CYAN="\033[1;36m"
C_GREEN="\033[1;32m"
C_YELLOW="\033[1;33m"
C_WHITE="\033[1;37m"
C_GRAY="\033[0;90m"

# Load room metadata if present
ROOM_FILE="/etc/linux_ctf_room.env"
if [ -f "$ROOM_FILE" ]; then
    source "$ROOM_FILE"
fi

ROOM_ID="${ROOM_ID:-01}"
ROOM_TITLE="${ROOM_TITLE:-The Awakening}"
ROOM_COMMANDS="${ROOM_COMMANDS:-pwd, ls}"
ROOM_MISSION="${ROOM_MISSION:-Find the hidden flag in this directory tree.}"
ROOM_HINT="${ROOM_HINT:-Check the man pages for options to view hidden files.}"

echo -e "${C_CYAN}======================================================================${C_RESET}"
echo -e "${C_WHITE}  [ LINUX CTF - LAB SANDBOX ]${C_RESET} ${C_GRAY}:: Rootless Lab Environment${C_RESET}"
echo -e "${C_CYAN}======================================================================${C_RESET}"
echo -e "  ${C_YELLOW}Room:${C_RESET}     [Level ${ROOM_ID}] ${ROOM_TITLE}"
echo -e "  ${C_YELLOW}Commands:${C_RESET} ${ROOM_COMMANDS}"
echo -e "  ${C_YELLOW}Mission:${C_RESET}  ${ROOM_MISSION}"
echo -e "  ${C_YELLOW}Hint:${C_RESET}     ${ROOM_HINT}"
echo -e "${C_CYAN}----------------------------------------------------------------------${C_RESET}"
echo -e "  ${C_GREEN}Submit Flag:${C_RESET}  submit-flag <YOUR_FLAG>"
echo -e "  ${C_GREEN}Manual Pages:${C_RESET} man <command> (e.g. man ls)"
echo -e "  ${C_GREEN}Exit Lab:${C_RESET}     exit"
echo -e "${C_CYAN}======================================================================${C_RESET}"
echo ""
