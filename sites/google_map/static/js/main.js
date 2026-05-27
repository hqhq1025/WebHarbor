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

    // ---------------------------------------------------------------
    //  R8 — Keyboard shortcuts (Vim-style + Cmd+K command palette +
    //  ? help modal + symbol-glossary tooltip).
    // ---------------------------------------------------------------
    var R8 = {
        modifierKey: function (e) {
            // Treat Cmd (macOS) and Ctrl (Win/Linux) as the same chord modifier.
            return e.metaKey || e.ctrlKey;
        },
        isTyping: function (target) {
            if (!target) return false;
            var tag = (target.tagName || '').toLowerCase();
            if (tag === 'input' || tag === 'textarea' || tag === 'select') return true;
            if (target.isContentEditable) return true;
            return false;
        },
        focusSearch: function () {
            var inp = document.querySelector('.search-bar input[name="q"]')
                || document.querySelector('input[name="q"]');
            if (inp) {
                inp.focus();
                if (typeof inp.select === 'function') inp.select();
            }
        },
        dispatchMapAction: function (action) {
            // Emit a custom event so the map canvas can react without a hard
            // dependency on the Maps API being loaded.  _mapcanvas.html
            // installs the listener.  Falls back to the data-action button
            // when present so the visual ctl reflects the shortcut.
            document.dispatchEvent(new CustomEvent('r8:map-action', { detail: { action: action } }));
            var btn = document.querySelector('[data-action="' + action + '"]');
            if (btn) btn.click();
        },
        navigate: function (href) {
            if (!href) return;
            window.location.href = href;
        },
        installChordTracker: function () {
            // Vim-style "g h", "g l", … chords: 'g' then a second key within 1.5s.
            R8._chordTimer = null;
            R8._chordActive = false;
            document.addEventListener('keydown', function (e) {
                if (R8.isTyping(e.target)) return;
                if (e.key === 'g' && !R8.modifierKey(e) && !e.altKey && !e.shiftKey) {
                    R8._chordActive = true;
                    if (R8._chordTimer) clearTimeout(R8._chordTimer);
                    R8._chordTimer = setTimeout(function () { R8._chordActive = false; }, 1500);
                    return;
                }
                if (R8._chordActive) {
                    R8._chordActive = false;
                    if (R8._chordTimer) clearTimeout(R8._chordTimer);
                    var map = { h: '/', l: '/lists', t: '/trips', e: '/explore', s: '/saved' };
                    if (map[e.key]) {
                        e.preventDefault();
                        R8.navigate(map[e.key]);
                    }
                }
            });
        }
    };

    // Help + command-palette modal markup is injected lazily on first use.
    function ensureModal(id, builder) {
        var m = document.getElementById(id);
        if (m) return m;
        m = document.createElement('div');
        m.id = id;
        m.className = 'r8-modal-backdrop';
        m.setAttribute('hidden', '');
        m.setAttribute('role', 'dialog');
        m.setAttribute('aria-modal', 'true');
        m.innerHTML = builder();
        document.body.appendChild(m);
        m.addEventListener('click', function (ev) {
            if (ev.target === m) hideModal(m);
        });
        return m;
    }
    function showModal(m) {
        m.removeAttribute('hidden');
        m.classList.add('open');
        var first = m.querySelector('input, button, a, [tabindex]');
        if (first) try { first.focus(); } catch (e) {}
    }
    function hideModal(m) {
        if (!m) return;
        m.setAttribute('hidden', '');
        m.classList.remove('open');
    }

    function buildHelpModal() {
        return '<div class="r8-modal" role="document">'
             + '<header><h2 id="r8-help-title">Keyboard shortcuts</h2>'
             + '<button class="r8-modal-close" type="button" aria-label="Close">×</button></header>'
             + '<div class="r8-modal-body" data-help-body><p>Loading…</p></div>'
             + '</div>';
    }
    function buildCommandPalette() {
        return '<div class="r8-modal r8-cmdp" role="document" aria-labelledby="r8-cmdp-title">'
             + '<header><h2 id="r8-cmdp-title" class="sr-only">Command palette</h2>'
             + '<input type="search" class="r8-cmdp-input" placeholder="Jump to place, category, or list…" autocomplete="off">'
             + '<button class="r8-modal-close" type="button" aria-label="Close">×</button></header>'
             + '<ul class="r8-cmdp-results" role="listbox"></ul>'
             + '<footer class="r8-cmdp-footer">Enter to open · Esc to close · ↑↓ to move</footer>'
             + '</div>';
    }

    function openHelp() {
        var m = ensureModal('r8-help', buildHelpModal);
        m.querySelector('.r8-modal-close').onclick = function () { hideModal(m); };
        var body = m.querySelector('[data-help-body]');
        body.innerHTML = '<p>Loading…</p>';
        Promise.all([
            fetch('/help/keyboard-shortcuts').then(function (r) { return r.json(); }),
            fetch('/help/symbol-glossary').then(function (r) { return r.json(); }),
        ]).then(function (out) {
            var sc = out[0].shortcuts || [];
            var gl = out[1].glyphs || [];
            var html = '<h3>Keyboard</h3><table class="r8-help-table"><tbody>';
            sc.forEach(function (s) {
                var keys = (s.keys || []).map(function (k) { return '<kbd>' + k + '</kbd>'; }).join(' / ');
                html += '<tr><td>' + keys + '</td><td>' + s.label + '</td><td class="r8-help-desc">' + s.description + '</td></tr>';
            });
            html += '</tbody></table><h3>Symbol glossary</h3><table class="r8-help-table"><tbody>';
            gl.forEach(function (g) {
                html += '<tr><td><code>' + g.glyph + '</code></td><td>' + g.label + '</td><td class="r8-help-desc">' + g.description + '</td></tr>';
            });
            html += '</tbody></table>';
            body.innerHTML = html;
        }).catch(function () {
            body.innerHTML = '<p>Could not load shortcuts.</p>';
        });
        showModal(m);
    }

    function openCommandPalette() {
        var m = ensureModal('r8-cmdp', buildCommandPalette);
        m.querySelector('.r8-modal-close').onclick = function () { hideModal(m); };
        var input = m.querySelector('.r8-cmdp-input');
        var list = m.querySelector('.r8-cmdp-results');
        var selectedIdx = 0;
        var lastResults = [];
        function render(results) {
            lastResults = results;
            list.innerHTML = '';
            results.forEach(function (r, i) {
                var li = document.createElement('li');
                li.setAttribute('role', 'option');
                li.dataset.href = r.href;
                li.className = 'r8-cmdp-item' + (i === selectedIdx ? ' selected' : '');
                li.innerHTML = '<span class="r8-cmdp-kind">' + r.kind + '</span>'
                             + '<span class="r8-cmdp-label">' + r.label + '</span>'
                             + (r.subtitle ? '<span class="r8-cmdp-sub">' + r.subtitle + '</span>' : '');
                li.addEventListener('click', function () { R8.navigate(r.href); });
                list.appendChild(li);
            });
        }
        function flatten(payload) {
            var r = payload.results || {};
            var out = [];
            (r.pages || []).forEach(function (p) { out.push(p); });
            (r.categories || []).forEach(function (p) { out.push(p); });
            (r.cities || []).forEach(function (p) { out.push(p); });
            (r.places || []).forEach(function (p) { out.push(p); });
            return out;
        }
        function query(q) {
            fetch('/api/command-palette?limit=10&q=' + encodeURIComponent(q))
                .then(function (r) { return r.json(); })
                .then(function (p) {
                    selectedIdx = 0;
                    render(flatten(p));
                })
                .catch(function () {});
        }
        var debounce = null;
        input.value = '';
        input.oninput = function () {
            clearTimeout(debounce);
            var v = input.value;
            debounce = setTimeout(function () { query(v); }, 120);
        };
        input.onkeydown = function (e) {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                selectedIdx = Math.min(lastResults.length - 1, selectedIdx + 1);
                render(lastResults);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                selectedIdx = Math.max(0, selectedIdx - 1);
                render(lastResults);
            } else if (e.key === 'Enter') {
                e.preventDefault();
                var pick = lastResults[selectedIdx];
                if (pick) R8.navigate(pick.href);
            }
        };
        query('');
        showModal(m);
    }

    // Global key dispatcher
    document.addEventListener('keydown', function (e) {
        // Esc always closes modals first.
        if (e.key === 'Escape') {
            ['r8-cmdp', 'r8-help'].forEach(function (id) {
                var m = document.getElementById(id);
                if (m && !m.hasAttribute('hidden')) hideModal(m);
            });
            return;
        }
        // Cmd+K / Ctrl+K opens command palette (also when typing).
        if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
            e.preventDefault();
            openCommandPalette();
            return;
        }
        if (R8.isTyping(e.target)) return;
        if (e.altKey || e.metaKey || e.ctrlKey) return;
        switch (e.key) {
            case '+':
            case '=':
                e.preventDefault();
                R8.dispatchMapAction(e.key === '=' ? 'zoom-reset' : 'zoom-in');
                break;
            case '-':
            case '_':
                e.preventDefault();
                R8.dispatchMapAction('zoom-out');
                break;
            case '/':
                e.preventDefault();
                R8.focusSearch();
                break;
            case '?':
                e.preventDefault();
                openHelp();
                break;
            case 't':
                R8.dispatchMapAction('toggle-traffic');
                break;
            case 's':
                R8.dispatchMapAction('toggle-satellite');
                break;
            case 'b':
                R8.dispatchMapAction('toggle-bicycling');
                break;
        }
    });

    R8.installChordTracker();

    // Symbol-glossary tooltip — hover/focus over [data-glyph]
    document.addEventListener('mouseover', function (e) {
        var el = e.target.closest && e.target.closest('[data-glyph]');
        if (!el) return;
        if (el.dataset.r8TooltipReady) return;
        el.dataset.r8TooltipReady = '1';
        fetch('/help/symbol-glossary')
            .then(function (r) { return r.json(); })
            .then(function (p) {
                var item = (p.glyphs || []).find(function (g) {
                    return g.glyph.toLowerCase() === (el.dataset.glyph || '').toLowerCase();
                });
                if (item) {
                    el.setAttribute('title', item.label + ' — ' + item.description);
                    el.setAttribute('aria-label', item.label);
                }
            })
            .catch(function () {});
    });

    // Expose for inline handlers / tests
    window.R8 = window.R8 || R8;
    window.R8.openHelp = openHelp;
    window.R8.openCommandPalette = openCommandPalette;
})();
