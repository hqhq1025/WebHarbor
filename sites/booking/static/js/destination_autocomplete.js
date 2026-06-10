/* WV-BOOKING-AUTOCOMPLETE-FIX-R2-2026-06-04
 *
 * Destination autocomplete for booking mirror's `<input name="ss">` field.
 * Round 2 fixes documented in
 *   .claude/workspace/booking_autocomplete_r2_fix.md
 *
 * Why R2 exists
 * -------------
 * Round-1 (sentinel WV-BOOKING-AUTOCOMPLETE-FIX-2026-06-04) shipped a working
 * popup BUT trajectories from `bulk_medium_v4_killed_0955` (tasks _0203
 * "Ember Rio de Janeiro", _0178 "Old Town villa") still timed out at 50 steps.
 * Inspection showed the agent was NOT interacting with the new autocomplete
 * at all — it was hammering the *native* `<select name="city_id">` widget on
 * /searchresults.html, which has 350+ <option> rows and falls back to type-to-
 * search letter-jumping:
 *   - _0203: `keypress R` cycles through "Rotterdam, Rio, …" forever.
 *   - _0178: `keypress O` jumps to "Ohio" then to "Old San Juan", never lands.
 * The team had already replaced the sort `<select>` with pills (see
 * WV-SELECT-FIX-2026-06-01) for exactly this reason — the city_id select
 * slipped through.
 *
 * R2 changes
 * ----------
 * 1. Selecting an autocomplete suggestion now populates ANY sibling form
 *    field named `city_id` (hidden <input> or <select>). On city selection
 *    we set both the visible "ss" text and the hidden city_id; on property
 *    selection we set ss to the property name and city_id to the property's
 *    owning city (search() resolves with `name LIKE %ss%` so the city_id
 *    helps narrow the result set).
 * 2. Row event listener is `mousedown` (not `click`) with preventDefault, so
 *    even a CUA harness that synthesises only `mousedown`/`mouseup` (no full
 *    click) still selects.
 * 3. Row minimum height bumped to 40px (was ~32px) — agents click by
 *    coordinates and easier targets reduce miss-rate.
 * 4. New `data-cityid-target` opt-in attribute on the `ss` input lets a
 *    template explicitly name a sibling field; default behaviour walks the
 *    form for `[name="city_id"]`.
 *
 * Markup contract (unchanged from R1)
 *   <input type="text" name="ss" data-destination-autocomplete ...>
 *   <input type="hidden" name="city_id" value="">     (optional — auto-populated)
 *   OR
 *   <select name="city_id"> ... </select>             (legacy — also auto-populated)
 */
(function () {
    'use strict';

    var DEBOUNCE_MS = 110;
    var MIN_QUERY_LEN = 1;
    var LIMIT = 15;
    var ENDPOINT = '/api/destination-suggest';
    // Row geometry — keep these wide. CUA agents target by coordinates and a
    // 40px tall row is the smallest comfortable click area in 1280×720.
    var ROW_MIN_HEIGHT_PX = 40;

    var openPopup = null;
    var openInput = null;
    var debounceTimer = null;
    var inflightController = null;
    var activeIndex = -1;
    var lastQuery = '';

    function closePopup() {
        if (openPopup && openPopup.parentNode) {
            openPopup.parentNode.removeChild(openPopup);
        }
        openPopup = null;
        openInput = null;
        activeIndex = -1;
        lastQuery = '';
        document.removeEventListener('mousedown', onDocMouseDown, true);
        document.removeEventListener('keydown', onGlobalKeyDown, true);
        window.removeEventListener('resize', positionPopup);
        window.removeEventListener('scroll', positionPopup, true);
        if (inflightController) {
            try { inflightController.abort(); } catch (e) {}
            inflightController = null;
        }
    }

    function onDocMouseDown(e) {
        if (!openPopup) return;
        if (openPopup.contains(e.target)) return;
        if (e.target === openInput) return;
        closePopup();
    }

    function onGlobalKeyDown(e) {
        if (e.key === 'Escape' || e.keyCode === 27) {
            closePopup();
        }
    }

    function positionPopup() {
        if (!openPopup || !openInput) return;
        var rect = openInput.getBoundingClientRect();
        openPopup.style.top = (rect.bottom + 4) + 'px';
        openPopup.style.left = rect.left + 'px';
        openPopup.style.minWidth = Math.max(rect.width, 320) + 'px';
    }

    function ensurePopup(input) {
        if (openPopup && openInput === input) return openPopup;
        if (openPopup) closePopup();

        var popup = document.createElement('div');
        popup.className = 'destination-autocomplete';
        popup.setAttribute('role', 'listbox');
        popup.setAttribute('aria-label', 'Destination suggestions');
        popup.style.cssText = [
            'position:fixed',
            'z-index:10050',
            'background:#fff',
            'border:1px solid #c7c7c7',
            'border-radius:4px',
            'box-shadow:0 4px 18px rgba(0,0,0,0.16)',
            'max-height:380px',
            'overflow-y:auto',
            'font-size:14px',
            'color:#262626',
            'padding:4px 0'
        ].join(';');
        // Don't steal focus from the typing input — see header comment.
        popup.addEventListener('mousedown', function (e) {
            e.preventDefault();
        });
        document.body.appendChild(popup);

        openPopup = popup;
        openInput = input;
        positionPopup();
        document.addEventListener('mousedown', onDocMouseDown, true);
        document.addEventListener('keydown', onGlobalKeyDown, true);
        window.addEventListener('resize', positionPopup);
        // capture=true so inner scrollables also fire — we reposition, NEVER close.
        window.addEventListener('scroll', positionPopup, true);
        return popup;
    }

    function renderItems(items) {
        if (!openPopup) return;
        openPopup.innerHTML = '';
        activeIndex = -1;
        if (!items || items.length === 0) {
            var empty = document.createElement('div');
            empty.className = 'destination-autocomplete-empty';
            empty.setAttribute('role', 'status');
            empty.textContent = 'No matching destinations';
            empty.style.cssText = 'padding:12px 14px;color:#5d666e;font-style:italic;';
            openPopup.appendChild(empty);
            return;
        }
        items.forEach(function (item, idx) {
            var row = document.createElement('div');
            row.className = 'destination-autocomplete-item';
            row.setAttribute('role', 'option');
            row.setAttribute('data-index', String(idx));
            row.setAttribute('data-value', item.value);
            row.style.cssText = [
                'padding:10px 14px',
                'min-height:' + ROW_MIN_HEIGHT_PX + 'px',
                'cursor:pointer',
                'display:flex',
                'justify-content:space-between',
                'gap:12px',
                'align-items:center',
                'border-bottom:1px solid #f1f1f1',
                'box-sizing:border-box'
            ].join(';');

            var left = document.createElement('div');
            left.style.cssText = 'flex:1;min-width:0;';
            var primary = document.createElement('div');
            primary.style.cssText = 'font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;';
            primary.textContent = item.label;
            left.appendChild(primary);
            if (item.sublabel) {
                var sub = document.createElement('div');
                sub.style.cssText = 'font-size:12px;color:#5d666e;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;';
                sub.textContent = item.sublabel;
                left.appendChild(sub);
            }
            row.appendChild(left);

            if (item.kind) {
                var tag = document.createElement('span');
                tag.style.cssText = 'font-size:11px;color:#fff;background:#006ce4;padding:3px 9px;border-radius:10px;flex-shrink:0;';
                tag.textContent = item.kind;
                row.appendChild(tag);
            }

            // Use mousedown (not click) — fires before blur and survives CUA
            // harnesses that only synthesise mousedown/up without a real click.
            // We preventDefault on the OUTER popup mousedown to keep focus on
            // the input; here we additionally stopPropagation so this row's
            // selection fires once and only once.
            row.addEventListener('mousedown', function (e) {
                e.preventDefault();
                e.stopPropagation();
                selectItem(item);
            });
            // Keep click as a belt-and-braces fallback (mouse-only browsers
            // that don't dispatch mousedown for some reason).
            row.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                selectItem(item);
            });
            // Hover highlight matches keyboard highlight, so the visible
            // active row IS the one that fires on Enter.
            row.addEventListener('mouseenter', function () {
                setActive(idx);
            });
            openPopup.appendChild(row);
        });
    }

    function findCityIdField(input) {
        // 1) Explicit override via data-cityid-target="<selector>"
        var sel = input.getAttribute('data-cityid-target');
        if (sel) {
            var explicit = document.querySelector(sel);
            if (explicit) return explicit;
        }
        // 2) Sibling field in the same form named "city_id".
        if (input.form) {
            return input.form.querySelector('[name="city_id"]');
        }
        return null;
    }

    function setCityIdField(input, cityId) {
        var field = findCityIdField(input);
        if (!field) return false;
        var value = (cityId == null) ? '' : String(cityId);
        // For <select>: set .value, fall back to scanning options for the id
        // string (some templates may render numeric vs string mismatch).
        if (field.tagName === 'SELECT') {
            field.value = value;
            if (field.value !== value) {
                // No option matched — fall back to inserting one so the form
                // still submits the chosen city_id. We append rather than
                // replace existing options to keep the visible label coherent.
                var opt = document.createElement('option');
                opt.value = value;
                opt.textContent = value;
                opt.selected = true;
                field.appendChild(opt);
                field.value = value;
            }
        } else {
            field.value = value;
        }
        try {
            field.dispatchEvent(new Event('change', { bubbles: true }));
            field.dispatchEvent(new Event('input', { bubbles: true }));
        } catch (e) { /* old browsers */ }
        return true;
    }

    function selectItem(item) {
        if (!openInput) return;
        var input = openInput;
        input.value = item.value;
        input.classList.remove('destination-autocomplete-invalid');
        // Order matters: dispatch `change` FIRST (which triggers external
        // listeners + the clear-on-edit logic in onInputType for any stale
        // city_id), THEN write our chosen city_id. We deliberately skip the
        // `input` event because it's wired to onInputType, which would race
        // against the assignment and clear it again. `change` is enough for
        // external listeners; the harness has the value committed by the
        // time the form submits.
        try {
            input.dispatchEvent(new Event('change', { bubbles: true }));
        } catch (e) { /* old browsers */ }
        // Populate the hidden city_id field (or <select>) so the search query
        // is narrowed deterministically — kills the "name substring matches
        // wrong city" + native-select-typeahead failure modes both at once.
        if (item.kind === 'City') {
            // item.id is the city id (api emits it for both kinds).
            setCityIdField(input, item.id);
        } else if (item.kind === 'Property') {
            // For Property hits we DELIBERATELY clear city_id and rely on the
            // search backend's name-substring match (Property.name ilike
            // %term%). Populating city_id here would override term-matching
            // and broaden the result to the entire owning city (e.g. picking
            // "JW Marriott Mumbai Juhu" → 61 hotels instead of 1, because
            // the search() handler treats city_id as authoritative when
            // present, ignoring ss). The property name itself is unique
            // enough to land on the right row.
            setCityIdField(input, null);
        }
        closePopup();
        // Submit the form if there is one (mirrors real booking behaviour).
        if (input.form && input.dataset.destinationAutocompleteSubmit !== '0') {
            try { input.form.submit(); } catch (e) {}
        } else {
            input.focus();
        }
    }

    function setActive(idx) {
        if (!openPopup) return;
        var rows = openPopup.querySelectorAll('.destination-autocomplete-item');
        if (rows.length === 0) return;
        if (idx < 0) idx = rows.length - 1;
        if (idx >= rows.length) idx = 0;
        activeIndex = idx;
        for (var i = 0; i < rows.length; i++) {
            if (i === idx) {
                rows[i].style.background = '#e8f0fe';
                rows[i].setAttribute('aria-selected', 'true');
                rows[i].scrollIntoView({ block: 'nearest' });
            } else {
                rows[i].style.background = '';
                rows[i].removeAttribute('aria-selected');
            }
        }
    }

    function fetchSuggestions(input, q) {
        if (inflightController) {
            try { inflightController.abort(); } catch (e) {}
        }
        inflightController = (typeof AbortController === 'function')
            ? new AbortController() : null;
        var url = ENDPOINT + '?q=' + encodeURIComponent(q) + '&limit=' + LIMIT;
        var opts = inflightController ? { signal: inflightController.signal } : {};
        fetch(url, opts).then(function (r) {
            if (!r.ok) return null;
            return r.json();
        }).then(function (data) {
            // Race: input changed since fetch started — drop.
            if (!openInput || openInput !== input) return;
            if ((input.value || '').trim() !== q) return;
            if (!data || !Array.isArray(data.items)) {
                renderItems([]);
                return;
            }
            renderItems(data.items);
        }).catch(function (err) {
            if (err && err.name === 'AbortError') return;
            if (openInput === input) renderItems([]);
        });
    }

    function onInputType(input) {
        var q = (input.value || '').trim();
        if (q.length < MIN_QUERY_LEN) {
            closePopup();
            return;
        }
        if (q === lastQuery && openInput === input) return;
        lastQuery = q;
        // If the user is editing the destination string after a previous
        // selection, the stored city_id no longer matches; clear it so we
        // don't silently apply a stale filter when they hit Enter.
        var field = findCityIdField(input);
        if (field && field.value) {
            if (field.tagName === 'SELECT') {
                field.value = '';
            } else {
                field.value = '';
            }
        }
        ensurePopup(input);
        if (openPopup.children.length === 0) {
            var loading = document.createElement('div');
            loading.style.cssText = 'padding:12px 14px;color:#5d666e;font-style:italic;';
            loading.textContent = 'Looking up destinations…';
            openPopup.appendChild(loading);
        }
        if (debounceTimer) clearTimeout(debounceTimer);
        debounceTimer = setTimeout(function () {
            fetchSuggestions(input, q);
        }, DEBOUNCE_MS);
    }

    function onInputKeyDown(input, e) {
        if (!openPopup) {
            if ((e.key === 'ArrowDown' || e.keyCode === 40)
                && (input.value || '').trim().length >= MIN_QUERY_LEN) {
                onInputType(input);
                e.preventDefault();
            }
            return;
        }
        if (e.key === 'ArrowDown' || e.keyCode === 40) {
            e.preventDefault();
            setActive(activeIndex + 1);
        } else if (e.key === 'ArrowUp' || e.keyCode === 38) {
            e.preventDefault();
            setActive(activeIndex - 1);
        } else if (e.key === 'Enter' || e.keyCode === 13) {
            if (activeIndex >= 0) {
                var rows = openPopup.querySelectorAll('.destination-autocomplete-item');
                if (rows[activeIndex]) {
                    e.preventDefault();
                    // Trigger mousedown to mirror the click path used by
                    // the pointer — keeps focus + uses the same selectItem
                    // logic + populates city_id correctly.
                    var ev;
                    try {
                        ev = new MouseEvent('mousedown', { bubbles: true, cancelable: true });
                    } catch (mErr) {
                        ev = document.createEvent('MouseEvents');
                        ev.initEvent('mousedown', true, true);
                    }
                    rows[activeIndex].dispatchEvent(ev);
                }
            } else {
                // Let the form submit naturally — but close the popup first.
                closePopup();
            }
        } else if (e.key === 'Tab') {
            if (activeIndex >= 0) {
                var trows = openPopup.querySelectorAll('.destination-autocomplete-item');
                if (trows[activeIndex]) {
                    var tev;
                    try {
                        tev = new MouseEvent('mousedown', { bubbles: true, cancelable: true });
                    } catch (mErr) {
                        tev = document.createEvent('MouseEvents');
                        tev.initEvent('mousedown', true, true);
                    }
                    trows[activeIndex].dispatchEvent(tev);
                }
            } else {
                closePopup();
            }
        }
    }

    function attach(input) {
        if (input.dataset.destinationAutocompleteBound === '1') return;
        input.dataset.destinationAutocompleteBound = '1';
        input.setAttribute('autocomplete', 'off');
        input.setAttribute('autocorrect', 'off');
        input.setAttribute('autocapitalize', 'off');
        input.setAttribute('spellcheck', 'false');
        input.setAttribute('role', 'combobox');
        input.setAttribute('aria-autocomplete', 'list');
        input.setAttribute('aria-haspopup', 'listbox');

        input.addEventListener('input', function () { onInputType(input); });
        input.addEventListener('focus', function () {
            if ((input.value || '').trim().length >= MIN_QUERY_LEN) onInputType(input);
        });
        input.addEventListener('keydown', function (e) { onInputKeyDown(input, e); });
    }

    function init() {
        var inputs = document.querySelectorAll('input[data-destination-autocomplete]');
        for (var i = 0; i < inputs.length; i++) attach(inputs[i]);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
