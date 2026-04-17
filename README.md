# VoiceClaude

Sprachgesteuertes Interface für Claude Code – als PWA auf dem Handy installierbar.

Spracheingabe auf dem Pixel → Server empfängt Text → Claude Code CLI verarbeitet → Antwort zurück aufs Handy.

## Architektur

```
┌─────────────┐       HTTPS/POST        ┌─────────────────┐
│  PWA auf    │  ──────────────────────► │  FastAPI Server  │
│  Android    │  ◄────────────────────── │  (VPS / lokal)   │
│  (Chrome)   │       JSON Response      │                  │
└─────────────┘                          │  → claude -p "…" │
                                         └─────────────────┘
```

## Features

- **Web Speech API** mit `de-CH` – kontinuierliche Aufnahme ohne Auto-Stop
- **PWA** – installierbar auf dem Homescreen, Standalone-Modus
- **Token-Auth** – optionaler Bearer Token für den API-Zugriff
- **Minimales UI** – dunkles Theme, IBM Plex Mono, kein Overhead

## Dateistruktur

```
voiceclaude/
├── server.py          # FastAPI Backend, ruft claude CLI auf
├── pwa/
│   ├── index.html     # Frontend mit Speech Recognition
│   ├── manifest.json  # PWA Manifest
│   ├── sw.js          # Service Worker
│   └── icon.svg       # App Icon
└── .venv/             # Python Virtual Environment
```

## Setup (lokal)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn

uvicorn server:app --host 0.0.0.0 --port 8000
```

Dann `http://localhost:8000` in Chrome öffnen. Web Speech API funktioniert auf localhost ohne HTTPS.

## Setup (VPS mit HTTPS)

HTTPS ist Pflicht für die Web Speech API auf Android.

```bash
# 1. Server starten
API_TOKEN=dein-geheimes-token uvicorn server:app --host 127.0.0.1 --port 8000

# 2. Caddy als Reverse Proxy (automatisches HTTPS)
# Caddyfile:
# voice.example.com {
#     reverse_proxy localhost:8000
# }
```

Auf dem Pixel: Chrome → `https://voice.example.com` → Dreipunkt-Menü → „Zum Startbildschirm hinzufügen".

## Konfiguration

| Variable | Beschreibung | Default |
|---|---|---|
| `API_TOKEN` | Bearer Token für `/prompt` Endpoint | leer (kein Auth) |

Die Server-URL und der Token können auch direkt in der App unter Einstellungen (⚙) konfiguriert werden.

## API

```
POST /prompt
Content-Type: application/json
Authorization: Bearer <token>  (optional)

{"text": "Deine Anweisung an Claude"}

→ {"response": "Antwort von Claude"}
```

## Voraussetzungen

- Python 3.10+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installiert und eingeloggt
- Chrome (Desktop oder Android) für Web Speech API
