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

// BBC News mirror — interactive helpers

function csrfToken() {
    const el = document.querySelector('meta[name="csrf-token"]');
    return el ? el.getAttribute('content') : '';
}

function showToast(message, type) {
    type = type || 'info';
    const toast = document.createElement('div');
    toast.className = 'toast toast-' + type;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 350);
    }, 2600);
}

function updateHeaderCounts(rlCount, bmCount) {
    const rl = document.getElementById('rl-count');
    if (rl && rlCount !== undefined) rl.textContent = rlCount;
    const bm = document.getElementById('bm-count');
    if (bm && bmCount !== undefined) bm.textContent = bmCount;
}

// --- Reading List ---
function toggleReadingList(articleId, btn) {
    const active = btn.classList.contains('active');
    const url = active ? '/api/reading-list/remove' : '/api/reading-list/add';
    const body = active
        ? { article_id: articleId }
        : { article_id: articleId, folder: 'Read Later' };
    if (active) {
        // Need an item_id to remove — fallback: use add endpoint with a "remove" flag, but API expects item_id.
        // Simpler: add will update if already exists; toggle state through a second call.
        // For detail page we only support "add" (saving). Subsequent clicks just re-save.
    }
    fetch('/api/reading-list/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ article_id: articleId, folder: 'Read Later' }),
    })
        .then((r) => r.json())
        .then((data) => {
            if (data.success) {
                btn.classList.add('active');
                const label = btn.querySelector('.rl-label');
                if (label) label.textContent = 'Saved to list';
                updateHeaderCounts(data.reading_list_count);
                showToast(data.message || 'Added to reading list', 'success');
            } else {
                showToast(data.message || 'Sign in to save stories', 'error');
            }
        })
        .catch(() => {
            window.location.href = '/login';
        });
}

// --- Bookmarks ---
function toggleBookmark(articleId, btn) {
    fetch('/api/bookmark/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ article_id: articleId }),
    })
        .then((r) => {
            if (r.status === 401) {
                window.location.href = '/login';
                return;
            }
            return r.json();
        })
        .then((data) => {
            if (!data) return;
            if (data.success) {
                const label = btn.querySelector('.bm-label');
                if (data.action === 'added') {
                    btn.classList.add('active');
                    if (label) label.textContent = 'Bookmarked';
                    showToast('Added to bookmarks', 'success');
                } else {
                    btn.classList.remove('active');
                    if (label) label.textContent = 'Bookmark';
                    showToast('Removed from bookmarks', 'info');
                }
                updateHeaderCounts(undefined, data.bookmark_count);
            }
        })
        .catch(() => {
            window.location.href = '/login';
        });
}

// --- Comment likes ---
function likeComment(commentId, btn) {
    fetch('/api/comment/like', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ comment_id: commentId }),
    })
        .then((r) => {
            if (r.status === 401) {
                window.location.href = '/login';
                return;
            }
            return r.json();
        })
        .then((data) => {
            if (data && data.success) {
                const count = btn.querySelector('.like-count');
                if (count) count.textContent = data.like_count;
            }
        })
        .catch(() => {});
}

// --- Share ---
function copyShareUrl() {
    if (navigator.clipboard) {
        navigator.clipboard
            .writeText(window.location.href)
            .then(() => showToast('Article link copied', 'success'))
            .catch(() => showToast('Could not copy link', 'error'));
    } else {
        showToast(window.location.href, 'info');
    }
}

// --- Mobile menu toggle ---
function toggleMobileNav() {
    const nav = document.getElementById('mobile-nav');
    if (nav) nav.classList.toggle('open');
}

// --- Fade-in on scroll ---
document.addEventListener('DOMContentLoaded', () => {
    const io = new IntersectionObserver(
        (entries) => {
            entries.forEach((e) => {
                if (e.isIntersecting) {
                    e.target.classList.add('in-view');
                    io.unobserve(e.target);
                }
            });
        },
        { threshold: 0.08 }
    );
    document.querySelectorAll('.fade-up').forEach((el) => io.observe(el));

    // Auto-dismiss flash messages
    setTimeout(() => {
        document.querySelectorAll('.flash-message').forEach((el) => {
            el.style.opacity = '0';
            setTimeout(() => el.remove(), 400);
        });
    }, 4500);
});

/* ============================================================
 * R4: share modal + sticky video player
 * ============================================================ */
(function () {
    const modal = document.getElementById('bbc-share-modal');
    if (!modal) return;
    const titleEl   = modal.querySelector('#bbc-share-title');
    const headEl    = modal.querySelector('#bbc-share-headline');
    const urlInput  = modal.querySelector('#bbc-share-url');
    const emailForm = modal.querySelector('.bbc-share-email-form');
    const emailNote = modal.querySelector('[data-share-result]');
    const twitterA  = modal.querySelector('.bbc-share-twitter');
    const facebookA = modal.querySelector('.bbc-share-facebook');
    const whatsappA = modal.querySelector('.bbc-share-whatsapp');

    function open(opts) {
        const url = opts.url || window.location.href;
        const title = opts.title || document.title;
        const slug = opts.slug || '';
        titleEl.textContent = 'Share this story';
        headEl.textContent = title;
        urlInput.value = url;
        twitterA.href  = 'https://twitter.com/intent/tweet?text=' + encodeURIComponent(title) + '&url=' + encodeURIComponent(url);
        facebookA.href = 'https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(url);
        whatsappA.href = 'https://wa.me/?text=' + encodeURIComponent(title + ' ' + url);
        if (slug) {
            emailForm.setAttribute('action', '/article/' + slug + '/share');
        }
        if (emailNote) { emailNote.hidden = true; emailNote.textContent = ''; }
        modal.hidden = false;
    }
    function close() { modal.hidden = true; }

    modal.addEventListener('click', function (ev) {
        if (ev.target.matches('[data-share-close]')) close();
    });
    document.addEventListener('keydown', function (ev) {
        if (ev.key === 'Escape' && !modal.hidden) close();
    });
    document.addEventListener('click', function (ev) {
        const trigger = ev.target.closest('[data-share-trigger]');
        if (!trigger) return;
        ev.preventDefault();
        open({
            url:   trigger.getAttribute('data-share-url')   || window.location.href,
            title: trigger.getAttribute('data-share-title') || document.title,
            slug:  trigger.getAttribute('data-share-slug')  || '',
        });
    });

    // Copy-link button
    modal.querySelector('[data-share-method="copy"]').addEventListener('click', function () {
        const v = urlInput.value;
        if (navigator.clipboard) navigator.clipboard.writeText(v);
        else { urlInput.select(); document.execCommand('copy'); }
        if (emailNote) {
            emailNote.hidden = false;
            emailNote.textContent = 'Link copied to clipboard.';
        }
    });

    // Email submit — POST to /article/<slug>/share with fetch
    if (emailForm) {
        emailForm.addEventListener('submit', function (ev) {
            ev.preventDefault();
            const action = emailForm.getAttribute('action');
            if (!action) return;
            const data = new FormData(emailForm);
            fetch(action, { method: 'POST', body: data, credentials: 'same-origin' })
                .then(r => r.json())
                .then(j => {
                    if (emailNote) {
                        emailNote.hidden = false;
                        emailNote.textContent = 'Email prepared: ' + (j.subject || '') + ' (to ' + (j.recipient || '') + ').';
                    }
                })
                .catch(() => {
                    if (emailNote) {
                        emailNote.hidden = false;
                        emailNote.textContent = 'Could not contact server.';
                    }
                });
        });
    }

    // Sticky video player — toggle a .is-stuck class when the user
    // scrolls past the original wrapper position.
    const stickyWraps = document.querySelectorAll('.sticky-video-wrap');
    if (stickyWraps.length && 'IntersectionObserver' in window) {
        stickyWraps.forEach(function (wrap) {
            const observer = new IntersectionObserver(function (entries) {
                entries.forEach(function (entry) {
                    wrap.classList.toggle('is-stuck', !entry.isIntersecting);
                });
            }, { rootMargin: '-120px 0px 0px 0px', threshold: 0 });
            observer.observe(wrap);
            const close = wrap.querySelector('.sticky-video-close');
            if (close) close.addEventListener('click', function () {
                wrap.classList.remove('is-stuck');
                wrap.style.display = 'none';
            });
        });
    }
})();

/* ============================================================
 * R5: dark-mode + high-contrast toggles (cookie + localStorage)
 * ============================================================ */
(function () {
    function setPref(name, value) {
        try { localStorage.setItem(name, value); } catch (e) {}
        document.body.setAttribute('data-' + name.replace('bbc_', '').replace('_', ''), value);
        const endpoint = name === 'bbc_dark_mode'
            ? '/api/dark-mode' : '/api/high-contrast';
        const form = new FormData();
        form.append('value', value);
        form.append('csrf_token', csrfToken());
        fetch(endpoint, { method: 'POST', body: form, credentials: 'same-origin' })
            .catch(() => {});
    }

    function loadPref(name) {
        try { return localStorage.getItem(name); } catch (e) { return null; }
    }

    document.addEventListener('DOMContentLoaded', function () {
        // Hydrate from localStorage (sync ahead of cookie round-trip).
        const dm = loadPref('bbc_dark_mode');
        if (dm) document.body.setAttribute('data-darkmode', dm);
        const hc = loadPref('bbc_high_contrast');
        if (hc) document.body.setAttribute('data-highcontrast', hc);

        const dmBtn = document.getElementById('darkmode-toggle');
        if (dmBtn) dmBtn.addEventListener('click', function () {
            const next = document.body.getAttribute('data-darkmode') === 'on' ? 'off' : 'on';
            setPref('bbc_dark_mode', next);
            dmBtn.setAttribute('aria-pressed', next === 'on' ? 'true' : 'false');
            dmBtn.setAttribute('data-current', next);
        });

        const hcBtn = document.getElementById('contrast-toggle');
        if (hcBtn) hcBtn.addEventListener('click', function () {
            const next = document.body.getAttribute('data-highcontrast') === 'on' ? 'off' : 'on';
            setPref('bbc_high_contrast', next);
            hcBtn.setAttribute('aria-pressed', next === 'on' ? 'true' : 'false');
            hcBtn.setAttribute('data-current', next);
        });
    });
})();

/* ============================================================
 * R5: ARIA live region — announce breaking news to screen readers
 * ============================================================ */
(function () {
    document.addEventListener('DOMContentLoaded', function () {
        const region = document.getElementById('bbc-live-region');
        if (!region) return;
        const headline = region.getAttribute('data-breaking-headline');
        if (headline) {
            // Wait a tick so the page has settled before the announcement.
            setTimeout(function () {
                region.textContent = 'Breaking: ' + headline;
            }, 600);
        }
    });
})();

/* ============================================================
 * R5: search auto-suggest (uses /api/search/suggest)
 * ============================================================ */
(function () {
    document.addEventListener('DOMContentLoaded', function () {
        const form = document.querySelector('[data-search-autosuggest]');
        if (!form) return;
        const input = form.querySelector('#bbc-search-input');
        const dropdown = form.querySelector('#bbc-search-suggest');
        if (!input || !dropdown) return;
        let timer = null;
        let lastQ = '';

        function render(payload) {
            if (!payload || !payload.ok) { dropdown.hidden = true; return; }
            const parts = [];
            if (payload.section) {
                parts.push('<div class="suggest-section">Section</div>');
                parts.push(
                    '<a class="suggest-item" href="' + payload.section.url + '">' +
                    payload.section.name +
                    ' <span class="suggest-cat">section</span></a>'
                );
            }
            if (payload.topics && payload.topics.length) {
                parts.push('<div class="suggest-section">Topics</div>');
                payload.topics.forEach(function (t) {
                    parts.push(
                        '<a class="suggest-item" href="/search?q=' +
                        encodeURIComponent(t) + '">' + t + '</a>'
                    );
                });
            }
            if (payload.articles && payload.articles.length) {
                parts.push('<div class="suggest-section">Stories</div>');
                payload.articles.forEach(function (a) {
                    parts.push(
                        '<a class="suggest-item" href="' + a.url + '">' +
                        a.headline +
                        '<span class="suggest-cat">' + (a.category || '') + '</span>' +
                        '</a>'
                    );
                });
            }
            if (!parts.length) { dropdown.hidden = true; return; }
            dropdown.innerHTML = parts.join('');
            dropdown.hidden = false;
        }

        input.addEventListener('input', function () {
            const q = (input.value || '').trim();
            if (q === lastQ) return;
            lastQ = q;
            if (timer) clearTimeout(timer);
            if (q.length < 2) { dropdown.hidden = true; return; }
            timer = setTimeout(function () {
                fetch('/api/search/suggest?q=' + encodeURIComponent(q), {
                    credentials: 'same-origin',
                })
                    .then(function (r) { return r.json(); })
                    .then(render)
                    .catch(function () { dropdown.hidden = true; });
            }, 180);
        });

        document.addEventListener('click', function (ev) {
            if (!form.contains(ev.target)) dropdown.hidden = true;
        });
        input.addEventListener('focus', function () {
            if (lastQ.length >= 2) dropdown.hidden = false;
        });
    });
})();

/* ============================================================
 * R5: emoji reactions on articles
 * ============================================================ */
(function () {
    document.addEventListener('click', function (ev) {
        const btn = ev.target.closest('.reaction-btn');
        if (!btn) return;
        ev.preventDefault();
        const slug = btn.getAttribute('data-react-slug');
        const emoji = btn.getAttribute('data-react-emoji');
        if (!slug || !emoji) return;
        const form = new FormData();
        form.append('emoji', emoji);
        form.append('csrf_token', csrfToken());
        fetch('/article/' + slug + '/react', {
            method: 'POST', body: form, credentials: 'same-origin',
        })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (!data || !data.ok) return;
                btn.classList.add('is-active');
                const counter = btn.querySelector('.rxn-count');
                if (counter) counter.textContent = data.reaction_count;
                showToast('Reacted ' + emoji, 'success');
            })
            .catch(function () {});
    });
})();

/* ============================================================
 * R5: comment thread expand/collapse
 * ============================================================ */
(function () {
    document.addEventListener('click', function (ev) {
        const btn = ev.target.closest('[data-thread-toggle]');
        if (!btn) return;
        ev.preventDefault();
        const section = btn.closest('[data-comment-thread]');
        if (!section) return;
        const total = parseInt(btn.getAttribute('data-thread-total') || '0', 10);
        const hidden = section.querySelectorAll('.comment.comment-hidden');
        const expanded = btn.getAttribute('aria-expanded') === 'true';
        if (expanded) {
            section.querySelectorAll('[data-comment-row]').forEach(function (row, i) {
                row.classList.toggle('comment-hidden', i >= 3);
            });
            btn.setAttribute('aria-expanded', 'false');
            btn.textContent = 'Show all ' + total;
        } else {
            hidden.forEach(function (row) { row.classList.remove('comment-hidden'); });
            btn.setAttribute('aria-expanded', 'true');
            btn.textContent = 'Show fewer';
        }
    });
})();

/* ============================================================
 * R5: video chapter markers — jump current player time
 * ============================================================ */
(function () {
    document.addEventListener('click', function (ev) {
        const btn = ev.target.closest('.vc-jump');
        if (!btn) return;
        ev.preventDefault();
        const t = parseInt(btn.getAttribute('data-vc-time') || '0', 10);
        const label = btn.getAttribute('data-vc-label') || '';
        // The mirror does not ship a real <video> element, so we simply
        // surface the jump for tasks via a toast + scroll the body to the
        // sticky player wrap.
        showToast('Jumped to ' + Math.floor(t / 60) + ':' +
                  String(t % 60).padStart(2, '0') +
                  (label ? ' — ' + label : ''), 'info');
        const wrap = document.querySelector('.sticky-video-wrap');
        if (wrap) wrap.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
})();

/* ============================================================
 * R5: live-blog auto-refresh indicator (per-page + per-article)
 * ============================================================ */
(function () {
    function attachRefresher(bar) {
        if (!bar || bar.__bbc_attached) return;
        bar.__bbc_attached = true;
        const slug = bar.getAttribute('data-live-slug') || '';
        const timeEl = bar.querySelector('.lrb-time');
        const toggle = bar.querySelector('.lrb-toggle');
        const liveRegion = document.getElementById('bbc-live-region');
        let interval = null;
        let lastSeen = null;

        function checkOnce() {
            const now = new Date();
            if (timeEl) timeEl.textContent = now.toLocaleTimeString();
            // Only call the API when we have a live-blog slug suffix.
            if (!slug) return;
            // Pick the slug suffix from data-live-slug — bake_extras stores
            // it inside feature_tags but the parent article's slug is the
            // shortest stable identifier.
            const url = '/api/live-blog/' + encodeURIComponent(slug) + '/updates';
            fetch(url, { credentials: 'same-origin' })
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (!data || !data.ok) return;
                    if (data.updates && data.updates.length) {
                        const top = data.updates[0];
                        if (top.slug !== lastSeen) {
                            lastSeen = top.slug;
                            if (liveRegion) {
                                liveRegion.textContent =
                                    'New live update: ' + top.headline;
                            }
                        }
                    }
                })
                .catch(function () {});
        }

        function start() {
            if (interval) return;
            checkOnce();
            interval = setInterval(checkOnce, 30000);
            bar.classList.remove('is-paused');
            if (toggle) {
                toggle.textContent = 'Pause';
                toggle.setAttribute('aria-pressed', 'true');
            }
        }
        function stop() {
            if (interval) { clearInterval(interval); interval = null; }
            bar.classList.add('is-paused');
            if (toggle) {
                toggle.textContent = 'Resume';
                toggle.setAttribute('aria-pressed', 'false');
            }
        }

        if (toggle) {
            toggle.addEventListener('click', function () {
                if (interval) stop(); else start();
            });
        }
        start();
    }

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('[data-live-refresh], [data-live-refresh-global]')
            .forEach(attachRefresher);
    });
})();

/* ============================================================
 * R5: hover-preview on related-link cards (desktop only)
 * ============================================================ */
(function () {
    let popEl = null;
    let timer = null;

    function buildPop() {
        if (popEl) return popEl;
        popEl = document.createElement('div');
        popEl.className = 'hover-preview-pop';
        document.body.appendChild(popEl);
        return popEl;
    }

    function showPreview(card) {
        if (window.innerWidth < 768) return;
        const pop = buildPop();
        const head = card.getAttribute('data-preview-headline') || '';
        const sub  = card.getAttribute('data-preview-subtitle') || '';
        const img  = card.getAttribute('data-preview-image') || '';
        pop.innerHTML =
            (img ? '<img class="hpp-image" src="' + img + '" alt="">' : '') +
            '<div class="hpp-title">' + head + '</div>' +
            '<div class="hpp-summary">' + sub + '</div>';
        const rect = card.getBoundingClientRect();
        pop.style.left = (rect.left + window.scrollX) + 'px';
        pop.style.top  = (rect.top + window.scrollY - 8) + 'px';
        pop.style.width = Math.min(320, rect.width + 40) + 'px';
        pop.classList.add('is-visible');
    }
    function hidePreview() {
        if (popEl) popEl.classList.remove('is-visible');
    }

    document.addEventListener('mouseover', function (ev) {
        const card = ev.target.closest('.hover-preview');
        if (!card) return;
        if (timer) clearTimeout(timer);
        timer = setTimeout(function () { showPreview(card); }, 220);
    });
    document.addEventListener('mouseout', function (ev) {
        const card = ev.target.closest('.hover-preview');
        if (!card) return;
        if (timer) clearTimeout(timer);
        hidePreview();
    });
})();

/* ============================================================
 * R5: srcset stub — attach responsive image hints to card images
 * ============================================================ */
(function () {
    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('.card-image').forEach(function (img) {
            if (img.srcset) return;
            const src = img.getAttribute('src') || '';
            if (!src || src.startsWith('data:')) return;
            // Three pixel-density / width hints. The mirror does not
            // actually serve resized variants — these are advisory only.
            img.setAttribute('sizes',
                '(max-width: 480px) 100vw, (max-width: 960px) 50vw, 33vw');
            img.setAttribute('srcset',
                src + ' 1x, ' + src + ' 2x');
            img.setAttribute('loading', 'lazy');
            img.setAttribute('decoding', 'async');
        });
    });
})();

