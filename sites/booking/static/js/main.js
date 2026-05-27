// Booking.com mirror - main.js
// Handles: save/wishlist toggle, add to bag, remove cart item, notifications

function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

function showNotification(message, type) {
    type = type || 'success';
    let container = document.getElementById('js-notifications');
    if (!container) {
        container = document.createElement('div');
        container.id = 'js-notifications';
        container.style.cssText = 'position:fixed;top:20px;right:20px;z-index:10000;display:flex;flex-direction:column;gap:10px;';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    const bg = type === 'error' ? '#e31c5f' : (type === 'info' ? '#006ce4' : '#008009');
    toast.style.cssText = 'background:' + bg + ';color:#fff;padding:12px 20px;border-radius:4px;box-shadow:0 4px 12px rgba(0,0,0,0.15);font-size:14px;min-width:240px;max-width:360px;opacity:0;transform:translateX(20px);transition:all 0.25s ease;';
    toast.textContent = message;
    container.appendChild(toast);
    // Animate in
    requestAnimationFrame(function () {
        toast.style.opacity = '1';
        toast.style.transform = 'translateX(0)';
    });
    // Auto-dismiss
    setTimeout(function () {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(20px)';
        setTimeout(function () { toast.remove(); }, 300);
    }, 3200);
}

function updateBagCount(count) {
    const btns = document.querySelectorAll('.header-btn');
    btns.forEach(function (btn) {
        if (btn.textContent.trim().startsWith('Bag')) {
            btn.textContent = count > 0 ? 'Bag (' + count + ')' : 'Bag';
        }
    });
}

function toggleSave(btn, propertyId) {
    fetch('/api/saved/toggle', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ property_id: propertyId })
    })
        .then(function (r) {
            if (r.status === 401 || r.redirected) {
                showNotification('Please sign in to save properties.', 'info');
                setTimeout(function () { window.location.href = '/login'; }, 800);
                return null;
            }
            return r.json();
        })
        .then(function (data) {
            if (!data) return;
            if (data.success) {
                if (data.action === 'added') {
                    btn.classList.add('saved');
                    showNotification('Saved to your list.');
                } else {
                    btn.classList.remove('saved');
                    showNotification('Removed from saved.', 'info');
                }
            } else {
                showNotification('Could not update your saved list.', 'error');
            }
        })
        .catch(function () {
            showNotification('Network error. Please try again.', 'error');
        });
}

function addToBag(propertyId, roomType) {
    const body = { property_id: propertyId };
    if (roomType) body.room_type = roomType;
    // Pull optional check-in/check-out from widget inputs if present
    const ci = document.querySelector('input[name="check_in"]');
    const co = document.querySelector('input[name="check_out"]');
    const adults = document.querySelector('select[name="adults"]');
    const rooms = document.querySelector('select[name="rooms"]');
    if (ci && ci.value) body.check_in = ci.value;
    if (co && co.value) body.check_out = co.value;
    if (adults && adults.value) body.adults = parseInt(adults.value, 10);
    if (rooms && rooms.value) body.rooms = parseInt(rooms.value, 10);

    fetch('/api/cart/add', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify(body)
    })
        .then(function (r) {
            if (r.status === 401 || r.redirected) {
                showNotification('Please sign in to book.', 'info');
                setTimeout(function () { window.location.href = '/login'; }, 800);
                return null;
            }
            return r.json();
        })
        .then(function (data) {
            if (!data) return;
            if (data.success) {
                updateBagCount(data.cart_count);
                showNotification(data.message || 'Added to your bag.');
            } else {
                showNotification(data.message || 'Could not add to bag.', 'error');
            }
        })
        .catch(function () {
            showNotification('Network error. Please try again.', 'error');
        });
}

function removeCartItem(itemId) {
    if (!confirm('Remove this item from your bag?')) return;
    fetch('/api/cart/remove', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ item_id: itemId })
    })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data && data.success) {
                updateBagCount(data.cart_count);
                // Reload to refresh totals
                window.location.reload();
            } else {
                showNotification('Could not remove item.', 'error');
            }
        })
        .catch(function () {
            showNotification('Network error. Please try again.', 'error');
        });
}

function updateCartItem(itemId, field, value) {
    const body = { item_id: itemId };
    body[field] = value;
    fetch('/api/cart/update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify(body)
    })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data && data.success) {
                showNotification('Updated.');
                window.location.reload();
            }
        })
        .catch(function () {
            showNotification('Network error. Please try again.', 'error');
        });
}

// Auto-dismiss flash messages
document.addEventListener('DOMContentLoaded', function () {
    setTimeout(function () {
        const flashes = document.querySelectorAll('.flash');
        flashes.forEach(function (f) {
            f.style.transition = 'opacity 0.4s';
            f.style.opacity = '0';
            setTimeout(function () { f.remove(); }, 500);
        });
    }, 5000);

    // Scroll reveal for elements with .reveal
    if ('IntersectionObserver' in window) {
        const io = new IntersectionObserver(function (entries) {
            entries.forEach(function (e) {
                if (e.isIntersecting) {
                    e.target.style.opacity = '1';
                    e.target.style.transform = 'translateY(0)';
                }
            });
        }, { threshold: 0.08 });
        document.querySelectorAll('.reveal').forEach(function (el) {
            el.style.opacity = '0';
            el.style.transform = 'translateY(16px)';
            el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            io.observe(el);
        });
    }

});

