# Backend-Beispiele

VoxGate hat zwei Endpoints:

- **`/claude`** — VoxGate ruft selbst die Anthropic-API auf. Du brauchst
  nur einen `ANTHROPIC_API_KEY` in `.env`.
- **`/prompt`** — VoxGate forwardet den Text an `TARGET_URL`. Du
  schreibst das Backend selbst (oder nutzt eines der Beispiele unten).

## `/prompt`-Backends

VoxGate sendet:

```
POST <TARGET_URL>
Authorization: Bearer <TARGET_TOKEN>      # falls gesetzt
Content-Type: application/json

{"text": "Voice-Eingabe als Text"}
```

und erwartet zurueck JSON mit einem `response`- (oder `text`-)Feld.

> ⚠️ Lass dein Backend nur auf `127.0.0.1` lauschen oder verlange selbst
> einen `TARGET_TOKEN`. Sonst macht VoxGate dein Backend ungewollt aus
> dem Internet erreichbar.

### Python / FastAPI — Claude Code Wrapper

Ruft die Claude-CLI als Subprozess auf. Mit `--continue` bleibt der
Konversationskontext erhalten:

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
        ["claude", "-p", "--continue", req.text],
        capture_output=True, text=True, timeout=120,
    )
    return {"response": result.stdout.strip()}
```

Start: `uvicorn app:app --host 127.0.0.1 --port 9000`

### Node / Express — Echo + Logik

```javascript
import express from "express";

const app = express();
app.use(express.json());

app.post("/prompt", (req, res) => {
  const text = req.body.text ?? "";
  // hier eigene Logik einklinken
  res.json({ response: `Du sagtest: ${text}` });
});

app.listen(9000, "127.0.0.1");
```

### Bash + curl — Stub fuer schnelle Tests

```bash
#!/usr/bin/env bash
# Mit `socat` oder `ncat` als 5-Zeilen-HTTP-Server. Nur fuer Tests.
while true; do
  printf 'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n%s' \
    '{"response":"ok"}' | nc -l -p 9000 -q 1
done
```

### Eigener Bot (z.B. zursetti-planner)

Wenn dein Service ohnehin schon eine HTTP-API hat, ergaenze einfach
einen `/prompt`-Endpoint, der den Vertrag erfuellt:

```
POST /prompt        →   {"response": "..."}
```

VoxGate ist agnostisch gegenueber dem, was im Backend passiert
(Datenbank, eigene LLM-Calls, Tool-Use, etc.).

## `/claude`-Clients

Wenn du VoxGate **als** Backend nutzen willst (z.B. um aus einer
eigenen App heraus Claude mit Voice/TTS-Wrapper zu erreichen):

### curl

```bash
curl -X POST https://voxgate.example.com/claude \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Was ist die Hauptstadt von Senegal?",
    "session_id": "my-app-session-001"
  }'
```

`session_id` muss `^[A-Za-z0-9_-]{8,128}$` matchen. Halte sie pro
Konversationsstrang stabil — VoxGate haelt bis zu 20 Messages
in-memory pro Session.

### Browser-Snippet

```javascript
async function ask(text) {
  const res = await fetch("https://voxgate.example.com/claude", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${localStorage.apiToken}`,
    },
    body: JSON.stringify({
      text,
      session_id: localStorage.sessionId ?? crypto.randomUUID(),
    }),
  });
  const { response } = await res.json();
  return response;
}
```

VoxGate kuemmert sich um die History — du gibst nur `text` und eine
stabile `session_id` mit.

## Fehler-Codes

| Code | Bedeutung |
|---|---|
| 401 | Token fehlt oder falsch |
| 422 | Validierung fehlgeschlagen (z.B. `text` zu lang/leer, `session_id` ungueltig) |
| 429 | Rate-Limit ueberschritten |
| 502 | Backend (Anthropic oder dein `TARGET_URL`) hat einen Fehler geliefert |
| 503 | Backend nicht konfiguriert (`ANTHROPIC_API_KEY` bzw. `TARGET_URL` leer) |
