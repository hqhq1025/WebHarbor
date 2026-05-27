// arxiv mirror — client JS

document.addEventListener("DOMContentLoaded", function() {
    // Auto-dismiss flash messages after 5s
    document.querySelectorAll('.flash').forEach(function(el) {
        setTimeout(function() {
            el.style.transition = "opacity 0.4s ease";
            el.style.opacity = "0";
            setTimeout(function() { el.remove(); }, 400);
        }, 5000);
    });
    // Close button on flash
    document.querySelectorAll('.flash .close').forEach(function(btn) {
        btn.addEventListener("click", function() {
            this.parentElement.remove();
        });
    });

    // R3 — collapsible abstract toggle on /abs paper pages.
    document.querySelectorAll('.abs-toggle').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var targetId = btn.getAttribute('data-target');
            var box = document.getElementById(targetId);
            if (!box) return;
            var expanded = box.classList.toggle('expanded');
            btn.textContent = expanded
                ? (btn.getAttribute('data-expanded') || 'Collapse')
                : (btn.getAttribute('data-collapsed') || 'Read more');
        });
    });

    // Fade-in on scroll (only activates if JS is available)
    document.documentElement.classList.add('js-fade-ready');
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(function(e) {
            if (e.isIntersecting) {
                e.target.classList.add('visible');
                observer.unobserve(e.target);
            }
        });
    }, { threshold: 0.01, rootMargin: "0px 0px -5% 0px" });
    document.querySelectorAll('.fade-in').forEach(function(el) { observer.observe(el); });
    // Safety fallback: after a short delay, reveal every fade-in element unconditionally
    // (handles full-page screenshots and any cases where IntersectionObserver misfires)
    setTimeout(function() {
        document.querySelectorAll('.fade-in').forEach(function(el) {
            el.classList.add('visible');
        });
    }, 300);

    initSearchTypeMenus();
});

function initSearchTypeMenus() {
    const menus = Array.from(document.querySelectorAll('[data-searchtype-menu]'));
    if (!menus.length) return;

    function closeMenu(menu) {
        menu.classList.remove('open');
        const trigger = menu.querySelector('[data-searchtype-trigger]');
        if (trigger) trigger.setAttribute('aria-expanded', 'false');
        menu.querySelectorAll('[data-searchtype-option]').forEach(function(option) {
            option.classList.remove('active');
        });
    }

    function openMenu(menu) {
        menus.forEach(function(other) {
            if (other !== menu) closeMenu(other);
        });
        menu.classList.add('open');
        const trigger = menu.querySelector('[data-searchtype-trigger]');
        if (trigger) trigger.setAttribute('aria-expanded', 'true');
    }

    function setValue(menu, option) {
        const input = menu.querySelector('[data-searchtype-input]');
        const label = menu.querySelector('[data-searchtype-label]');
        if (input) input.value = option.dataset.value || 'all';
        if (label) label.textContent = option.textContent.trim();
        menu.querySelectorAll('[data-searchtype-option]').forEach(function(item) {
            const selected = item === option;
            item.classList.toggle('selected', selected);
            item.setAttribute('aria-selected', selected ? 'true' : 'false');
        });
        closeMenu(menu);
        const trigger = menu.querySelector('[data-searchtype-trigger]');
        if (trigger) trigger.focus();
    }

    function focusOption(menu, direction) {
        const options = Array.from(menu.querySelectorAll('[data-searchtype-option]'));
        if (!options.length) return;
        const current = document.activeElement && document.activeElement.matches('[data-searchtype-option]')
            ? options.indexOf(document.activeElement)
            : options.findIndex(function(option) { return option.classList.contains('selected'); });
        let next = current;
        if (direction === 'first') next = 0;
        else if (direction === 'last') next = options.length - 1;
        else next = (current + direction + options.length) % options.length;
        options.forEach(function(option) {
            option.classList.remove('active');
        });
        options[next].classList.add('active');
        options[next].focus();
    }

    menus.forEach(function(menu) {
        const trigger = menu.querySelector('[data-searchtype-trigger]');
        const options = Array.from(menu.querySelectorAll('[data-searchtype-option]'));
        if (!trigger || !options.length) return;

        trigger.addEventListener('click', function() {
            if (menu.classList.contains('open')) closeMenu(menu);
            else openMenu(menu);
        });

        trigger.addEventListener('keydown', function(event) {
            if (event.key === 'ArrowDown') {
                event.preventDefault();
                openMenu(menu);
                focusOption(menu, 1);
            } else if (event.key === 'ArrowUp') {
                event.preventDefault();
                openMenu(menu);
                focusOption(menu, -1);
            } else if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                if (menu.classList.contains('open')) closeMenu(menu);
                else {
                    openMenu(menu);
                    focusOption(menu, 'first');
                }
            } else if (event.key === 'Escape') {
                closeMenu(menu);
            }
        });

        options.forEach(function(option) {
            option.addEventListener('click', function() {
                setValue(menu, option);
            });
            option.addEventListener('keydown', function(event) {
                if (event.key === 'ArrowDown') {
                    event.preventDefault();
                    focusOption(menu, 1);
                } else if (event.key === 'ArrowUp') {
                    event.preventDefault();
                    focusOption(menu, -1);
                } else if (event.key === 'Home') {
                    event.preventDefault();
                    focusOption(menu, 'first');
                } else if (event.key === 'End') {
                    event.preventDefault();
                    focusOption(menu, 'last');
                } else if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    setValue(menu, option);
                } else if (event.key === 'Escape') {
                    closeMenu(menu);
                    trigger.focus();
                }
            });
        });
    });

    document.addEventListener('click', function(event) {
        menus.forEach(function(menu) {
            if (!menu.contains(event.target)) closeMenu(menu);
        });
    });
}

// ---- Library (cart) actions ----
async function addToLibrary(paperId) {
    try {
        const res = await fetch('/api/library/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ paper_id: paperId })
        });
        if (res.status === 401) {
            window.location = '/login';
            return;
        }
        const data = await res.json();
        if (data.success) {
            updateLibraryCount(data.library_count);
            showToast(data.message || 'Added to library');
            // Update button state
            const btn = document.querySelector(`[data-add-paper-id="${paperId}"]`);
            if (btn) {
                btn.textContent = 'In Your Library';
                btn.disabled = true;
            }
        } else {
            showToast(data.message || 'Error', true);
        }
    } catch (e) {
        showToast('Network error', true);
    }
}

async function removeFromLibrary(itemId) {
    if (!confirm('Remove this paper from your library?')) return;
    const res = await fetch('/api/library/remove', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_id: itemId })
    });
    const data = await res.json();
    if (data.success) {
        const row = document.querySelector(`[data-lib-item="${itemId}"]`);
        if (row) row.remove();
        updateLibraryCount(data.library_count);
        showToast('Removed from library');
    }
}

async function toggleStar(paperId) {
    const res = await fetch('/api/star/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paper_id: paperId })
    });
    if (res.status === 401) {
        window.location = '/login';
        return;
    }
    const data = await res.json();
    if (data.success) {
        const btn = document.querySelector(`[data-star-paper-id="${paperId}"]`);
        if (btn) {
            if (data.action === 'added') {
                btn.classList.add('starred');
                btn.textContent = '★ Starred';
            } else {
                btn.classList.remove('starred');
                btn.textContent = '☆ Star';
            }
        }
        showToast(data.action === 'added' ? 'Starred' : 'Unstarred');
    }
}

function updateLibraryCount(n) {
    const el = document.getElementById('library-count');
    if (el) el.textContent = n;
}

function showToast(msg, error=false) {
    const toast = document.createElement('div');
    toast.className = 'flash ' + (error ? 'flash-error' : 'flash-success');
    toast.style.cssText = 'position:fixed;top:70px;right:20px;z-index:9999;min-width:220px;max-width:360px;box-shadow:0 2px 8px rgba(0,0,0,0.15);';
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(function() {
        toast.style.transition = 'opacity 0.4s';
        toast.style.opacity = '0';
        setTimeout(function() { toast.remove(); }, 400);
    }, 3000);
}

// Star rating widget
function setRating(n) {
    document.querySelectorAll('.star-rate').forEach(function(s, i) {
        s.classList.toggle('active', i < n);
        s.textContent = i < n ? '★' : '☆';
    });
    const input = document.getElementById('rating-input');
    if (input) input.value = n;
}

// =====================================================================
// R5 — version-history modal, dyslexia-friendly font toggle.
// =====================================================================

(function () {
    "use strict";

    // ---- Version history modal ---------------------------------------
    function setupVersionModal() {
        var modal = document.getElementById("version-history-modal");
        if (!modal) return;
        var openers = document.querySelectorAll("[data-version-modal-open]");
        var closer = modal.querySelector("[data-version-modal-close]");
        var previouslyFocused = null;

        function open(e) {
            if (e) e.preventDefault();
            previouslyFocused = document.activeElement;
            modal.hidden = false;
            document.body.style.overflow = "hidden";
            if (closer) closer.focus();
        }
        function close() {
            modal.hidden = true;
            document.body.style.overflow = "";
            if (previouslyFocused && previouslyFocused.focus) {
                previouslyFocused.focus();
            }
        }

        openers.forEach(function (btn) { btn.addEventListener("click", open); });
        if (closer) closer.addEventListener("click", close);
        modal.addEventListener("click", function (ev) {
            if (ev.target === modal) close();
        });
        document.addEventListener("keydown", function (ev) {
            if (!modal.hidden && ev.key === "Escape") close();
        });
    }

    // ---- Dyslexia-friendly font toggle --------------------------------
    function setupDyslexiaToggle() {
        var btn = document.getElementById("a11y-dyslexia-toggle");
        if (!btn) return;
        var STORAGE_KEY = "arxiv_a11y_dyslexia";
        function apply(on) {
            document.body.classList.toggle("dyslexia-friendly", on);
            btn.setAttribute("aria-pressed", on ? "true" : "false");
        }
        var stored = null;
        try { stored = window.localStorage.getItem(STORAGE_KEY); } catch (e) {}
        apply(stored === "1");
        btn.addEventListener("click", function () {
            var on = !document.body.classList.contains("dyslexia-friendly");
            apply(on);
            try { window.localStorage.setItem(STORAGE_KEY, on ? "1" : "0"); } catch (e) {}
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () {
            setupVersionModal();
            setupDyslexiaToggle();
        });
    } else {
        setupVersionModal();
        setupDyslexiaToggle();
    }
})();


/* =====================================================================
 * R8 — keyboard shortcuts (j/k listing nav, ? help, Ctrl/Cmd+K palette,
 * e to toggle abstract collapse, g-prefix go-to actions).
 *
 * No external state required; all targets are looked up by data
 * attributes injected by the server templates:
 *   - data-kbd-nav        — a UL/OL whose <li> rows are individual papers
 *   - data-kbd-nav-link   — the primary <a href="/abs/..."> inside each row
 *   - data-kbd-current    — applied to the row currently focused by j/k
 * ===================================================================*/
(function () {
    function isTypingInForm(ev) {
        var t = ev.target;
        if (!t) return false;
        var tag = (t.tagName || "").toUpperCase();
        if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
        if (t.isContentEditable) return true;
        return false;
    }

    // --------------------- j/k paper navigation ----------------------
    function findNavList() {
        return document.querySelector("[data-kbd-nav]");
    }

    function getRows(list) {
        return Array.from(list.querySelectorAll("[data-kbd-nav-row]"));
    }

    function moveCursor(delta) {
        var list = findNavList();
        if (!list) return false;
        var rows = getRows(list);
        if (!rows.length) return false;
        var idx = rows.findIndex(function (r) {
            return r.hasAttribute("data-kbd-current");
        });
        var next = idx + delta;
        if (idx === -1) next = delta > 0 ? 0 : rows.length - 1;
        if (next < 0) next = 0;
        if (next >= rows.length) next = rows.length - 1;
        rows.forEach(function (r) { r.removeAttribute("data-kbd-current"); });
        var target = rows[next];
        target.setAttribute("data-kbd-current", "");
        target.scrollIntoView({ block: "center", behavior: "smooth" });
        // Visually outline the row.
        target.style.outline = "2px solid #b31b1b";
        target.style.outlineOffset = "2px";
        rows.forEach(function (r) {
            if (r !== target) { r.style.outline = ""; r.style.outlineOffset = ""; }
        });
        return true;
    }

    function openCurrentRow() {
        var list = findNavList();
        if (!list) return false;
        var row = list.querySelector("[data-kbd-current]");
        if (!row) return false;
        var link = row.querySelector("[data-kbd-nav-link]") || row.querySelector("a[href]");
        if (link) { window.location.href = link.href; return true; }
        return false;
    }

    // --------------------- help panel (?) ----------------------------
    function ensureHelpPanel() {
        var existing = document.getElementById("kbd-help-panel");
        if (existing) return existing;
        var div = document.createElement("div");
        div.id = "kbd-help-panel";
        div.setAttribute("role", "dialog");
        div.setAttribute("aria-label", "Keyboard shortcuts");
        div.style.cssText = [
            "position:fixed", "right:24px", "bottom:24px",
            "background:#fff", "color:#222",
            "border:1px solid #b31b1b", "border-radius:6px",
            "padding:16px 20px", "max-width:360px",
            "box-shadow:0 4px 20px rgba(0,0,0,0.2)",
            "font-size:13px", "line-height:1.5",
            "z-index:9999", "display:none"
        ].join(";");
        div.innerHTML = [
            "<h3 style=\"margin:0 0 8px;font-size:14px;color:#b31b1b\">Keyboard shortcuts</h3>",
            "<table style=\"width:100%;border-collapse:collapse\">",
            "<tr><td><kbd>j</kbd></td><td>Next paper</td></tr>",
            "<tr><td><kbd>k</kbd></td><td>Previous paper</td></tr>",
            "<tr><td><kbd>Enter</kbd></td><td>Open selected paper</td></tr>",
            "<tr><td><kbd>e</kbd></td><td>Toggle abstract</td></tr>",
            "<tr><td><kbd>?</kbd></td><td>Toggle this help</td></tr>",
            "<tr><td><kbd>Ctrl</kbd>+<kbd>K</kbd></td><td>Open command palette</td></tr>",
            "<tr><td><kbd>g</kbd> <kbd>h</kbd></td><td>Go to homepage</td></tr>",
            "<tr><td><kbd>g</kbd> <kbd>l</kbd></td><td>Go to library</td></tr>",
            "<tr><td><kbd>g</kbd> <kbd>s</kbd></td><td>Go to advanced search</td></tr>",
            "<tr><td><kbd>Esc</kbd></td><td>Close dialogs</td></tr>",
            "</table>",
            "<p style=\"margin:10px 0 0;font-size:11px;color:#666\">Full list at <a href=\"/help/keyboard\">/help/keyboard</a>.</p>"
        ].join("");
        document.body.appendChild(div);
        return div;
    }

    function toggleHelpPanel(force) {
        var panel = ensureHelpPanel();
        var show = (typeof force === "boolean") ? force
            : panel.style.display === "none";
        panel.style.display = show ? "block" : "none";
    }

    // --------------------- command palette ---------------------------
    function ensurePalette() {
        var existing = document.getElementById("kbd-palette");
        if (existing) return existing;
        var wrap = document.createElement("div");
        wrap.id = "kbd-palette";
        wrap.setAttribute("role", "dialog");
        wrap.setAttribute("aria-label", "Command palette");
        wrap.style.cssText = [
            "position:fixed", "top:120px", "left:50%",
            "transform:translateX(-50%)",
            "background:#fff", "color:#222",
            "border:1px solid #b31b1b", "border-radius:6px",
            "padding:16px 18px", "width:min(480px, 92vw)",
            "box-shadow:0 4px 24px rgba(0,0,0,0.25)",
            "z-index:9999", "display:none"
        ].join(";");
        wrap.innerHTML = [
            "<label for=\"kbd-palette-input\" style=\"font-weight:600;font-size:12px;color:#b31b1b\">",
            "Jump to /abs/&lt;arxiv-id&gt;</label>",
            "<input id=\"kbd-palette-input\" type=\"text\" autocomplete=\"off\" ",
            "placeholder=\"e.g. 2401.12345\" style=\"width:100%;padding:8px 10px;",
            "font-size:14px;border:1px solid #aaa;border-radius:4px;margin-top:6px\">",
            "<p id=\"kbd-palette-hint\" style=\"margin:8px 0 0;font-size:11px;color:#666\">",
            "Press Enter to navigate, Esc to close.</p>"
        ].join("");
        document.body.appendChild(wrap);
        var input = wrap.querySelector("#kbd-palette-input");
        input.addEventListener("keydown", function (ev) {
            if (ev.key === "Enter") {
                ev.preventDefault();
                var val = (input.value || "").trim();
                if (!val) return;
                // Accept full URL, "arXiv:2401.12345", or bare id.
                val = val.replace(/^arxiv:/i, "")
                         .replace(/^https?:\/\/[^/]+\/abs\//i, "");
                window.location.href = "/abs/" + encodeURIComponent(val);
            } else if (ev.key === "Escape") {
                togglePalette(false);
            }
        });
        return wrap;
    }

    function togglePalette(force) {
        var pal = ensurePalette();
        var show = (typeof force === "boolean") ? force
            : pal.style.display === "none";
        pal.style.display = show ? "block" : "none";
        if (show) {
            var inp = pal.querySelector("#kbd-palette-input");
            if (inp) { inp.value = ""; inp.focus(); }
        }
    }

    // --------------------- abstract collapse (e) ---------------------
    function toggleAbstract() {
        var btn = document.querySelector(".abs-toggle");
        if (!btn) return false;
        btn.click();
        return true;
    }

    // --------------------- focus search (/) --------------------------
    function focusSearch() {
        var input = document.querySelector(".header-search input[name=query]");
        if (input) { input.focus(); input.select && input.select(); return true; }
        return false;
    }

    // --------------------- main listener -----------------------------
    var pendingPrefix = null;       // "g" prefix state
    var pendingPrefixTimer = null;

    function clearPrefix() {
        pendingPrefix = null;
        if (pendingPrefixTimer) {
            window.clearTimeout(pendingPrefixTimer);
            pendingPrefixTimer = null;
        }
    }

    function setPrefix(key) {
        pendingPrefix = key;
        if (pendingPrefixTimer) window.clearTimeout(pendingPrefixTimer);
        pendingPrefixTimer = window.setTimeout(clearPrefix, 1200);
    }

    document.addEventListener("keydown", function (ev) {
        // Command palette is allowed even while typing — match VS Code.
        if ((ev.ctrlKey || ev.metaKey) && (ev.key === "k" || ev.key === "K")) {
            ev.preventDefault();
            togglePalette();
            return;
        }
        if (isTypingInForm(ev)) return;
        if (ev.altKey || ev.ctrlKey || ev.metaKey) return;

        // Two-key prefix (g h/l/s).
        if (pendingPrefix === "g") {
            if (ev.key === "h") { window.location.href = "/"; clearPrefix(); return; }
            if (ev.key === "l") { window.location.href = "/library"; clearPrefix(); return; }
            if (ev.key === "s") { window.location.href = "/search/advanced"; clearPrefix(); return; }
            clearPrefix();
        }

        switch (ev.key) {
            case "j":
                if (moveCursor(1)) ev.preventDefault();
                break;
            case "k":
                if (moveCursor(-1)) ev.preventDefault();
                break;
            case "Enter":
                if (openCurrentRow()) ev.preventDefault();
                break;
            case "?":
                toggleHelpPanel();
                ev.preventDefault();
                break;
            case "e":
                if (toggleAbstract()) ev.preventDefault();
                break;
            case "/":
                if (focusSearch()) ev.preventDefault();
                break;
            case "g":
                setPrefix("g");
                break;
            case "Escape":
                toggleHelpPanel(false);
                togglePalette(false);
                break;
            default:
                break;
        }
    });

    // ---- Contextual help (hover) ------------------------------------
    // Any element with [data-help-topic="<key>"] gets a lazy-fetched
    // tooltip from /api/help/<key>.
    var helpCache = {};
    function showTooltip(el, text) {
        var tip = document.createElement("span");
        tip.className = "ctx-help-tip";
        tip.textContent = text;
        tip.style.cssText = [
            "position:absolute", "background:#222", "color:#fff",
            "padding:6px 10px", "border-radius:4px",
            "font-size:11px", "line-height:1.4",
            "max-width:280px", "z-index:9998",
            "pointer-events:none", "box-shadow:0 2px 6px rgba(0,0,0,0.3)"
        ].join(";");
        document.body.appendChild(tip);
        var rect = el.getBoundingClientRect();
        tip.style.left = (window.scrollX + rect.left) + "px";
        tip.style.top = (window.scrollY + rect.bottom + 6) + "px";
        el._ctxHelpTip = tip;
    }
    function hideTooltip(el) {
        if (el._ctxHelpTip) {
            el._ctxHelpTip.remove();
            el._ctxHelpTip = null;
        }
    }
    document.addEventListener("mouseover", function (ev) {
        var el = ev.target.closest && ev.target.closest("[data-help-topic]");
        if (!el || el._ctxHelpTip) return;
        var topic = el.getAttribute("data-help-topic");
        if (!topic) return;
        if (helpCache[topic] !== undefined) {
            if (helpCache[topic]) showTooltip(el, helpCache[topic]);
            return;
        }
        fetch("/api/help/" + encodeURIComponent(topic), { credentials: "same-origin" })
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (data) {
                helpCache[topic] = data && data.body ? data.body : "";
                if (helpCache[topic] && el.matches(":hover")) {
                    showTooltip(el, helpCache[topic]);
                }
            })
            .catch(function () { helpCache[topic] = ""; });
    });
    document.addEventListener("mouseout", function (ev) {
        var el = ev.target.closest && ev.target.closest("[data-help-topic]");
        if (el) hideTooltip(el);
    });
})();
