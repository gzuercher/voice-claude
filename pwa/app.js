  let instanceConfig = { name: 'VoxGate', color: '#c8ff00', lang: 'de-CH', langs: ['de-CH', 'fr-CH'], maxLength: 4000 };
  let recognition = null;
  let isRecording = false;
  let currentTranscript = '';
  let finalTranscript = '';
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
  const langBtn = document.getElementById('langBtn');
  const muteBtn = document.getElementById('muteBtn');
  const newConvBtn = document.getElementById('newConvBtn');

  function updateLangBtn() {
    langBtn.textContent = activeLang().toUpperCase();
  }

  function updateMuteBtn() {
    muteBtn.textContent = muted ? '🔇' : '🔊';
    muteBtn.classList.toggle('muted', muted);
  }

  langBtn.addEventListener('click', () => {
    const langs = supportedLangs();
    const lang = activeLang();
    const idx = langs.indexOf(lang);
    const next = langs[(idx + 1) % langs.length] || langs[0];
    currentLang = next;
    localStorage.setItem('voxLang', next);
    updateLangBtn();
    if (isRecording) stopRecording();
  });

  muteBtn.addEventListener('click', () => {
    muted = !muted;
    localStorage.setItem('voxMuted', muted ? '1' : '0');
    if (muted && 'speechSynthesis' in window) speechSynthesis.cancel();
    updateMuteBtn();
  });

  newConvBtn.addEventListener('click', () => {
    sessionId = (crypto.randomUUID ? crypto.randomUUID()
      : Date.now() + '-' + Math.random().toString(36).slice(2));
    sessionStorage.setItem('voxSession', sessionId);
    messagesEl.innerHTML = '';
    if ('speechSynthesis' in window) speechSynthesis.cancel();
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
    transcriptBox.textContent = text || 'Bereit...';
    transcriptBox.className = 'transcript-box' + (active ? ' active' : '');
  }

  function addMessage(role, text) {
    const empty = document.getElementById('emptyState');
    if (empty) empty.remove();

    const div = document.createElement('div');
    div.className = 'message ' + role;
    const label = role === 'user' ? 'Du' : instanceConfig.name;
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
    if (isRecording) {
      stopAndSend();
    } else {
      startRecording();
    }
  }

  function startRecording() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      alert('Web Speech API not supported. Use Chrome.');
      return;
    }

    if ('speechSynthesis' in window) speechSynthesis.cancel();

    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SR();
    recognition.lang = activeLang();
    recognition.continuous = true;
    recognition.interimResults = true;

    finalTranscript = '';
    currentTranscript = '';

    recognition.onstart = () => {
      isRecording = true;
      micBtn.classList.add('recording');
      micLabel.textContent = 'Senden';
      updateTranscript('', true);
      setStatus('online');
    };

    recognition.onresult = (e) => {
      let interim = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript;
        if (e.results[i].isFinal) {
          finalTranscript += t + ' ';
        } else {
          interim += t;
        }
      }
      currentTranscript = (finalTranscript + interim).trim();
      updateTranscript(currentTranscript, true);
    };

    recognition.onend = () => {
      if (isRecording) {
        recognition.start();
      }
    };

    recognition.onerror = (e) => {
      if (e.error === 'no-speech') return;
      console.error(e.error);
      stopRecording();
      setStatus('error');
    };

    recognition.start();
  }

  function stopRecording() {
    isRecording = false;
    if (recognition) {
      recognition.onend = null;
      recognition.stop();
    }
    micBtn.classList.remove('recording');
    micLabel.textContent = 'Aufnehmen';
  }

  async function stopAndSend() {
    const text = currentTranscript.trim();
    stopRecording();

    if (!text) {
      updateTranscript('', false);
      return;
    }

    addMessage('user', text);
    currentTranscript = '';
    finalTranscript = '';
    updateTranscript('', false);

    const typingDiv = addMessage('assistant', '');
    typingDiv.classList.add('typing');
    setStatus('sending');

    try {
      const headers = { 'Content-Type': 'application/json' };
      const token = localStorage.getItem('apiToken');
      if (token) headers['Authorization'] = 'Bearer ' + token;

      const res = await fetch('/claude', {
        method: 'POST',
        headers,
        body: JSON.stringify({ text, session_id: sessionId })
      });

      if (!res.ok) throw new Error('HTTP ' + res.status);
      const data = await res.json();
      const reply = data.response || data.text || JSON.stringify(data);

      typingDiv.classList.remove('typing');
      typingDiv.querySelector('.message-bubble').textContent = reply;
      setStatus('online');
      speak(reply);
    } catch (err) {
      typingDiv.classList.remove('typing');
      typingDiv.querySelector('.message-bubble').textContent = 'Fehler: ' + err.message;
      setStatus('error');
    }

    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  updateLangBtn();
  updateMuteBtn();
  loadConfig().then(updateLangBtn);
  setStatus('');
