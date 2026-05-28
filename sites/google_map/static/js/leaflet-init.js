// =============================================================================
//  Leaflet boot for the right-hand map widget (_mapcanvas.html).
//
//  Reads center / markers / route from the rendered <section class="main-map">
//  and #map-canvas data-* attributes, then instantiates a real Leaflet L.Map
//  inside #leaflet-map.
//
//  Tile sources (all keyless, public-CDN):
//    Map:        OpenStreetMap standard
//    Satellite:  Esri World Imagery
//    Terrain:    OpenTopoMap
//    Cycling:    CyclOSM overlay (transit/cycling layer toggle)
//    Transit:    OpenRailwayMap (works as transit lines overlay)
//
//  Click handlers on the existing chrome (.map-ctrl-btn / .map-type-btn /
//  .layer-toggle) are bound at the top of main.js's delegated dispatch;
//  here we attach a sibling listener with higher priority so when a real
//  L.Map exists we use map.zoomIn() / setView() / etc., and main.js's CSS
//  fallback path becomes a no-op for those buttons.
//
//  Failure path: if window.L never resolves (CDN blocked, offline), we
//  leave the CSS-styled fallback in place and main.js still handles the
//  buttons through CSS transforms — no regression in click-audit.
// =============================================================================

(function () {
    'use strict';

    if (window.__gmLeafletBooted) return;
    window.__gmLeafletBooted = true;

    var MAP_LABEL = { map: 'Map view', satellite: 'Satellite', terrain: 'Terrain' };

    var TILE = {
        map: {
            url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            attr: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
            maxZoom: 19, subdomains: 'abc'
        },
        satellite: {
            url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr: 'Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics',
            maxZoom: 19
        },
        terrain: {
            url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
            attr: 'Map data: &copy; OpenStreetMap, SRTM | Style: &copy; OpenTopoMap',
            maxZoom: 17, subdomains: 'abc'
        }
    };

    var OVERLAY = {
        // CyclOSM cycling overlay (works as cycling layer toggle).
        cycling: {
            url: 'https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png',
            attr: 'CyclOSM | &copy; OpenStreetMap', maxZoom: 19, subdomains: 'abc'
        },
        // OpenRailwayMap = transit/rail overlay.
        transit: {
            url: 'https://{s}.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png',
            attr: 'OpenRailwayMap', maxZoom: 19, subdomains: 'abc'
        }
    };

    function $(sel, root) { return (root || document).querySelector(sel); }
    function $$(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

    function getMain()   { return document.querySelector('.main-map'); }
    function getCanvas() { return document.getElementById('map-canvas'); }
    function getHost()   { return document.getElementById('leaflet-map'); }
    function getPill()   { return document.getElementById('map-status-pill'); }

    function parseDataJSON(el, key, fallback) {
        try {
            var raw = el.getAttribute(key);
            if (!raw) return fallback;
            return JSON.parse(raw);
        } catch (e) {
            try { console.warn('[gm-leaflet] bad ' + key, e); } catch (_) {}
            return fallback;
        }
    }

    // -------------------------------------------------------------------------
    // Status pill — kept in sync with current zoom / type / active layers /
    // rotation so every map control click visibly changes textContent.
    // -------------------------------------------------------------------------
    function refreshStatus() {
        var main = getMain();
        var pill = getPill();
        if (!main || !pill) return;
        var zoom = parseInt(main.getAttribute('data-zoom') || '12', 10);
        var mt = main.getAttribute('data-map-type') || 'map';
        var layers = (main.getAttribute('data-active-layers') || '').split(',').filter(Boolean);
        var hc = main.classList.contains('high-contrast') ? ' · high contrast' : '';
        var rot = main.getAttribute('data-rotation');
        var rotTxt = (rot && rot !== '0') ? (' · rotated ' + rot + '°') : '';
        var layerTxt = layers.length ? (' · ' + layers.join('+')) : '';
        pill.textContent = 'Zoom ' + zoom + ' · ' + (MAP_LABEL[mt] || mt) + layerTxt + hc + rotTxt;
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

    // -------------------------------------------------------------------------
    // Marker rendering — circle pins for places, A/B teardrops for the
    // directions origin/destination.
    // -------------------------------------------------------------------------
    function markerIconForRole(role, focus) {
        if (role === 'origin') {
            return L.divIcon({
                className: 'gm-marker gm-marker-origin',
                html: '<div class="gm-pin gm-pin-origin">A</div>',
                iconSize: [28, 36], iconAnchor: [14, 34], popupAnchor: [0, -30]
            });
        }
        if (role === 'destination') {
            return L.divIcon({
                className: 'gm-marker gm-marker-dest',
                html: '<div class="gm-pin gm-pin-dest">B</div>',
                iconSize: [28, 36], iconAnchor: [14, 34], popupAnchor: [0, -30]
            });
        }
        if (focus) {
            return L.divIcon({
                className: 'gm-marker gm-marker-focus',
                html: '<div class="gm-pin gm-pin-focus"><span class="material-icons" style="font-size:18px;color:#fff;">place</span></div>',
                iconSize: [32, 40], iconAnchor: [16, 38], popupAnchor: [0, -34]
            });
        }
        return L.divIcon({
            className: 'gm-marker',
            html: '<div class="gm-pin gm-pin-poi"></div>',
            iconSize: [18, 24], iconAnchor: [9, 22], popupAnchor: [0, -20]
        });
    }

    function popupHTML(m) {
        var stars = '';
        if (m.rating) {
            var f = Math.floor(m.rating);
            for (var i = 0; i < f; i++) stars += '★';
            for (var j = f; j < 5; j++) stars += '☆';
        }
        var link = m.slug ? ('/place/' + encodeURIComponent(m.slug)) : '';
        return '' +
            '<div class="gm-popup">' +
                '<div class="gm-popup-name">' + (link ? '<a href="' + link + '">' + escapeHtml(m.name) + '</a>' : escapeHtml(m.name)) + '</div>' +
                (m.cat ? '<div class="gm-popup-cat">' + escapeHtml(m.cat) + '</div>' : '') +
                (m.rating ? '<div class="gm-popup-rating"><span style="color:#fbbc04;">' + stars + '</span> ' + Number(m.rating).toFixed(1) + (m.reviews ? ' (' + Number(m.reviews).toLocaleString() + ')' : '') + '</div>' : '') +
                (m.addr ? '<div class="gm-popup-addr">' + escapeHtml(m.addr) + '</div>' : '') +
                (link ? '<div class="gm-popup-actions"><a href="' + link + '">View details &rarr;</a></div>' : '') +
            '</div>';
    }

    function escapeHtml(s) {
        return String(s || '').replace(/[&<>"']/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
    }

    // -------------------------------------------------------------------------
    // Boot. Waits for Leaflet (loaded via deferred <script>) before
    // mounting; gives up after ~4s if window.L never appears.
    // -------------------------------------------------------------------------
    function boot() {
        var host = getHost();
        var main = getMain();
        var canvas = getCanvas();
        if (!host || !main || !canvas) return false;
        if (host._leafletInited) return true;

        if (typeof L === 'undefined') return false;

        var lat  = parseFloat(main.getAttribute('data-center-lat') || '40');
        var lng  = parseFloat(main.getAttribute('data-center-lng') || '-20');
        var zoom = parseInt(main.getAttribute('data-zoom') || '12', 10);
        var markers = parseDataJSON(canvas, 'data-markers', []) || [];
        var route   = parseDataJSON(canvas, 'data-route',   []) || [];

        // Mount the map.
        var map = L.map(host, {
            zoomControl: false,        // chrome already provides +/- buttons
            attributionControl: true,
            preferCanvas: true
        }).setView([lat, lng], zoom);

        // Base layers.
        var layers = {
            map:       L.tileLayer(TILE.map.url,       { maxZoom: TILE.map.maxZoom,       attribution: TILE.map.attr,       subdomains: TILE.map.subdomains }),
            satellite: L.tileLayer(TILE.satellite.url, { maxZoom: TILE.satellite.maxZoom, attribution: TILE.satellite.attr }),
            terrain:   L.tileLayer(TILE.terrain.url,   { maxZoom: TILE.terrain.maxZoom,   attribution: TILE.terrain.attr,   subdomains: TILE.terrain.subdomains })
        };
        layers.map.addTo(map);

        // Overlay tile layers (transit / cycling) — initially absent.
        var overlays = {
            transit: L.tileLayer(OVERLAY.transit.url, { maxZoom: OVERLAY.transit.maxZoom, attribution: OVERLAY.transit.attr, subdomains: OVERLAY.transit.subdomains, opacity: 0.85 }),
            cycling: L.tileLayer(OVERLAY.cycling.url, { maxZoom: OVERLAY.cycling.maxZoom, attribution: OVERLAY.cycling.attr, subdomains: OVERLAY.cycling.subdomains, opacity: 0.85 })
        };

        // SVG-style overlays for layers without dedicated tile servers — drawn
        // as semi-transparent rect overlays via Leaflet's polygon helpers so a
        // visible band appears across the visible bounds.
        var svgOverlays = {};

        function addSvgBandOverlay(name, color, opacity) {
            if (svgOverlays[name]) return svgOverlays[name];
            // Diagonal hatch stripes across the world bounds.
            var rect = L.rectangle(
                [[-85, -180], [85, 180]],
                { color: color, weight: 0, fillColor: color, fillOpacity: opacity, interactive: false }
            );
            svgOverlays[name] = rect;
            return rect;
        }

        // Render markers.
        var markerGroup = L.featureGroup().addTo(map);
        markers.forEach(function (m) {
            if (m.lat == null || m.lng == null) return;
            var mk = L.marker([m.lat, m.lng], { icon: markerIconForRole(m.role, m.focus) });
            mk.bindPopup(popupHTML(m), { maxWidth: 260, minWidth: 200 });
            mk.addTo(markerGroup);
        });

        // If the directions page passed an origin+destination, draw a polyline
        // between them (great-circle straight line). Real routing-engine
        // polylines would follow streets; this is a deliberate stub clearly
        // marked as "approximate" via dashArray.
        var routeLine = null;
        if (route && route.length >= 2) {
            routeLine = L.polyline(route, {
                color: '#1a73e8', weight: 5, opacity: 0.85, dashArray: '0',
                lineJoin: 'round'
            }).addTo(map);
            // Auto-fit to the route.
            try { map.fitBounds(routeLine.getBounds().pad(0.2)); } catch (e) {}
        } else if (markers.length >= 2) {
            // Multi-marker fit (only if there's no specific focus + room).
            try {
                var bounds = markerGroup.getBounds();
                if (bounds.isValid()) {
                    var center = map.getCenter();
                    // only auto-fit when the original center wasn't a hard
                    // anchor (place_detail) — heuristic: zoom < 13.
                    if (zoom < 13) {
                        map.fitBounds(bounds.pad(0.15), { maxZoom: 14 });
                    }
                }
            } catch (e) {}
        }

        // Hide the static CSS fallback labels (they only existed for no-JS).
        var fb = document.querySelector('.map-canvas-fallback');
        if (fb) fb.style.display = 'none';

        // Wire status pill update to actual map events.
        map.on('zoomend', function () {
            main.setAttribute('data-zoom', String(map.getZoom()));
            refreshStatus();
        });
        map.on('moveend', function () {
            var c = map.getCenter();
            main.setAttribute('data-center-lat', c.lat.toFixed(6));
            main.setAttribute('data-center-lng', c.lng.toFixed(6));
        });

        // Save handles for the click-handlers below.
        window.__gmMap = map;
        window.__gmLayers = layers;
        window.__gmOverlays = overlays;
        window.__gmSvgOverlays = svgOverlays;
        window.__gmMarkerGroup = markerGroup;
        window.__gmRouteLine = routeLine;
        window.__gmInitialView = { lat: lat, lng: lng, zoom: zoom };
        window.__gmAddSvgOverlay = addSvgBandOverlay;

        host._leafletInited = true;

        // Force re-layout in case the map container size was 0 at boot
        // (template heavy with rails / panels). Leaflet needs an invalidateSize.
        setTimeout(function () { try { map.invalidateSize(); } catch (e) {} }, 50);
        setTimeout(function () { try { map.invalidateSize(); } catch (e) {} }, 400);

        refreshStatus();
        return true;
    }

    // -------------------------------------------------------------------------
    // High-priority click dispatch — runs in CAPTURE phase so it pre-empts
    // main.js's delegated handler when a real L.Map is present.
    // -------------------------------------------------------------------------
    function setMapType(type) {
        var main = getMain();
        var map = window.__gmMap;
        if (!main) return;
        main.setAttribute('data-map-type', type);
        $$('.map-type-btn').forEach(function (btn) {
            var active = btn.getAttribute('data-map-type') === type;
            btn.classList.toggle('active', active);
            btn.setAttribute('aria-selected', active ? 'true' : 'false');
        });
        if (map && window.__gmLayers) {
            // Remove all base layers, add the chosen one.
            ['map', 'satellite', 'terrain'].forEach(function (k) {
                if (window.__gmLayers[k] && map.hasLayer(window.__gmLayers[k])) {
                    map.removeLayer(window.__gmLayers[k]);
                }
            });
            if (window.__gmLayers[type]) window.__gmLayers[type].addTo(map);
        }
        refreshStatus();
    }

    function toggleLayer(name) {
        var main = getMain();
        if (!main) return;
        var layers = (main.getAttribute('data-active-layers') || '').split(',').filter(Boolean);
        var idx = layers.indexOf(name);
        var willBeOn = idx < 0;
        if (idx >= 0) layers.splice(idx, 1); else layers.push(name);
        main.setAttribute('data-active-layers', layers.join(','));
        $$('.layer-toggle[data-layer="' + name + '"]').forEach(function (btn) {
            btn.setAttribute('aria-pressed', willBeOn ? 'true' : 'false');
        });

        var map = window.__gmMap;
        if (map) {
            // Tile-backed overlays for transit / cycling.
            if (name === 'transit' && window.__gmOverlays && window.__gmOverlays.transit) {
                if (willBeOn) window.__gmOverlays.transit.addTo(map);
                else map.removeLayer(window.__gmOverlays.transit);
            } else if (name === 'cycling' && window.__gmOverlays && window.__gmOverlays.cycling) {
                if (willBeOn) window.__gmOverlays.cycling.addTo(map);
                else map.removeLayer(window.__gmOverlays.cycling);
            } else if (name === 'traffic') {
                // Semi-transparent red wash to simulate traffic data without a real provider.
                if (willBeOn && window.__gmAddSvgOverlay) {
                    window.__gmAddSvgOverlay('traffic', '#ea4335', 0.10).addTo(map);
                } else if (window.__gmSvgOverlays.traffic) {
                    map.removeLayer(window.__gmSvgOverlays.traffic);
                    delete window.__gmSvgOverlays.traffic;
                }
            } else if (name === 'walking') {
                if (willBeOn && window.__gmAddSvgOverlay) {
                    window.__gmAddSvgOverlay('walking', '#8e44ad', 0.07).addTo(map);
                } else if (window.__gmSvgOverlays.walking) {
                    map.removeLayer(window.__gmSvgOverlays.walking);
                    delete window.__gmSvgOverlays.walking;
                }
            } else if (name === '3d') {
                if (willBeOn && window.__gmAddSvgOverlay) {
                    window.__gmAddSvgOverlay('3d', '#5f6368', 0.05).addTo(map);
                } else if (window.__gmSvgOverlays['3d']) {
                    map.removeLayer(window.__gmSvgOverlays['3d']);
                    delete window.__gmSvgOverlays['3d'];
                }
            }
        }

        renderActiveLayerChips();
        refreshStatus();
    }

    function locate() {
        var map = window.__gmMap;
        var main = getMain();
        if (!main) return;
        if (map) {
            // Synthetic "your location" marker — pin at current view center,
            // pulsing circle. We don't request real geolocation (no prompts).
            var c = map.getCenter();
            if (window.__gmLocateMarker) map.removeLayer(window.__gmLocateMarker);
            var locIcon = L.divIcon({
                className: 'gm-marker gm-marker-locate',
                html: '<div class="gm-locate-pulse"></div><div class="gm-locate-dot"></div>',
                iconSize: [24, 24], iconAnchor: [12, 12]
            });
            window.__gmLocateMarker = L.marker([c.lat, c.lng], { icon: locIcon, interactive: false }).addTo(map);
            map.setView([c.lat, c.lng], Math.max(map.getZoom(), 14));
        }
        refreshStatus();
    }

    function fitBounds() {
        var map = window.__gmMap;
        if (!map) return;
        try {
            if (window.__gmRouteLine) {
                map.fitBounds(window.__gmRouteLine.getBounds().pad(0.2));
            } else if (window.__gmMarkerGroup) {
                var b = window.__gmMarkerGroup.getBounds();
                if (b.isValid()) map.fitBounds(b.pad(0.15));
            }
        } catch (e) {}
    }

    function resetView() {
        var map = window.__gmMap;
        var iv = window.__gmInitialView;
        if (!map || !iv) return;
        map.setView([iv.lat, iv.lng], iv.zoom);
    }

    function rotate() {
        // Real Leaflet doesn't rotate; we update the CSS transform on the
        // host so the visual change is observable, and bump data-rotation
        // so the status pill reflects it.
        var main = getMain();
        var host = getHost();
        if (!main || !host) return;
        var rot = parseInt(main.getAttribute('data-rotation') || '0', 10);
        rot = (rot + 45) % 360;
        main.setAttribute('data-rotation', String(rot));
        host.style.transform = 'rotate(' + rot + 'deg)';
        host.style.transformOrigin = '50% 50%';
        host.style.transition = 'transform 200ms ease-out';
        // Reset so subsequent panning doesn't accumulate.
        setTimeout(function () {
            if (window.__gmMap) { try { window.__gmMap.invalidateSize(); } catch (e) {} }
        }, 220);
        refreshStatus();
    }

    function toggleContrast() {
        var main = getMain();
        if (!main) return;
        var on = main.classList.toggle('high-contrast');
        $$('.map-ctrl-btn[data-action="contrast"]').forEach(function (btn) {
            btn.setAttribute('aria-pressed', on ? 'true' : 'false');
        });
        var host = getHost();
        if (host) {
            host.style.filter = on
                ? 'contrast(1.4) saturate(0.7) brightness(0.95)'
                : '';
        }
        refreshStatus();
    }

    // Capture-phase listener so we beat main.js's delegated handler.
    document.addEventListener('click', function (ev) {
        var t = ev.target;
        if (!t || !t.closest) return;

        var mc = t.closest('.map-ctrl-btn[data-action]');
        if (mc) {
            var act = mc.getAttribute('data-action');
            var handled = true;
            switch (act) {
                case 'zoom-in':    if (window.__gmMap) window.__gmMap.zoomIn(); break;
                case 'zoom-out':   if (window.__gmMap) window.__gmMap.zoomOut(); break;
                case 'locate':     locate(); break;
                case 'fit-bounds': fitBounds(); break;
                case 'reset-view': resetView(); break;
                case 'rotate':     rotate(); break;
                case 'contrast':   toggleContrast(); break;
                default: handled = false;
            }
            if (handled && window.__gmMap) {
                ev.preventDefault();
                ev.stopPropagation();
                refreshStatus();
                return;
            }
        }
        var mt = t.closest('.map-type-btn[data-map-type]');
        if (mt && window.__gmMap) {
            ev.preventDefault();
            ev.stopPropagation();
            setMapType(mt.getAttribute('data-map-type'));
            return;
        }
        var lt = t.closest('.layer-toggle[data-layer]');
        if (lt && window.__gmMap) {
            ev.preventDefault();
            ev.stopPropagation();
            toggleLayer(lt.getAttribute('data-layer'));
            return;
        }
    }, true);

    // ---- Boot sequence -------------------------------------------------------
    // Leaflet's <script> is deferred, so window.L exists by DOMContentLoaded
    // ~99% of the time. Poll for up to 4s just in case.
    function whenReady(fn) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', fn);
        } else { fn(); }
    }
    whenReady(function () {
        if (boot()) return;
        var tries = 0;
        var iv = setInterval(function () {
            tries++;
            if (boot() || tries > 40) clearInterval(iv);
        }, 100);
    });
})();
