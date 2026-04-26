# Sicherheits-Checkliste

Vor dem Oeffentlich-Gehen einmal Punkt fuer Punkt durchgehen. Jeder
Punkt sollte sich ohne Quellcode-Lesen mit ja/nein beantworten lassen.

## Vor dem ersten Public-Deploy

- [ ] **`API_TOKEN` ist in `.env` fest gesetzt.** VoxGate erzeugt
      sonst pro Container-Start einen neuen Token (gut fuer Dev,
      schlecht fuer Produktion — die PWA-Clients verlieren bei jedem
      Restart den Zugriff).
- [ ] **`ANTHROPIC_API_KEY` hat ein Spending-Limit.** Setze es im
      Anthropic-Console-Dashboard. Token-Lecks werden so kostenmaessig
      gekappt.
- [ ] **`ALLOWED_ORIGIN` zeigt auf die echte Domain.** Leer = kein
      Browser-Origin darf die API aufrufen. Ungenau (`*` o.ae.) gibt es
      bewusst nicht.
- [ ] **`TRUST_PROXY_HEADERS=1` nur, wenn der Server ausschliesslich
      hinter dem Reverse-Proxy erreichbar ist.** Sonst koennen Clients
      `X-Forwarded-For` selbst setzen und das Rate-Limit umgehen.
      Im `deploy/caddy/`-Bundle ist das automatisch der Fall.
- [ ] **`RATE_LIMIT_PER_MINUTE` bewusst gesetzt.** Default 30 ist
      OK fuer eine Person; fuer eine Familie ggf. hoeher. Zu hoch =
      kein Schutz mehr gegen Bot-Abuse.

## Backend-spezifisch

### Wenn `ANTHROPIC_API_KEY` aktiv (`/claude`)

- [ ] **API-Key-Rotation:** der Key wird beim ersten `/claude`-Call
      gecached. Nach Rotation den Container neu starten.
- [ ] **`SYSTEM_PROMPT` enthaelt keine Geheimnisse.** Er steht
      effektiv im Klartext im Container — und falls jemand `/config`
      und Logs einsehen kann, auch dort.

### Wenn `TARGET_URL` aktiv (`/prompt`)

- [ ] **Target-Backend bindet auf `127.0.0.1`** oder verlangt selbst
      einen `TARGET_TOKEN`. Sonst macht VoxGate dein Backend
      ungewollt aus dem Internet erreichbar.
- [ ] **Target-Backend-Backups laufen separat.** VoxGate hat keinen
      State, der gesichert werden muss; das Target-Backend potenziell
      schon.

## Im laufenden Betrieb

- [ ] **Logs werden gesichtet.** `docker compose logs -f voxgate`
      zeigt Audit-Eintraege mit IP, Session-Prefix und Text-Laenge
      (kein Inhalt). 429- und Backend-Fehler ebenso.
- [ ] **Keine zusaetzliche `Content-Security-Policy` im Reverse
      Proxy.** VoxGate setzt eine strikte CSP selbst. Eine zweite
      Direktive im Caddy/Nginx-Block kollidiert.
- [ ] **Updates pruefen.** `git pull && docker compose build &&
      docker compose up -d` regelmaessig — vor allem nach Security-
      Releases.

## Was VoxGate von Haus aus mitbringt

Ohne Operator-Aktion aktiv:

- Token-Pflicht fuer `/prompt` und `/claude`. Auto-Generierung wenn
  leer (kein "open mode").
- Timing-safe Token-Vergleich (`secrets.compare_digest`).
- Per-IP-Rate-Limit auf beiden Endpoints.
- Session-TTL und globale Session-Cap (Speicher-DoS-Schutz).
- Strikte `session_id`-Validierung (`^[A-Za-z0-9_-]{8,128}$`).
- Strikte CSP, `X-Frame-Options: DENY`, `X-Content-Type-Options:
  nosniff`, `Referrer-Policy`, `Permissions-Policy` (nur Mikrofon).
- Audit-Log ohne Payload.
- CORS standardmaessig blockiert.

## Restrisiken

- **localStorage-XSS**: der Bearer-Token liegt im Browser in
  `localStorage`. Die CSP blockiert Inline-Skripte; jede kuenftige
  Verwendung von `innerHTML` mit Server-Daten muesste sehr vorsichtig
  sein.
- **In-Memory-Sessions**: Histories leben im Prozess. Restart loescht
  sie. Bewusst so.
- **Per-IP-Rate-Limit nur**: hinter NAT/CGNAT teilen sich Nutzer das
  Kontingent.
