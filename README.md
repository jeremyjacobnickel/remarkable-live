# remarkable-live

MCP-Server, über den Claude live sieht, was gerade auf dem reMarkable Paper Pro
geöffnet ist – während du schreibst, ohne auf den Cloud-Sync zu warten.

## Wie es funktioniert

Das Tablet streamt über die offizielle **Bildschirm teilen**-Funktion in die
reMarkable-Desktop-App (macOS). Der Server sucht das vorderste Fenster der App,
macht davon mit `screencapture` einen Screenshot (auch wenn es verdeckt ist),
skaliert ihn auf max. 1600 px und gibt ihn als Bild an Claude zurück.

Tool: `remarkable_live_screen(wait_for_change_seconds=0)`

- `0` – aktuelles Bild sofort.
- `> 0` – wartet bis zu N Sekunden, bis sich der Bildschirm seit dem letzten
  Abruf ändert (zum Mitverfolgen beim Schreiben).

## Benutzung

1. reMarkable-Desktop-App öffnen (Tablet und Mac im selben WLAN oder per USB).
2. Auf dem Tablet bzw. in der App **Bildschirm teilen** starten.
3. Fenster nicht minimieren (verdecken ist ok).
4. Claude fragen, z. B. „Schau auf mein reMarkable“.

Einmalig: Der Claude-App (bzw. dem Terminal, in dem Claude Code läuft) unter
*Systemeinstellungen → Datenschutz & Sicherheit → Bildschirm- & Systemaudioaufnahme*
erlauben.

## Installation

```bash
claude mcp add --scope user remarkable-live -- /opt/homebrew/bin/uv run -q --script ~/Programmieren/remarkable-live/server.py
```

Für Claude Desktop in `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
"remarkable-live": {
  "command": "/opt/homebrew/bin/uv",
  "args": ["run", "-q", "--script", "/Users/Jeremy/Programmieren/remarkable-live/server.py"]
}
```

## Tests

```bash
uv run --with 'mcp<2' --with pyobjc-framework-Quartz --with pytest pytest -q
```
