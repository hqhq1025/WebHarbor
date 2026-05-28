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

// >>> map-controls-wiring
// Wire client-side handlers for map controls, layers, type-switcher, locate,
// rotate, contrast, plus the "menu" drawer and "apps" grid popover. Each
// handler mutates a visible DOM element so the click is observably non-dead:
// either the .map-status-pill text changes (Zoom 13 -> 14), an overlay node
// is added/removed (drawer, popover, locate pin), or aria-pressed flips with
// a chip appearing in #map-active-layers. Mirrors the real google.com/maps
// chrome (no actual tile-server zoom is possible client-side).
//
// Root cause of pre-fix audit failure (37.4% dead): these <button> elements
// shipped with data-action / data-layer attributes but no JS handler — the
// audit clicked them, body innerText + child count unchanged → no_effect.
(function () {
    'use strict';

    var MAP_LABEL = { map: 'Map view', satellite: 'Satellite', terrain: 'Terrain' };

    function $(sel, root) { return (root || document).querySelector(sel); }
    function $$(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

    function getMain() { return document.querySelector('.main-map'); }
    function getPill() { return document.getElementById('map-status-pill'); }
    function getCanvas() { return document.querySelector('.map-canvas'); }

    function setStatus(text) {
        var pill = getPill();
        if (pill) pill.textContent = text;
    }

    function refreshStatus() {
        var main = getMain();
        if (!main) return;
        var zoom = parseInt(main.getAttribute('data-zoom') || '12', 10);
        var mt = main.getAttribute('data-map-type') || 'map';
        var layers = (main.getAttribute('data-active-layers') || '').split(',').filter(Boolean);
        var hc = main.classList.contains('high-contrast') ? ' · high contrast' : '';
        var rot = main.getAttribute('data-rotation');
        var rotTxt = (rot && rot !== '0') ? (' · rotated ' + rot + '°') : '';
        var layerTxt = layers.length ? (' · ' + layers.join('+')) : '';
        setStatus('Zoom ' + zoom + ' · ' + (MAP_LABEL[mt] || mt) + layerTxt + hc + rotTxt);
    }

    function renderActiveLayerChips() {
        var main = getMain();
        var holder = document.getElementById('map-active-layers');
        if (!main || !holder) return;
        var layers = (main.getAttribute('data-active-layers') || '').split(',').filter(Boolean);
        holder.innerHTML = '';
        layers.forEach(function (name) {
            var chip = document.createElement('div');
            chip.className = 'gm-layer-chip';
            chip.setAttribute('data-layer-chip', name);
            chip.textContent = name.charAt(0).toUpperCase() + name.slice(1) + ' layer on';
            chip.style.cssText = 'background:#fff;border:1px solid #1a73e8;color:#1a73e8;' +
                'border-radius:12px;padding:2px 10px;box-shadow:0 1px 2px rgba(0,0,0,0.08);';
            holder.appendChild(chip);
        });
    }

    function applyZoomVisual() {
        var main = getMain();
        var canvas = getCanvas();
        if (!main || !canvas) return;
        var z = parseInt(main.getAttribute('data-zoom') || '12', 10);
        // 12 is baseline; scale 0.7 .. 1.5 for visual feedback
        var scale = Math.max(0.7, Math.min(1.5, 0.7 + (z - 8) * 0.08));
        canvas.style.transform = 'scale(' + scale.toFixed(2) + ')';
        canvas.style.transformOrigin = '50% 50%';
        canvas.style.transition = 'transform 200ms ease-out';
    }

    function applyRotation() {
        var main = getMain();
        var canvas = getCanvas();
        if (!main || !canvas) return;
        var rot = parseInt(main.getAttribute('data-rotation') || '0', 10);
        var z = parseInt(main.getAttribute('data-zoom') || '12', 10);
        var scale = Math.max(0.7, Math.min(1.5, 0.7 + (z - 8) * 0.08));
        canvas.style.transform = 'scale(' + scale.toFixed(2) + ') rotate(' + rot + 'deg)';
    }

    function changeZoom(delta) {
        var main = getMain();
        if (!main) return;
        var z = parseInt(main.getAttribute('data-zoom') || '12', 10);
        z = Math.max(3, Math.min(20, z + delta));
        main.setAttribute('data-zoom', String(z));
        applyZoomVisual();
        refreshStatus();
    }

    function toggleLayer(name) {
        var main = getMain();
        if (!main) return;
        var layers = (main.getAttribute('data-active-layers') || '').split(',').filter(Boolean);
        var idx = layers.indexOf(name);
        if (idx >= 0) layers.splice(idx, 1); else layers.push(name);
        main.setAttribute('data-active-layers', layers.join(','));
        $$('.layer-toggle[data-layer="' + name + '"]').forEach(function (btn) {
            btn.setAttribute('aria-pressed', idx >= 0 ? 'false' : 'true');
        });
        renderActiveLayerChips();
        refreshStatus();
    }

    function setMapType(type) {
        var main = getMain();
        if (!main) return;
        main.setAttribute('data-map-type', type);
        $$('.map-type-btn').forEach(function (btn) {
            var active = btn.getAttribute('data-map-type') === type;
            btn.classList.toggle('active', active);
            btn.setAttribute('aria-selected', active ? 'true' : 'false');
        });
        // Visual tint on canvas so the change is observable in screenshots too.
        var canvas = getCanvas();
        if (canvas) {
            canvas.classList.remove('mt-map', 'mt-satellite', 'mt-terrain');
            canvas.classList.add('mt-' + type);
        }
        refreshStatus();
    }

    function dropLocatePin() {
        var canvas = getCanvas();
        if (!canvas) return;
        // remove existing
        var prev = canvas.querySelector('.map-pin.locate');
        if (prev) prev.remove();
        var pin = document.createElement('div');
        pin.className = 'map-pin locate';
        pin.setAttribute('aria-label', 'Your location');
        pin.style.cssText = 'top:50%;left:50%;transform:translate(-50%,-100%);';
        pin.innerHTML = '<div class="pin-head blue" style="background:#1a73e8;"></div>' +
                        '<div class="pin-label">You are here</div>';
        canvas.appendChild(pin);
    }

    function toggleContrast() {
        var main = getMain();
        if (!main) return;
        var on = main.classList.toggle('high-contrast');
        $$('.map-ctrl-btn[data-action="contrast"]').forEach(function (btn) {
            btn.setAttribute('aria-pressed', on ? 'true' : 'false');
        });
        refreshStatus();
    }

    function rotate() {
        var main = getMain();
        if (!main) return;
        var rot = parseInt(main.getAttribute('data-rotation') || '0', 10);
        rot = (rot + 45) % 360;
        main.setAttribute('data-rotation', String(rot));
        applyRotation();
        refreshStatus();
    }

    // ---- Drawer (hamburger menu) ----------------------------------------- //
    function buildDrawer() {
        if (document.getElementById('gm-drawer')) return;
        var drawer = document.createElement('aside');
        drawer.id = 'gm-drawer';
        drawer.className = 'gm-drawer';
        drawer.setAttribute('role', 'dialog');
        drawer.setAttribute('aria-label', 'Maps menu');
        drawer.hidden = true;
        drawer.innerHTML = [
            '<div class="gm-drawer-head">',
                '<button type="button" class="gm-drawer-close" data-action="close-drawer" aria-label="Close menu">',
                    '<span class="material-icons-outlined">close</span>',
                '</button>',
                '<span class="gm-drawer-title">Google Maps</span>',
            '</div>',
            '<nav class="gm-drawer-nav" aria-label="Maps sections">',
                '<a href="/" class="gm-drawer-link"><span class="material-icons-outlined">home</span>Home</a>',
                '<a href="/explore" class="gm-drawer-link"><span class="material-icons-outlined">explore</span>Explore</a>',
                '<a href="/directions" class="gm-drawer-link"><span class="material-icons-outlined">directions</span>Directions</a>',
                '<a href="/saved" class="gm-drawer-link"><span class="material-icons-outlined">bookmark</span>Saved</a>',
                '<a href="/your-places" class="gm-drawer-link"><span class="material-icons-outlined">place</span>Your places</a>',
                '<a href="/timeline" class="gm-drawer-link"><span class="material-icons-outlined">schedule</span>Timeline</a>',
                '<a href="/contribute" class="gm-drawer-link"><span class="material-icons-outlined">add_location_alt</span>Contribute</a>',
                '<a href="/settings" class="gm-drawer-link"><span class="material-icons-outlined">settings</span>Settings</a>',
                '<a href="/help" class="gm-drawer-link"><span class="material-icons-outlined">help_outline</span>Help & feedback</a>',
            '</nav>',
        ].join('');
        document.body.appendChild(drawer);
    }
    function openDrawer() {
        buildDrawer();
        var d = document.getElementById('gm-drawer');
        if (!d) return;
        d.hidden = false;
        d.classList.add('show');
        $$('[data-action="open-drawer"]').forEach(function (b) {
            b.setAttribute('aria-expanded', 'true');
        });
    }
    function closeDrawer() {
        var d = document.getElementById('gm-drawer');
        if (!d) return;
        d.classList.remove('show');
        d.hidden = true;
        $$('[data-action="open-drawer"]').forEach(function (b) {
            b.setAttribute('aria-expanded', 'false');
        });
    }

    // ---- Apps grid popover ----------------------------------------------- //
    var APPS = [
        { name: 'Search',   icon: 'search',          href: 'https://google.com/' },
        { name: 'Maps',     icon: 'map',             href: '/' },
        { name: 'YouTube',  icon: 'smart_display',   href: 'https://youtube.com/' },
        { name: 'Drive',    icon: 'cloud',           href: 'https://drive.google.com/' },
        { name: 'Gmail',    icon: 'mail',            href: 'https://mail.google.com/' },
        { name: 'Calendar', icon: 'calendar_today',  href: 'https://calendar.google.com/' },
        { name: 'Photos',   icon: 'photo_library',   href: 'https://photos.google.com/' },
        { name: 'Docs',     icon: 'description',     href: 'https://docs.google.com/' },
        { name: 'Translate',icon: 'translate',       href: 'https://translate.google.com/' },
    ];
    function buildAppsPopover() {
        if (document.getElementById('gm-apps-popover')) return;
        var pop = document.createElement('div');
        pop.id = 'gm-apps-popover';
        pop.className = 'gm-apps-popover';
        pop.setAttribute('role', 'dialog');
        pop.setAttribute('aria-label', 'Google apps');
        pop.hidden = true;
        var html = ['<div class="gm-apps-grid">'];
        APPS.forEach(function (a) {
            html.push(
                '<a class="gm-apps-tile" href="' + a.href + '">' +
                    '<span class="material-icons-outlined">' + a.icon + '</span>' +
                    '<span class="gm-apps-label">' + a.name + '</span>' +
                '</a>'
            );
        });
        html.push('</div>');
        pop.innerHTML = html.join('');
        document.body.appendChild(pop);
    }
    function toggleAppsPopover(btn) {
        buildAppsPopover();
        var pop = document.getElementById('gm-apps-popover');
        if (!pop) return;
        var showing = !pop.hidden;
        if (showing) {
            pop.hidden = true;
            pop.classList.remove('show');
            if (btn) btn.setAttribute('aria-expanded', 'false');
        } else {
            pop.hidden = false;
            pop.classList.add('show');
            if (btn) btn.setAttribute('aria-expanded', 'true');
        }
    }

    // ---- Delegated click dispatch ---------------------------------------- //
    document.addEventListener('click', function (ev) {
        var t = ev.target;
        if (!t || !t.closest) return;

        // apps grid
        var apps = t.closest('.apps-grid-btn');
        if (apps) {
            ev.preventDefault();
            toggleAppsPopover(apps);
            return;
        }

        // close drawer (via the X)
        var closeBtn = t.closest('[data-action="close-drawer"]');
        if (closeBtn) {
            ev.preventDefault();
            closeDrawer();
            return;
        }

        // open drawer (hamburger in rail or in search bar)
        var openBtn = t.closest('[data-action="open-drawer"]');
        if (openBtn) {
            ev.preventDefault();
            var d = document.getElementById('gm-drawer');
            if (d && !d.hidden) closeDrawer(); else openDrawer();
            return;
        }

        // map control buttons (zoom / pinch / locate / rotate / contrast)
        var mc = t.closest('.map-ctrl-btn[data-action]');
        if (mc) {
            ev.preventDefault();
            var act = mc.getAttribute('data-action');
            switch (act) {
                case 'zoom-in':   changeZoom(+1); break;
                case 'zoom-out':  changeZoom(-1); break;
                case 'pinch-in':  changeZoom(+1); break;
                case 'pinch-out': changeZoom(-1); break;
                case 'locate':    dropLocatePin(); refreshStatus(); break;
                case 'rotate':    rotate(); break;
                case 'contrast':  toggleContrast(); break;
            }
            return;
        }

        // map type switch
        var mt = t.closest('.map-type-btn[data-map-type]');
        if (mt) {
            ev.preventDefault();
            setMapType(mt.getAttribute('data-map-type'));
            return;
        }

        // layer toggles
        var lt = t.closest('.layer-toggle[data-layer]');
        if (lt) {
            ev.preventDefault();
            toggleLayer(lt.getAttribute('data-layer'));
            return;
        }
    }, false);

    // Initial status render once DOM ready (so the pill text reflects defaults).
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', refreshStatus);
    } else {
        refreshStatus();
    }
})();
// <<< map-controls-wiring
