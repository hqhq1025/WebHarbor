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

// Google Maps Mirror - main.js

(function () {
    'use strict';

    // Flash auto-dismiss
    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('.flash').forEach(function (el) {
            setTimeout(function () {
                el.style.transition = 'opacity 300ms ease';
                el.style.opacity = '0';
                setTimeout(function () { el.remove(); }, 300);
            }, 4000);
        });

        // Flash close button
        document.querySelectorAll('.flash-close').forEach(function (btn) {
            btn.addEventListener('click', function () {
                btn.closest('.flash').remove();
            });
        });
    });

    document.querySelectorAll('form[data-path-search="maps"]').forEach(function (form) {
        form.addEventListener('submit', function (event) {
            var input = form.querySelector('input[name="q"]');
            var query = input ? input.value.trim() : '';
            if (!query) return;
            event.preventDefault();
            var params = new URLSearchParams(new FormData(form));
            params.delete('q');
            var suffix = params.toString();
            window.location.href = '/maps/search/' + encodeURIComponent(query) + (suffix ? '?' + suffix : '');
        });
    });

    // Save place toggle
    window.toggleSave = function (placeId, btn) {
        fetch('/api/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ place_id: placeId })
        })
            .then(function (r) {
                if (r.status === 401) {
                    window.location.href = '/login';
                    throw new Error('login required');
                }
                return r.json();
            })
            .then(function (data) {
                if (!data.success) {
                    showToast(data.message || 'Error', 'error');
                    return;
                }
                if (btn) {
                    if (data.saved) {
                        btn.classList.add('saved');
                        var lbl = btn.querySelector('.lbl');
                        if (lbl) lbl.textContent = 'Saved';
                    } else {
                        btn.classList.remove('saved');
                        var lbl2 = btn.querySelector('.lbl');
                        if (lbl2) lbl2.textContent = 'Save';
                    }
                }
                showToast(data.message, 'success');
            })
            .catch(function () { /* swallowed */ });
    };

    // Toast / snackbar
    window.showToast = function (msg, type) {
        type = type || 'info';
        var c = document.querySelector('.flash-container');
        if (!c) {
            c = document.createElement('div');
            c.className = 'flash-container';
            document.body.appendChild(c);
        }
        var f = document.createElement('div');
        f.className = 'flash ' + type;
        f.innerHTML = '<span>' + msg + '</span><button class="flash-close">×</button>';
        f.querySelector('.flash-close').addEventListener('click', function () { f.remove(); });
        c.appendChild(f);
        setTimeout(function () {
            f.style.transition = 'opacity 300ms ease';
            f.style.opacity = '0';
            setTimeout(function () { f.remove(); }, 300);
        }, 4000);
    };

    // Live search suggestions
    var searchInputs = document.querySelectorAll('.search-bar input[name="q"]');
    var debounceTimer = null;
    searchInputs.forEach(function (inp) {
        inp.addEventListener('input', function () {
            var v = inp.value.trim();
            clearTimeout(debounceTimer);
            if (v.length < 2) return;
            debounceTimer = setTimeout(function () {
                // Could enhance with real autocomplete - for now just let submit handle it
            }, 250);
        });
    });

})();
