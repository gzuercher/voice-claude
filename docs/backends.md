# Backend examples

VoxGate has one chat endpoint, `/chat`. Every authenticated request is
forwarded to `TARGET_URL` using the strict JSON contract documented in
[`integration.md`](integration.md). Read that first — this
file shows minimal implementations that fulfil the contract.

What VoxGate sends:

```
POST <TARGET_URL>
Authorization: Bearer <TARGET_TOKEN>      # only if TARGET_TOKEN is set
Content-Type: application/json

{
  "user":        "voice or typed input",
  "user_email":  "alice@example.com",
  "session_id":  "550e8400-e29b-41d4-a716-446655440000",
  "metadata":    { "lang": "de-CH", "instance": "VoxGate" }
}
```

What VoxGate expects back, **strictly**:

```json
{ "response": "<assistant reply, plain string>" }
```

Anything else surfaces as `502` to the PWA — no silent passthrough.

> ⚠️ Bind your backend only to `127.0.0.1` (or a private network), or
> require a `TARGET_TOKEN` of its own. Otherwise VoxGate inadvertently
> exposes your backend to the internet.

## Python / FastAPI — minimal echo

```python
from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/")
async def chat(req: Request):
    body = await req.json()
    user = body["user"]
    email = body["user_email"]
    return {"response": f"hello {email}, you said: {user}"}
```

Run: `uvicorn app:app --host 127.0.0.1 --port 9000`

VoxGate `.env`: `TARGET_URL=http://127.0.0.1:9000/`.

## Python / FastAPI — voice-to-Claude adapter

A small adapter that forwards to the Anthropic API. This used to be
built into VoxGate; it now lives in your backend so VoxGate stays
LLM-agnostic.

```python
import os
from fastapi import FastAPI, Request
from anthropic import AsyncAnthropic

app = FastAPI()
client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# Per-session in-memory history, keyed by VoxGate's session_id.
HISTORY: dict[str, list[dict]] = {}
MAX_TURNS = 20

@app.post("/")
async def chat(req: Request):
    body = await req.json()
    sid = body["session_id"]
    history = HISTORY.setdefault(sid, [])
    history.append({"role": "user", "content": body["user"]})
    msg = await client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        system="You are a helpful assistant. Answer concisely.",
        messages=history,
    )
    reply = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
    history.append({"role": "assistant", "content": reply})
    while len(history) > MAX_TURNS:
        del history[0:2]
    return {"response": reply}
```

`pip install fastapi uvicorn anthropic`. Run on a private port and
configure `TARGET_URL=http://127.0.0.1:9000/` in VoxGate's `.env`.

## Node / Express — echo

```javascript
import express from "express";

const app = express();
app.use(express.json());

app.post("/", (req, res) => {
  const { user, user_email } = req.body;
  res.json({ response: `Hello ${user_email}, you said: ${user}` });
});

app.listen(9000, "127.0.0.1");
```

## Bash + nc — test stub

```bash
#!/usr/bin/env bash
# Tiny HTTP responder. Test use only — does not parse the request body.
while true; do
  printf 'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n%s' \
    '{"response":"ok"}' | nc -l -p 9000 -q 1
done
```

## Your own service

If your service already has an HTTP API (e.g. a planner with its own
business logic), give it an endpoint that accepts the contract above
and returns `{"response": "..."}`. The `user_email` field is verified
by VoxGate via Google Sign-In; backends can rely on it for ACL
decisions and *should not* trust any client-provided e-mail.

## Authentication scheme reminder

VoxGate is the auth boundary. By the time a request arrives at your
backend:

- The user's e-mail has been verified by Google.
- The e-mail is on the operator's `ALLOWED_EMAILS` list.
- CSRF and Origin checks have already passed.

The backend can therefore trust `user_email` and treat the request as
an authorised action by that user.

## Error codes (PWA-visible)

| Code | Meaning |
|---|---|
| 401 | Not signed in (cookie missing or expired). |
| 403 | E-mail not in `ALLOWED_EMAILS`, CSRF missing/wrong, or cross-origin. |
| 422 | Validation failed (e.g. `text` too long/empty, `session_id` invalid). |
| 429 | Rate limit exceeded. |
| 502 | Backend unreachable, errored, or violated the response contract. |
| 503 | TARGET_URL not configured. |
