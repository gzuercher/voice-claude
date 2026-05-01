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
      headerMenu: 'Menü öffnen',
      menuTitle: 'Einstellungen',
      menuClose: 'Menü schließen',
      menuLanguage: 'Sprache',
      menuTTS: 'Sprachausgabe',
      menuTTSToggle: 'Sprachausgabe umschalten',
      menuTheme: 'Erscheinungsbild',
      menuThemeAria: 'Erscheinungsbild wählen',
      themeAuto: 'Auto',
      themeLight: 'Hell',
      themeDark: 'Dunkel',
      menuHelp: 'Hilfe',
      ttsOn: 'Ein',
      ttsOff: 'Aus',
      helpTitle: 'Hilfe',
      helpClose: 'Hilfe schließen',
      helpBody: [
        '<strong>Aufnehmen:</strong> Tippe auf den großen Mikrofon-Knopf, sprich, dann nochmal tippen zum Senden.',
        '<strong>Tippen:</strong> Du kannst auch direkt ins Textfeld tippen, statt zu sprechen — oder beides mischen.',
        '<strong>Bild senden:</strong> Mit dem 📷-Knopf kannst du ein Foto aus der Galerie wählen oder die Kamera öffnen. Es wird zusammen mit (oder anstelle von) Text mitgeschickt.',
        '<strong>Löschen:</strong> Der ✕-Knopf neben dem Mikrofon leert den aktuellen Text und ein angehängtes Bild und bricht eine laufende Aufnahme ab.',
        '<strong>Sprachausgabe (TTS):</strong> Standardmäßig aus. Aktiviere sie im Menü, wenn du Antworten vorgelesen haben willst.',
        '<strong>Sprache:</strong> Wähle im Menü oben links zwischen Deutsch, Französisch, Italienisch, Englisch und Spanisch — beeinflusst Spracherkennung, Vorlesen und die App-Beschriftungen.',
        '<strong>Neues Gespräch:</strong> Der Knopf ganz unten startet eine neue Sitzung — das Backend kann das nutzen, um den Gesprächskontext zurückzusetzen.',
        '<strong>Anmeldung:</strong> Nur freigeschaltete Google-Konten können diese Instanz nutzen. Über das Menü → Abmelden meldest du dich ab.',
      ],
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
      cameraAria: 'Bild anhängen',
      attachmentRemoveAria: 'Bild entfernen',
      imageTooLarge: 'Bild zu groß. Bitte ein kleineres wählen.',
      imageProcessFailed: 'Bild konnte nicht verarbeitet werden.',
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
      headerMenu: 'Ouvrir le menu',
      menuTitle: 'Paramètres',
      menuClose: 'Fermer le menu',
      menuLanguage: 'Langue',
      menuTTS: 'Synthèse vocale',
      menuTTSToggle: 'Activer/désactiver la synthèse',
      menuTheme: 'Apparence',
      menuThemeAria: "Choisir l'apparence",
      themeAuto: 'Auto',
      themeLight: 'Clair',
      themeDark: 'Sombre',
      menuHelp: 'Aide',
      ttsOn: 'On',
      ttsOff: 'Off',
      helpTitle: 'Aide',
      helpClose: "Fermer l'aide",
      helpBody: [
        "<strong>Enregistrer :</strong> appuyez sur le grand bouton micro, parlez, puis appuyez à nouveau pour envoyer.",
        '<strong>Saisir :</strong> vous pouvez aussi taper directement dans la zone de texte — ou mélanger voix et clavier.',
        "<strong>Envoyer une image :</strong> le bouton 📷 ouvre la galerie ou la caméra. L'image part avec (ou à la place du) texte au prochain envoi.",
        '<strong>Effacer :</strong> le bouton ✕ à côté du micro vide le texte courant et toute image jointe, et interrompt un enregistrement.',
        '<strong>Synthèse vocale (TTS) :</strong> désactivée par défaut. Activez-la dans le menu pour entendre les réponses.',
        "<strong>Langue :</strong> dans le menu en haut à gauche, choisissez entre allemand, français, italien, anglais et espagnol — affecte reconnaissance, lecture vocale et libellés.",
        "<strong>Nouvelle conversation :</strong> le bouton tout en bas démarre une nouvelle session — le backend peut s'en servir pour réinitialiser le contexte.",
        '<strong>Connexion :</strong> seuls les comptes Google autorisés ont accès. Menu → Se déconnecter pour vous déconnecter.',
      ],
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
      cameraAria: 'Joindre une image',
      attachmentRemoveAria: "Supprimer l'image",
      imageTooLarge: "Image trop grande. Choisissez-en une plus petite.",
      imageProcessFailed: "Impossible de traiter l'image.",
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
      headerMenu: 'Apri menu',
      menuTitle: 'Impostazioni',
      menuClose: 'Chiudi menu',
      menuLanguage: 'Lingua',
      menuTTS: 'Sintesi vocale',
      menuTTSToggle: 'Attiva/disattiva sintesi',
      menuTheme: 'Aspetto',
      menuThemeAria: "Scegli l'aspetto",
      themeAuto: 'Auto',
      themeLight: 'Chiaro',
      themeDark: 'Scuro',
      menuHelp: 'Aiuto',
      ttsOn: 'On',
      ttsOff: 'Off',
      helpTitle: 'Aiuto',
      helpClose: "Chiudi l'aiuto",
      helpBody: [
        '<strong>Registrare:</strong> tocca il pulsante grande del microfono, parla, poi tocca di nuovo per inviare.',
        '<strong>Scrivere:</strong> puoi anche scrivere direttamente nel campo di testo — o mischiare voce e tastiera.',
        '<strong>Inviare immagini:</strong> il pulsante 📷 apre la galleria o la fotocamera. Lʼimmagine parte insieme (o al posto) del testo al prossimo invio.',
        '<strong>Cancellare:</strong> il pulsante ✕ accanto al microfono svuota il testo e qualsiasi immagine allegata, e interrompe la registrazione.',
        '<strong>Sintesi vocale (TTS):</strong> disattivata per impostazione predefinita. Attivala nel menu per ascoltare le risposte.',
        '<strong>Lingua:</strong> nel menu in alto a sinistra scegli tra tedesco, francese, italiano, inglese e spagnolo — riguarda riconoscimento, lettura e testi.',
        '<strong>Nuova conversazione:</strong> il pulsante in basso avvia una nuova sessione — il backend può usarlo per ripartire da zero.',
        '<strong>Accesso:</strong> solo gli account Google autorizzati possono accedere. Menu → Disconnetti per uscire.',
      ],
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
      cameraAria: 'Allega immagine',
      attachmentRemoveAria: 'Rimuovi immagine',
      imageTooLarge: 'Immagine troppo grande. Scegline una più piccola.',
      imageProcessFailed: "Impossibile elaborare l'immagine.",
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
      headerMenu: 'Open menu',
      menuTitle: 'Settings',
      menuClose: 'Close menu',
      menuLanguage: 'Language',
      menuTTS: 'Voice output',
      menuTTSToggle: 'Toggle voice output',
      menuTheme: 'Appearance',
      menuThemeAria: 'Choose appearance',
      themeAuto: 'Auto',
      themeLight: 'Light',
      themeDark: 'Dark',
      menuHelp: 'Help',
      ttsOn: 'On',
      ttsOff: 'Off',
      helpTitle: 'Help',
      helpClose: 'Close help',
      helpBody: [
        '<strong>Recording:</strong> tap the large mic button, speak, then tap again to send.',
        '<strong>Typing:</strong> you can also type directly into the text box — or mix voice and keyboard.',
        '<strong>Sending an image:</strong> the 📷 button opens your photo library or camera. The image is sent alongside (or instead of) text on the next tap.',
        '<strong>Clearing:</strong> the ✕ button next to the mic empties the current text and any attached image, and aborts an ongoing recording.',
        '<strong>Voice output (TTS):</strong> off by default. Turn it on in the menu if you want answers read aloud.',
        '<strong>Language:</strong> the menu (top left) lets you switch between German, French, Italian, English and Spanish — affects recognition, read-aloud and labels.',
        '<strong>New conversation:</strong> the bottom button starts a new session — the backend can use that to reset context.',
        '<strong>Sign-in:</strong> only authorized Google accounts can use this instance. Menu → Sign out to log out.',
      ],
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
      cameraAria: 'Attach image',
      attachmentRemoveAria: 'Remove image',
      imageTooLarge: 'Image too large. Please pick a smaller one.',
      imageProcessFailed: 'Could not process the image.',
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
      headerMenu: 'Abrir menú',
      menuTitle: 'Ajustes',
      menuClose: 'Cerrar menú',
      menuLanguage: 'Idioma',
      menuTTS: 'Síntesis de voz',
      menuTTSToggle: 'Activar/desactivar síntesis',
      menuTheme: 'Apariencia',
      menuThemeAria: 'Elegir apariencia',
      themeAuto: 'Auto',
      themeLight: 'Claro',
      themeDark: 'Oscuro',
      menuHelp: 'Ayuda',
      ttsOn: 'On',
      ttsOff: 'Off',
      helpTitle: 'Ayuda',
      helpClose: 'Cerrar ayuda',
      helpBody: [
        '<strong>Grabar:</strong> toca el gran botón de micrófono, habla y vuelve a tocar para enviar.',
        '<strong>Escribir:</strong> también puedes escribir directamente en el cuadro de texto — o mezclar voz y teclado.',
        '<strong>Enviar imagen:</strong> el botón 📷 abre la galería o la cámara. La imagen se envía junto con (o en lugar de) texto al pulsar de nuevo.',
        '<strong>Borrar:</strong> el botón ✕ junto al micrófono vacía el texto y cualquier imagen adjunta, y aborta una grabación en curso.',
        '<strong>Síntesis de voz (TTS):</strong> desactivada por defecto. Actívala en el menú para que las respuestas se lean en voz alta.',
        '<strong>Idioma:</strong> en el menú arriba a la izquierda elige entre alemán, francés, italiano, inglés y español — afecta reconocimiento, lectura y etiquetas.',
        '<strong>Nueva conversación:</strong> el botón inferior inicia una nueva sesión — el backend puede usarlo para reiniciar el contexto.',
        '<strong>Sesión:</strong> sólo cuentas Google autorizadas pueden usar esta instancia. Menú → Cerrar sesión para salir.',
      ],
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
      cameraAria: 'Adjuntar imagen',
      attachmentRemoveAria: 'Quitar imagen',
      imageTooLarge: 'Imagen demasiado grande. Elige una más pequeña.',
      imageProcessFailed: 'No se pudo procesar la imagen.',
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
  // TTS is OFF by default — having it on by default startled new users
  // when the app suddenly started talking. They can opt in via the menu.
  // Key 'voxMuted' is preserved for backwards compat with installs that
  // already chose a value: '1' = muted (TTS off), '0' = TTS on.
  const _ttsStored = localStorage.getItem('voxMuted');
  let muted = _ttsStored === null ? true : _ttsStored === '1';
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
  const newConvBtn = document.getElementById('newConvBtn');
  const discardBtn = document.getElementById('discardBtn');
  const cameraBtn = document.getElementById('cameraBtn');
  const fileInput = document.getElementById('fileInput');
  const attachmentChips = document.getElementById('attachmentChips');
  const menuBtn = document.getElementById('menuBtn');
  const menuOverlay = document.getElementById('menuOverlay');
  const menuDrawer = document.getElementById('menuDrawer');
  const menuCloseBtn = document.getElementById('menuCloseBtn');
  const menuHelpBtn = document.getElementById('menuHelpBtn');
  const menuLogoutBtn = document.getElementById('menuLogoutBtn');
  const menuUserLine = document.getElementById('menuUserLine');
  const ttsToggle = document.getElementById('ttsToggle');
  const ttsToggleState = document.getElementById('ttsToggleState');
  const helpOverlay = document.getElementById('helpOverlay');
  const helpCloseBtn = document.getElementById('helpCloseBtn');
  const helpBody = document.getElementById('helpBody');
  // Auth overlay is owned by VoxGateAuth (auth.js). The logo button opens the
  // overlay so the user can switch accounts or sign out without waiting for a
  // 401 from the API. Day-to-day settings (lang, TTS, logout, help) live in
  // the hamburger drawer.
  logo.addEventListener('click', () => VoxGateAuth.showLogin());

  function setMenuOpen(open) {
    menuOverlay.hidden = !open;
    menuDrawer.hidden = !open;
    menuDrawer.setAttribute('aria-hidden', open ? 'false' : 'true');
    menuBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (open) {
      const user = VoxGateAuth.getUser && VoxGateAuth.getUser();
      if (user && user.email) {
        menuUserLine.hidden = false;
        menuUserLine.textContent = (t('loggedInAs') || '') + ' ' + user.email;
      } else {
        menuUserLine.hidden = true;
      }
    }
  }
  menuBtn.addEventListener('click', () => setMenuOpen(true));
  menuCloseBtn.addEventListener('click', () => setMenuOpen(false));
  menuOverlay.addEventListener('click', () => setMenuOpen(false));
  menuLogoutBtn.addEventListener('click', () => {
    setMenuOpen(false);
    VoxGateAuth.logout();
  });
  menuHelpBtn.addEventListener('click', () => {
    setMenuOpen(false);
    setHelpOpen(true);
  });

  function setHelpOpen(open) {
    if (open) renderHelp();
    helpOverlay.hidden = !open;
  }
  helpCloseBtn.addEventListener('click', () => setHelpOpen(false));
  helpOverlay.addEventListener('click', (e) => {
    if (e.target === helpOverlay) setHelpOpen(false);
  });

  function renderHelp() {
    const paragraphs = (I18N[activeLang()] && I18N[activeLang()].helpBody)
      || I18N['de-CH'].helpBody;
    // helpBody entries contain inline <strong> tags we want preserved,
    // so we trust the i18n-controlled content; user-typed text never
    // flows through here.
    helpBody.innerHTML = paragraphs.map((p) => '<p>' + p + '</p>').join('');
  }

  function updateTtsToggleUI() {
    const on = !muted;
    ttsToggle.setAttribute('aria-checked', on ? 'true' : 'false');
    ttsToggleState.textContent = t(on ? 'ttsOn' : 'ttsOff');
    ttsToggleState.dataset.i18n = on ? 'ttsOn' : 'ttsOff';
  }
  ttsToggle.addEventListener('click', () => {
    muted = !muted; // toggle
    localStorage.setItem('voxMuted', muted ? '1' : '0');
    if (muted && 'speechSynthesis' in window) speechSynthesis.cancel();
    updateTtsToggleUI();
  });

  // ── Theme: 3-way (auto / light / dark) ──────────────────────────────
  // Initial value already applied to <html data-theme="..."> by theme.js
  // (synchronous, in <head>) to avoid flash-of-wrong-theme. Here we
  // just wire the menu segment and persist user changes.
  const themeSegment = document.getElementById('themeSegment');
  const themeBtns = themeSegment.querySelectorAll('[data-theme-value]');
  // Match the OS-aware accent for the browser-chrome / status-bar tint.
  const themeColorMeta = document.querySelector('meta[name="theme-color"]');
  const _osLight = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)');

  function effectiveThemeIsLight(choice) {
    if (choice === 'light') return true;
    if (choice === 'dark') return false;
    return !!(_osLight && _osLight.matches);
  }

  function applyTheme(choice) {
    if (choice !== 'auto' && choice !== 'light' && choice !== 'dark') {
      choice = 'auto';
    }
    document.documentElement.dataset.theme = choice;
    themeBtns.forEach((b) => {
      b.setAttribute('aria-checked', b.dataset.themeValue === choice ? 'true' : 'false');
    });
    if (themeColorMeta) {
      themeColorMeta.content = effectiveThemeIsLight(choice) ? '#f7f7f8' : '#0a0a0a';
    }
  }

  themeBtns.forEach((b) => {
    b.addEventListener('click', () => {
      const next = b.dataset.themeValue;
      try { localStorage.setItem('voxTheme', next); } catch (_) {}
      applyTheme(next);
    });
  });

  // When the user picks "auto", react to OS preference flips at runtime
  // (they may toggle dark mode in Settings while the app is open).
  if (_osLight && _osLight.addEventListener) {
    _osLight.addEventListener('change', () => {
      if (document.documentElement.dataset.theme === 'auto') {
        applyTheme('auto');  // re-tint the meta theme-color
      }
    });
  }

  // Read whatever theme.js already applied (or default to "auto") and
  // ensure the segment + meta are in sync.
  applyTheme(document.documentElement.dataset.theme || 'auto');

  // Esc closes whichever overlay is on top.
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    if (!helpOverlay.hidden) setHelpOpen(false);
    else if (!menuDrawer.hidden) setMenuOpen(false);
  });

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
    // Keep the CSS placeholder in sync with the UI language. The actual
    // placeholder is rendered by .transcript-box:empty::before reading
    // this attribute — never written into textContent.
    transcriptBox.setAttribute('data-placeholder', t('transcriptReady'));
    // Re-apply state-dependent labels.
    if (state === 'idle') {
      micLabel.textContent = t('micRecord');
    } else if (state === 'recording') {
      micLabel.textContent = t('micStop');
    } else if (state === 'review') {
      micLabel.textContent = t('micSend');
    }
    // Toggle pill carries dynamic state-aware text not driven by a
    // static data-i18n key; refresh it explicitly.
    updateTtsToggleUI();
    // If the help modal is open, re-render its body in the new language.
    if (helpOverlay && !helpOverlay.hidden) renderHelp();
  }

  langSelect.addEventListener('change', () => {
    const next = langSelect.value;
    if (!next || next === currentLang) return;
    currentLang = next;
    localStorage.setItem('voxLang', next);
    if (state !== 'idle') discardReview();
    applyLang();
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

  // ── Attachments (one-way, client → backend) ─────────────────────────
  // Pending images for the next /chat send. Each entry mirrors the
  // server-side Attachment model: {kind, mime, name, data, _previewUrl}.
  // _previewUrl is a local object URL kept around for the chip thumbnail
  // and revoked when the chip is removed (no leak).
  const MAX_IMAGE_DIMENSION = 1600;
  const IMAGE_QUALITY = 0.85;
  // Server caps base64 length; pick a slightly tighter client limit so
  // the user gets a friendly message instead of a 422.
  const CLIENT_MAX_B64_BYTES = 3.8 * 1024 * 1024;
  let pendingAttachments = [];

  cameraBtn.addEventListener('click', () => {
    if (cameraBtn.disabled) return;
    fileInput.click();
  });
  fileInput.addEventListener('change', async () => {
    const file = fileInput.files && fileInput.files[0];
    fileInput.value = ''; // reset so the same file can be re-picked
    if (!file) return;
    cameraBtn.classList.add('busy');
    try {
      const att = await processImageFile(file);
      pendingAttachments.push(att);
      renderAttachmentChips();
      // From idle, having an attachment means the next mic-tap should
      // send (not start recording). Re-run setState to refresh labels.
      if (state === 'idle') setState('idle');
    } catch (err) {
      alert(err && err.message ? err.message : t('imageProcessFailed'));
    } finally {
      cameraBtn.classList.remove('busy');
    }
  });

  // Read + downscale + JPEG-encode the picked file. iOS HEIC inputs are
  // decoded by the browser when drawn to canvas, so the output is always
  // a uniform JPEG regardless of source format.
  function processImageFile(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(new Error(t('imageProcessFailed')));
      reader.onload = () => {
        const img = new Image();
        img.onerror = () => reject(new Error(t('imageProcessFailed')));
        img.onload = () => {
          try {
            const { width, height } = fitWithin(img.naturalWidth, img.naturalHeight, MAX_IMAGE_DIMENSION);
            const canvas = document.createElement('canvas');
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0, width, height);
            const dataUrl = canvas.toDataURL('image/jpeg', IMAGE_QUALITY);
            // dataUrl: "data:image/jpeg;base64,<...>"
            const comma = dataUrl.indexOf(',');
            const data = dataUrl.slice(comma + 1);
            if (data.length > CLIENT_MAX_B64_BYTES) {
              reject(new Error(t('imageTooLarge')));
              return;
            }
            const previewUrl = URL.createObjectURL(new Blob(
              [Uint8Array.from(atob(data), (c) => c.charCodeAt(0))],
              { type: 'image/jpeg' },
            ));
            resolve({
              kind: 'image',
              mime: 'image/jpeg',
              name: file.name || 'image.jpg',
              data: data,
              _previewUrl: previewUrl,
            });
          } catch (e) { reject(e); }
        };
        img.src = reader.result;
      };
      reader.readAsDataURL(file);
    });
  }

  function fitWithin(w, h, max) {
    if (w <= max && h <= max) return { width: w, height: h };
    const scale = Math.min(max / w, max / h);
    return { width: Math.round(w * scale), height: Math.round(h * scale) };
  }

  function renderAttachmentChips() {
    attachmentChips.innerHTML = '';
    if (!pendingAttachments.length) {
      attachmentChips.hidden = true;
      return;
    }
    attachmentChips.hidden = false;
    pendingAttachments.forEach((att, idx) => {
      const chip = document.createElement('div');
      chip.className = 'attachment-chip';
      const img = document.createElement('img');
      img.alt = att.name || '';
      img.src = att._previewUrl;
      const rm = document.createElement('button');
      rm.className = 'attachment-chip-remove';
      rm.type = 'button';
      rm.textContent = '✕';
      rm.setAttribute('aria-label', t('attachmentRemoveAria'));
      rm.addEventListener('click', () => removeAttachment(idx));
      chip.appendChild(img);
      chip.appendChild(rm);
      attachmentChips.appendChild(chip);
    });
  }

  function removeAttachment(idx) {
    const removed = pendingAttachments.splice(idx, 1)[0];
    if (removed && removed._previewUrl) URL.revokeObjectURL(removed._previewUrl);
    renderAttachmentChips();
    if (state === 'idle') setState('idle');
  }

  function clearAttachments() {
    pendingAttachments.forEach((a) => a._previewUrl && URL.revokeObjectURL(a._previewUrl));
    pendingAttachments = [];
    renderAttachmentChips();
  }


  // Typing into the transcript box from idle or recording switches to
  // review. The placeholder lives in CSS (data-placeholder + :empty::before),
  // so the first keystroke replaces it automatically.
  transcriptBox.addEventListener('beforeinput', () => {
    if (state === 'idle') {
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
    // Empty content is shown as a CSS-driven placeholder (see
    // .transcript-box:empty::before); we never write the placeholder
    // string into textContent so it can't be sent or appended to.
    transcriptBox.textContent = text || '';
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
      // With a queued attachment but no transcript yet, the next tap
      // should send the photo (possibly with empty text), not start a
      // new recording. Mirrors the mic-label, which also shows "Senden".
      if (pendingAttachments.length > 0) {
        sendCurrent();
      } else {
        startRecording();
      }
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
    const hasAttachments = pendingAttachments.length > 0;
    // The discard button is always visible (next to the text field) so
    // its position stays stable across states. Disable it when there is
    // nothing to clear, otherwise the user gets a no-op tap.
    if (next === 'idle') {
      micLabel.textContent = hasAttachments ? t('micSend') : t('micRecord');
      updateTranscript('', false);
    } else if (next === 'recording') {
      micLabel.textContent = t('micStop');
    } else if (next === 'review') {
      micLabel.textContent = t('micSend');
      transcriptBox.classList.remove('active');
    }
    const hasText = (transcriptBox.textContent || '').trim().length > 0;
    discardBtn.disabled = next === 'idle' && !hasAttachments && !hasText;
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
    // The discard button now also represents "clear pending attachment".
    clearAttachments();
    setState('idle');
    setStatus('');
  }

  async function sendCurrent() {
    const text = (transcriptBox.textContent || '').trim();
    // Snapshot the attachments before resetting state so the network
    // call uses the right list even after the UI clears.
    const attachments = pendingAttachments.map((a) => ({
      kind: a.kind, mime: a.mime, name: a.name, data: a.data,
    }));
    clearAttachments();
    setState('idle');
    currentTranscript = '';
    sessionFinal = '';
    currentSessionText = '';
    if (!text && attachments.length === 0) return;
    await sendText(text, attachments);
  }

  async function sendText(text, attachments) {
    attachments = attachments || [];
    // Show the user bubble with the text plus a placeholder for any
    // attached image. Bubbles do not render images today (one-way: we
    // only forward them to the backend); the count makes the upload
    // visible to the user.
    const visible = text || (attachments.length
      ? '🖼 (' + attachments.length + ')'
      : '');
    addMessage('user', visible);

    const typingDiv = addMessage('assistant', '');
    typingDiv.classList.add('typing');
    setStatus('sending');

    const body = { text, session_id: sessionId, lang: activeLang() };
    if (attachments.length) body.attachments = attachments;

    try {
      const res = await fetch('/chat', VoxGateAuth.withAuthHeaders({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
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
      // Strict contract: backend must return {"response": "<string>"}. The
      // server enforces this and rejects malformed responses with 502, so
      // by the time we get here the field is guaranteed — but we still
      // guard defensively in case of future API drift.
      if (typeof data.response !== 'string') {
        throw new Error('Malformed response from server');
      }
      const reply = data.response;

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
  updateTtsToggleUI();
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
