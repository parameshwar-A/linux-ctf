# Linux CTF: Activity-Based Linux Command Mastery

Linux CTF is an interactive, gamified command-line learning platform designed to teach Linux fundamentals through hands-on challenge rooms. Learners navigate isolated rootless containers, solve realistic command-line puzzles, and capture cryptographic flags (`FLAG{...}`) to validate their skills.

---

## Repositories & Ecosystem

* **Player App & TUI Engine**: [github.com/parameshwar-A/linux-ctf](https://github.com/parameshwar-A/linux-ctf) (`git@github.com:parameshwar-A/linux-ctf.git`)
* **Challenge Rooms & Author Repo**: [github.com/parameshwar-A/linux-ctf-rooms](https://github.com/parameshwar-A/linux-ctf-rooms) (`git@github.com:parameshwar-A/linux-ctf-rooms.git`)

---

## Key Features

* **Rootless Podman Sandboxes**: Every room executes inside a self-contained, unprivileged rootless container. Ephemeral containers spin up instantly on entry and cleanly tear down on exit.
* **Kerckhoffs-Compliant Architecture**: The platform does not rely on source code secrecy. Challenge rooms remain non-cheatable and tamper-resistant even though both repositories are 100% public and open-source.
* **In-Container Daemon Verification (`ctf-checkd`)**: Flag verification and challenge state checks are managed by a root-owned background daemon communicating over a local UNIX socket (`/run/ctf.sock`). Verifier binaries contain zero embedded flags or hashes.
* **Dynamic Ephemeral Secrets**: Every room session generates a unique, cryptographic 32-character hex flag via kernel CSPRNG. Plaintext flags are never stored in image layers or exposed via `podman inspect`.
* **Terminal User Interface (TUI)**: A modern Textual-based terminal dashboard featuring live room status tracking, mission briefings, toggleable hints, in-app flag submission, and seamless one-key terminal handoff into containers.
* **Full-Featured Headless CLI**: Complete scriptable command-line interface for listing rooms, pulling images, entering sessions, testing flags, and cleaning up container storage.
* **Built-in MOTD & Manual Integration**: Each container launches with an informative welcome banner summarizing the room objective and mission, along with fully indexed manual pages (`man`) for reference.
* **Zero Icon Dependency**: Terminal output and TUI widgets are styled using clean ASCII indicators and rich ANSI colors, ensuring compatibility across all terminal emulators and fonts without broken glyphs.

---

## Architectural & Security Design Principles

### 1. Why Rootless Podman?
Traditional container setups (such as standard Docker) require a background daemon running with root privileges (`dockerd`), meaning any misconfiguration or container breakout could grant root access to the host machine. 

Linux CTF was engineered from the ground up around **Rootless Podman**:
* **Daemonless Execution**: Podman operates directly via fork/exec without a centralized root daemon.
* **User Namespaces (`userns`)**: The root user inside the container is mapped to your standard, unprivileged user ID on the host. Even if code inside the container were to achieve UID 0, it holds zero root privileges on the host system.
* **Zero Host Volume Mounts**: Containers run on an isolated, ephemeral root filesystem. No host directories (`~`, `/tmp`, `/etc`, or SSH keys) are mounted into the lab environment.
* **Network Isolation (`--network none`)**: Containers launch with loopback networking only. They cannot access local LAN services, connect to host ports on `127.0.0.1`, or make outbound connections.
* **Host Resource & DoS Protection**:
  * `--pids-limit 256`: Neutralizes fork bombs (`:(){ :|:& };:`).
  * `--memory 512m --memory-swap 512m`: Prevents container memory leaks from invoking the host Out-Of-Memory (OOM) killer.
  * `--cpus 1.0`: Prevents container CPU starvation on multi-core systems.
  * `--ulimit fsize=104857600:104857600`: Imposes a strict **100MB file-size ceiling**, preventing runaway scripts or commands (`cat /dev/urandom > file`) from filling up host disk storage.

### 2. Kerckhoffs's Principle & Anti-Cheat Design
In computer security, **Kerckhoffs's Principle** states that a system should be secure even if everything about it—except the key—is public knowledge.

Both Linux CTF repositories (`02_linux_ctf` and `02_01_linux_ctf_rooms`) are completely public on GitHub. We designed the puzzle mechanics so that browsing the repository source code provides zero direct cheat codes:
* **Ephemeral Flags**: Flags follow the format `FLAG{l<room>_<32_hex_chars>}` and are generated dynamically at runtime using cryptographically secure pseudorandom number generators (`secrets.token_hex(16)` and kernel `getrandom()`).
* **Podman Secret Mounts**: Secrets are delivered into the container via Podman's tmpfs secret mount (`--secret <name>,target=ctf_flag,mode=0400`). Plaintext flags are **never passed as environment variables** or command-line arguments, leaving zero trace in `podman inspect` or host `ps`.
* **State Verification Instead of Flag Hiding**: In advanced rooms (Rooms 03, 04, 05, 06, 15), flags are only returned by `ctf-checkd` after the learner has legitimately manipulated the filesystem (e.g. configuring `dispatch.conf`, organizing production payloads, moving and cleaning clutter debris, or identifying the correct `$PATH` binary).
* **Decoy Flag Entropy**: Inspection-heavy rooms (Rooms 07–13) plant decoy flags with identical formatting and entropy (`FLAG{l<room>_<hex>}`). A 300ms throttling penalty on failed submissions in `ctf-checkd.c` neutralizes automated brute-force loops while preserving instantaneous UX for genuine human solves.
* **Salted SHA-256 Offline Verification**: The local session store (`~/.config/linux_ctf/sessions/`) never writes plaintext flags to disk. It stores only owner-only (`0600`) salted SHA-256 hashes for offline validation.

---

## Prerequisites & Installation

### System Requirements
* **Operating System**: Linux (Ubuntu, Debian, Fedora, RHEL, Arch Linux, openSUSE) or **macOS** (12.0+ on Apple Silicon / Intel)
* **Container Runtime**: [Podman](https://podman.io/) (v4.0 or higher; on macOS managed via `podman machine`)
* **Python**: Python 3.10 or higher
* **Tools**: `bash`, `coreutils`, `git` (optional: `uv` for fast Python environment management)

---

### Install Dependencies Across Platforms

Select your operating system below to install Podman, Python, and Git:

#### Ubuntu / Debian (22.04 LTS, 24.04 LTS, Debian 12+)
```bash
sudo apt update
sudo apt install -y podman python3 python3-venv git uidmap
```

#### Fedora / RHEL / CentOS Stream (Fedora 38+, RHEL 9+)
```bash
sudo dnf install -y podman python3 git shadow-utils
```

#### Arch Linux / Manjaro
```bash
sudo pacman -S --needed podman python git shadow
```

#### openSUSE (Leap / Tumbleweed)
```bash
sudo zypper install -y podman python3 git shadow
```

#### macOS (Homebrew)
```bash
# Install tools via Homebrew
brew install podman python git

# Initialize and launch the Podman Linux virtual machine (one-time setup)
podman machine init
podman machine start
```

---

## Quick Start Guide

### 1. Clone the Repository
```bash
# Clone via SSH (recommended):
git clone git@github.com:parameshwar-A/linux-ctf.git
cd linux-ctf

# Or clone via HTTPS:
git clone https://github.com/parameshwar-A/linux-ctf.git
cd linux-ctf
```

### 2. Launch the Interactive TUI Dashboard

The fastest and most visual way to play is via the built-in TUI:

```bash
# Option A: Automatic launcher script (creates venv and installs dependencies automatically)
./scripts/tui.sh

# Option B: Manual virtual environment setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m linux_ctf
```

#### TUI Keyboard Shortcuts

| Key | Action | Description |
|:---:|---|---|
| `p` | **Pull** | Pulls the pre-built room container image from Docker Hub |
| `e` | **Enter** | Launches an interactive terminal session inside the sandbox |
| `c` | **Clean Room** | Prompts confirmation to stop active container and remove room image |
| `h` | **Hint** | Toggles room hint reveal drawer |
| `s` | **Submit Flag** | Opens modal dialog to test and verify a discovered flag |
| `r` | **Refresh** | Updates status of all rooms in the sidebar |
| `q` | **Quit** | Exits the TUI application |

---

## CLI Reference (Headless Mode)

Linux CTF includes a full-featured CLI driver via `linux_ctf.cli`:

```bash
# List all available rooms, tier, status, and completion progress
python3 -m linux_ctf.cli list

# View detailed mission briefing and command targets for a specific room
python3 -m linux_ctf.cli show 01

# Pull a room image from Docker Hub
python3 -m linux_ctf.cli pull 01

# Launch interactive terminal session inside room (generates dynamic session flag)
python3 -m linux_ctf.cli enter 01

# Stop an active container for a room
python3 -m linux_ctf.cli stop 01

# Verify a flag offline or non-interactively
python3 -m linux_ctf.cli verify 01 "FLAG{l01_...}"

# Clean up container and delete room image
python3 -m linux_ctf.cli clean-room 01

# Clean up all room containers and images
python3 -m linux_ctf.cli clean-room --all

# Reset room progress (single room or all)
python3 -m linux_ctf.cli reset-progress 01
python3 -m linux_ctf.cli reset-progress
```

---

## Challenge Workflow: Solving Rooms & Submitting Flags

1. **Enter Room**: Launch via the TUI (`e`) or CLI (`python3 -m linux_ctf.cli enter 01`).
2. **Review Mission Briefing**: Read the login MOTD banner displayed at shell startup.
3. **Investigate & Learn**: Use standard GNU/Linux tools (`pwd`, `ls`, `cd`, `cat`, `grep`, `find`, `man`).
4. **Need a Hint?**: Run `hint` inside the container terminal or press `h` in the TUI.
5. **Instant In-Container Validation**:
   When you locate the flag, test it instantly inside the machine:
   ```bash
   submit-flag "FLAG{...}"
   ```
   > [!NOTE]
   > Running `submit-flag` gives instant feedback on flag validity. Because containers run in an isolated sandbox, **progress is officially recorded in the host app**.

6. **Submit in App to Record Progress**:
   - Exit the container by typing `exit` or pressing `Ctrl+D`.
   - **In TUI**: Press `s`, paste your flag, and press Enter. The room status advances to **[COMPLETED]** and updates your persistent progress tracker.
   - **In CLI**: Run `python3 -m linux_ctf.cli verify <room_id> "FLAG{...}"`.

---

## Lab Runner Utility (`scripts/lab.sh`)

For scripting and headless lab automation without Python:

```bash
# Pull a specific room image
./scripts/lab.sh pull 01

# Pull all room images (01 through 15)
./scripts/lab.sh pull-all

# Launch room container session directly with ephemeral secret mount
./scripts/lab.sh run 01

# Clean up a single room container and image
./scripts/lab.sh clean-room 01

# Clean up all containers, images, and lingering secrets
./scripts/lab.sh clean-rooms
```

---

## Running the Automated Test Suite

The test suite validates engine container management, CLI arguments, session persistence, and TUI lifecycle states:

```bash
# Using project virtual environment
.venv/bin/python -m unittest discover -s tests
```

---

## Project Structure

```
02_linux_ctf/
├── linux_ctf/
│   ├── data/
│   │   └── rooms.json            # Bundled room catalogue manifest (missions, commands)
│   ├── models.py                 # Dataclasses and room models
│   ├── cli.py                    # Complete CLI driver implementation
│   ├── engine/
│   │   ├── podman.py             # Rootless Podman orchestration & pull engine
│   │   ├── rooms.py              # Room discovery & manifest parser
│   │   ├── secrets.py            # CSPRNG session secret & salted hash engine
│   │   ├── session_store.py      # Secure atomic 0600 session persistence
│   │   └── progress.py           # User completion tracker
│   └── ui/
│       ├── app.py                # Textual TUI dashboard implementation
│       ├── styles.tcss           # Terminal CSS styling and responsive layout
│       └── screens/              # Modal dialogs (SubmitModal, ConfirmCleanModal)
├── scripts/
│   ├── lab.sh                    # Player bash runner utility
│   └── tui.sh                    # TUI launcher script (automatic venv setup)
├── tests/                        # Automated unit and integration test suite
├── requirements.txt              # Minimal Python dependencies (textual, rich)
├── .gitignore                    # Git exclusions
└── README.md                     # Player documentation
```
