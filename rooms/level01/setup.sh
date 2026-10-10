#!/usr/bin/env bash
set -euo pipefail

# Injected variables
SALT="ROOM01_SECRET_SALT_2026"
HASH="295998052b8fa219b845d2f2ef31e3cae7992d8109acc4bb4ccb1bd1dac64ef4"
FLAG="FLAG{l01_welcome_to_linux_shell_7f9b2d}"

# 1. Setup Room Environment Config for MOTD
cat <<'EOF' > /etc/linux_ctf_room.env
ROOM_ID="01"
ROOM_TITLE="The Awakening"
ROOM_COMMANDS="pwd, ls"
ROOM_MISSION="Locate the hidden flag (.hidden_flag) concealed in your workspace."
ROOM_HINT="Files starting with a '.' are hidden by default. Check 'man ls' to see which flag reveals all files."
EOF
chmod 644 /etc/linux_ctf_room.env

# 2. Compile Hardened Validator
gcc -O2 -s \
    -DEXPECTED_HASH="\"$HASH\"" \
    -DSALT="\"$SALT\"" \
    -DROOM_NAME="\"Level 01 - The Awakening\"" \
    /opt/linux_ctf/submit_flag.c \
    -o /usr/local/bin/submit-flag
chmod 755 /usr/local/bin/submit-flag
chown root:root /usr/local/bin/submit-flag

# 3. Setup Puzzle Environment in /home/learner
mkdir -p /home/learner/workspace /home/learner/docs
cat <<'EOF' > /home/learner/welcome.txt
======================================================
  Welcome to Linux CTF!
======================================================
This is an isolated sandbox environment.
Your goal is to use Linux commands to locate the flag.
A flag always looks like: FLAG{...}

Run 'submit-flag <YOUR_FLAG>' once you discover it!
EOF

cat <<'EOF' > /home/learner/docs/guide.txt
Remember to test different command flags.
Run 'man ls' or 'ls --help' for details.
EOF

# Plant the secret hidden dotfile
echo "$FLAG" > /home/learner/.hidden_flag

# Ensure proper user ownership
chown -R learner:learner /home/learner
chmod 644 /home/learner/.hidden_flag
chmod 644 /home/learner/welcome.txt

echo "[+] Room 01 challenge setup completed successfully."
