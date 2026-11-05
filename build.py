"""Baut rmgrab für den reMarkable Paper Pro (Linux, ARM64, statisch).

Läuft unter macOS, Linux und Windows: `uv run build.py` oder `python build.py`.
"""
import os
import subprocess
from pathlib import Path

env = {**os.environ, "CGO_ENABLED": "0", "GOOS": "linux", "GOARCH": "arm64"}
subprocess.run(
    ["go", "build", "-trimpath", "-ldflags=-s -w", "-o", "rmgrab-linux-arm64", "."],
    cwd=Path(__file__).parent / "rmgrab", env=env, check=True,
)
