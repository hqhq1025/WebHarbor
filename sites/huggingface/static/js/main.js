// Hugging Face Mirror — client-side interactivity
(function () {
    "use strict";

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || "";

    function postJSON(url, data) {
        return fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken,
            },
            body: JSON.stringify(data || {}),
        }).then((r) => r.json());
    }
    window.postJSON = postJSON;

    // Toast notification
    function showToast(msg, kind) {
        const t = document.createElement("div");
        t.className = "toast toast-" + (kind || "info");
        t.textContent = msg;
        t.style.cssText =
            "position:fixed;bottom:24px;right:24px;background:#1e293b;color:#fff;padding:14px 20px;border-radius:10px;box-shadow:0 6px 24px rgba(0,0,0,.25);z-index:10000;font-size:14px;animation:slidein .3s;";
        document.body.appendChild(t);
        setTimeout(() => {
            t.style.opacity = "0";
            t.style.transition = "opacity .3s";
            setTimeout(() => t.remove(), 300);
        }, 2600);
    }
    window.showToast = showToast;

    // Like toggle
    document.addEventListener("click", function (e) {
        const likeBtn = e.target.closest("[data-like-toggle]");
        if (likeBtn) {
            e.preventDefault();
            const repoId = likeBtn.getAttribute("data-repo-id");
            postJSON("/api/like/toggle", { repo_id: repoId })
                .then((data) => {
                    if (data.error) {
                        showToast("Please log in to like.", "error");
                        return;
                    }
                    likeBtn.classList.toggle("is-liked", data.liked);
                    const countEl = likeBtn.querySelector("[data-like-count]");
                    if (countEl) countEl.textContent = data.likes_count;
                    showToast(data.liked ? "Added to your likes" : "Removed from likes");
                });
            return;
        }

        const followBtn = e.target.closest("[data-follow-toggle]");
        if (followBtn) {
            e.preventDefault();
            const authorId = followBtn.getAttribute("data-author-id");
            postJSON("/api/follow/toggle", { author_id: authorId })
                .then((data) => {
                    if (data.error) {
                        showToast("Please log in to follow.", "error");
                        return;
                    }
                    followBtn.textContent = data.following ? "Following" : "Follow";
                    followBtn.classList.toggle("is-following", data.following);
                    showToast(data.following ? "Following" : "Unfollowed");
                });
            return;
        }

        const deployBtn = e.target.closest("[data-deploy-add]");
        if (deployBtn) {
            e.preventDefault();
            const repoId = deployBtn.getAttribute("data-repo-id");
            const hw = deployBtn.getAttribute("data-hardware") || "t4-small";
            postJSON("/api/deploy/add", { repo_id: repoId, hardware_slug: hw, hours: 24 })
                .then((data) => {
                    if (data.error) {
                        showToast("Please log in to deploy.", "error");
                        return;
                    }
                    const badge = document.querySelector(".gn-cart-badge");
                    if (badge) badge.textContent = data.cart_count;
                    showToast(data.message || "Added to deployment cart");
                });
            return;
        }

        const upvoteBtn = e.target.closest("[data-upvote]");
        if (upvoteBtn) {
            e.preventDefault();
            const dId = upvoteBtn.getAttribute("data-discussion-id");
            postJSON("/discussions/" + dId + "/upvote", {}).then((data) => {
                if (data.upvotes !== undefined) {
                    const countEl = upvoteBtn.querySelector("[data-upvote-count]");
                    if (countEl) countEl.textContent = data.upvotes;
                }
            });
            return;
        }
    });

    // Cart update/remove
    document.addEventListener("change", function (e) {
        const hoursInput = e.target.closest("[data-cart-hours]");
        if (hoursInput) {
            const itemId = hoursInput.getAttribute("data-item-id");
            postJSON("/api/deploy/update", { item_id: itemId, hours: parseInt(hoursInput.value, 10) || 1 })
                .then(() => location.reload());
        }
    });

    document.addEventListener("click", function (e) {
        const rm = e.target.closest("[data-cart-remove]");
        if (rm) {
            e.preventDefault();
            const itemId = rm.getAttribute("data-item-id");
            postJSON("/api/deploy/remove", { item_id: itemId }).then(() => location.reload());
        }
    });

    // Scroll fade-in
    const io = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = "1";
                    entry.target.style.transform = "translateY(0)";
                    io.unobserve(entry.target);
                }
            });
        },
        { threshold: 0.1 }
    );
    document.querySelectorAll(".fade-in").forEach((el) => {
        el.style.opacity = "0";
        el.style.transform = "translateY(20px)";
        el.style.transition = "opacity .6s, transform .6s";
        io.observe(el);
    });
})();

/* R3: code copy buttons — auto-attach to <pre> blocks inside .repo-readme, .docs, etc. */
(function() {
    function attachCopy(pre) {
        if (pre.dataset.copyAttached) return;
        var wrap = document.createElement('div');
        wrap.className = 'code-copy-wrap';
        pre.parentNode.insertBefore(wrap, pre);
        wrap.appendChild(pre);
        var btn = document.createElement('button');
        btn.className = 'code-copy-btn';
        btn.type = 'button';
        btn.textContent = 'Copy';
        btn.addEventListener('click', function() {
            var text = pre.innerText;
            try {
                navigator.clipboard.writeText(text).then(function() {
                    btn.textContent = 'Copied!';
                    btn.classList.add('copied');
                    setTimeout(function() {
                        btn.textContent = 'Copy';
                        btn.classList.remove('copied');
                    }, 1400);
                });
            } catch (e) {
                /* fallback for older browsers */
                var ta = document.createElement('textarea');
                ta.value = text;
                document.body.appendChild(ta);
                ta.select();
                try { document.execCommand('copy'); } catch (_) {}
                document.body.removeChild(ta);
                btn.textContent = 'Copied!';
                btn.classList.add('copied');
                setTimeout(function() { btn.textContent = 'Copy'; btn.classList.remove('copied'); }, 1400);
            }
        });
        wrap.appendChild(btn);
        pre.dataset.copyAttached = '1';
    }
    function init() {
        document.querySelectorAll('.repo-readme pre, .docs-body pre, .blog-body pre, .doc-content pre').forEach(attachCopy);
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

/* R8: keyboard shortcuts + Cmd+K command palette + j/k card nav. */
(function() {
    "use strict";

    function isEditable(el) {
        if (!el) return false;
        var t = (el.tagName || "").toLowerCase();
        if (t === "input" || t === "textarea" || t === "select") return true;
        if (el.isContentEditable) return true;
        return false;
    }

    var cmdkRoot = document.getElementById('r8-cmdk');
    var cmdkInput = document.getElementById('r8-cmdk-input');
    var cmdkList = document.getElementById('r8-cmdk-list');
    var helpRoot = document.getElementById('r8-help');
    var helpClose = document.getElementById('r8-help-close');

    function openCmdK() {
        if (!cmdkRoot) return;
        cmdkRoot.hidden = false;
        if (cmdkInput) {
            cmdkInput.value = '';
            cmdkInput.focus();
        }
        loadPalette('');
    }
    function closeCmdK() { if (cmdkRoot) cmdkRoot.hidden = true; }
    function toggleHelp() { if (helpRoot) helpRoot.hidden = !helpRoot.hidden; }
    function closeHelp() { if (helpRoot) helpRoot.hidden = true; }

    var paletteItems = [];
    var paletteCursor = 0;

    function renderPalette() {
        if (!cmdkList) return;
        cmdkList.innerHTML = '';
        paletteItems.forEach(function(it, i) {
            var li = document.createElement('li');
            li.setAttribute('role', 'option');
            li.dataset.url = it.url;
            li.style.cssText = 'padding:10px 18px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;gap:12px;font-size:14px;' + (i === paletteCursor ? 'background:#eef2ff;' : '');
            li.innerHTML = '<span><strong style="font-weight:500;color:#111827;">' + it.label.replace(/[<>]/g, '') + '</strong>' +
                (it.kind && it.kind !== 'page' ? ' <span style="color:#6b7280;font-size:12px;">· ' + it.kind + '</span>' : '') +
                '</span><span style="font-family:ui-monospace,Menlo,monospace;color:#6b7280;font-size:12px;">' + (it.url || '') + '</span>';
            li.addEventListener('mouseenter', function() {
                paletteCursor = i;
                renderPalette();
            });
            li.addEventListener('click', function() {
                if (it.url) location.href = it.url;
            });
            cmdkList.appendChild(li);
        });
    }

    function loadPalette(q) {
        fetch('/api/command-palette?q=' + encodeURIComponent(q || ''), { credentials: 'same-origin' })
            .then(function(r) { return r.json(); })
            .then(function(d) {
                paletteItems = (d && d.items) || [];
                paletteCursor = 0;
                renderPalette();
            })
            .catch(function() { paletteItems = []; renderPalette(); });
    }

    if (cmdkInput) {
        var debounceTimer = null;
        cmdkInput.addEventListener('input', function() {
            clearTimeout(debounceTimer);
            var q = cmdkInput.value;
            debounceTimer = setTimeout(function() { loadPalette(q); }, 120);
        });
        cmdkInput.addEventListener('keydown', function(e) {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                paletteCursor = Math.min(paletteItems.length - 1, paletteCursor + 1);
                renderPalette();
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                paletteCursor = Math.max(0, paletteCursor - 1);
                renderPalette();
            } else if (e.key === 'Enter') {
                e.preventDefault();
                var it = paletteItems[paletteCursor];
                if (it && it.url) location.href = it.url;
            } else if (e.key === 'Escape') {
                closeCmdK();
            }
        });
    }
    if (cmdkRoot) {
        cmdkRoot.addEventListener('click', function(e) {
            if (e.target === cmdkRoot) closeCmdK();
        });
    }
    if (helpRoot) {
        helpRoot.addEventListener('click', function(e) {
            if (e.target === helpRoot) closeHelp();
        });
    }
    if (helpClose) helpClose.addEventListener('click', closeHelp);

    /* j/k card navigation — applies to any list page that exposes .repo-card or .card-grid > .card. */
    function listableCards() {
        var sel = '[data-repo-card], .repo-card, .repo-list .card, .repo-list li[data-repo-slug]';
        return Array.prototype.slice.call(document.querySelectorAll(sel));
    }
    var navCursor = -1;
    function setNavCursor(idx) {
        var cards = listableCards();
        if (!cards.length) return;
        if (idx < 0) idx = 0;
        if (idx >= cards.length) idx = cards.length - 1;
        cards.forEach(function(c) { c.classList.remove('r8-keynav-active'); c.style.outline = ''; });
        navCursor = idx;
        var el = cards[navCursor];
        el.classList.add('r8-keynav-active');
        el.style.outline = '2px solid #3b82f6';
        el.style.outlineOffset = '4px';
        el.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }
    function openNavCursor() {
        var cards = listableCards();
        if (navCursor < 0 || navCursor >= cards.length) return;
        var el = cards[navCursor];
        var a = el.querySelector('a[href]');
        if (a) location.href = a.href;
    }

    /* g-then-X chord support */
    var gPending = false;
    var gTimer = null;
    function clearG() { gPending = false; if (gTimer) { clearTimeout(gTimer); gTimer = null; } }

    document.addEventListener('keydown', function(e) {
        if (e.defaultPrevented) return;
        if (isEditable(document.activeElement) && document.activeElement !== cmdkInput) {
            // Allow Cmd/Ctrl+K even from an input
            if ((e.key === 'k' || e.key === 'K') && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                openCmdK();
            }
            return;
        }
        if ((e.key === 'k' || e.key === 'K') && (e.metaKey || e.ctrlKey)) {
            e.preventDefault();
            openCmdK();
            return;
        }
        if (e.key === 'Escape') {
            if (cmdkRoot && !cmdkRoot.hidden) { closeCmdK(); return; }
            if (helpRoot && !helpRoot.hidden) { closeHelp(); return; }
            clearG();
        }
        if (cmdkRoot && !cmdkRoot.hidden) return;
        if (helpRoot && !helpRoot.hidden) return;
        if (e.key === '?' || (e.key === '/' && e.shiftKey)) {
            e.preventDefault();
            toggleHelp();
            return;
        }
        if (e.key === '/') {
            var search = document.querySelector('.gn-search input[name="q"]');
            if (search) {
                e.preventDefault();
                search.focus();
                search.select();
                return;
            }
        }
        if (e.key === 'j' || e.key === 'J') {
            e.preventDefault();
            setNavCursor(navCursor < 0 ? 0 : navCursor + 1);
            return;
        }
        if (e.key === 'k' || e.key === 'K') {
            e.preventDefault();
            setNavCursor(navCursor < 0 ? 0 : navCursor - 1);
            return;
        }
        if (e.key === 'Enter' && navCursor >= 0) {
            openNavCursor();
            return;
        }
        if (e.key === 'g' || e.key === 'G') {
            gPending = true;
            if (gTimer) clearTimeout(gTimer);
            gTimer = setTimeout(clearG, 800);
            return;
        }
        if (gPending) {
            if (e.key === 'm' || e.key === 'M') { e.preventDefault(); location.href = '/models'; clearG(); return; }
            if (e.key === 'd' || e.key === 'D') { e.preventDefault(); location.href = '/datasets'; clearG(); return; }
            if (e.key === 's' || e.key === 'S') { e.preventDefault(); location.href = '/spaces'; clearG(); return; }
            if (e.key === 'h' || e.key === 'H') { e.preventDefault(); location.href = '/'; clearG(); return; }
            if (e.key === 'p' || e.key === 'P') { e.preventDefault(); location.href = '/papers'; clearG(); return; }
            clearG();
        }
    });

    /* Pipeline-tag tooltip — annotate any element that carries data-pipeline-tag */
    var PIPELINE_TAG_TOOLTIPS = {
        'text-generation': 'Autoregressive language modeling — predicts next token.',
        'text-to-image': 'Image diffusion conditioned on a text caption.',
        'automatic-speech-recognition': 'Speech-to-text transcription.',
        'text-to-speech': 'Synthesizes speech from input text.',
        'image-classification': 'Single label per image from a fixed taxonomy.',
        'object-detection': 'Bounding boxes + class labels.',
        'image-segmentation': 'Per-pixel class labels.',
        'depth-estimation': 'Per-pixel depth from a monocular RGB image.',
        'translation': 'Maps a sentence from one language to another.',
        'summarization': 'Condenses documents into short summaries.',
        'feature-extraction': 'Fixed-size embeddings for retrieval / similarity.',
        'token-classification': 'Per-token labels — NER, POS tagging, chunking.',
        'text-classification': 'One label per sentence — sentiment, intent, topic.',
        'question-answering': 'Answers a question against a context passage.',
        'zero-shot-classification': 'Arbitrary labels without task-specific training.',
        'image-text-to-text': 'Multimodal — image + text → text.',
        'text-to-video': 'Synthesizes video clips from text prompts.',
        'image-to-video': 'Animates a still image into a clip.',
        'text-to-3d': 'Generates 3D mesh / NeRF from text.',
        'image-to-3d': 'Lifts a single image into a 3D mesh.',
        'reinforcement-learning': 'Agents that learn from environmental rewards.',
        'fill-mask': 'Predicts missing tokens in a masked sentence.',
        'sentence-similarity': 'Scores semantic similarity between two texts.',
        'audio-classification': 'Sound-event / speaker / genre classification.',
        'audio-to-audio': 'Audio enhancement / separation / voice conversion.',
        'table-question-answering': 'QA grounded in a tabular schema.',
        'text-ranking': 'Reranks candidate passages by relevance.',
        'tabular-classification': 'Classifies rows of structured tabular data.',
        'tabular-regression': 'Predicts continuous targets from tabular features.'
    };
    function attachTagTooltips() {
        document.querySelectorAll('[data-pipeline-tag]').forEach(function(el) {
            var tag = el.getAttribute('data-pipeline-tag') || '';
            var def = PIPELINE_TAG_TOOLTIPS[tag];
            if (def && !el.title) el.title = tag + ' — ' + def;
        });
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', attachTagTooltips);
    } else {
        attachTagTooltips();
    }
})();
