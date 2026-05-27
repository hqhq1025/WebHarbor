/* R8: Google Flights embed widget loader.
 *
 * Hydrates every <div data-google-flights-widget> on the page by injecting
 * a sized iframe into /flights?from=...&to=...&embed=1. Educational scaffold
 * for the developer/widget-embed page — agents can fetch this URL to verify
 * the documented script-embed path serves real JavaScript.
 */
(function () {
  'use strict';
  function init() {
    var hosts = document.querySelectorAll('[data-google-flights-widget]');
    if (!hosts || hosts.length === 0) return;
    var base = (function () {
      try {
        var u = new URL(document.currentScript ? document.currentScript.src : window.location.href);
        return u.origin;
      } catch (e) { return ''; }
    })();
    hosts.forEach(function (host) {
      var origin = (host.dataset.origin || 'JFK').toUpperCase();
      var destination = (host.dataset.destination || 'LAX').toUpperCase();
      var width = host.dataset.width || host.getAttribute('width') || '320';
      var height = host.dataset.height || host.getAttribute('height') || '420';
      var iframe = document.createElement('iframe');
      iframe.src = base + '/flights?from=' + encodeURIComponent(origin) +
                   '&to=' + encodeURIComponent(destination) + '&embed=1';
      iframe.width = String(width);
      iframe.height = String(height);
      iframe.frameBorder = '0';
      iframe.loading = 'lazy';
      iframe.title = 'Google Flights - ' + origin + ' to ' + destination;
      iframe.style.border = '0';
      iframe.style.borderRadius = '6px';
      iframe.style.display = 'block';
      host.appendChild(iframe);
    });
  }
  if (document.readyState !== 'loading') { init(); }
  else { document.addEventListener('DOMContentLoaded', init); }
})();
