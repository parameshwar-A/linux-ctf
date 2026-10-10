#!/usr/bin/env bash
set -euo pipefail

SALT="ROOM02_SECRET_SALT_2026"
HASH="d449775f92a0acf39d028e6a9ccf77d5b2bc2bdf1b2b2f2fc21be16bd0a78142"
FLAG="FLAG{l02_cd_and_cat_mastery_8a1e4c}"

# 1. Setup Room Environment Config for MOTD
cat <<'EOF' > /etc/linux_ctf_room.env
ROOM_ID="02"
ROOM_TITLE="The Reading Room"
ROOM_COMMANDS="cd, cat"
ROOM_MISSION="Navigate into 'archives/classified/2026' and read the secret document. Beware of spaces in filenames!"
ROOM_HINT="Use 'cd' to change into directories. Wrap filenames with spaces in quotes or escape with a backslash: cat 'top secret document.txt'"
EOF
chmod 644 /etc/linux_ctf_room.env

# 2. Compile Hardened Validator
gcc -O2 -s \
    -DEXPECTED_HASH="\"$HASH\"" \
    -DSALT="\"$SALT\"" \
    -DROOM_NAME="\"Level 02 - The Reading Room\"" \
    /opt/linux_ctf/submit_flag.c \
    -o /usr/local/bin/submit-flag
chmod 755 /usr/local/bin/submit-flag
chown root:root /usr/local/bin/submit-flag

# 3. Setup Puzzle Environment in /home/learner
mkdir -p /home/learner/archives/classified/2026
cat <<'EOF' > /home/learner/archives/readme.txt
Classified documents are stored in the archive subdirectories.
Find your way into 2026 to view the briefing.
EOF

# Plant the secret document with spaces in the filename
echo "$FLAG" > "/home/learner/archives/classified/2026/top secret document.txt"

# Ensure proper user ownership
chown -R learner:learner /home/learner
chmod -R 755 /home/learner/archives
chmod 644 "/home/learner/archives/classified/2026/top secret document.txt"

echo "[+] Room 02 challenge setup completed successfully."
