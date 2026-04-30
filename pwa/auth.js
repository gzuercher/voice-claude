// Auth module for VoxGate PWA.
//
// Wraps Google Identity Services and the server's /auth/* endpoints.
// Frontend stays Google-only for now; adding another OIDC provider
// later is a localized change inside this file plus the relevant
// /auth/login/{provider} backend route.
const VoxGateAuth = (() => {
  let currentUser = null; // { email, provider } or null
  let onChange = null;
  let googleClientId = '';
  let providers = [];
  let translate = (k) => k;
  let initialized = false;

  function getCookie(name) {
    const parts = ('; ' + document.cookie).split('; ' + name + '=');
    if (parts.length < 2) return '';
    return parts.pop().split(';').shift();
  }

  async function fetchMe() {
    try {
      const res = await fetch('/auth/me', { credentials: 'include' });
      if (res.ok) return await res.json();
    } catch (_) { /* offline */ }
    return null;
  }

  async function postLogin(provider, idToken) {
    const res = await fetch(`/auth/login/${provider}`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id_token: idToken }),
    });
    let data = null;
    try { data = await res.json(); } catch (_) { /* ignore */ }
    return { status: res.status, data };
  }

  async function logout() {
    try {
      // Logout is state-changing — send the CSRF header so the server can
      // distinguish a real user click from a cross-site logout-CSRF attempt.
      await fetch('/auth/logout', withAuthHeaders({ method: 'POST' }));
    } catch (_) { /* offline */ }
    if (window.google && window.google.accounts && window.google.accounts.id) {
      try { window.google.accounts.id.disableAutoSelect(); } catch (_) {}
    }
    currentUser = null;
    if (onChange) onChange(null);
    updateHeaderUI();
    showOverlay();
  }

  function updateHeaderUI() {
    const headerLogoutBtn = document.getElementById('headerLogoutBtn');
    if (headerLogoutBtn) headerLogoutBtn.hidden = !currentUser;
  }

  function withAuthHeaders(init) {
    const out = Object.assign({}, init || {});
    out.credentials = 'include';
    out.headers = Object.assign({}, (init && init.headers) || {});
    const csrf = getCookie('vg_csrf');
    if (csrf) out.headers['X-CSRF-Token'] = csrf;
    return out;
  }

  function renderGoogleButton() {
    const el = document.getElementById('googleSignInButton');
    if (!el) return;
    if (!googleClientId) {
      el.textContent = translate('signInUnavailable');
      return;
    }
    if (!window.google || !window.google.accounts || !window.google.accounts.id) {
      // GSI library is loaded async; retry shortly.
      setTimeout(renderGoogleButton, 200);
      return;
    }
    if (!initialized) {
      window.google.accounts.id.initialize({
        client_id: googleClientId,
        callback: async (response) => {
          const result = await postLogin('google', response.credential);
          if (result.status === 200) {
            currentUser = result.data;
            if (onChange) onChange(currentUser);
            updateHeaderUI();
            hideOverlay();
          } else if (result.status === 403) {
            showOverlay(translate('notAllowedError'));
          } else if (result.status === 429) {
            showOverlay(translate('rateLimitedError'));
          } else {
            showOverlay(translate('signInFailedError'));
          }
        },
      });
      initialized = true;
    }
    el.innerHTML = '';
    window.google.accounts.id.renderButton(el, {
      theme: 'outline',
      size: 'large',
      type: 'standard',
      shape: 'rectangular',
    });
  }

  function showOverlay(errorMessage) {
    const overlay = document.getElementById('authOverlay');
    const errorEl = document.getElementById('authError');
    const userEl = document.getElementById('authUser');
    const logoutBtn = document.getElementById('logoutBtn');
    if (overlay) overlay.hidden = false;
    if (errorEl) {
      errorEl.hidden = !errorMessage;
      errorEl.textContent = errorMessage || '';
    }
    if (currentUser) {
      if (userEl) {
        userEl.hidden = false;
        userEl.textContent = (translate('loggedInAs') || '') + ' ' + currentUser.email;
      }
      if (logoutBtn) logoutBtn.hidden = false;
    } else {
      if (userEl) userEl.hidden = true;
      if (logoutBtn) logoutBtn.hidden = true;
      renderGoogleButton();
    }
  }

  function hideOverlay() {
    const overlay = document.getElementById('authOverlay');
    if (overlay) overlay.hidden = true;
  }

  async function init(opts) {
    googleClientId = (opts && opts.googleClientId) || '';
    providers = (opts && opts.providers) || [];
    onChange = (opts && opts.onChange) || null;
    translate = (opts && opts.translate) || ((k) => k);
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
      logoutBtn.addEventListener('click', (e) => {
        e.preventDefault();
        logout();
      });
    }
    const headerLogoutBtn = document.getElementById('headerLogoutBtn');
    if (headerLogoutBtn) {
      headerLogoutBtn.addEventListener('click', (e) => {
        e.preventDefault();
        logout();
      });
    }
    const me = await fetchMe();
    if (me) {
      currentUser = me;
      if (onChange) onChange(currentUser);
      updateHeaderUI();
      hideOverlay();
    } else {
      currentUser = null;
      updateHeaderUI();
      showOverlay();
    }
  }

  return {
    init,
    withAuthHeaders,
    logout,
    showLogin: showOverlay,
    isAuthenticated: () => currentUser !== null,
    getUser: () => currentUser,
    refreshTranslations: () => {
      // Called by app.js when the UI language changes — re-render Google button
      // labels and re-run any visible-text updates.
      const overlay = document.getElementById('authOverlay');
      if (overlay && !overlay.hidden && !currentUser) {
        renderGoogleButton();
      }
    },
  };
})();

window.VoxGateAuth = VoxGateAuth;
