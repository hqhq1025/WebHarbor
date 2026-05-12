// Amazon mirror - client-side behaviors

// CSRF helper
function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

// Auto-dismiss flash messages
document.addEventListener('DOMContentLoaded', () => {
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

    // Search form
    const searchForm = document.querySelector('.nav-search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', (e) => {
            const input = searchForm.querySelector('input');
            if (!input.value.trim()) {
                e.preventDefault();
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
