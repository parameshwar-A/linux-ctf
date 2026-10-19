#!/usr/bin/env python3
from __future__ import annotations
import sys
from linux_ctf.ui.app import run_app

if __name__ == "__main__":
    if len(sys.argv) > 1:
        from linux_ctf.cli import main
        sys.exit(main())
    else:
        run_app()
