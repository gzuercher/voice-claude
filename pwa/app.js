  let instanceConfig = { name: 'VoxGate', color: '#c8ff00', lang: 'de-CH', langs: ['de-CH', 'fr-CH'], maxLength: 4000, googleClientId: '', providers: [] };

  // Autonyms — each language labelled in its own form. The picker shows
  // these regardless of current UI language so a French speaker can find
  // "Français" without having to read German first.
  const LANGUAGE_LABELS = {
    'de-CH': 'Deutsch',
    'fr-CH': 'Français',
    'it-CH': 'Italiano',
    'en-US': 'English',
    'es-ES': 'Español',
  };

  function languageLabel(code) {
    return LANGUAGE_LABELS[code] || code;
  }

  const I18N = {
    'de-CH': {
      headerToggleLang: 'Sprache wählen',
      headerToggleAuth: 'Konto wechseln',
      headerToggleMute: 'Sprachausgabe stummschalten',
      authTitle: 'Anmelden',
      authIntro: 'Diese Instanz ist privat. Melde dich mit einem Google-Konto an, das vom Betreiber freigeschaltet wurde.',
      authHint: 'Anmeldung erfolgt direkt bei Google. VoxGate erhält nur deine E-Mail-Adresse.',
      notAllowedError: 'Diese Google-Adresse ist auf dieser Instanz nicht freigeschaltet.',
      rateLimitedError: 'Zu viele Anmeldeversuche. Bitte später erneut versuchen.',
      signInFailedError: 'Anmeldung fehlgeschlagen. Bitte erneut versuchen.',
      signInUnavailable: 'Anmeldung nicht verfügbar — Betreiber muss GOOGLE_CLIENT_ID setzen.',
      loggedInAs: 'Angemeldet als',
      logout: 'Abmelden',
      emptyTitle: 'Tippen und sprechen',
      emptyHint: 'Nochmal tippen = senden',
      transcriptReady: 'Bereit...',
      micAria: 'Aufnehmen und senden',
      clearAria: 'Text löschen',
      micRecord: 'Aufnehmen',
      micStop: 'Stop',
      micSend: 'Senden',
      newConv: 'Neues Gespräch',
      userLabel: 'Du',
      errorPrefix: 'Fehler: ',
      speechUnsupported: 'Web Speech API wird nicht unterstützt. Bitte Chrome verwenden.',
    },
    'fr-CH': {
      headerToggleLang: 'Choisir la langue',
      headerToggleAuth: 'Changer de compte',
      headerToggleMute: 'Couper la synthèse vocale',
      authTitle: 'Connexion',
      authIntro: "Cette instance est privée. Connectez-vous avec un compte Google autorisé par l'exploitant.",
      authHint: 'La connexion se fait directement chez Google. VoxGate reçoit uniquement votre adresse e-mail.',
      notAllowedError: "Cette adresse Google n'est pas autorisée sur cette instance.",
      rateLimitedError: 'Trop de tentatives. Veuillez réessayer plus tard.',
      signInFailedError: 'Échec de la connexion. Veuillez réessayer.',
      signInUnavailable: "Connexion indisponible — l'exploitant doit définir GOOGLE_CLIENT_ID.",
      loggedInAs: 'Connecté en tant que',
      logout: 'Se déconnecter',
      emptyTitle: 'Touchez et parlez',
      emptyHint: 'Touchez à nouveau pour envoyer',
      transcriptReady: 'Prêt...',
      micAria: 'Enregistrer et envoyer',
      clearAria: 'Effacer le texte',
      micRecord: 'Enregistrer',
      micStop: 'Arrêter',
      micSend: 'Envoyer',
      newConv: 'Nouvelle conversation',
      userLabel: 'Moi',
      errorPrefix: 'Erreur : ',
      speechUnsupported: 'Web Speech API non supportée. Utilisez Chrome.',
    },
    'it-CH': {
      headerToggleLang: 'Scegli la lingua',
      headerToggleAuth: 'Cambia account',
      headerToggleMute: 'Disattiva sintesi vocale',
      authTitle: 'Accesso',
      authIntro: 'Questa istanza è privata. Accedi con un account Google autorizzato dal gestore.',
      authHint: "L'accesso avviene direttamente presso Google. VoxGate riceve solo il tuo indirizzo e-mail.",
      notAllowedError: 'Questo indirizzo Google non è autorizzato su questa istanza.',
      rateLimitedError: 'Troppi tentativi di accesso. Riprova più tardi.',
      signInFailedError: 'Accesso fallito. Riprova.',
      signInUnavailable: 'Accesso non disponibile — il gestore deve impostare GOOGLE_CLIENT_ID.',
      loggedInAs: 'Connesso come',
      logout: 'Disconnetti',
      emptyTitle: 'Tocca e parla',
      emptyHint: 'Tocca di nuovo per inviare',
      transcriptReady: 'Pronto...',
      micAria: 'Registra e invia',
      clearAria: 'Cancella testo',
      micRecord: 'Registra',
      micStop: 'Stop',
      micSend: 'Invia',
      newConv: 'Nuova conversazione',
      userLabel: 'Io',
      errorPrefix: 'Errore: ',
      speechUnsupported: 'Web Speech API non supportata. Usa Chrome.',
    },
    'en-US': {
      headerToggleLang: 'Choose language',
      headerToggleAuth: 'Switch account',
      headerToggleMute: 'Mute voice output',
      authTitle: 'Sign in',
      authIntro: 'This instance is private. Sign in with a Google account that the operator has authorized.',
      authHint: 'Sign-in happens directly with Google. VoxGate only receives your e-mail address.',
      notAllowedError: 'This Google address is not authorized on this instance.',
      rateLimitedError: 'Too many sign-in attempts. Please try again later.',
      signInFailedError: 'Sign-in failed. Please try again.',
      signInUnavailable: 'Sign-in unavailable — operator must set GOOGLE_CLIENT_ID.',
      loggedInAs: 'Signed in as',
      logout: 'Sign out',
      emptyTitle: 'Tap and speak',
      emptyHint: 'Tap again to send',
      transcriptReady: 'Ready...',
      micAria: 'Record and send',
      clearAria: 'Clear text',
      micRecord: 'Record',
      micStop: 'Stop',
      micSend: 'Send',
      newConv: 'New conversation',
      userLabel: 'You',
      errorPrefix: 'Error: ',
      speechUnsupported: 'Web Speech API not supported. Use Chrome.',
    },
    'es-ES': {
      headerToggleLang: 'Elegir idioma',
      headerToggleAuth: 'Cambiar cuenta',
      headerToggleMute: 'Silenciar voz',
      authTitle: 'Iniciar sesión',
      authIntro: 'Esta instancia es privada. Inicia sesión con una cuenta de Google autorizada por el operador.',
      authHint: 'El inicio de sesión se realiza directamente con Google. VoxGate solo recibe tu dirección de correo.',
      notAllowedError: 'Esta dirección de Google no está autorizada en esta instancia.',
      rateLimitedError: 'Demasiados intentos. Vuelve a intentarlo más tarde.',
      signInFailedError: 'Error al iniciar sesión. Inténtalo de nuevo.',
      signInUnavailable: 'Inicio de sesión no disponible — el operador debe configurar GOOGLE_CLIENT_ID.',
      loggedInAs: 'Sesión iniciada como',
      logout: 'Cerrar sesión',
      emptyTitle: 'Toca y habla',
      emptyHint: 'Toca de nuevo para enviar',
      transcriptReady: 'Listo...',
      micAria: 'Grabar y enviar',
      clearAria: 'Borrar texto',
      micRecord: 'Grabar',
      micStop: 'Stop',
      micSend: 'Enviar',
      newConv: 'Nueva conversación',
      userLabel: 'Yo',
      errorPrefix: 'Error: ',
      speechUnsupported: 'Web Speech API no soportada. Usa Chrome.',
    },
  };

  function t(key) {
    const dict = I18N[activeLang()] || I18N['de-CH'];
    return dict[key] !== undefined ? dict[key] : key;
  }

  // Debug logger. No-op unless ?debug=<token> is in the URL and debug.js
  // initialised window.__dbg. Never log secrets, user input or LLM
  // responses — only event names and structural metadata.
  function dbg(type, data) {
    if (window.__dbg) window.__dbg(type, data);
  }
  let recognition = null;
  // 'idle': waiting for user. 'recording': SpeechRecognition active.
  // 'review': recording stopped, transcript editable, next tap sends.
  let state = 'idle';
  let currentTranscript = '';
  // Text locked in from previous recognition sessions (after auto-restart).
  // Continuous mode is unreliable on Android Chrome — onend fires repeatedly
  // mid-utterance, so we restart and stitch sessions together here.
  let sessionFinal = '';
  // Live text from the currently-running recognition session, rebuilt from
  // scratch on every onresult event to stay idempotent against Android's
  // tendency to re-emit the same result with shifting isFinal flags.
  let currentSessionText = '';
  function supportedLangs() {
    return (instanceConfig.langs && instanceConfig.langs.length)
      ? instanceConfig.langs
      : [instanceConfig.lang];
  }
  let currentLang = localStorage.getItem('voxLang') || null;
  let muted = localStorage.getItem('voxMuted') === '1';
  let sessionId = sessionStorage.getItem('voxSession');
  if (!sessionId) {
    sessionId = (crypto.randomUUID ? crypto.randomUUID()
      : Date.now() + '-' + Math.random().toString(36).slice(2));
    sessionStorage.setItem('voxSession', sessionId);
  }

  function activeLang() {
    return currentLang || instanceConfig.lang;
  }

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('sw.js');
  }

  const micBtn = document.getElementById('micBtn');
  const micLabel = document.getElementById('micLabel');
  const transcriptBox = document.getElementById('transcriptBox');
  const messagesEl = document.getElementById('messages');
  const statusDot = document.getElementById('statusDot');
  const logo = document.getElementById('logo');
  const langSelect = document.getElementById('langSelect');
  const muteBtn = document.getElementById('muteBtn');
  const newConvBtn = document.getElementById('newConvBtn');
  const discardBtn = document.getElementById('discardBtn');
  // Auth overlay is owned by VoxGateAuth (auth.js). The logo button opens the
  // overlay so the user can switch accounts or sign out without waiting for a
  // 401 from the API.
  logo.addEventListener('click', () => VoxGateAuth.showLogin());

  function populateLangSelect() {
    const langs = supportedLangs();
    const current = activeLang();
    // Rebuild only if the option set changed (avoids losing focus on every
    // applyLang call).
    const desired = langs.join(',');
    if (langSelect.dataset.langs !== desired) {
      langSelect.innerHTML = '';
      for (const code of langs) {
        const opt = document.createElement('option');
        opt.value = code;
        opt.textContent = languageLabel(code);
        langSelect.appendChild(opt);
      }
      langSelect.dataset.langs = desired;
    }
    if (langSelect.value !== current) langSelect.value = current;
  }

  // Pick a sensible language when the user has no stored preference yet.
  // Browser/OS languages are checked first by exact tag, then by primary
  // subtag (de-DE → de-CH). Falls back to the server-side default.
  function detectInitialLang() {
    const stored = localStorage.getItem('voxLang');
    const supported = supportedLangs();
    if (stored && supported.includes(stored)) return stored;
    const candidates = navigator.languages && navigator.languages.length
      ? navigator.languages
      : (navigator.language ? [navigator.language] : []);
    for (const c of candidates) {
      if (supported.includes(c)) return c;
    }
    for (const c of candidates) {
      const primary = c.split('-')[0].toLowerCase();
      const found = supported.find(l => l.split('-')[0].toLowerCase() === primary);
      if (found) return found;
    }
    return instanceConfig.lang;
  }

  function applyLang() {
    const lang = activeLang();
    document.documentElement.lang = lang.split('-')[0];
    populateLangSelect();
    document.querySelectorAll('[data-i18n]').forEach(el => {
      el.textContent = t(el.dataset.i18n);
    });
    document.querySelectorAll('[data-i18n-aria]').forEach(el => {
      el.setAttribute('aria-label', t(el.dataset.i18nAria));
    });
    // Re-apply state-dependent labels.
    if (state === 'idle') {
      micLabel.textContent = t('micRecord');
      transcriptBox.textContent = t('transcriptReady');
    } else if (state === 'recording') {
      micLabel.textContent = t('micStop');
    } else if (state === 'review') {
      micLabel.textContent = t('micSend');
    }
  }

  function updateMuteBtn() {
    muteBtn.textContent = muted ? '🔇' : '🔊';
    muteBtn.classList.toggle('muted', muted);
  }

  langSelect.addEventListener('change', () => {
    const next = langSelect.value;
    if (!next || next === currentLang) return;
    currentLang = next;
    localStorage.setItem('voxLang', next);
    if (state !== 'idle') discardReview();
    applyLang();
  });

  muteBtn.addEventListener('click', () => {
    muted = !muted;
    localStorage.setItem('voxMuted', muted ? '1' : '0');
    if (muted && 'speechSynthesis' in window) speechSynthesis.cancel();
    updateMuteBtn();
  });

  newConvBtn.addEventListener('click', () => {
    if (state !== 'idle') discardReview();
    sessionId = (crypto.randomUUID ? crypto.randomUUID()
      : Date.now() + '-' + Math.random().toString(36).slice(2));
    sessionStorage.setItem('voxSession', sessionId);
    messagesEl.innerHTML = '';
    if ('speechSynthesis' in window) speechSynthesis.cancel();
  });

  discardBtn.addEventListener('click', () => discardReview());

  // Typing into the transcript box from idle or recording switches to
  // review. From idle we also wipe the placeholder ("Bereit...") so the
  // first keystroke does not append to it.
  transcriptBox.addEventListener('beforeinput', () => {
    if (state === 'idle') {
      transcriptBox.textContent = '';
      setState('review');
    } else if (state === 'recording') {
      stopRecognition();
      sessionFinal = mergeTranscript(sessionFinal, currentSessionText);
      currentSessionText = '';
      setState('review');
    }
  });

  function speak(text) {
    if (muted || !('speechSynthesis' in window) || !text) return;
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = activeLang();
    speechSynthesis.speak(u);
  }

  async function loadConfig() {
    try {
      const res = await fetch('/config');
      if (res.ok) {
        instanceConfig = await res.json();
        document.title = instanceConfig.name;
        logo.textContent = instanceConfig.name;
        document.documentElement.style.setProperty('--accent', instanceConfig.color);
        const dimColor = instanceConfig.color + '1f';
        document.documentElement.style.setProperty('--accent-dim', dimColor);
        document.querySelector('meta[name="theme-color"]').content = '#0a0a0a';
      }
    } catch (e) {
      // use defaults
    }
  }

  function setStatus(state) {
    statusDot.className = 'status-dot ' + state;
  }

  function updateTranscript(text, active) {
    transcriptBox.textContent = text || t('transcriptReady');
    transcriptBox.className = 'transcript-box' + (active ? ' active' : '');
  }

  function addMessage(role, text) {
    const empty = document.getElementById('emptyState');
    if (empty) empty.remove();

    const div = document.createElement('div');
    div.className = 'message ' + role;
    const label = role === 'user' ? t('userLabel') : instanceConfig.name;
    div.innerHTML = `
      <div class="message-label">${escapeHtml(label)}</div>
      <div class="message-bubble">${escapeHtml(text)}</div>
    `;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return div;
  }

  function escapeHtml(t) {
    return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  micBtn.addEventListener('click', () => handleTap());

  function handleTap() {
    if (state === 'idle') {
      startRecording();
    } else if (state === 'recording') {
      enterReview();
    } else if (state === 'review') {
      sendCurrent();
    }
  }

  function setState(next) {
    dbg('state', { from: state, to: next });
    state = next;
    micBtn.classList.toggle('recording', next === 'recording');
    if (next === 'idle') {
      micLabel.textContent = t('micRecord');
      discardBtn.hidden = true;
      updateTranscript('', false);
    } else if (next === 'recording') {
      micLabel.textContent = t('micStop');
      discardBtn.hidden = true;
    } else if (next === 'review') {
      micLabel.textContent = t('micSend');
      transcriptBox.classList.remove('active');
      discardBtn.hidden = false;
    }
  }

  // Build the current session's text from a SpeechRecognitionResultList.
  // Filters out finals that are merely a prefix of a later final — this
  // happens on Android Chrome, where each new word causes the engine to
  // re-emit the entire growing phrase as another isFinal=true result.
  function buildSessionText(results) {
    const finals = [];
    let interim = '';
    for (let i = 0; i < results.length; i++) {
      const t = results[i][0].transcript;
      if (results[i].isFinal) {
        finals.push(t.trim());
      } else {
        interim += t;
      }
    }
    const kept = [];
    for (let i = 0; i < finals.length; i++) {
      let isPrefix = false;
      for (let j = i + 1; j < finals.length; j++) {
        if (finals[j].startsWith(finals[i])) {
          isPrefix = true;
          break;
        }
      }
      if (!isPrefix) kept.push(finals[i]);
    }
    return (kept.join(' ') + ' ' + interim).trim();
  }

  // Merge previous-session locked text with the running session's text.
  // If the running text is a continuation/restatement of the locked text
  // (Android pattern), replace; if it's strictly older, keep the locked;
  // otherwise append as a new utterance (desktop pattern).
  function mergeTranscript(prev, curr) {
    prev = (prev || '').trim();
    curr = (curr || '').trim();
    if (!prev) return curr;
    if (!curr) return prev;
    if (curr.startsWith(prev)) return curr;
    if (prev.endsWith(curr)) return prev;
    return prev + ' ' + curr;
  }

  function startRecording() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      alert(t('speechUnsupported'));
      return;
    }

    if ('speechSynthesis' in window) speechSynthesis.cancel();

    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SR();
    recognition.lang = activeLang();
    recognition.continuous = true;
    recognition.interimResults = true;

    sessionFinal = '';
    currentSessionText = '';
    currentTranscript = '';

    recognition.onstart = () => {
      dbg('sr-onstart', { lang: recognition.lang });
      setState('recording');
      // On Android Chrome, recognition.onend fires on every micro-pause and
      // we auto-restart. Don't wipe the display on each restart — keep the
      // already-locked text visible so the user sees their utterance grow.
      // On the first start sessionFinal is '', falling back to the placeholder.
      updateTranscript(sessionFinal.trim(), true);
      setStatus('online');
    };

    recognition.onresult = (e) => {
      dbg('sr-onresult', {
        resultIndex: e.resultIndex,
        length: e.results.length,
        results: Array.from(e.results).map((r) => ({
          transcript: r[0] && r[0].transcript,
          isFinal: r.isFinal,
          confidence: r[0] && r[0].confidence,
        })),
      });
      currentSessionText = buildSessionText(e.results);
      currentTranscript = mergeTranscript(sessionFinal, currentSessionText);
      dbg('sr-merged', {
        sessionFinal: sessionFinal,
        currentSessionText: currentSessionText,
        display: currentTranscript,
      });
      updateTranscript(currentTranscript, true);
    };

    recognition.onend = () => {
      // Lock the just-ended session's text and restart if still recording.
      // Use mergeTranscript so an Android-style restatement collapses into
      // sessionFinal instead of duplicating it.
      const before = sessionFinal;
      sessionFinal = mergeTranscript(sessionFinal, currentSessionText);
      dbg('sr-onend', {
        before: before,
        currentSessionText: currentSessionText,
        after: sessionFinal,
        willRestart: state === 'recording',
      });
      currentSessionText = '';
      if (state === 'recording') {
        recognition.start();
      }
    };

    recognition.onerror = (e) => {
      dbg('sr-onerror', { error: e.error });
      if (e.error === 'no-speech') return;
      console.error(e.error);
      stopRecognition();
      setState('idle');
      setStatus('error');
    };

    recognition.start();
  }

  function stopRecognition() {
    if (recognition) {
      recognition.onend = null;
      try { recognition.stop(); } catch (_) {}
    }
  }

  function enterReview() {
    stopRecognition();
    const text = currentTranscript.trim();
    if (!text) {
      setState('idle');
      return;
    }
    setState('review');
    transcriptBox.textContent = text;
    setStatus('');
    setTimeout(() => {
      transcriptBox.focus();
      const range = document.createRange();
      range.selectNodeContents(transcriptBox);
      range.collapse(false);
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
    }, 50);
  }

  function discardReview() {
    stopRecognition();
    currentTranscript = '';
    sessionFinal = '';
    currentSessionText = '';
    setState('idle');
    setStatus('');
  }

  async function sendCurrent() {
    const text = (transcriptBox.textContent || '').trim();
    setState('idle');
    currentTranscript = '';
    sessionFinal = '';
    currentSessionText = '';
    if (!text) return;
    await sendText(text);
  }

  async function sendText(text) {
    addMessage('user', text);

    const typingDiv = addMessage('assistant', '');
    typingDiv.classList.add('typing');
    setStatus('sending');

    try {
      const res = await fetch('/claude', VoxGateAuth.withAuthHeaders({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, session_id: sessionId })
      }));

      if (res.status === 401) {
        typingDiv.remove();
        setStatus('error');
        VoxGateAuth.showLogin();
        return;
      }
      if (res.status === 403) {
        typingDiv.remove();
        setStatus('error');
        VoxGateAuth.showLogin(t('notAllowedError'));
        return;
      }
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const data = await res.json();
      const reply = data.response || data.text || JSON.stringify(data);

      typingDiv.classList.remove('typing');
      typingDiv.querySelector('.message-bubble').textContent = reply;
      setStatus('online');
      speak(reply);
    } catch (err) {
      typingDiv.classList.remove('typing');
      typingDiv.querySelector('.message-bubble').textContent = t('errorPrefix') + err.message;
      setStatus('error');
    }

    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  // Initial lang from localStorage or browser/OS, refined once /config gives
  // us the actual SPEECH_LANGS list.
  if (!currentLang) currentLang = detectInitialLang();
  applyLang();
  updateMuteBtn();
  loadConfig().then(() => {
    if (!localStorage.getItem('voxLang')) {
      currentLang = detectInitialLang();
    }
    applyLang();
    VoxGateAuth.init({
      googleClientId: instanceConfig.googleClientId || '',
      providers: instanceConfig.providers || [],
      translate: t,
      onChange: () => { /* user state changed; nothing to do here yet */ },
    });
  });
  setStatus('');
