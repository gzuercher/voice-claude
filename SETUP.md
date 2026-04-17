# VoiceClaude Setup

## Directory structure on VPS
```
/opt/voiceclaude/
  server.py
  pwa/
    index.html
    manifest.json
    sw.js
    icon.svg
```

## 1. Dependencies
```bash
pip install fastapi uvicorn python-multipart
```

Claude Code must be installed and authenticated:
```bash
npm install -g @anthropic-ai/claude-code
claude login
```

## 2. Start
```bash
export API_TOKEN="your-secure-token"          # required!
export ALLOWED_ORIGIN="https://your-server.example.com"
uvicorn server:app --host 127.0.0.1 --port 8000
```

> **Warning:** Never run without `API_TOKEN` on a public server. The server logs a warning if no token is set.

## 3. HTTPS (required for Web Speech API)
Using Caddy (simplest option):
```
# Caddyfile
your-server.example.com {
  reverse_proxy localhost:8000
}
```
```bash
apt install caddy
caddy run
```

## 4. Set up as systemd service
```ini
# /etc/systemd/system/voiceclaude.service
[Unit]
Description=VoiceClaude
After=network.target

[Service]
WorkingDirectory=/opt/voiceclaude
Environment="API_TOKEN=your-secure-token"
Environment="ALLOWED_ORIGIN=https://your-server.example.com"
ExecStart=uvicorn server:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
systemctl enable --now voiceclaude
```

## 5. Install PWA on Pixel
1. Open Chrome → https://your-server.example.com
2. Three-dot menu → "Add to Home screen"
3. Done

## App settings
- Server URL: `https://your-server.example.com/prompt`
- API Token: the token you configured
