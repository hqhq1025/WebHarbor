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

// Google Search mirror — main client-side helpers (R5).
// Adds: ARIA-aware PAA toggle, search-bar autocomplete (history+topic+spell),
// voice-input mock modal, sticky-tab shadow observer, mobile-swipe verticals,
// infinite-scroll toggle, skip-link focus management.

(function () {
    'use strict';

    // ---------- Flash messages: auto-dismiss after 4s ----------
    document.querySelectorAll('.flash-msg').forEach(msg => {
        setTimeout(() => {
            msg.style.transition = 'opacity 0.4s';
            msg.style.opacity = '0';
            setTimeout(() => msg.remove(), 400);
        }, 4000);
    });

    // ---------- People Also Ask accordion (ARIA-driven) ----------
    document.querySelectorAll('.paa-item').forEach(item => {
        const ansId = item.getAttribute('aria-controls');
        const ans = ansId ? document.getElementById(ansId) : item.nextElementSibling;
        const setOpen = (open) => {
            item.setAttribute('aria-expanded', open ? 'true' : 'false');
            item.classList.toggle('open', open);
            if (ans) {
                if (open) {
                    ans.removeAttribute('hidden');
                } else {
                    ans.setAttribute('hidden', '');
                }
            }
        };
        item.addEventListener('click', () => {
            const next = item.getAttribute('aria-expanded') !== 'true';
            setOpen(next);
        });
        item.addEventListener('keydown', (e) => {
            if (e.key === ' ' || e.key === 'Enter') {
                e.preventDefault();
                item.click();
            }
        });
    });

    // ---------- App launcher ----------
    const appBtn = document.querySelector('[data-apps-toggle]');
    const appDrop = document.querySelector('.apps-dropdown');
    if (appBtn && appDrop) {
        appBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const opened = appDrop.classList.toggle('open');
            appBtn.setAttribute('aria-expanded', opened ? 'true' : 'false');
        });
        document.addEventListener('click', (e) => {
            if (!appDrop.contains(e.target)) {
                appDrop.classList.remove('open');
                appBtn.setAttribute('aria-expanded', 'false');
            }
        });
    }

    // ---------- Bookmark toggle ----------
    window.toggleBookmark = async function (btn, resultId) {
        try {
            const res = await fetch('/api/bookmark/toggle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ result_id: resultId }),
            });
            if (res.status === 401) {
                window.location.href = '/login';
                return;
            }
            const data = await res.json();
            if (data.saved) {
                btn.classList.add('saved');
                btn.textContent = '★ Saved';
            } else {
                btn.classList.remove('saved');
                btn.textContent = '☆ Save';
            }
        } catch (e) { /* ignore */ }
    };

    // ---------- Helpers ----------
    function escapeHtml(s) {
        return String(s).replace(/[&<>"']/g, c => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        }[c]));
    }

    // Keyboard shortcut: / focuses search
    document.addEventListener('keydown', (e) => {
        if (e.key === '/' && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
            e.preventDefault();
            const input = document.querySelector('.search-box input');
            if (input) input.focus();
        }
        if (e.key === 'Escape') {
            closeAutocomplete();
            closeVoiceModal();
        }
    });

    // ---------- R5: Autocomplete dropdown ----------
    const acInput = document.querySelector('[data-autocomplete-input]');
    const acList = document.getElementById('ac-listbox');
    let acTimer = null;
    let acItems = [];
    let acIndex = -1;
    let acAbort = null;

    function closeAutocomplete() {
        if (!acList) return;
        acList.hidden = true;
        acList.innerHTML = '';
        acItems = [];
        acIndex = -1;
        if (acInput) acInput.setAttribute('aria-expanded', 'false');
    }

    function renderAutocomplete(data) {
        if (!acList) return;
        acItems = [];
        acList.innerHTML = '';
        const items = (data && data.suggestions) || [];
        if (data && data.spelling) {
            const li = document.createElement('li');
            li.className = 'ac-item ac-spelling';
            li.setAttribute('role', 'option');
            li.dataset.term = data.spelling.text;
            li.innerHTML = 'Did you mean <strong>' + escapeHtml(data.spelling.text) + '</strong>?';
            acList.appendChild(li);
            acItems.push(li);
        }
        items.forEach(s => {
            const li = document.createElement('li');
            li.className = 'ac-item ac-' + s.kind;
            li.setAttribute('role', 'option');
            li.dataset.term = s.text;
            const icon = s.kind === 'history' ? '⟲'
                : s.kind === 'trending' ? '↗'
                : s.kind === 'topic' ? '◎'
                : '🔍';
            li.innerHTML = '<span class="ac-icon" aria-hidden="true">' + icon + '</span>'
                + '<span class="ac-text">' + escapeHtml(s.text) + '</span>'
                + '<span class="ac-tag">' + escapeHtml(s.kind) + '</span>';
            acList.appendChild(li);
            acItems.push(li);
        });
        if (acItems.length === 0) {
            closeAutocomplete();
            return;
        }
        acList.hidden = false;
        acIndex = -1;
        if (acInput) acInput.setAttribute('aria-expanded', 'true');
        acItems.forEach((li, i) => {
            li.addEventListener('mousedown', (e) => {
                e.preventDefault();
                pickAutocomplete(i);
            });
        });
    }

    function pickAutocomplete(i) {
        if (i < 0 || i >= acItems.length || !acInput) return;
        const term = acItems[i].dataset.term;
        acInput.value = term;
        closeAutocomplete();
        const form = acInput.closest('form');
        if (form) form.submit();
    }

    function highlightAutocomplete() {
        acItems.forEach((li, i) => li.classList.toggle('active', i === acIndex));
    }

    if (acInput && acList) {
        acInput.addEventListener('input', () => {
            const q = acInput.value;
            if (acTimer) clearTimeout(acTimer);
            acTimer = setTimeout(() => {
                if (acAbort) acAbort.abort();
                acAbort = new AbortController();
                fetch('/api/suggestions?q=' + encodeURIComponent(q),
                      { signal: acAbort.signal, headers: { 'Accept': 'application/json' } })
                    .then(r => r.ok ? r.json() : null)
                    .then(data => { if (data) renderAutocomplete(data); })
                    .catch(() => { /* aborted or net error */ });
            }, 120);
        });
        acInput.addEventListener('focus', () => {
            if (!acInput.value.trim()) {
                fetch('/api/suggestions?q=')
                    .then(r => r.ok ? r.json() : null)
                    .then(data => { if (data) renderAutocomplete(data); })
                    .catch(() => {});
            }
        });
        acInput.addEventListener('keydown', (e) => {
            if (acList.hidden) return;
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                acIndex = Math.min(acIndex + 1, acItems.length - 1);
                highlightAutocomplete();
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                acIndex = Math.max(acIndex - 1, -1);
                highlightAutocomplete();
            } else if (e.key === 'Enter') {
                if (acIndex >= 0) {
                    e.preventDefault();
                    pickAutocomplete(acIndex);
                }
            }
        });
        document.addEventListener('click', (e) => {
            if (!acList.contains(e.target) && e.target !== acInput) {
                closeAutocomplete();
            }
        });
    }

    // ---------- R5: Voice-input mock modal ----------
    const voiceBtn = document.querySelector('[data-voice-toggle]');
    const voiceModal = document.querySelector('.voice-modal');
    function openVoiceModal() {
        if (!voiceModal) return;
        voiceModal.removeAttribute('hidden');
        voiceModal.classList.add('open');
        const closeBtn = voiceModal.querySelector('[data-voice-close]');
        if (closeBtn) closeBtn.focus();
    }
    function closeVoiceModal() {
        if (!voiceModal) return;
        voiceModal.classList.remove('open');
        voiceModal.setAttribute('hidden', '');
    }
    if (voiceBtn && voiceModal) {
        voiceBtn.addEventListener('click', (e) => {
            e.preventDefault();
            openVoiceModal();
        });
        voiceModal.addEventListener('click', (e) => {
            if (e.target === voiceModal) closeVoiceModal();
        });
        const closeBtn = voiceModal.querySelector('[data-voice-close]');
        if (closeBtn) closeBtn.addEventListener('click', closeVoiceModal);
    }

    // ---------- R5: Sticky-tab shadow observer ----------
    const tabs = document.querySelector('.serp-tabs-sticky');
    if (tabs && 'IntersectionObserver' in window) {
        const sentinel = document.createElement('div');
        sentinel.className = 'serp-tabs-sentinel';
        tabs.parentNode.insertBefore(sentinel, tabs);
        const obs = new IntersectionObserver(entries => {
            entries.forEach(en => {
                tabs.classList.toggle('is-stuck', !en.isIntersecting);
            });
        }, { threshold: [0] });
        obs.observe(sentinel);
    }

    // ---------- R5: Swipeable verticals tabs (mobile) ----------
    const swipeTabs = document.querySelector('[data-swipeable-tabs]');
    if (swipeTabs) {
        let downX = null;
        let scrollStart = 0;
        swipeTabs.addEventListener('touchstart', (e) => {
            downX = e.touches[0].clientX;
            scrollStart = swipeTabs.scrollLeft;
        }, { passive: true });
        swipeTabs.addEventListener('touchmove', (e) => {
            if (downX === null) return;
            const dx = e.touches[0].clientX - downX;
            swipeTabs.scrollLeft = scrollStart - dx;
        }, { passive: true });
        swipeTabs.addEventListener('touchend', () => { downX = null; });
    }

    // ---------- R5: Infinite-scroll toggle ----------
    const modeBtns = document.querySelectorAll('.scroll-mode-btn');
    const pagination = document.querySelector('.pagination');
    const seeMoreBar = document.querySelector('.see-more-bar');
    let infiniteMode = false;
    let infinitePage = 1;
    let infiniteBusy = false;

    function setScrollMode(mode) {
        infiniteMode = (mode === 'infinite');
        modeBtns.forEach(b => {
            const on = b.dataset.scrollMode === mode;
            b.classList.toggle('active', on);
            b.setAttribute('aria-pressed', on ? 'true' : 'false');
        });
        if (pagination) pagination.style.display = infiniteMode ? 'none' : '';
        if (seeMoreBar) seeMoreBar.style.display = infiniteMode ? 'none' : '';
    }
    modeBtns.forEach(btn => {
        btn.addEventListener('click', () => setScrollMode(btn.dataset.scrollMode));
    });

    function maybeLoadMore() {
        if (!infiniteMode || infiniteBusy) return;
        const buffer = 600;
        if (window.innerHeight + window.scrollY + buffer < document.body.offsetHeight) return;
        infiniteBusy = true;
        const params = new URLSearchParams(window.location.search);
        infinitePage += 1;
        params.set('page', String(infinitePage));
        params.set('partial', '1');
        fetch(window.location.pathname + '?' + params.toString())
            .then(r => r.ok ? r.text() : null)
            .then(html => {
                if (!html) { infiniteBusy = false; return; }
                // Extract serp-results from returned HTML (works because the
                // route still renders full pages; we splice the matching div).
                const tmp = document.createElement('div');
                tmp.innerHTML = html;
                const newResults = tmp.querySelectorAll('.serp-result');
                const host = document.querySelector('.serp-main');
                const lastResult = Array.from(host.querySelectorAll('.serp-result')).pop();
                newResults.forEach(r => {
                    if (lastResult) lastResult.parentNode.insertBefore(r.cloneNode(true), lastResult.nextSibling);
                    else host.appendChild(r.cloneNode(true));
                });
                infiniteBusy = false;
                if (newResults.length === 0) infiniteMode = false;
            })
            .catch(() => { infiniteBusy = false; });
    }
    window.addEventListener('scroll', maybeLoadMore, { passive: true });

    // ---------- R5: Skip-link focus ----------
    const skip = document.querySelector('.skip-link');
    if (skip) {
        skip.addEventListener('click', () => {
            const target = document.getElementById('main-results');
            if (target) {
                target.setAttribute('tabindex', '-1');
                target.focus();
            }
        });
    }
})();
