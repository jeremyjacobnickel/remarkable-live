# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "mcp>=1.2,<2",
# ]
# ///
"""MCP-Server: zeigt Claude live, was gerade auf dem reMarkable offen ist.

Das Hilfsprogramm rmgrab läuft per SSH auf dem Tablet, liest den
Bildpuffer der Oberfläche direkt aus dem Speicher und liefert ein PNG.
Weder Desktop-App noch Cloud-Sync sind beteiligt.
"""

import hashlib
import os
import subprocess
import tempfile
import time
from pathlib import Path

from mcp.server.fastmcp import FastMCP, Image

HOST = os.environ.get("REMARKABLE_HOST", "remarkable")
REMOTE_BINARY = "/home/root/rmgrab"
LOCAL_BINARY = Path(__file__).parent / "rmgrab" / "rmgrab-linux-arm64"
SSH_OPTIONS = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=5"]
COMMAND_NOT_FOUND = 127
MAX_IMAGE_SIDE = 1600
POLL_INTERVAL_SECONDS = 1.0

mcp = FastMCP("remarkable-live")
_last_hash: str | None = None


def _run_grabber() -> subprocess.CompletedProcess:
    return subprocess.run(
        ["ssh", *SSH_OPTIONS, HOST, REMOTE_BINARY], capture_output=True, timeout=30
    )


def _deploy_grabber() -> None:
    if not LOCAL_BINARY.exists():
        raise RuntimeError(f"{LOCAL_BINARY} fehlt – zuerst ./build.sh ausführen.")
    subprocess.run(
        ["scp", "-q", *SSH_OPTIONS, str(LOCAL_BINARY), f"{HOST}:{REMOTE_BINARY}"],
        capture_output=True,
        check=True,
        timeout=60,
    )


def grab_png() -> bytes:
    """Aktueller Tablet-Bildschirm als PNG (lange Seite max. 1600 px)."""
    result = _run_grabber()
    if result.returncode == COMMAND_NOT_FOUND:
        _deploy_grabber()
        result = _run_grabber()
    if result.returncode != 0:
        raise RuntimeError(
            f"Bild vom reMarkable ({HOST}) konnte nicht geholt werden: "
            f"{result.stderr.decode(errors='replace').strip()}. Ist das Tablet "
            "per USB verbunden (bzw. SSH über WLAN aktiv) und entsperrt?"
        )

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "screen.png"
        path.write_bytes(result.stdout)
        subprocess.run(
            ["sips", "-Z", str(MAX_IMAGE_SIDE), str(path)], capture_output=True, check=True
        )
        return path.read_bytes()


@mcp.tool()
def remarkable_live_screen(wait_for_change_seconds: int = 0) -> list:
    """Zeigt, was gerade auf dem reMarkable-Bildschirm zu sehen ist (live).

    Liest den Bildschirminhalt direkt vom Tablet – ohne Cloud-Sync und ohne
    Desktop-App.

    wait_for_change_seconds: > 0 wartet bis zu so viele Sekunden, bis sich der
    Bildschirm gegenüber dem zuletzt gelieferten Bild ändert (zum
    Mitverfolgen beim Schreiben). 0 liefert sofort das aktuelle Bild.
    """
    global _last_hash
    data = grab_png()
    deadline = time.monotonic() + max(0, wait_for_change_seconds)
    changed = hashlib.sha256(data).hexdigest() != _last_hash
    while not changed and time.monotonic() < deadline:
        time.sleep(POLL_INTERVAL_SECONDS)
        data = grab_png()
        changed = hashlib.sha256(data).hexdigest() != _last_hash

    _last_hash = hashlib.sha256(data).hexdigest()
    status = "geändert" if changed else "unverändert seit letztem Abruf"
    return [Image(data=data, format="png"), f"reMarkable-Bildschirm {status}"]


if __name__ == "__main__":
    mcp.run()
