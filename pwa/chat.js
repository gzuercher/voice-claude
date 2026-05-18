// VoxGate chat-network module. Owns the wire format for /chat,
// /chat/stream and /chat/cancel. UI concerns (DOM, render, TTS) stay
// in app.js — this module only knows about JSON-in, callbacks-out.
//
// Exposed as window.VoxGateChat:
//   send(body)               → Promise<{response, awaiting_user_input?, suggestion?}>
//   stream(body, handlers)   → Promise<void>     // resolves on final/error
//   cancel(sessionId)        → Promise<{cancelled: bool}>
//
// `handlers` for stream():
//   onChunk(delta:string)
//   onTool({name, phase})    // optional
//   onFinal({response, awaiting_user_input?, suggestion?})
//   onError({code, message})
(function () {
  'use strict';

  async function send(body) {
    const res = await fetch('/chat', VoxGateAuth.withAuthHeaders({
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }));
    if (res.status === 401 || res.status === 403) {
      const err = new Error('HTTP ' + res.status);
      err.status = res.status;
      throw err;
    }
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    if (typeof data.response !== 'string') {
      throw new Error('Malformed response from server');
    }
    return data;
  }

  // SSE frame parser. Backend may write byte-by-byte; we keep an
  // incomplete tail in `buffer` and only emit on `\n\n` boundaries.
  // Returns the remaining buffer.
  function parseFrames(buffer, onEvent) {
    let idx;
    while ((idx = buffer.indexOf('\n\n')) !== -1) {
      const raw = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      if (!raw.trim()) continue;
      let event = 'message';
      let dataLines = [];
      for (const line of raw.split('\n')) {
        if (line.startsWith('event:')) event = line.slice(6).trim();
        else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
        // `id:` and `retry:` are ignored — we don't reconnect SSE.
      }
      const data = dataLines.join('\n');
      let parsed;
      try { parsed = data ? JSON.parse(data) : {}; }
      catch (_) { parsed = { _raw: data }; }
      onEvent(event, parsed);
    }
    return buffer;
  }

  async function stream(body, handlers, options) {
    handlers = handlers || {};
    options = options || {};
    const init = VoxGateAuth.withAuthHeaders({
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'text/event-stream' },
      body: JSON.stringify(body),
    });
    if (options.signal) init.signal = options.signal;

    const res = await fetch('/chat/stream', init);
    if (res.status === 401 || res.status === 403) {
      const err = new Error('HTTP ' + res.status);
      err.status = res.status;
      throw err;
    }
    if (!res.ok) {
      handlers.onError && handlers.onError({
        code: 'http_' + res.status,
        message: 'HTTP ' + res.status,
      });
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';
    let gotFinal = false;
    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        buffer = parseFrames(buffer, (event, data) => {
          if (event === 'chunk' && typeof data.delta === 'string') {
            handlers.onChunk && handlers.onChunk(data.delta);
          } else if (event === 'tool') {
            handlers.onTool && handlers.onTool(data);
          } else if (event === 'final') {
            gotFinal = true;
            handlers.onFinal && handlers.onFinal(data);
          } else if (event === 'error') {
            handlers.onError && handlers.onError(data);
          }
        });
      }
    } catch (err) {
      if (err && err.name === 'AbortError') {
        // Caller aborted; treat as cancelled, not as error.
        return;
      }
      handlers.onError && handlers.onError({
        code: 'network', message: (err && err.message) || 'network error',
      });
      return;
    }
    if (!gotFinal) {
      handlers.onError && handlers.onError({
        code: 'stream_truncated',
        message: 'Stream ended without a final event',
      });
    }
  }

  async function cancel(sessionId) {
    try {
      const res = await fetch('/chat/cancel', VoxGateAuth.withAuthHeaders({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      }));
      if (!res.ok) return { cancelled: false };
      return await res.json();
    } catch (_) {
      return { cancelled: false };
    }
  }

  window.VoxGateChat = { send, stream, cancel };
})();
