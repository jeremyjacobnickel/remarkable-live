# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "mcp>=1.2,<2",
#     "pyobjc-framework-Quartz>=10",
# ]
# ///
"""MCP-Server: zeigt Claude live, was gerade auf dem reMarkable offen ist.

Quelle ist das offizielle Screen-Share-Fenster der reMarkable-Desktop-App
(macOS). Das Tablet streamt dorthin in Echtzeit – ein Cloud-Sync ist nicht
nötig. Der Server macht davon auf Anfrage einen Fenster-Screenshot.
"""

import hashlib
import subprocess
import tempfile
import time
from pathlib import Path

import Quartz
from mcp.server.fastmcp import FastMCP, Image

APP_OWNER_NAME = "reMarkable"
SCREEN_SHARE_TITLES = {"Bildschirm teilen", "Screen share", "Screen Share"}
MIN_WINDOW_SIDE = 200
MAX_IMAGE_SIDE = 1600
POLL_INTERVAL_SECONDS = 1.0

mcp = FastMCP("remarkable-live")
_last_hash: str | None = None


def choose_window(windows: list[dict]) -> dict | None:
    """Wählt das Screen-Share-Fenster, sonst das vorderste Fenster der App.

    Quartz liefert Fenster von vorne nach hinten.
    """
    candidates = [
        w
        for w in windows
        if w.get("kCGWindowOwnerName") == APP_OWNER_NAME
        and w.get("kCGWindowLayer") == 0
        and w.get("kCGWindowIsOnscreen")
        and w["kCGWindowBounds"]["Width"] >= MIN_WINDOW_SIDE
        and w["kCGWindowBounds"]["Height"] >= MIN_WINDOW_SIDE
    ]
    for w in candidates:
        if w.get("kCGWindowName") in SCREEN_SHARE_TITLES:
            return w
    return candidates[0] if candidates else None


def capture_screen() -> tuple[bytes, str]:
    """Screenshot des Screen-Share-Fensters als PNG plus Fenstertitel."""
    windows = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID
    )
    window = choose_window(list(windows))
    if window is None:
        raise RuntimeError(
            "Kein sichtbares Fenster der reMarkable-Desktop-App gefunden. "
            "App öffnen, auf dem Tablet 'Bildschirm teilen' starten und das "
            "Fenster nicht minimieren."
        )

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "screen.png"
        result = subprocess.run(
            ["screencapture", "-x", "-o", "-l", str(window["kCGWindowNumber"]), str(path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or not path.exists():
            raise RuntimeError(
                "Fenster-Screenshot fehlgeschlagen. Der Claude-App (bzw. dem "
                "Terminal) unter Systemeinstellungen > Datenschutz & Sicherheit > "
                "Bildschirm- & Systemaudioaufnahme erlauben und neu starten. "
                f"({result.stderr.strip()})"
            )
        subprocess.run(
            ["sips", "-Z", str(MAX_IMAGE_SIDE), str(path)],
            capture_output=True,
            check=True,
        )
        data = path.read_bytes()

    title = window.get("kCGWindowName") or "(Titel nicht verfügbar)"
    return data, title


@mcp.tool()
def remarkable_live_screen(wait_for_change_seconds: int = 0) -> list:
    """Zeigt, was gerade auf dem reMarkable-Bildschirm zu sehen ist (live).

    Nutzt das Screen-Share-Fenster der reMarkable-Desktop-App, daher ohne
    Verzögerung durch Cloud-Sync. Vorher auf dem Tablet bzw. in der App
    'Bildschirm teilen' starten.

    wait_for_change_seconds: > 0 wartet bis zu so viele Sekunden, bis sich der
    Bildschirm gegenüber dem zuletzt gelieferten Bild ändert (zum
    Mitverfolgen beim Schreiben). 0 liefert sofort das aktuelle Bild.
    """
    global _last_hash
    data, title = capture_screen()
    deadline = time.monotonic() + max(0, wait_for_change_seconds)
    changed = hashlib.sha256(data).hexdigest() != _last_hash
    while not changed and time.monotonic() < deadline:
        time.sleep(POLL_INTERVAL_SECONDS)
        data, title = capture_screen()
        changed = hashlib.sha256(data).hexdigest() != _last_hash

    _last_hash = hashlib.sha256(data).hexdigest()
    status = "geändert" if changed else "unverändert seit letztem Abruf"
    return [Image(data=data, format="png"), f"Fenster: {title} – Bildschirm {status}"]


if __name__ == "__main__":
    mcp.run()
