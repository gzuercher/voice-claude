# VoiceClaude Setup

## Option A: Docker (recommended)

### 1. Clone and configure
```bash
git clone git@github.com:gzuercher/voice-claude.git
cd voice-claude
cp .env.example .env
# Edit .env with your tokens and target URLs
```

### 2. Start
```bash
docker compose up -d
```

Default instances:
- **Claude** → http://localhost:8001
- **Dokbot** → http://localhost:8002

### 3. Add more instances
Add a new service to `docker-compose.yml`:
```yaml
notes:
  build: .
  ports:
    - "8003:8000"
  environment:
    - INSTANCE_NAME=Notizen
    - INSTANCE_COLOR=#ff6b6b
    - TARGET_URL=http://host.docker.internal:9002/notes
    - API_TOKEN=${API_TOKEN_NOTES:-}
```

## Option B: Direct (without Docker)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn httpx

export INSTANCE_NAME="Claude"
export INSTANCE_COLOR="#c8ff00"
export TARGET_URL="http://localhost:9000/prompt"
export API_TOKEN="your-secure-token"          # required for production!
uvicorn server:app --host 127.0.0.1 --port 8000
```

> **Warning:** Never run without `API_TOKEN` on a public server.

## HTTPS (required for Web Speech API on Android)

Using Caddy (automatic HTTPS):
```
# Caddyfile
claude.example.com {
  reverse_proxy localhost:8001
}
dokbot.example.com {
  reverse_proxy localhost:8002
}
```
```bash
apt install caddy
caddy run
```

## Systemd (per instance)

```ini
# /etc/systemd/system/voiceclaude-claude.service
[Unit]
Description=VoiceClaude - Claude
After=network.target

[Service]
WorkingDirectory=/opt/voiceclaude
Environment="INSTANCE_NAME=Claude"
Environment="INSTANCE_COLOR=#c8ff00"
Environment="TARGET_URL=http://localhost:9000/prompt"
Environment="API_TOKEN=your-secure-token"
Environment="ALLOWED_ORIGIN=https://claude.example.com"
ExecStart=uvicorn server:app --host 127.0.0.1 --port 8001
Restart=always

[Install]
WantedBy=multi-user.target
```

## Install PWA on Pixel

1. Open Chrome → https://claude.example.com
2. Three-dot menu → "Add to Home screen"
3. Repeat for each instance (different URL = different PWA)

## Target Backend Contract

Any HTTP service that accepts this request works as a target:

```
POST <TARGET_URL>
Content-Type: application/json
Authorization: Bearer <TARGET_TOKEN>

{"text": "voice input text"}
→ {"response": "answer"}
```

### Example: Claude Code wrapper

A minimal target that runs Claude Code CLI:

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

This runs on the machine where Claude Code is installed (e.g. your Mac).
