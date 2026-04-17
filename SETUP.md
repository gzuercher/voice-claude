# VoiceClaude Setup

## Struktur auf dem VPS
```
/opt/voiceclaude/
  server.py
  pwa/
    index.html
    manifest.json
    sw.js
    icon.svg
```

## 1. Abhängigkeiten
```bash
pip install fastapi uvicorn python-multipart
```

Claude Code muss installiert und eingeloggt sein:
```bash
npm install -g @anthropic-ai/claude-code
claude login
```

## 2. Starten
```bash
export API_TOKEN="dein-sicheres-token"
uvicorn server:app --host 0.0.0.0 --port 8000
```

## 3. HTTPS (Pflicht für Web Speech API)
Mit Caddy (einfachste Option):
```
# Caddyfile
dein-server.example.com {
  reverse_proxy localhost:8000
}
```
```bash
apt install caddy
caddy run
```

## 4. Als Service einrichten
```ini
# /etc/systemd/system/voiceclaude.service
[Unit]
Description=VoiceClaude
After=network.target

[Service]
WorkingDirectory=/opt/voiceclaude
Environment="API_TOKEN=dein-sicheres-token"
ExecStart=uvicorn server:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
systemctl enable --now voiceclaude
```

## 5. PWA auf Pixel installieren
1. Chrome öffnen → https://dein-server.example.com
2. Drei Punkte → "Zum Startbildschirm hinzufügen"
3. Fertig

## Einstellungen in der App
- Server URL: `https://dein-server.example.com/prompt`
- API Token: dein gesetztes Token
