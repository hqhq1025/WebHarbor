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

// Amazon mirror - client-side behaviors

// CSRF helper
function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

// R5: AJAX search suggest dropdown.
// Activates on the header search box; uses /api/search/suggest.
// Supports keyboard navigation (ArrowDown / ArrowUp / Enter / Escape).
function initSearchSuggest() {
    const input = document.getElementById('nav-search-input');
    const list = document.getElementById('nav-search-suggest');
    if (!input || !list) return;

    let activeIdx = -1;
    let lastQ = '';
    let inflightAbort = null;
    let debounceTimer = null;

    function closeList() {
        list.hidden = true;
        list.innerHTML = '';
        input.setAttribute('aria-expanded', 'false');
        activeIdx = -1;
    }
    function render(items) {
        if (!items.length) { closeList(); return; }
        list.innerHTML = items.map((it, i) =>
            '<li role="option" data-href="' + it.href + '" id="suggest-opt-' + i + '"' +
            ' class="nav-search-suggest-item">' +
            '<span class="suggest-kind">' + (it.kind === 'category' ? 'in ' : '') + '</span>' +
            '<span class="suggest-text">' + escapeHtml(it.text) + '</span>' +
            '</li>'
        ).join('');
        list.hidden = false;
        input.setAttribute('aria-expanded', 'true');
        // Click handlers
        list.querySelectorAll('li').forEach((li, i) => {
            li.addEventListener('mousedown', (e) => {
                e.preventDefault();
                window.location.href = li.getAttribute('data-href');
            });
            li.addEventListener('mouseenter', () => setActive(i));
        });
    }
    function setActive(i) {
        const items = list.querySelectorAll('li');
        items.forEach(el => el.classList.remove('active'));
        activeIdx = i;
        if (i >= 0 && items[i]) {
            items[i].classList.add('active');
            input.setAttribute('aria-activedescendant', items[i].id);
        } else {
            input.removeAttribute('aria-activedescendant');
        }
    }
    function escapeHtml(s) {
        return String(s).replace(/[&<>"']/g, c => ({
            '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'
        })[c]);
    }
    function fetchSuggest(q) {
        if (inflightAbort) inflightAbort.abort();
        inflightAbort = new AbortController();
        fetch('/api/search/suggest?q=' + encodeURIComponent(q),
              {signal: inflightAbort.signal, credentials: 'same-origin'})
            .then(r => r.json())
            .then(d => {
                if (q !== lastQ) return;
                render(d.suggestions || []);
            })
            .catch(() => {});
    }

    input.addEventListener('input', () => {
        const q = input.value.trim();
        lastQ = q;
        if (debounceTimer) clearTimeout(debounceTimer);
        if (q.length < 2) { closeList(); return; }
        debounceTimer = setTimeout(() => fetchSuggest(q), 120);
    });
    input.addEventListener('keydown', (e) => {
        const items = list.querySelectorAll('li');
        if (list.hidden || !items.length) return;
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            setActive((activeIdx + 1) % items.length);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            setActive(activeIdx <= 0 ? items.length - 1 : activeIdx - 1);
        } else if (e.key === 'Enter') {
            if (activeIdx >= 0 && items[activeIdx]) {
                e.preventDefault();
                window.location.href = items[activeIdx].getAttribute('data-href');
            }
        } else if (e.key === 'Escape') {
            closeList();
        }
    });
    document.addEventListener('click', (e) => {
        if (!list.contains(e.target) && e.target !== input) closeList();
    });
}

// Auto-dismiss flash messages
document.addEventListener('DOMContentLoaded', () => {
    initSearchSuggest();
    document.querySelectorAll('.flash-msg').forEach(msg => {
        setTimeout(() => {
            msg.style.transition = 'opacity 0.4s';
            msg.style.opacity = '0';
            setTimeout(() => msg.remove(), 400);
        }, 4500);
    });

    // Close button for flash messages
    document.querySelectorAll('.flash-msg .close-btn').forEach(btn => {
        btn.addEventListener('click', () => btn.closest('.flash-msg').remove());
    });

    // Product detail thumb switch
    document.querySelectorAll('.pd-thumb').forEach(thumb => {
        thumb.addEventListener('click', () => {
            const mainImg = document.querySelector('.pd-main-image img');
            const img = thumb.querySelector('img');
            if (mainImg && img) {
                mainImg.src = img.src;
                document.querySelectorAll('.pd-thumb').forEach(t => t.classList.remove('active'));
                thumb.classList.add('active');
            }
        });
    });

    // Variant option selection
    document.querySelectorAll('.pd-variant-group').forEach(group => {
        const options = group.querySelectorAll('.pd-variant-option');
        options.forEach(opt => {
            opt.addEventListener('click', () => {
                options.forEach(o => o.classList.remove('active'));
                opt.classList.add('active');
            });
        });
    });

    // Search form — empty submit is allowed and lands on /s (mirrors real
    // amazon.com behavior of returning a generic browse page). Previous
    // preventDefault made the magnifier button look "dead" to click audits
    // when the input was empty, since no nav/dom-mutation fired.
    const searchForm = document.querySelector('.nav-search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', (e) => {
            const input = searchForm.querySelector('input[name="k"]');
            if (input && !input.value.trim()) {
                // Hint to backend this was an empty submit; /s still renders.
                input.value = '';
            }
        });
    }

    // Scroll to top button
    const scrollBtn = document.querySelector('.footer-back-top');
    if (scrollBtn) {
        scrollBtn.addEventListener('click', () => {
            window.scrollTo({top: 0, behavior: 'smooth'});
        });
    }

    // Scroll animations for gallery
    const observer = new IntersectionObserver(entries => {
        entries.forEach(e => {
            if (e.isIntersecting) {
                e.target.style.opacity = '1';
                e.target.style.transform = 'translateY(0)';
            }
        });
    }, {threshold: 0.1});

    document.querySelectorAll('.pd-gallery-section').forEach(section => {
        section.style.opacity = '0';
        section.style.transform = 'translateY(20px)';
        section.style.transition = 'opacity 0.6s, transform 0.6s';
        observer.observe(section);
    });
});

// Add to bag
function addToBag(productId, variant = '') {
    const selectedVariants = {};
    document.querySelectorAll('.pd-variant-group').forEach(group => {
        const label = group.querySelector('.pd-variant-label').textContent.replace(':', '').trim();
        const active = group.querySelector('.pd-variant-option.active');
        if (active) selectedVariants[label] = active.textContent.trim();
    });

    const variantStr = Object.entries(selectedVariants).map(([k, v]) => `${k}:${v}`).join(', ');

    fetch('/api/cart/add', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        credentials: 'same-origin',
        body: JSON.stringify({
            product_id: productId,
            quantity: parseInt(document.getElementById('pd-qty')?.value || 1),
            variant: variantStr
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            updateCartCount(data.cart_count);
            showToast(data.message);
        } else if (data.redirect) {
            window.location.href = data.redirect;
        } else {
            showToast(data.error || 'Error adding to cart', 'error');
        }
    })
    .catch(err => showToast('Error adding to cart', 'error'));
}

// Quick add (from product cards)
function quickAddToBag(productId) {
    fetch('/api/cart/add', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        credentials: 'same-origin',
        body: JSON.stringify({product_id: productId, quantity: 1})
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            updateCartCount(data.cart_count);
            showToast(data.message);
        } else if (data.redirect) {
            window.location.href = data.redirect;
        } else {
            showToast(data.error || 'Error', 'error');
        }
    });
}

// Buy now - add then redirect to checkout
function buyNow(productId) {
    fetch('/api/cart/add', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        credentials: 'same-origin',
        body: JSON.stringify({product_id: productId, quantity: 1})
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            window.location.href = '/checkout';
        } else if (data.redirect) {
            window.location.href = data.redirect;
        }
    });
}

// Cart updates
function updateCartItem(itemId, quantity) {
    fetch('/api/cart/update', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({item_id: itemId, quantity: quantity})
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            updateCartCount(data.cart_count);
            if (quantity <= 0) {
                location.reload();
            } else {
                // Update subtotal
                const subEl = document.querySelector('.subtotal-value');
                if (subEl) subEl.textContent = '$' + data.subtotal.toFixed(2);
                location.reload();
            }
        }
    });
}

function removeCartItem(itemId) {
    fetch('/api/cart/remove', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({item_id: itemId})
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            updateCartCount(data.cart_count);
            location.reload();
        }
    });
}

// Wishlist toggle
function toggleWishlist(productId, btn) {
    fetch('/api/wishlist/toggle', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({product_id: productId})
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            if (btn) {
                btn.textContent = data.in_wishlist ? '♥ In Wishlist' : '♡ Add to Wishlist';
            }
            showToast(data.message);
        } else if (data.redirect) {
            window.location.href = data.redirect;
        }
    });
}

// Update cart count in header
function updateCartCount(count) {
    document.querySelectorAll('.cart-count').forEach(el => {
        el.textContent = count;
    });
}

// Toast notifications
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = 'toast';
    if (type === 'error') toast.style.borderLeftColor = '#b12704';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.transition = 'opacity 0.4s';
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 400);
    }, 3000);
}

// Image error handling
document.addEventListener('error', (e) => {
    if (e.target.tagName === 'IMG') {
        e.target.style.display = 'none';
        if (e.target.parentElement && e.target.parentElement.classList.contains('pd-gallery-img')) {
            e.target.parentElement.style.display = 'none';
        }
    }
}, true);
