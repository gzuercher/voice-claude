# VoxGate Setup

Ausführliche Anleitung für System-Betreiber. Für die Übersicht siehe [`README.md`](README.md).

## Variante A: Docker (empfohlen)

### 1. Klonen und konfigurieren

```bash
git clone git@github.com:gzuercher/vox-gate.git
cd vox-gate
cp .env.example .env
# .env editieren — siehe nächster Abschnitt
```

### 2. `.env` ausfüllen

Mindestens **eines** der folgenden Backends konfigurieren:

**Direct-Claude (einfachster Weg):**
```bash
ANTHROPIC_API_KEY=sk-ant-...
SYSTEM_PROMPT=Du bist ein hilfreicher Assistent. Antworte knapp.
API_TOKEN_CLAUDE=ein-zufaelliger-langer-string
```

**Eigenes Backend per Forwarding:**
```bash
TARGET_URL=http://host.docker.internal:9000/prompt
TARGET_TOKEN=optional-bearer-token
API_TOKEN_CLAUDE=ein-zufaelliger-langer-string
```

> ⚠️ **Wichtig:** Setze `API_TOKEN_*` immer, sobald der Server von aussen erreichbar ist. Ohne Token kann jeder Anfragen stellen — bei aktivem `/claude` zahlst du die Anthropic-Rechnung für Fremde.
>
> Seit der Security-Härtung **weigert sich der Server zu starten**, wenn ein Backend konfiguriert ist und `API_TOKEN` leer. Nur `VOXGATE_ALLOW_OPEN=1` umgeht das (lokale Entwicklung).
>
> Token generieren: `openssl rand -hex 32`

### 3. Starten

```bash
docker compose up -d
```

Default-Instanzen:
- **Claude** → http://localhost:8001
- **Dokbot** → http://localhost:8002

### 4. Weitere Instanzen

In `docker-compose.yml` einen Service ergänzen:

```yaml
notes:
  build: .
  ports:
    - "8003:8000"
  environment:
    - INSTANCE_NAME=Notizen
    - INSTANCE_COLOR=#ff6b6b
    - SPEECH_LANG=de-CH
    - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    - SYSTEM_PROMPT=Du bist ein Notiz-Assistent.
    - API_TOKEN=${API_TOKEN_NOTES:-}
    - ALLOWED_ORIGIN=https://notizen.example.com
```

## Variante B: Direkt (ohne Docker)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
# Installiert fastapi, uvicorn, httpx, anthropic plus Dev-Tools

export INSTANCE_NAME="Claude"
export INSTANCE_COLOR="#c8ff00"
export ANTHROPIC_API_KEY="sk-ant-..."
export API_TOKEN="dein-langer-zufaelliger-token"
export ALLOWED_ORIGIN="https://claude.example.com"

uvicorn server:app --host 127.0.0.1 --port 8000
# WICHTIG: kein --workers N — siehe Skalierungshinweis in README
```

> ⚠️ **Niemals** ohne `API_TOKEN` auf einem öffentlich erreichbaren Server betreiben.

## HTTPS (Pflicht für Web Speech API auf Android)

Caddy mit automatischen Zertifikaten:

```
# Caddyfile
claude.example.com {
  reverse_proxy localhost:8001
}
dokbot.example.com {
  reverse_proxy localhost:8002
}
```

Caddy setzt `X-Forwarded-For` automatisch. Damit Rate-Limit auf die echte Client-IP greift, in `.env` zusätzlich:

```bash
TRUST_PROXY_HEADERS=1
```

> ⚠️ `TRUST_PROXY_HEADERS=1` nur einschalten, wenn der Server **ausschliesslich** über den Proxy erreichbar ist. Sonst kann der Client `X-Forwarded-For` selbst setzen und das Rate-Limit umgehen.

```bash
apt install caddy
caddy run --config /etc/caddy/Caddyfile
```

## Systemd (eine Unit pro Instanz)

```ini
# /etc/systemd/system/voxgate-claude.service
[Unit]
Description=VoxGate - Claude
After=network.target

[Service]
WorkingDirectory=/opt/voxgate
Environment="INSTANCE_NAME=Claude"
Environment="INSTANCE_COLOR=#c8ff00"
Environment="SPEECH_LANG=de-CH"
Environment="ANTHROPIC_API_KEY=sk-ant-..."
Environment="SYSTEM_PROMPT=Du bist ein hilfreicher Assistent. Antworte knapp."
Environment="API_TOKEN=langer-zufaelliger-token"
Environment="ALLOWED_ORIGIN=https://claude.example.com"
# Kein --workers N — Sessions werden In-Memory gehalten (siehe README "Skalierung")
ExecStart=/opt/voxgate/.venv/bin/uvicorn server:app --host 127.0.0.1 --port 8001
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable --now voxgate-claude
journalctl -u voxgate-claude -f
```

## PWA auf dem Pixel installieren

1. Chrome öffnen → https://claude.example.com
2. Drei-Punkte-Menü → "Zum Startbildschirm hinzufügen"
3. Für jede Instanz wiederholen — verschiedene URL = verschiedene PWA mit eigener Farbe und eigenem Icon.

## Eigenes Backend für `/prompt`

Jeder HTTP-Service, der diesen Vertrag erfüllt, funktioniert als Ziel:

```
POST <TARGET_URL>
Content-Type: application/json
Authorization: Bearer <TARGET_TOKEN>     # falls TARGET_TOKEN gesetzt

{"text": "voice input text"}
→ {"response": "Antwort"}
```

### Beispiel: Claude-Code-Wrapper

Ein minimales Backend, das die Claude-Code-CLI aufruft:

```python
from fastapi import FastAPI
from pydantic import BaseModel
import subprocess

app = FastAPI()

class Req(BaseModel):
    text: str

@app.post("/prompt")
async def prompt(req: Req):
    result = subprocess.run(
        ["claude", "-p", req.text],
        capture_output=True, text=True, timeout=120,
    )
    return {"response": result.stdout.strip()}
```

Läuft auf der Maschine, auf der Claude Code installiert ist (z.B. dein Mac). VoxGate läuft auf dem Server und leitet weiter.

## Wartung & Betrieb

- **Logs:** `docker compose logs -f` bzw. `journalctl -u voxgate-* -f`
- **Update:** `git pull && docker compose build && docker compose up -d`
- **Sessions:** werden im Speicher gehalten, gehen beim Neustart verloren. Das ist beabsichtigt für eine leichtgewichtige Installation.
- **Anthropic-Kosten überwachen:** Dashboard auf console.anthropic.com nutzen, ggf. Spending Limits setzen.
- **Single-Worker-Constraint beachten:** Siehe Abschnitt "Skalierung" in der `README.md`.
