// Optional in-browser debug log overlay. Activated by appending
// ?debug=<token> to the URL where <token> matches the server's
// DEBUG_TOKEN env var. When inactive, this script does nothing and
// window.__dbg stays undefined, so call-sites must guard with
// `if (window.__dbg) window.__dbg(...)`.
(function () {
  var url = new URL(location.href);
  var token = url.searchParams.get('debug');
  if (!token) return;

  var t0 = Date.now();
  var events = [];
  var sendFailed = false;

  var panel = document.createElement('div');
  panel.id = 'debugPanel';
  panel.innerHTML =
    '<div class="debug-bar">' +
      '<span class="debug-tag">DEBUG</span>' +
      '<span class="debug-status" id="debugStatus">live</span>' +
      '<button type="button" id="debugCopy">Copy</button>' +
      '<button type="button" id="debugShare">Share</button>' +
      '<button type="button" id="debugClear">Clear</button>' +
      '<button type="button" id="debugMin">_</button>' +
    '</div>' +
    '<div class="debug-log" id="debugLog"></div>';

  function mount() {
    document.body.appendChild(panel);
    var logEl = document.getElementById('debugLog');
    var statusEl = document.getElementById('debugStatus');

    function render(ev) {
      var line = document.createElement('div');
      line.textContent = ev.t + 'ms ' + ev.type + ' ' + JSON.stringify(ev.data);
      logEl.appendChild(line);
      logEl.scrollTop = logEl.scrollHeight;
      while (logEl.children.length > 200) logEl.removeChild(logEl.firstChild);
    }

    function send(ev) {
      fetch('/debug-log', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Debug-Token': token,
        },
        body: JSON.stringify(ev),
        keepalive: true,
      }).then(function (r) {
        if (!r.ok) markFailed(r.status);
        else if (sendFailed) {
          sendFailed = false;
          statusEl.textContent = 'live';
          statusEl.className = 'debug-status';
        }
      }).catch(function () { markFailed('net'); });
    }

    function markFailed(why) {
      if (!sendFailed) {
        sendFailed = true;
        statusEl.textContent = 'local-only (' + why + ')';
        statusEl.className = 'debug-status warn';
      }
    }

    window.__dbg = function (type, data) {
      var ev = { t: Date.now() - t0, type: type, data: data || {} };
      events.push(ev);
      if (events.length > 500) events.shift();
      render(ev);
      send(ev);
    };

    document.getElementById('debugCopy').addEventListener('click', function () {
      var text = JSON.stringify(events, null, 2);
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(function () {
          flash(statusEl, 'copied');
        }, function () {
          fallbackCopy(text); flash(statusEl, 'copied (fallback)');
        });
      } else {
        fallbackCopy(text); flash(statusEl, 'copied (fallback)');
      }
    });

    document.getElementById('debugShare').addEventListener('click', function () {
      var blob = new Blob([JSON.stringify(events, null, 2)], { type: 'application/json' });
      var fileName = 'voxgate-debug-' + Date.now() + '.json';
      var file;
      try { file = new File([blob], fileName, { type: 'application/json' }); } catch (_) {}
      if (file && navigator.canShare && navigator.canShare({ files: [file] })) {
        navigator.share({ files: [file], title: 'VoxGate debug log' }).catch(function () {});
      } else {
        var u = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = u; a.download = fileName; a.click();
        setTimeout(function () { URL.revokeObjectURL(u); }, 5000);
      }
    });

    document.getElementById('debugClear').addEventListener('click', function () {
      events.length = 0;
      logEl.innerHTML = '';
      t0 = Date.now();
    });

    document.getElementById('debugMin').addEventListener('click', function () {
      panel.classList.toggle('minimized');
    });

    window.__dbg('start', { ua: navigator.userAgent, platform: document.documentElement.dataset.platform });
  }

  function fallbackCopy(text) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); } catch (_) {}
    document.body.removeChild(ta);
  }

  function flash(el, msg) {
    var prev = el.textContent;
    el.textContent = msg;
    setTimeout(function () { el.textContent = prev; }, 1500);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mount);
  } else {
    mount();
  }
})();
