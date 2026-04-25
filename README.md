# VoxGate

**Sprich mit Claude (oder einem anderen Chatbot) per Stimme — direkt von deinem Handy.**

VoxGate ist eine kleine Web-App, die du wie eine native App auf deinem Smartphone-Homescreen installierst. Du tippst auf den Mikrofon-Knopf, sprichst, und bekommst die Antwort vorgelesen. Es funktioniert in Deutsch und Französisch (Schweiz) und kann mehrere Backends gleichzeitig bedienen.

## Was kann ich damit machen?

- **Direkt mit Claude sprechen** — du gibst einen Anthropic-API-Key an und VoxGate spricht direkt mit Claude. Konversationen bleiben innerhalb einer Session erhalten.
- **Eigene Backends ansprechen** — z.B. ein Skript auf deinem Mac, das Claude Code im Terminal ausführt. VoxGate leitet deine gesprochene Frage als HTTP-POST weiter.
- **Mehrere Instanzen parallel betreiben** — z.B. eine grüne PWA "Claude" und eine blaue PWA "Dokbot", jede mit eigenem Symbol auf dem Homescreen.

Typische Anwendung: Du gehst spazieren, tippst auf das Claude-Icon, fragst "Wie spät ist es in Tokio?" und hörst die Antwort, ohne tippen zu müssen.

## Bedienung (für Endbenutzer)

Nach Installation als PWA auf dem Homescreen öffnest du die App und siehst:

| Element | Funktion |
|---|---|
| **Mikrofon-Knopf (gross)** | Tippen = Aufnahme starten. Erneut tippen = senden. |
| **Sprache (oben links)** | Zwischen `DE-CH` und `FR-CH` umschalten. Wahl wird gespeichert. |
| **Lautsprecher (oben rechts)** | Sprachausgabe stumm/laut schalten. |
| **Status-Punkt (oben rechts)** | Grün = bereit, blinkend = sendet, rot = Fehler. |
| **Neues Gespräch (unten)** | Setzt den Konversationsverlauf zurück. |

Antworten werden automatisch vorgelesen, sofern nicht stumm geschaltet. Tippst du während der Wiedergabe erneut auf das Mikro, wird die laufende Stimme abgebrochen.

### Voraussetzungen

- **Browser:** Chrome auf Android oder Desktop (Web Speech API). Safari/iOS hat eingeschränkte Unterstützung.
- **Mikrofon-Berechtigung** beim ersten Start zulassen.
- **HTTPS** ist auf Android Pflicht — siehe Setup unten.

## Architektur

```
┌─────────────┐                             ┌──────────────────┐
│  PWA        │     POST /claude            │                  │     Anthropic API
│  (Smartphone│  ────────────────────────►  │  VoxGate Server  │  ────────────────────►  Claude
│  Homescreen)│  ◄────────────────────────  │  (FastAPI)       │  ◄────────────────────  (claude-sonnet-4-5)
│             │                             │                  │
│             │     POST /prompt            │                  │     POST TARGET_URL
│             │  ────────────────────────►  │                  │  ────────────────────►  Eigenes Backend
│             │  ◄────────────────────────  │                  │  ◄────────────────────  (z.B. Mac mit Claude Code)
└─────────────┘                             └──────────────────┘
```

Der Server kennt zwei Endpoints:

- **`/claude`** — direkt zur Anthropic-API. Behält Konversationsverlauf pro Session. Nutzt `ANTHROPIC_API_KEY`.
- **`/prompt`** — leitet an ein eigenes Backend weiter (`TARGET_URL`). Stateless. Hat den Originalzweck "Voice-Gateway für irgendeinen Chatbot".

Die PWA verwendet `/claude`. `/prompt` bleibt aus Kompatibilität erhalten und kann mit eigenen Clients genutzt werden.

## Schnellstart (Docker, empfohlen)

```bash
git clone git@github.com:gzuercher/vox-gate.git
cd vox-gate
cp .env.example .env
# .env editieren — mindestens ANTHROPIC_API_KEY setzen
docker compose up -d
```

Default:
- **Claude** auf `http://localhost:8001` (grün)
- **Dokbot** auf `http://localhost:8002` (blau)

## Konfiguration

Alles über Umgebungsvariablen.

### Allgemein

| Variable | Beschreibung | Default |
|---|---|---|
| `INSTANCE_NAME` | Name im UI-Header | `VoxGate` |
| `INSTANCE_COLOR` | Akzentfarbe (Hex) | `#c8ff00` |
| `SPEECH_LANG` | Default-Sprache (Web Speech API) | `de-CH` |
| `MAX_PROMPT_LENGTH` | Maximale Textlänge | `4000` |
| `REQUEST_TIMEOUT` | Timeout für ausgehende Requests (Sekunden) | `120` |
| `API_TOKEN` | Bearer-Token für VoxGate selbst | *(leer, Server startet nicht falls Backend gesetzt)* |
| `ALLOWED_ORIGIN` | Erlaubter CORS-Origin | *(leer, blockiert)* |
| `RATE_LIMIT_PER_MINUTE` | Anfragen/Minute pro IP für `/claude` und `/prompt` | `30` |
| `SESSION_TTL_SECONDS` | Lebensdauer einer Session ohne Aktivität | `1800` |
| `MAX_SESSIONS` | Globales Cap an gleichzeitig gehaltenen Sessions | `1000` |
| `TRUST_PROXY_HEADERS` | `1` falls VoxGate hinter Caddy/Nginx läuft (X-Forwarded-For) | `0` |
| `VOXGATE_ALLOW_OPEN` | `1` umgeht den Fail-Loud-Start (nur lokale Entwicklung) | *(leer)* |

### Direct-Claude-Backend (`/claude`)

| Variable | Beschreibung | Default |
|---|---|---|
| `ANTHROPIC_API_KEY` | API-Key von console.anthropic.com | *(leer, /claude liefert 503)* |
| `SYSTEM_PROMPT` | System-Prompt für Claude | `You are a helpful assistant. Answer concisely.` |
| `CLAUDE_MODEL` | Anthropic-Modell-ID | `claude-sonnet-4-5` |

> ⚠️ **Kostenhinweis:** Anthropic-API-Aufrufe sind kostenpflichtig. Setze ein `API_TOKEN`, bevor du den Server öffentlich exponierst, sonst können Fremde auf deine Rechnung Anfragen stellen.

### Forwarding-Backend (`/prompt`)

| Variable | Beschreibung | Default |
|---|---|---|
| `TARGET_URL` | URL des eigenen Backends | *(leer, /prompt liefert 503)* |
| `TARGET_TOKEN` | Bearer-Token für das Ziel-Backend | *(leer)* |

## API-Referenz

### `POST /claude`

Direkter Anthropic-Aufruf mit Session-Verlauf.

```json
POST /claude
Authorization: Bearer <API_TOKEN>     // falls API_TOKEN gesetzt
Content-Type: application/json

{
  "text": "Wie spät ist es in Tokio?",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

Antwort:

```json
{ "response": "Aktuell ist es in Tokio …" }
```

Fehler:
- `401` — Token fehlt oder falsch
- `422` — Validierung fehlgeschlagen (`text` zu lang/leer, `session_id` fehlt)
- `502` — Anthropic-API-Fehler
- `503` — `ANTHROPIC_API_KEY` nicht konfiguriert

Verlauf: bis zu 20 Nachrichten pro `session_id` werden In-Memory gehalten; ältere werden paarweise verworfen.

### `POST /prompt`

Reines Forwarding zu `TARGET_URL`.

```json
POST /prompt
Authorization: Bearer <API_TOKEN>
Content-Type: application/json

{ "text": "Hallo Backend" }
```

VoxGate sendet weiter:

```json
POST <TARGET_URL>
Authorization: Bearer <TARGET_TOKEN>   // falls gesetzt
Content-Type: application/json

{ "text": "Hallo Backend" }
```

Das Backend muss JSON mit Feld `response` (oder `text`) zurückgeben.

### `GET /config`

Liefert Instanz-Konfiguration für die PWA. Kein Auth.

```json
{ "name": "Claude", "color": "#c8ff00", "lang": "de-CH", "maxLength": 4000 }
```

## PWA-Installation

1. Chrome auf Android öffnen → `https://claude.example.com`
2. Drei-Punkte-Menü → "Zum Startbildschirm hinzufügen"
3. Für jede Instanz wiederholen — jedes Icon öffnet eine eigene PWA mit eigener Farbe.

## HTTPS (Pflicht für Android)

Caddy als Reverse-Proxy mit automatischen Zertifikaten:

```
# Caddyfile
claude.example.com {
    reverse_proxy localhost:8001
}
dokbot.example.com {
    reverse_proxy localhost:8002
}
```

Details, Systemd-Units und ein Beispiel-Backend findest du in [`SETUP.md`](SETUP.md).

## Troubleshooting

| Problem | Ursache / Lösung |
|---|---|
| Mikrofon reagiert nicht | Berechtigung im Browser erteilen. Auf Android nur über HTTPS. |
| Keine Sprachausgabe | Prüfe den Lautsprecher-Knopf (oben rechts). iOS unterstützt Web Speech eingeschränkt. |
| `503` bei `/claude` | `ANTHROPIC_API_KEY` ist nicht gesetzt. |
| `401` | `API_TOKEN` falsch oder fehlend. Token in `localStorage.apiToken` setzen oder Header senden. |
| Konversation "vergisst" plötzlich | Wahrscheinlich mit mehreren Workern gestartet — siehe Skalierung. |
| Funktioniert auf Safari/iOS nicht richtig | Web Speech API ist dort eingeschränkt; Chrome empfohlen. |

## Sicherheit

VoxGate ist auf öffentlichen Betrieb ausgelegt. Eingebaute Schutzmassnahmen:

| Mechanismus | Wirkung |
|---|---|
| **Fail-Loud-Start** | Server weigert sich zu starten, wenn ein Backend (`ANTHROPIC_API_KEY` oder `TARGET_URL`) konfiguriert ist, aber `API_TOKEN` leer. Nur `VOXGATE_ALLOW_OPEN=1` umgeht das (lokale Entwicklung). |
| **Timing-sichere Token-Prüfung** | Bearer-Token-Vergleich via `secrets.compare_digest`. |
| **Rate-Limiting** | `RATE_LIMIT_PER_MINUTE` Anfragen pro IP für `/claude` und `/prompt`. Default 30/min. |
| **Session-TTL** | Sessions ohne Aktivität nach `SESSION_TTL_SECONDS` (default 30 Min) verworfen. |
| **Session-Cap** | Max. `MAX_SESSIONS` parallele Sessions; älteste rausgeworfen. |
| **`session_id`-Validierung** | Pattern `^[A-Za-z0-9_-]{8,128}$`. Steuerzeichen, Newlines etc. abgewiesen. |
| **Security-Header** | `Content-Security-Policy` (strikt, kein Inline-Script), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` (nur Mikrofon). |
| **Audit-Log** | Jede Anfrage wird mit IP, Session-Präfix und Textlänge geloggt (kein Inhalt). 429 und Backend-Fehler ebenfalls. |
| **CORS** | Default leer = blockiert. `ALLOWED_ORIGIN` explizit setzen. |

### Operative Pflichten

- **`API_TOKEN`** zwingend vor öffentlicher Erreichbarkeit setzen — möglichst lang (≥32 Zeichen, generiert via `openssl rand -hex 32`).
- **`TRUST_PROXY_HEADERS=1`** setzen, sobald VoxGate hinter Caddy/Nginx läuft, damit das Rate-Limit auf die echte Client-IP wirkt statt auf die Proxy-IP. Nur einschalten, wenn der Proxy `X-Forwarded-For` zuverlässig setzt — sonst fälscht der Client sich seine IP.
- **Anthropic-Spending-Limit** im Console-Dashboard setzen, als Versicherung gegen Token-Leak.
- **Caddy-CSP-Override** vermeiden: VoxGate setzt CSP selbst — Caddy nicht zusätzlich `header` für CSP konfigurieren.
- **Key-Rotation:** `ANTHROPIC_API_KEY` wird beim ersten `/claude`-Aufruf gecacht. Nach Rotation Container/Prozess neu starten.

### Verbleibende Risiken

- **localStorage-XSS:** Das Bearer-Token (falls genutzt vom PWA-Client) liegt in `localStorage`. CSP blockiert Inline-Scripts, aber jede zukünftige `innerHTML`-Verwendung mit Antwortdaten würde das Token gefährden. Bei Code-Änderungen am PWA-Output beachten.
- **In-Memory-Sessions:** Verläufe leben nur im Prozess. Bei Neustart weg. Kein Datenträger-Leak — bewusst so.
- **Kein Per-Benutzer-Rate-Limit:** Rate-Limit ist pro IP. Hinter NAT/CGNAT teilen sich Benutzer ein Limit.

## Skalierung & Deployment-Beschränkungen

**VoxGate muss mit genau einem Uvicorn-Worker pro Prozess laufen.** Der `/claude`-Endpoint hält den Konversationsverlauf pro `session_id` in einem In-Memory-Dict. Jeder Worker-Prozess hat eine eigene Kopie — Anfragen, die auf unterschiedlichen Workern landen, sehen unterschiedliche (oder leere) Verläufe. Für Benutzer wirkt das wie sporadischer "Gedächtnisverlust" mitten im Gespräch.

Das mitgelieferte `Dockerfile` und `docker-compose.yml` starten bereits einen einzelnen Worker — out-of-the-box ist also alles in Ordnung.

### Warum sollte man überhaupt skalieren?

Drei typische Motive — für VoxGate aktuell alle nicht akut:

1. **CPU-Auslastung.** Pythons GIL begrenzt einen Prozess auf einen Kern. Mehrere Worker = mehrere Kerne. Hier irrelevant: der Server ist I/O-bound (er wartet nur auf Anthropic). Ein async-Worker bedient hunderte parallele Anfragen.
2. **Durchsatz / parallele Benutzer.** Viele gleichzeitig aktive Sessions könnten einen Worker auslasten. Eine private oder familiengrosse Installation erreicht das nie.
3. **Hochverfügbarkeit.** Mehrere Container hinter einem Load Balancer überleben den Ausfall einer einzelnen Instanz. Das wahrscheinlichste reale Motiv, sobald VoxGate für mehrere Personen läuft.

### Implikationen

- Setze **kein** `--workers N` (N > 1) bei `uvicorn`.
- Stelle **keine** mehreren VoxGate-Container hinter einen Load Balancer mit aktivem `/claude`, ausser mit Sticky Sessions konfiguriert (und selbst das ist beim Container-Neustart fragil).
- Verläufe gehen beim Container-Neustart verloren — das ist ein bewusstes Design für eine leichtgewichtige Installation.
- `/prompt` ist stateless und unbetroffen — den Teil zu skalieren ist unproblematisch.

### Migrationspfad (falls Skalierung nötig wird)

Das `_sessions`-Dict aus dem Prozess-Speicher in einen geteilten Store auslagern. Redis ist die Standardwahl: jeder Worker liest/schreibt aus Redis, alle Worker bleiben synchron, Sessions überleben Neustarts. Erfordert eine zusätzliche Abhängigkeit und Anpassung von `server.py`.

## Dateistruktur

```
voxgate/
├── server.py              # FastAPI-Gateway (/claude, /prompt, /config)
├── pwa/
│   ├── index.html         # Voice-UI mit TTS, Sprach-Toggle, Sessions
│   ├── manifest.json      # PWA-Manifest
│   ├── sw.js              # Service Worker
│   └── icon.svg           # App-Icon
├── tests/
│   └── test_server.py     # pytest-Tests (Endpoints, Auth, Sessions)
├── .claude/
│   └── rules/             # Code-Regeln für Claude Code (security, quality, …)
├── .env.example           # Vorlage für Konfiguration
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── Makefile               # make setup/run/test/lint
├── CLAUDE.md              # Playbook für Claude Code
├── CONTRIBUTING.md        # Mitwirken
├── SETUP.md               # Detaillierte Setup-Anleitung
└── lessons.md             # Lernerfahrungen
```

## Entwicklung

```bash
make setup          # venv anlegen, Abhängigkeiten installieren
make run            # Server lokal starten
make test           # pytest
make lint           # ruff
make format         # ruff format
make check          # lint + test
```

Siehe [`CONTRIBUTING.md`](CONTRIBUTING.md) für Details zu Konventionen und Workflow.

## Voraussetzungen

- Python 3.10+ (oder Docker)
- Chrome (Desktop oder Android) für die Web Speech API
- Anthropic-API-Key (für `/claude`) oder ein eigenes Backend (für `/prompt`)

## Lizenz

MIT
