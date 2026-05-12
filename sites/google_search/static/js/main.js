// Google Search mirror — main client-side helpers
// Includes: PAA toggle, bookmark toggle, app launcher, flash dismiss

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

    // ---------- People Also Ask accordion ----------
    document.querySelectorAll('.paa-item').forEach(item => {
        item.addEventListener('click', () => {
            item.classList.toggle('open');
        });
    });

    // ---------- App launcher ----------
    const appBtn = document.querySelector('[data-apps-toggle]');
    const appDrop = document.querySelector('.apps-dropdown');
    if (appBtn && appDrop) {
        appBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            appDrop.classList.toggle('open');
        });
        document.addEventListener('click', (e) => {
            if (!appDrop.contains(e.target)) appDrop.classList.remove('open');
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
    });
})();
