// Platform detection. Loaded synchronously from index.html <head> so the
// [data-platform] selector applies before stylesheet parsing (no FOUC).
// iPadOS reports as Mac, so touch-points act as the tiebreaker.
(function () {
  var ua = navigator.userAgent;
  var p = 'other';
  if (/iPad|iPhone|iPod/.test(ua)) p = 'ios';
  else if (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1) p = 'ios';
  else if (/Android/.test(ua)) p = 'android';
  document.documentElement.dataset.platform = p;
})();
