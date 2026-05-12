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
});

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
