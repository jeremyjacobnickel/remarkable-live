# remarkable-live

MCP-Server, über den Claude live sieht, was gerade auf dem reMarkable Paper Pro
geöffnet ist – während du schreibst, ohne Cloud-Sync und ohne Desktop-App.

## Wie es funktioniert

`rmgrab` (Go, statisch für Linux/ARM64) läuft per SSH auf dem Tablet. Es liest
den Qt-Bildpuffer der Oberfläche `xochitl` direkt aus `/proc/<pid>/mem`
(1632×2160, BGRA, rechts 12 px Polsterung), schneidet ihn auf 1620×2160 zu und
schreibt ein PNG nach stdout. Ein Abruf dauert per USB etwa 0,8 s.

Der Puffer ist ein per mmap angelegter malloc-Chunk mit wechselnder Adresse.
`rmgrab` sucht ihn in den anonymen Speicherbereichen über Chunk-Größe und
deckenden Alpha-Kanal (unterscheidet ihn vom ähnlich großen Puffer des
E-Ink-Treibers) und merkt sich die Adresse pro xochitl-Prozess in
`/tmp/rmgrab.cache`.

Tool: `remarkable_live_screen(wait_for_change_seconds=0)`

- `0` – aktuelles Bild sofort.
- `> 0` – wartet bis zu N Sekunden, bis sich der Bildschirm seit dem letzten
  Abruf ändert (zum Mitverfolgen beim Schreiben).

## Voraussetzungen

- Entwicklermodus am Tablet aktiv, SSH-Schlüssel installiert
  (`ssh-copy-id -i ~/.ssh/id_rsa_remarkable.pub root@10.11.99.1`).
- `REMARKABLE_HOSTS`: SSH-Ziele, durch Komma getrennt, z. B.
  `remarkable,root@192.168.178.154` (USB-Alias aus `~/.ssh/config`, dann WLAN).
  Der Server probiert sie der Reihe nach, den zuletzt erreichbaren zuerst.
  Schlüssel: `REMARKABLE_SSH_KEY` (Standard `~/.ssh/id_rsa_remarkable`).
- Für WLAN: auf dem Tablet einmal `rm-ssh-over-wlan on` (bleibt über Neustarts
  aktiv) und im Router eine feste IP für das Tablet vergeben.

Fehlt `rmgrab` auf dem Tablet (z. B. nach Zurücksetzen), spielt der Server es
automatisch per `scp` nach `/home/root/rmgrab` auf.

## Installation

```bash
./build.sh
claude mcp add --scope user remarkable-live -e REMARKABLE_HOSTS=remarkable,root@192.168.178.154 -- /opt/homebrew/bin/uv run -q --script ~/Programmieren/remarkable-live/server.py
```

Für Claude Desktop in `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
"remarkable-live": {
  "command": "/opt/homebrew/bin/uv",
  "args": ["run", "-q", "--script", "/Users/Jeremy/Programmieren/remarkable-live/server.py"],
  "env": {"REMARKABLE_HOSTS": "remarkable,root@192.168.178.154"}
}
```

## Tests

```bash
(cd rmgrab && go test ./...)
uv run --with 'mcp<2' --with pytest pytest -q
```
