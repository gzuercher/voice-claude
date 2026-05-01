// Theme bootstrap. Loaded synchronously from index.html <head> so the
// [data-theme] attribute is on <html> before stylesheet parsing — same
// pattern as platform.js. Without this, a stored "light" preference
// would cause a brief flash of the dark default before app.js runs.
(function () {
  var stored = null;
  try { stored = localStorage.getItem('voxTheme'); } catch (_) {}
  // Valid values: "auto" (follow OS), "light", "dark". Anything else
  // is treated as "auto" so a corrupted localStorage entry doesn't
  // brick the UI.
  if (stored !== 'light' && stored !== 'dark') stored = 'auto';
  document.documentElement.dataset.theme = stored;
})();
