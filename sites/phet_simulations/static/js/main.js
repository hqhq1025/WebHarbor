// >>> silent-fail-fix: fetch-auth-wrapper
// Wraps window.fetch so that a JSON 401 response with {error:'login_required',
// redirect:'/login?next=...'} triggers an actual browser redirect to /login.
// Without this the JSON body is swallowed as a 'success' result and the user
// click silently no-ops. Pairs with the @login_manager.unauthorized_handler
// installed in app.py. Root cause docs: gotcha #49.
(function () {
    if (window._fetchAuthWrapped) return;
    if (typeof window.fetch !== 'function') return;
    window._fetchAuthWrapped = true;
    var _origFetch = window.fetch.bind(window);
    window.fetch = function () {
        return _origFetch.apply(this, arguments).then(function (r) {
            if (r && r.status === 401) {
                var ct = '';
                try { ct = (r.headers && r.headers.get && r.headers.get('Content-Type')) || ''; } catch (e) {}
                if (ct.indexOf('application/json') !== -1) {
                    var cloned;
                    try { cloned = r.clone(); } catch (e) { return r; }
                    return cloned.json().then(function (d) {
                        if (d && d.error === 'login_required') {
                            var next = encodeURIComponent(location.pathname + location.search);
                            var url = (d.redirect || '/login');
                            url += (url.indexOf('?') === -1 ? '?' : '&') + 'next=' + next;
                            try { console.warn('[auth] redirecting:', url, d.message || ''); } catch (e) {}
                            location.href = url;
                        }
                        return r;
                    }).catch(function () { return r; });
                }
            }
            return r;
        });
    };
})();
// <<< silent-fail-fix

(function () {
  function getCsrfToken(form) {
    var input = form.querySelector('input[name="csrf_token"]');
    return input ? input.value : '';
  }

  document.querySelectorAll('.save-form').forEach(function (form) {
    var status = form.querySelector('.save-status');
    form.querySelectorAll('button[data-action]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var action = btn.getAttribute('data-action');
        var simId = form.getAttribute('data-sim-id');
        var endpoint = action === 'save' ? '/api/save-sim' : '/api/unsave-sim';

        fetch(endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(form),
          },
          body: JSON.stringify({ sim_id: simId }),
        })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (!data.ok) {
              status.textContent = 'Error: ' + (data.error || 'unknown');
              status.style.color = '#c0392b';
              return;
            }
            if (action === 'save') {
              btn.textContent = 'Remove from saved';
              btn.setAttribute('data-action', 'unsave');
              btn.classList.remove('btn-primary');
              btn.classList.add('btn-ghost');
              status.textContent = 'Saved to your account.';
            } else {
              btn.textContent = 'Save to my account';
              btn.setAttribute('data-action', 'save');
              btn.classList.remove('btn-ghost');
              btn.classList.add('btn-primary');
              status.textContent = 'Removed from saved.';
            }
            status.style.color = '#2e7d32';
          })
          .catch(function () {
            status.textContent = 'Network error, please retry.';
            status.style.color = '#c0392b';
          });
      });
    });
  });

  var playBtn = document.querySelector('.sim-detail-play');
  if (playBtn) {
    playBtn.addEventListener('click', function () {
      alert('Mirror snapshot — simulation playback is disabled in benchmark mode.');
    });
  }
})();
