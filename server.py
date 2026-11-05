# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "mcp>=1.2,<2",
#     "pillow>=10",
# ]
# ///
"""MCP-Server: zeigt Claude live, was gerade auf dem reMarkable offen ist.

Das Hilfsprogramm rmgrab läuft per SSH auf dem Tablet, liest den
Bildpuffer der Oberfläche direkt aus dem Speicher und liefert ein PNG.
Weder Desktop-App noch Cloud-Sync sind beteiligt.
"""

import hashlib
import io
import os
import subprocess
import time
from pathlib import Path

from mcp.server.fastmcp import FastMCP, Image
from PIL import Image as PILImage

# SSH-Ziele in Reihenfolge, z. B. USB-Alias und WLAN-Adresse.
HOSTS = os.environ.get("REMARKABLE_HOSTS", "remarkable").split(",")
SSH_KEY = Path(os.environ.get("REMARKABLE_SSH_KEY", "~/.ssh/id_rsa_remarkable")).expanduser()
REMOTE_BINARY = "/home/root/rmgrab"
LOCAL_BINARY = Path(__file__).parent / "rmgrab" / "rmgrab-linux-arm64"
SSH_OPTIONS = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=3", "-i", str(SSH_KEY)]
SSH_CONNECTION_ERROR = 255
COMMAND_NOT_FOUND = 127
MAX_IMAGE_SIDE = 1600
POLL_INTERVAL_SECONDS = 1.0

mcp = FastMCP("remarkable-live")
_last_hash: str | None = None
_working_host: str | None = None


def _run_grabber(host: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["ssh", *SSH_OPTIONS, host, REMOTE_BINARY], capture_output=True, timeout=30
    )


def _deploy_grabber(host: str) -> None:
    if not LOCAL_BINARY.exists():
        raise RuntimeError(f"{LOCAL_BINARY} fehlt – zuerst ./build.sh ausführen.")
    # Über ssh statt scp: scp deutet Windows-Pfade wie C:\... als Host.
    subprocess.run(
        ["ssh", *SSH_OPTIONS, host, f"cat > {REMOTE_BINARY}.part && chmod +x {REMOTE_BINARY}.part"
         f" && mv {REMOTE_BINARY}.part {REMOTE_BINARY}"],
        input=LOCAL_BINARY.read_bytes(),
        capture_output=True,
        check=True,
        timeout=60,
    )


def _grab_from(host: str) -> subprocess.CompletedProcess:
    result = _run_grabber(host)
    if result.returncode == COMMAND_NOT_FOUND:
        _deploy_grabber(host)
        result = _run_grabber(host)
    return result


def grab_png() -> bytes:
    """Aktueller Tablet-Bildschirm als PNG (lange Seite max. 1600 px).

    Probiert die Hosts der Reihe nach, den zuletzt erreichbaren zuerst.
    """
    global _working_host
    hosts = sorted(HOSTS, key=lambda h: h != _working_host)
    errors = []
    for host in hosts:
        result = _grab_from(host)
        if result.returncode == 0:
            _working_host = host
            break
        errors.append(f"{host}: {result.stderr.decode(errors='replace').strip()}")
        if result.returncode != SSH_CONNECTION_ERROR:
            break  # Tablet erreicht, aber rmgrab selbst ist gescheitert
    if result.returncode != 0:
        raise RuntimeError(
            "Bild vom reMarkable konnte nicht geholt werden ("
            + "; ".join(errors)
            + "). Ist das Tablet per USB oder WLAN erreichbar und entsperrt?"
        )

    return shrink_png(result.stdout)


def shrink_png(png: bytes, max_side: int = MAX_IMAGE_SIDE) -> bytes:
    """PNG verkleinern, so dass die lange Seite höchstens max_side Pixel hat."""
    image = PILImage.open(io.BytesIO(png))
    image.thumbnail((max_side, max_side), PILImage.LANCZOS)
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


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
