/* Booking mirror — vanilla JS date picker.
 * Replaces native <input type="date"> (which on Chromium allows 5+ digit years)
 * with a clickable month-grid popup PLUS strict YYYY-MM-DD typed input.
 *
 * Markup contract:
 *   <input type="text" maxlength="10" inputmode="numeric"
 *          pattern="\d{4}-\d{2}-\d{2}" autocomplete="off"
 *          data-datepicker="checkin"|"checkout"|"single"
 *          [data-datepicker-min="YYYY-MM-DD"]>
 *   The datepicker pairs a "checkout" input with the nearest "checkin" input
 *   in the same form: checkout dates <= checkin are disabled / flagged invalid.
 *
 * Typing UX:
 *   - Only digits and `-` (plus navigation/edit keys) are accepted.
 *   - Auto-inserts `-` after the year (4 digits) and after the month (2 more).
 *     So typing `20240225` becomes `2024-02-25` automatically.
 *   - Backspace over an auto-inserted `-` removes both the hyphen and the
 *     digit before it for symmetric editing.
 *   - On valid YYYY-MM-DD typed value, the popup updates to that month and
 *     marks the day as selected. The popup never steals focus from the input.
 *   - On blur, an invalid value gets a `.dp-input-invalid` class but the user's
 *     text is preserved so they can fix it.
 */
(function () {
    'use strict';

    var WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    var MONTH_NAMES = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ];

    var openPopup = null;
    var openInput = null;

    function pad2(n) { return (n < 10 ? '0' : '') + n; }

    function fmtDate(d) {
        return d.getFullYear() + '-' + pad2(d.getMonth() + 1) + '-' + pad2(d.getDate());
    }

    function parseDate(s) {
        if (!s) return null;
        var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
        if (!m) return null;
        var y = parseInt(m[1], 10);
        var mo = parseInt(m[2], 10) - 1;
        var d = parseInt(m[3], 10);
        var dt = new Date(y, mo, d);
        if (dt.getFullYear() !== y || dt.getMonth() !== mo || dt.getDate() !== d) return null;
        return dt;
    }

    function startOfDay(d) {
        return new Date(d.getFullYear(), d.getMonth(), d.getDate());
    }

    function getCheckinValue(input) {
        // For a checkout input, find the matching checkin input (same form preferred).
        var form = input.form || document;
        var checkin = form.querySelector('input[data-datepicker="checkin"]');
        if (!checkin) checkin = document.querySelector('input[data-datepicker="checkin"]');
        return checkin ? parseDate(checkin.value) : null;
    }

    function closePopup() {
        if (openPopup && openPopup.parentNode) {
            openPopup.parentNode.removeChild(openPopup);
        }
        openPopup = null;
        openInput = null;
        document.removeEventListener('mousedown', onDocMouseDown, true);
        document.removeEventListener('keydown', onGlobalKeyDown, true);
        window.removeEventListener('resize', positionPopup);
        window.removeEventListener('scroll', positionPopup, true);
    }

    function onDocMouseDown(e) {
        if (!openPopup) return;
        if (openPopup.contains(e.target)) return;
        if (e.target === openInput) return;
        closePopup();
    }

    function onGlobalKeyDown(e) {
        // Escape closes — but only when the user is interacting with this input.
        if (e.key === 'Escape' || e.keyCode === 27) {
            closePopup();
        }
    }

    function positionPopup() {
        if (!openPopup || !openInput) return;
        var rect = openInput.getBoundingClientRect();
        var top = rect.bottom + window.scrollY + 4;
        var left = rect.left + window.scrollX;
        openPopup.style.top = top + 'px';
        openPopup.style.left = left + 'px';
    }

    function buildPopup(input) {
        var role = input.getAttribute('data-datepicker') || 'single';

        var initial = parseDate(input.value);
        var viewDate;
        if (initial) {
            viewDate = new Date(initial.getFullYear(), initial.getMonth(), 1);
        } else {
            var today = new Date();
            viewDate = new Date(today.getFullYear(), today.getMonth(), 1);
        }

        var popup = document.createElement('div');
        popup.className = 'datepicker-popup';
        popup.setAttribute('role', 'dialog');
        popup.setAttribute('aria-label', 'Choose date');
        // Prevent the popup from stealing focus when clicked: any element inside
        // that has tabindex / receives mousedown would normally pull focus, so we
        // intercept mousedown at the popup root and preventDefault() — the click
        // events on buttons still fire (preventDefault on mousedown does NOT
        // suppress click).
        popup.addEventListener('mousedown', function (e) {
            // Do not steal focus from the typing input.
            e.preventDefault();
        });

        function render() {
            popup.innerHTML = '';

            // Header
            var header = document.createElement('div');
            header.className = 'datepicker-header';

            var prev = document.createElement('button');
            prev.type = 'button';
            prev.className = 'datepicker-nav datepicker-prev';
            prev.tabIndex = -1;
            prev.setAttribute('aria-label', 'Previous month');
            prev.textContent = '\u2039';
            prev.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                viewDate = new Date(viewDate.getFullYear(), viewDate.getMonth() - 1, 1);
                render();
            });

            var label = document.createElement('div');
            label.className = 'datepicker-month-label';
            label.textContent = MONTH_NAMES[viewDate.getMonth()] + ' ' + viewDate.getFullYear();

            var next = document.createElement('button');
            next.type = 'button';
            next.className = 'datepicker-nav datepicker-next';
            next.tabIndex = -1;
            next.setAttribute('aria-label', 'Next month');
            next.textContent = '\u203A';
            next.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                viewDate = new Date(viewDate.getFullYear(), viewDate.getMonth() + 1, 1);
                render();
            });

            header.appendChild(prev);
            header.appendChild(label);
            header.appendChild(next);
            popup.appendChild(header);

            // Weekday header
            var wkRow = document.createElement('div');
            wkRow.className = 'datepicker-weekdays';
            for (var i = 0; i < 7; i++) {
                var wd = document.createElement('div');
                wd.className = 'datepicker-weekday';
                wd.textContent = WEEKDAYS[i];
                wkRow.appendChild(wd);
            }
            popup.appendChild(wkRow);

            // Day grid
            var grid = document.createElement('div');
            grid.className = 'datepicker-grid';

            var firstWeekday = viewDate.getDay();
            var daysInMonth = new Date(viewDate.getFullYear(), viewDate.getMonth() + 1, 0).getDate();
            var daysInPrevMonth = new Date(viewDate.getFullYear(), viewDate.getMonth(), 0).getDate();

            var today = startOfDay(new Date());
            var selected = parseDate(input.value);
            var checkinDate = (role === 'checkout') ? getCheckinValue(input) : null;

            var minAttr = parseDate(input.getAttribute('data-datepicker-min') || '');

            // 6 weeks * 7 days = 42 cells.
            for (var c = 0; c < 42; c++) {
                var cellDate;
                var inMonth = true;
                if (c < firstWeekday) {
                    cellDate = new Date(viewDate.getFullYear(), viewDate.getMonth() - 1, daysInPrevMonth - (firstWeekday - 1 - c));
                    inMonth = false;
                } else if (c >= firstWeekday + daysInMonth) {
                    cellDate = new Date(viewDate.getFullYear(), viewDate.getMonth() + 1, c - firstWeekday - daysInMonth + 1);
                    inMonth = false;
                } else {
                    cellDate = new Date(viewDate.getFullYear(), viewDate.getMonth(), c - firstWeekday + 1);
                }

                var cell = document.createElement('button');
                cell.type = 'button';
                cell.className = 'datepicker-cell';
                cell.tabIndex = -1;
                cell.textContent = cellDate.getDate();
                cell.setAttribute('data-date', fmtDate(cellDate));

                if (!inMonth) cell.classList.add('datepicker-cell-outside');
                if (cellDate.getTime() === today.getTime()) cell.classList.add('datepicker-cell-today');
                if (selected && cellDate.getTime() === startOfDay(selected).getTime()) {
                    cell.classList.add('datepicker-cell-selected');
                }

                var disabled = false;
                if (role === 'checkout' && checkinDate && cellDate.getTime() <= startOfDay(checkinDate).getTime()) {
                    disabled = true;
                }
                if (minAttr && cellDate.getTime() < startOfDay(minAttr).getTime()) {
                    disabled = true;
                }

                if (disabled) {
                    cell.classList.add('datepicker-cell-disabled');
                    cell.disabled = true;
                } else {
                    (function (dStr) {
                        cell.addEventListener('click', function (e) {
                            e.preventDefault();
                            e.stopPropagation();
                            input.value = dStr;
                            input.classList.remove('dp-input-invalid');
                            // Fire change/input so listeners (e.g. checkout refresh) can react.
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                            input.dispatchEvent(new Event('change', { bubbles: true }));
                            closePopup();
                        });
                    })(fmtDate(cellDate));
                }

                grid.appendChild(cell);
            }

            popup.appendChild(grid);
        }

        // Expose render so the input handlers can refresh the popup as the user types.
        popup._render = render;
        popup._setView = function (d) {
            viewDate = new Date(d.getFullYear(), d.getMonth(), 1);
            render();
        };

        render();
        return popup;
    }

    function refreshOpenPopupForCurrentInput() {
        if (!openPopup || !openInput) return;
        var parsed = parseDate(openInput.value);
        if (parsed && openPopup._setView) {
            openPopup._setView(parsed);
        } else if (openPopup._render) {
            // Re-render so "selected" highlight clears when value becomes invalid.
            openPopup._render();
        }
    }

    function openFor(input) {
        if (openInput === input && openPopup) return;
        closePopup();
        var popup = buildPopup(input);
        document.body.appendChild(popup);
        openPopup = popup;
        openInput = input;
        positionPopup();
        document.addEventListener('mousedown', onDocMouseDown, true);
        document.addEventListener('keydown', onGlobalKeyDown, true);
        window.addEventListener('resize', positionPopup);
        window.addEventListener('scroll', positionPopup, true);
    }

    /* ------------------------------------------------------------------ */
    /*                       Typed-input behaviours                        */
    /* ------------------------------------------------------------------ */

    var ALLOWED_NAV_KEYS = {
        'Backspace': 1, 'Delete': 1, 'Tab': 1, 'Enter': 1, 'Escape': 1,
        'ArrowLeft': 1, 'ArrowRight': 1, 'ArrowUp': 1, 'ArrowDown': 1,
        'Home': 1, 'End': 1
    };

    function isDigitKey(e) {
        // Ignore modified keys (cmd/ctrl/alt combos like Ctrl+A, Ctrl+C, Ctrl+V).
        if (e.ctrlKey || e.metaKey || e.altKey) return false;
        return e.key && e.key.length === 1 && e.key >= '0' && e.key <= '9';
    }

    function isHyphenKey(e) {
        if (e.ctrlKey || e.metaKey || e.altKey) return false;
        return e.key === '-';
    }

    function onTypedKeyDown(input, e) {
        // Allow common ctrl/cmd shortcuts (copy/paste/select-all) untouched.
        if (e.ctrlKey || e.metaKey) {
            return;
        }

        if (e.key === 'Escape' || e.keyCode === 27) {
            closePopup();
            return;
        }

        if (ALLOWED_NAV_KEYS[e.key]) {
            // Backspace: if the char to delete is the auto-inserted hyphen at
            // position 5 or 8 AND the cursor is right after it AND there's no
            // selection, also remove the digit before so backspace feels symmetric.
            if (e.key === 'Backspace' && input.selectionStart === input.selectionEnd) {
                var pos = input.selectionStart;
                var v = input.value;
                if (pos > 0 && v.charAt(pos - 1) === '-' && (pos === 5 || pos === 8)) {
                    e.preventDefault();
                    var newVal = v.slice(0, pos - 2) + v.slice(pos);
                    input.value = newVal;
                    var newPos = pos - 2;
                    input.setSelectionRange(newPos, newPos);
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                }
            }
            return;
        }

        if (isHyphenKey(e)) {
            // Allow `-` only at positions 4 or 7 (so the resulting string can be
            // YYYY-MM-DD). And don't allow if the next char is already `-`.
            var pos2 = input.selectionStart;
            if ((pos2 === 4 || pos2 === 7) && input.selectionStart === input.selectionEnd) {
                // Avoid double hyphen.
                if (input.value.charAt(pos2) === '-') {
                    e.preventDefault();
                    // Skip past the existing hyphen.
                    input.setSelectionRange(pos2 + 1, pos2 + 1);
                    return;
                }
                return; // allow normal insert
            }
            e.preventDefault();
            return;
        }

        if (isDigitKey(e)) {
            // Allow normal digit insertion; auto-hyphen is added in the input
            // handler after the digit lands so we see the new value.
            return;
        }

        // Anything else (letters, punctuation, etc.) is blocked.
        e.preventDefault();
    }

    function onTypedInput(input) {
        // Auto-insert hyphen after position 4 and 7 when the user has typed pure
        // digits and the cursor is at the end of the new digit segment.
        var v = input.value;

        // Strip any character that isn't a digit or `-` (defensive against IME
        // inputs / paste). Keep length capped at 10.
        var cleaned = '';
        for (var i = 0; i < v.length && cleaned.length < 10; i++) {
            var ch = v.charAt(i);
            if ((ch >= '0' && ch <= '9') || ch === '-') cleaned += ch;
        }
        if (cleaned !== v) {
            v = cleaned;
            input.value = v;
        }

        // Auto-insert hyphen logic. Trigger only when the user is typing at the
        // very end of the field (not editing in the middle), to avoid surprises.
        var caret = input.selectionStart;
        if (caret === v.length) {
            if (v.length === 4 && /^\d{4}$/.test(v)) {
                input.value = v + '-';
                input.setSelectionRange(5, 5);
                v = input.value;
            } else if (v.length === 7 && /^\d{4}-\d{2}$/.test(v)) {
                input.value = v + '-';
                input.setSelectionRange(8, 8);
                v = input.value;
            }
        }

        // Try to parse. If valid, update popup view + selection highlight.
        var parsed = parseDate(v);
        if (parsed) {
            input.classList.remove('dp-input-invalid');
            if (openInput === input && openPopup && openPopup._setView) {
                openPopup._setView(parsed);
            }
        } else {
            // Don't pop the invalid-class on every keystroke — only on blur.
            // But re-render the popup so any old "selected" cell clears.
            if (openInput === input && openPopup && openPopup._render) {
                openPopup._render();
            }
        }
    }

    function isValidCheckoutAgainstCheckin(input, parsed) {
        if (!parsed) return false;
        if (input.getAttribute('data-datepicker') !== 'checkout') return true;
        var ci = getCheckinValue(input);
        if (!ci) return true;
        return parsed.getTime() > startOfDay(ci).getTime();
    }

    function onTypedBlur(input) {
        // Defer slightly so a click on the popup that ends up calling closePopup
        // can still see the input value and so the click handler runs.
        setTimeout(function () {
            var v = input.value;
            if (v === '') {
                input.classList.remove('dp-input-invalid');
                return;
            }
            var parsed = parseDate(v);
            if (!parsed || !isValidCheckoutAgainstCheckin(input, parsed)) {
                input.classList.add('dp-input-invalid');
            } else {
                input.classList.remove('dp-input-invalid');
                // Normalise (in case of e.g. "2024-2-5" — not technically allowed,
                // but if pattern lets it slip we'd rewrite). Our regex demands
                // 2-digit month/day so this is a no-op.
                input.value = fmtDate(parsed);
            }
        }, 0);
    }

    /* ------------------------------------------------------------------ */
    /*                              Attach                                */
    /* ------------------------------------------------------------------ */

    function attach(input) {
        if (input.dataset.datepickerBound === '1') return;
        input.dataset.datepickerBound = '1';

        if (input.type !== 'text') {
            try { input.type = 'text'; } catch (_e) { /* some browsers */ }
        }
        // Make sure templates that still carry `readonly` get cleared (defensive).
        input.removeAttribute('readonly');
        input.setAttribute('autocomplete', 'off');
        if (!input.hasAttribute('maxlength')) input.setAttribute('maxlength', '10');
        if (!input.hasAttribute('inputmode')) input.setAttribute('inputmode', 'numeric');
        if (!input.hasAttribute('pattern')) input.setAttribute('pattern', '\\d{4}-\\d{2}-\\d{2}');
        if (!input.hasAttribute('placeholder')) input.setAttribute('placeholder', 'YYYY-MM-DD');

        input.addEventListener('focus', function () { openFor(input); });
        input.addEventListener('click', function () { openFor(input); });

        input.addEventListener('keydown', function (e) { onTypedKeyDown(input, e); });
        input.addEventListener('input', function () { onTypedInput(input); });
        input.addEventListener('change', function () {
            // Re-validate after a change (e.g. paste).
            var parsed = parseDate(input.value);
            if (parsed && openInput === input && openPopup && openPopup._setView) {
                openPopup._setView(parsed);
            }
        });
        input.addEventListener('blur', function () { onTypedBlur(input); });

        // If this is a checkin input, refresh any open checkout popup when value changes.
        if (input.getAttribute('data-datepicker') === 'checkin') {
            input.addEventListener('change', function () {
                if (openInput && openInput.getAttribute('data-datepicker') === 'checkout') {
                    var refreshed = buildPopup(openInput);
                    var prev = openPopup;
                    openPopup = refreshed;
                    document.body.appendChild(refreshed);
                    if (prev && prev.parentNode) prev.parentNode.removeChild(prev);
                    positionPopup();
                }
                // Auto-clear an invalid checkout (<= new checkin) so user re-picks.
                var form = input.form || document;
                var checkout = form.querySelector('input[data-datepicker="checkout"]');
                if (checkout && checkout.value) {
                    var ci = parseDate(input.value);
                    var co = parseDate(checkout.value);
                    if (ci && co && co.getTime() <= ci.getTime()) {
                        checkout.value = '';
                        checkout.classList.remove('dp-input-invalid');
                    }
                }
            });
        }
    }

    function init() {
        var inputs = document.querySelectorAll('input[data-datepicker]');
        for (var i = 0; i < inputs.length; i++) attach(inputs[i]);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
