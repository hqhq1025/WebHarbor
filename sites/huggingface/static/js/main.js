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
