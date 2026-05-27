// Booking.com mirror - main.js
// Handles: save/wishlist toggle, add to bag, remove cart item, notifications

function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

function showNotification(message, type) {
    type = type || 'success';
    let container = document.getElementById('js-notifications');
    if (!container) {
        container = document.createElement('div');
        container.id = 'js-notifications';
        container.style.cssText = 'position:fixed;top:20px;right:20px;z-index:10000;display:flex;flex-direction:column;gap:10px;';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    const bg = type === 'error' ? '#e31c5f' : (type === 'info' ? '#006ce4' : '#008009');
    toast.style.cssText = 'background:' + bg + ';color:#fff;padding:12px 20px;border-radius:4px;box-shadow:0 4px 12px rgba(0,0,0,0.15);font-size:14px;min-width:240px;max-width:360px;opacity:0;transform:translateX(20px);transition:all 0.25s ease;';
    toast.textContent = message;
    container.appendChild(toast);
    // Animate in
    requestAnimationFrame(function () {
        toast.style.opacity = '1';
        toast.style.transform = 'translateX(0)';
    });
    // Auto-dismiss
    setTimeout(function () {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(20px)';
        setTimeout(function () { toast.remove(); }, 300);
    }, 3200);
}

function updateBagCount(count) {
    const btns = document.querySelectorAll('.header-btn');
    btns.forEach(function (btn) {
        if (btn.textContent.trim().startsWith('Bag')) {
            btn.textContent = count > 0 ? 'Bag (' + count + ')' : 'Bag';
        }
    });
}

function toggleSave(btn, propertyId) {
    fetch('/api/saved/toggle', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ property_id: propertyId })
    })
        .then(function (r) {
            if (r.status === 401 || r.redirected) {
                showNotification('Please sign in to save properties.', 'info');
                setTimeout(function () { window.location.href = '/login'; }, 800);
                return null;
            }
            return r.json();
        })
        .then(function (data) {
            if (!data) return;
            if (data.success) {
                if (data.action === 'added') {
                    btn.classList.add('saved');
                    showNotification('Saved to your list.');
                } else {
                    btn.classList.remove('saved');
                    showNotification('Removed from saved.', 'info');
                }
            } else {
                showNotification('Could not update your saved list.', 'error');
            }
        })
        .catch(function () {
            showNotification('Network error. Please try again.', 'error');
        });
}

function addToBag(propertyId, roomType) {
    const body = { property_id: propertyId };
    if (roomType) body.room_type = roomType;
    // Pull optional check-in/check-out from widget inputs if present
    const ci = document.querySelector('input[name="check_in"]');
    const co = document.querySelector('input[name="check_out"]');
    const adults = document.querySelector('select[name="adults"]');
    const rooms = document.querySelector('select[name="rooms"]');
    if (ci && ci.value) body.check_in = ci.value;
    if (co && co.value) body.check_out = co.value;
    if (adults && adults.value) body.adults = parseInt(adults.value, 10);
    if (rooms && rooms.value) body.rooms = parseInt(rooms.value, 10);

    fetch('/api/cart/add', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify(body)
    })
        .then(function (r) {
            if (r.status === 401 || r.redirected) {
                showNotification('Please sign in to book.', 'info');
                setTimeout(function () { window.location.href = '/login'; }, 800);
                return null;
            }
            return r.json();
        })
        .then(function (data) {
            if (!data) return;
            if (data.success) {
                updateBagCount(data.cart_count);
                showNotification(data.message || 'Added to your bag.');
            } else {
                showNotification(data.message || 'Could not add to bag.', 'error');
            }
        })
        .catch(function () {
            showNotification('Network error. Please try again.', 'error');
        });
}

function removeCartItem(itemId) {
    if (!confirm('Remove this item from your bag?')) return;
    fetch('/api/cart/remove', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ item_id: itemId })
    })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data && data.success) {
                updateBagCount(data.cart_count);
                // Reload to refresh totals
                window.location.reload();
            } else {
                showNotification('Could not remove item.', 'error');
            }
        })
        .catch(function () {
            showNotification('Network error. Please try again.', 'error');
        });
}

function updateCartItem(itemId, field, value) {
    const body = { item_id: itemId };
    body[field] = value;
    fetch('/api/cart/update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify(body)
    })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data && data.success) {
                showNotification('Updated.');
                window.location.reload();
            }
        })
        .catch(function () {
            showNotification('Network error. Please try again.', 'error');
        });
}

// Auto-dismiss flash messages
document.addEventListener('DOMContentLoaded', function () {
    setTimeout(function () {
        const flashes = document.querySelectorAll('.flash');
        flashes.forEach(function (f) {
            f.style.transition = 'opacity 0.4s';
            f.style.opacity = '0';
            setTimeout(function () { f.remove(); }, 500);
        });
    }, 5000);

    // Scroll reveal for elements with .reveal
    if ('IntersectionObserver' in window) {
        const io = new IntersectionObserver(function (entries) {
            entries.forEach(function (e) {
                if (e.isIntersecting) {
                    e.target.style.opacity = '1';
                    e.target.style.transform = 'translateY(0)';
                }
            });
        }, { threshold: 0.08 });
        document.querySelectorAll('.reveal').forEach(function (el) {
            el.style.opacity = '0';
            el.style.transform = 'translateY(16px)';
            el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            io.observe(el);
        });
    }

    // ===== R8 keyboard shortcuts + command palette + amenity tooltips =====
    bookingR8.init();
});


// ---------------------------------------------------------------------------
// R8 — keyboard shortcuts ('/', Cmd+K, '?'), command palette, amenity glossary
// tooltips, currency live-convert hint. All client-side; backed by JSON
// endpoints /api/palette/suggest and /api/amenity-glossary.
// ---------------------------------------------------------------------------
const bookingR8 = {
    paletteOpen: false,
    shortcutsOpen: false,
    glossary: null,
    init: function () {
        this._markSearchInput();
        this._buildPalette();
        this._buildShortcutsOverlay();
        this._installKeyHandlers();
        this._installAmenityTooltips();
    },
    _markSearchInput: function () {
        // Tag the first search-style input on the page so '/' can target it.
        const sel = 'input[name="ss"], input[name="destination"], input[name="q"]';
        const first = document.querySelector(sel);
        if (first && !first.id) {
            first.id = 'r8-search-input';
        }
    },
    _buildPalette: function () {
        if (document.getElementById('r8-palette')) return;
        const root = document.createElement('div');
        root.id = 'r8-palette';
        root.style.cssText = 'position:fixed;inset:0;background:rgba(0,30,80,0.45);z-index:11000;display:none;align-items:flex-start;justify-content:center;padding-top:80px;';
        root.innerHTML = ''
            + '<div id="r8-palette-box" style="background:#fff;width:560px;max-width:92vw;border-radius:8px;box-shadow:0 12px 36px rgba(0,0,0,0.2);overflow:hidden;">'
            +   '<div style="padding:10px 14px;border-bottom:1px solid #eee;display:flex;align-items:center;gap:10px;">'
            +     '<strong style="color:#003580;">Jump to</strong>'
            +     '<span style="color:#888;font-size:12px;">Cmd+K · Ctrl+K · Esc to close</span>'
            +   '</div>'
            +   '<input id="r8-palette-input" type="text" placeholder="Search cities, properties, saved, trip tools..." style="width:100%;padding:14px;border:0;font-size:16px;outline:none;">'
            +   '<div id="r8-palette-results" style="max-height:340px;overflow:auto;border-top:1px solid #f1f1f1;"></div>'
            + '</div>';
        document.body.appendChild(root);
        root.addEventListener('click', function (e) {
            if (e.target === root) bookingR8._closePalette();
        });
        const input = root.querySelector('#r8-palette-input');
        let lastFetch = 0;
        input.addEventListener('input', function () {
            const ts = ++lastFetch;
            const q = input.value;
            fetch('/api/palette/suggest?q=' + encodeURIComponent(q))
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (ts !== lastFetch) return;
                    bookingR8._renderPalette(data);
                });
        });
        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') {
                const first = document.querySelector('#r8-palette-results a');
                if (first) { window.location.href = first.getAttribute('href'); }
            }
        });
    },
    _renderPalette: function (data) {
        const wrap = document.getElementById('r8-palette-results');
        if (!wrap) return;
        if (!data.sections || data.sections.length === 0) {
            wrap.innerHTML = '<div style="padding:18px;color:#888;">No matches. Try a city, property name, or "trip".</div>';
            return;
        }
        let html = '';
        data.sections.forEach(function (sec) {
            html += '<div style="padding:6px 14px;color:#666;font-size:12px;text-transform:uppercase;letter-spacing:0.5px;">' + sec.name + '</div>';
            sec.items.forEach(function (it) {
                html += '<a href="' + it.href + '" style="display:flex;justify-content:space-between;padding:10px 14px;text-decoration:none;color:#003580;border-top:1px solid #f5f5f5;">'
                     +   '<span>' + it.label + '</span>'
                     +   '<span style="color:#999;font-size:11px;">' + it.category + '</span>'
                     + '</a>';
            });
        });
        wrap.innerHTML = html;
    },
    _openPalette: function () {
        const root = document.getElementById('r8-palette');
        if (!root) return;
        root.style.display = 'flex';
        this.paletteOpen = true;
        const input = root.querySelector('#r8-palette-input');
        input.value = '';
        input.focus();
        // Show default jumps when first opened.
        fetch('/api/palette/suggest?q=')
            .then(function (r) { return r.json(); })
            .then(function (d) { bookingR8._renderPalette(d); });
    },
    _closePalette: function () {
        const root = document.getElementById('r8-palette');
        if (!root) return;
        root.style.display = 'none';
        this.paletteOpen = false;
    },
    _buildShortcutsOverlay: function () {
        if (document.getElementById('r8-shortcuts')) return;
        const root = document.createElement('div');
        root.id = 'r8-shortcuts';
        root.style.cssText = 'position:fixed;inset:0;background:rgba(0,30,80,0.45);z-index:11050;display:none;align-items:center;justify-content:center;';
        root.innerHTML = ''
            + '<div style="background:#fff;width:440px;max-width:92vw;border-radius:8px;padding:20px 24px;box-shadow:0 12px 36px rgba(0,0,0,0.2);">'
            +   '<h3 style="margin:0 0 12px;color:#003580;">Keyboard shortcuts</h3>'
            +   '<ul style="list-style:none;padding:0;margin:0;font-size:14px;color:#333;">'
            +     '<li style="padding:6px 0;border-bottom:1px solid #f3f3f3;"><kbd>/</kbd> &nbsp; Focus search</li>'
            +     '<li style="padding:6px 0;border-bottom:1px solid #f3f3f3;"><kbd>Cmd</kbd>+<kbd>K</kbd> &nbsp; Open command palette</li>'
            +     '<li style="padding:6px 0;border-bottom:1px solid #f3f3f3;"><kbd>?</kbd> &nbsp; Toggle this overlay</li>'
            +     '<li style="padding:6px 0;border-bottom:1px solid #f3f3f3;"><kbd>g</kbd> then <kbd>s</kbd> &nbsp; Go to Saved</li>'
            +     '<li style="padding:6px 0;border-bottom:1px solid #f3f3f3;"><kbd>g</kbd> then <kbd>b</kbd> &nbsp; Go to Bag</li>'
            +     '<li style="padding:6px 0;border-bottom:1px solid #f3f3f3;"><kbd>g</kbd> then <kbd>h</kbd> &nbsp; Go home</li>'
            +     '<li style="padding:6px 0;"><kbd>g</kbd> then <kbd>t</kbd> &nbsp; Trip budget split</li>'
            +   '</ul>'
            +   '<p style="margin-top:14px;font-size:12px;color:#888;">Press Esc to close. Full list at <a href="/keyboard-shortcuts">/keyboard-shortcuts</a>.</p>'
            + '</div>';
        document.body.appendChild(root);
        root.addEventListener('click', function (e) {
            if (e.target === root) bookingR8._closeShortcuts();
        });
    },
    _openShortcuts: function () {
        const root = document.getElementById('r8-shortcuts');
        if (!root) return;
        root.style.display = 'flex';
        this.shortcutsOpen = true;
    },
    _closeShortcuts: function () {
        const root = document.getElementById('r8-shortcuts');
        if (!root) return;
        root.style.display = 'none';
        this.shortcutsOpen = false;
    },
    _installKeyHandlers: function () {
        let gPending = null;
        document.addEventListener('keydown', function (e) {
            const tag = (e.target && e.target.tagName) || '';
            const inField = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT'
                || (e.target && e.target.isContentEditable);
            // Cmd+K / Ctrl+K — open palette anywhere, including fields.
            if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
                e.preventDefault();
                bookingR8._openPalette();
                return;
            }
            if (e.key === 'Escape') {
                if (bookingR8.paletteOpen) bookingR8._closePalette();
                if (bookingR8.shortcutsOpen) bookingR8._closeShortcuts();
                return;
            }
            // Single-key shortcuts only outside form fields.
            if (inField) return;
            if (e.key === '/') {
                const input = document.getElementById('r8-search-input');
                if (input) {
                    e.preventDefault();
                    input.focus();
                    input.select && input.select();
                }
                return;
            }
            if (e.key === '?') {
                e.preventDefault();
                if (bookingR8.shortcutsOpen) bookingR8._closeShortcuts();
                else bookingR8._openShortcuts();
                return;
            }
            // 'g' chord shortcuts.
            if (e.key === 'g') {
                gPending = setTimeout(function () { gPending = null; }, 800);
                return;
            }
            if (gPending) {
                clearTimeout(gPending); gPending = null;
                if (e.key === 's') { window.location.href = '/saved'; }
                else if (e.key === 'b') { window.location.href = '/bag'; }
                else if (e.key === 'h') { window.location.href = '/'; }
                else if (e.key === 't') { window.location.href = '/trip/split'; }
            }
        });
    },
    _installAmenityTooltips: function () {
        // Decorate any element with data-amenity="<term>" on hover with the
        // glossary definition. Lazy-loads /api/amenity-glossary once.
        document.body.addEventListener('mouseover', function (e) {
            const el = e.target.closest('[data-amenity]');
            if (!el || el._r8Tipped) return;
            const term = el.getAttribute('data-amenity');
            bookingR8._ensureGlossary(function (g) {
                const def = g[term];
                if (def) {
                    el.title = term + ' — ' + def;
                    el._r8Tipped = true;
                }
            });
        });
    },
    _ensureGlossary: function (cb) {
        if (this.glossary) { cb(this.glossary); return; }
        fetch('/api/amenity-glossary')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                bookingR8.glossary = data;
                cb(data);
            })
            .catch(function () { cb({}); });
    },
};
