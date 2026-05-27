/* R8 — Cmd+K command palette + Vim-style keyboard shortcuts.
 *
 * Bindings:
 *   Cmd/Ctrl+K   open palette
 *   /            focus the top nav search input
 *   g h          go home (chord — 1s window)
 *   g o          go to orders
 *   g w          go to wishlist
 *   g c          go to cart / bag
 *   g d          go to today's deals
 *   ?            show keyboard shortcut help (in palette)
 *   esc          close palette
 *
 * Suggestions are filtered against PALETTE_ITEMS plus live /api/command-palette
 * lookups for products. Activation does location.assign() — no SPA routing.
 */
(function() {
    'use strict';

    var PALETTE_ITEMS = [
        { label: 'Home',                 hint: 'go to homepage',            url: '/',                  keys: 'home index landing' },
        { label: "Today's Deals",        hint: 'browse deals',              url: '/todays-deals',      keys: 'deals discount sale' },
        { label: 'Bestsellers',          hint: 'top selling products',      url: '/bestsellers',       keys: 'best top popular' },
        { label: 'Departments',          hint: 'all departments',           url: '/departments',       keys: 'departments shop all' },
        { label: 'Prime',                hint: 'Prime benefits',            url: '/prime',             keys: 'prime membership' },
        { label: 'Gift Finder',          hint: 'find a gift',               url: '/gift-finder',       keys: 'gift present finder' },
        { label: 'Gift Cards',           hint: 'buy gift cards',            url: '/gift-cards',        keys: 'gift cards giftcard' },
        { label: 'Registry',             hint: 'create a registry',         url: '/registry',          keys: 'wedding baby registry' },
        { label: 'Subscribe & Save',     hint: 'recurring deliveries',      url: '/subscribe-save',    keys: 'subscribe save recurring' },
        { label: 'Sell on Amazon',       hint: 'become a seller',           url: '/sell',              keys: 'sell seller storefront' },
        { label: 'Customer Service',     hint: 'get help',                  url: '/customer-service',  keys: 'help support service' },
        { label: 'Cart',                 hint: 'view bag / cart',           url: '/bag',               keys: 'cart bag checkout basket' },
        { label: 'Account',              hint: 'your account',              url: '/account',           keys: 'account profile me' },
        { label: 'Your Orders',          hint: 'order history',             url: '/account/orders',    keys: 'orders history past' },
        { label: 'Your Wishlist',        hint: 'saved for later',           url: '/wishlist',          keys: 'wishlist saved favorites' },
        { label: 'Addresses',            hint: 'manage shipping addresses', url: '/account/addresses', keys: 'addresses shipping address' },
        { label: 'Payment Methods',      hint: 'manage cards',              url: '/account/payment',   keys: 'payment cards credit debit' },
        // R8 category jumps
        { label: 'Browse Electronics',   hint: 'shop electronics',          url: '/c/electronics',     keys: 'electronics tech gadgets' },
        { label: 'Browse Computers',     hint: 'shop computers',            url: '/c/computers',       keys: 'computers laptops pc' },
        { label: 'Browse Home & Kitchen',hint: 'shop home',                 url: '/c/home',            keys: 'home kitchen' },
        { label: 'Browse Fashion',       hint: 'shop fashion',              url: '/c/fashion',         keys: 'fashion clothing shoes' },
        { label: 'Browse Books',         hint: 'shop books',                url: '/c/books',           keys: 'books reading' },
        { label: 'Browse Beauty',        hint: 'shop beauty',               url: '/c/beauty',          keys: 'beauty skincare makeup' },
        { label: 'Browse Sports',        hint: 'shop sports',               url: '/c/sports',          keys: 'sports fitness' },
        { label: 'Browse Toys',          hint: 'shop toys',                 url: '/c/toys',            keys: 'toys kids children' },
        { label: 'Browse Grocery',       hint: 'shop grocery',              url: '/c/grocery',         keys: 'grocery food fresh whole foods' },
        { label: 'Browse Audible',       hint: 'shop audiobooks',           url: '/c/audible',         keys: 'audible audiobook listen' },
        { label: 'Browse Kindle Store',  hint: 'shop ebooks',               url: '/c/kindle',          keys: 'kindle ebook reader' },
        // R8 ops
        { label: 'Health (/healthz)',         hint: 'service health',          url: '/healthz',                keys: 'health healthcheck liveness probe' },
        { label: 'Metrics (/metrics)',        hint: 'service metrics',         url: '/metrics',                keys: 'metrics prometheus' },
        { label: 'Two-Step Verification',     hint: 'setup MFA / WebAuthn',    url: '/signin/twostep',         keys: 'mfa two factor 2fa webauthn passkey' },
        { label: 'Developer OAuth',           hint: 'create OAuth app',        url: '/developer/oauth',        keys: 'developer oauth api client' },
        { label: 'Business Prime',            hint: 'B2B tier',                url: '/business-prime/tier',    keys: 'business prime b2b tier' },
        { label: 'Accessibility Statement',   hint: 'WCAG AA conformance',     url: '/.well-known/accessibility', keys: 'accessibility wcag a11y' },
    ];

    function $(id) { return document.getElementById(id); }
    function score(item, q) {
        if (!q) return 0;
        q = q.toLowerCase();
        var bag = (item.label + ' ' + item.hint + ' ' + (item.keys || '')).toLowerCase();
        if (bag.indexOf(q) === -1) return -1;
        var pos = item.label.toLowerCase().indexOf(q);
        return pos >= 0 ? 1000 - pos : 500 - bag.indexOf(q);
    }

    function render(items, selectedIdx) {
        var ul = $('cmdk-list');
        if (!ul) return;
        if (!items.length) {
            ul.innerHTML = '<li style="padding:14px;color:#5a6671;text-align:center">No matches. Press <kbd>esc</kbd> to close.</li>';
            return;
        }
        var html = items.map(function(it, i) {
            var bg = i === selectedIdx ? '#eef6fb' : '#fff';
            return '<li role="option" data-url="' + it.url + '" data-i="' + i + '"' +
                ' style="display:flex;justify-content:space-between;align-items:center;padding:9px 12px;border-radius:6px;cursor:pointer;background:' + bg + '">' +
                '<span><strong style="color:#0F1111">' + it.label + '</strong>' +
                '<span style="color:#5a6671;margin-left:8px;font-size:13px">' + it.hint + '</span></span>' +
                '<span style="color:#9aa4ab;font-size:12px">' + it.url + '</span></li>';
        }).join('');
        ul.innerHTML = html;
    }

    function CmdK() {
        var overlay = $('cmdk-overlay');
        var input = $('cmdk-input');
        var list = $('cmdk-list');
        if (!overlay || !input || !list) return null;
        var visible = false, selectedIdx = 0, current = [];

        function open() {
            overlay.hidden = false;
            visible = true;
            input.value = '';
            selectedIdx = 0;
            current = PALETTE_ITEMS.slice(0, 12);
            render(current, selectedIdx);
            setTimeout(function() { input.focus(); }, 10);
            document.body.style.overflow = 'hidden';
        }
        function close() {
            overlay.hidden = true;
            visible = false;
            document.body.style.overflow = '';
        }
        function move(delta) {
            if (!current.length) return;
            selectedIdx = (selectedIdx + delta + current.length) % current.length;
            render(current, selectedIdx);
            var sel = list.querySelector('[data-i="' + selectedIdx + '"]');
            if (sel && sel.scrollIntoView) sel.scrollIntoView({ block: 'nearest' });
        }
        function activate() {
            if (!current.length) return;
            var it = current[selectedIdx];
            if (it && it.url) window.location.assign(it.url);
        }
        function update() {
            var q = input.value.trim();
            if (!q) {
                current = PALETTE_ITEMS.slice(0, 12);
            } else {
                var scored = PALETTE_ITEMS.map(function(it) {
                    return { it: it, s: score(it, q) };
                }).filter(function(x) { return x.s >= 0; })
                  .sort(function(a, b) { return b.s - a.s; })
                  .slice(0, 10)
                  .map(function(x) { return x.it; });
                current = scored;
                if (q.length >= 2) {
                    fetch('/api/command-palette?q=' + encodeURIComponent(q))
                        .then(function(r) { return r.ok ? r.json() : null; })
                        .then(function(j) {
                            if (!j || !j.items || !visible) return;
                            if (input.value.trim() !== q) return;
                            j.items.slice(0, 5).forEach(function(it) { current.push(it); });
                            render(current, selectedIdx);
                        }).catch(function() {});
                }
            }
            selectedIdx = 0;
            render(current, selectedIdx);
        }

        overlay.addEventListener('click', function(e) {
            if (e.target === overlay) close();
        });
        list.addEventListener('click', function(e) {
            var li = e.target.closest('li[data-url]');
            if (li) window.location.assign(li.getAttribute('data-url'));
        });
        list.addEventListener('mouseover', function(e) {
            var li = e.target.closest('li[data-i]');
            if (li) {
                selectedIdx = parseInt(li.getAttribute('data-i'), 10) || 0;
                render(current, selectedIdx);
            }
        });
        input.addEventListener('input', update);
        input.addEventListener('keydown', function(e) {
            if (e.key === 'ArrowDown') { e.preventDefault(); move(1); }
            else if (e.key === 'ArrowUp') { e.preventDefault(); move(-1); }
            else if (e.key === 'Enter') { e.preventDefault(); activate(); }
            else if (e.key === 'Escape') { e.preventDefault(); close(); }
        });

        return { open: open, close: close, isVisible: function() { return visible; } };
    }

    var chord = { active: false, key: null, ts: 0 };

    function chordHandler(e) {
        if (chord.active && (Date.now() - chord.ts) < 1200 && chord.key === 'g') {
            chord.active = false;
            var t = (e.key || '').toLowerCase();
            var map = { h: '/', o: '/account/orders', w: '/wishlist',
                        c: '/bag', d: '/todays-deals', a: '/account', p: '/prime' };
            if (map[t]) {
                e.preventDefault();
                window.location.assign(map[t]);
                return true;
            }
            return false;
        }
        if ((e.key || '').toLowerCase() === 'g') {
            // Don't enter chord mode when typing in a field.
            var tag = (e.target && e.target.tagName) || '';
            if (tag !== 'INPUT' && tag !== 'TEXTAREA' && tag !== 'SELECT' &&
                !(e.target && e.target.isContentEditable)) {
                chord.active = true;
                chord.key = 'g';
                chord.ts = Date.now();
                setTimeout(function() {
                    if ((Date.now() - chord.ts) >= 1100) chord.active = false;
                }, 1200);
                return true;
            }
        }
        return false;
    }

    document.addEventListener('DOMContentLoaded', function() {
        var palette = CmdK();
        if (!palette) return;
        document.addEventListener('keydown', function(e) {
            var tag = (e.target && e.target.tagName) || '';
            var inField = (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' ||
                           (e.target && e.target.isContentEditable));
            // Cmd/Ctrl+K — open palette from anywhere.
            if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
                e.preventDefault();
                palette.open();
                return;
            }
            if (palette.isVisible()) return;
            if (inField) return;
            // '/' — focus nav search.
            if (e.key === '/') {
                var search = document.getElementById('nav-search-input');
                if (search) { e.preventDefault(); search.focus(); search.select(); }
                return;
            }
            // '?' — open palette in help mode.
            if (e.key === '?') {
                e.preventDefault();
                palette.open();
                var input = document.getElementById('cmdk-input');
                if (input) { input.value = ''; input.dispatchEvent(new Event('input')); }
                return;
            }
            chordHandler(e);
        });
    });
})();
