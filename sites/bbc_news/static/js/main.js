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
