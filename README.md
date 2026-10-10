# Linux CTF: Activity-Based Linux Command Mastery

Linux CTF is an interactive, gamified command-line learning platform designed to teach Linux fundamentals through hands-on challenge rooms. Learners navigate isolated rootless containers, solve realistic command-line puzzles, and capture cryptographic flags (`FLAG{...}`) to validate their skills.

---

## Key Features

* **Rootless Podman Sandboxes**: Every room executes inside a self-contained, unprivileged rootless container. Ephemeral containers spin up instantly on entry and cleanly tear down on exit.
* **Hardened In-Container Verification**: Flags are validated inside each container via a compiled, stripped C binary (`/usr/local/bin/submit-flag`) using compile-time salted SHA-256 hashes. Plaintext flags are never stored in container filesystems or visible via `strings`.
* **Terminal User Interface (TUI)**: A modern Textual-based terminal dashboard featuring live room status tracking, mission briefings, target command chips, toggleable hints, in-app flag submission, and seamless one-key terminal handoff into containers.
* **Full-Featured CLI**: Complete scriptable command-line interface for listing rooms, building images, entering sessions, testing flags, and cleaning images.
* **Built-in MOTD & Manual Integration**: Each container launches with an informative welcome banner summarizing the room objective and commands, along with fully indexed manual pages (`man`) for reference.
* **Zero Icon Dependency**: Terminal output and TUI widgets are styled using clean ASCII indicators and rich ANSI colors, ensuring compatibility across all terminal emulators and fonts without broken glyphs.

---

## System Requirements

* **Operating System**: Linux (Ubuntu, Debian, Fedora, Arch, etc.)
* **Container Runtime**: [Podman](https://podman.io/) (configured for rootless operation)
* **Python**: Python 3.10 or higher
* **Package Manager / Tools**: `bash`, `coreutils` (optional: `uv` for fast Python environment management)

---

## Quick Start

### 1. Launch Interactive TUI Dashboard

The easiest way to start learning is via the interactive Terminal User Interface:

```bash
# Using the launcher script (automatically prepares virtual environment)
./scripts/tui.sh

# Or directly with Python
python3 -m venv .venv
source .venv/bin/activate
pip install textual rich
python3 -m linux_ctf
```

#### TUI Keyboard Shortcuts

| Key | Action | Description |
|---|---|---|
| `b` | **Build** | Builds the room challenge image (or base sandbox if first run) |
| `e` | **Enter** | Launches interactive terminal session inside the container |
| `c` | **Clean Room** | Prompts confirmation to stop active container and remove room image |
| `h` | **Hint** | Toggles room hint reveal |
| `s` | **Submit Flag** | Opens modal dialog to test and verify a discovered flag |
| `r` | **Refresh** | Updates status of all rooms in the sidebar |
| `q` | **Quit** | Exits the TUI application |

---

## CLI Usage

Linux CTF provides a headless CLI via `linux_ctf.cli`:

```bash
# List all available rooms and their current build/running status
python3 -m linux_ctf.cli list

# Show detailed room briefing, tier, and target commands
python3 -m linux_ctf.cli show 01

# Build the container image for a room
python3 -m linux_ctf.cli build 01

# Enter an interactive session in the room
python3 -m linux_ctf.cli enter 01

# Stop an active container for a room
python3 -m linux_ctf.cli stop 01

# Test a flag non-interactively
python3 -m linux_ctf.cli verify 01 "FLAG{l01_welcome_to_linux_shell_7f9b2d}"

# Clean up container and delete room image
python3 -m linux_ctf.cli clean-room 01

# Clean up all built rooms
python3 -m linux_ctf.cli clean-room --all
```

---

## Inside the Challenge Container

Once inside a room session (`python3 -m linux_ctf.cli enter <id>` or pressing `e` in the TUI):

1. **Read the Mission**: Review the login MOTD banner for target commands and objective.
2. **Inspect the Environment**: Use standard commands (e.g. `pwd`, `ls -la`, `cat`, `man`).
3. **Submit Your Flag**: Once you discover the flag string, run:
   ```bash
   submit-flag "FLAG{...}"
   ```
4. **Exit the Room**: Type `exit` or press `Ctrl+D` to return to your host terminal or TUI dashboard.

---

## Developer Utilities

A helper script (`scripts/lab.sh`) is provided for developers and challenge authors:

```bash
# Build the shared base image (Debian Bookworm + coreutils + man-db + gcc)
./scripts/lab.sh build-base

# Build a specific room
./scripts/lab.sh build 01

# Launch container session directly via podman
./scripts/lab.sh run 01

# Run automated validation test on a room (tests wrong flag & correct flag)
./scripts/lab.sh test 01

# Clean a specific room container and image
./scripts/lab.sh clean-room 01

# Clean all built rooms
./scripts/lab.sh clean-rooms
```

### Running Test Suite

Unit and integration tests cover the engine, registry, and TUI lifecycle:

```bash
python3 -m unittest discover tests
```

---

## Architecture Overview

```
02_linux_ctf/
├── common/
│   ├── Containerfile.base        # Shared base image (Debian Bookworm slim)
│   ├── validator/
│   │   └── submit_flag.c         # Hardened compile-time SHA-256 C validator
│   └── scripts/
│       └── motd_banner.sh        # In-container login MOTD generator
├── linux_ctf/
│   ├── models.py                 # Room data models
│   ├── cli.py                    # Command-line interface
│   ├── engine/
│   │   ├── podman.py             # Rootless Podman orchestration engine
│   │   └── rooms.py              # Room discovery & metadata parser
│   └── ui/
│       ├── app.py                # Textual TUI dashboard
│       ├── styles.tcss           # Terminal styling and layout
│       └── screens/              # Modal dialogs (Submit, Confirm Clean)
├── rooms/
│   ├── level01/                  # Room 01: The Awakening (pwd, ls)
│   └── level02/                  # Room 02: The Reading Room (cd, cat)
├── scripts/
│   ├── lab.sh                    # Developer automation script
│   └── tui.sh                    # TUI startup launcher
├── tests/                        # Automated unit and integration tests
├── .gitignore                    # Git ignore configuration
└── README.md                     # Documentation
```

---

## Security Model

* **Salted Hashes**: Every challenge room injects a unique cryptographic salt and expected SHA-256 hash into `submit_flag.c` during room image build.
* **Stripped Binaries**: The validator binary is compiled with optimization and stripped symbol tables (`gcc -O2 -s`), preventing extraction of plaintext flags using `strings` or binary inspection.
* **Rootless Privilege Separation**: Containers run as non-root on the host system, and drop into an unprivileged `learner` user inside the container.
