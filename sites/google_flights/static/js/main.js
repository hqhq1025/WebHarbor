// Google Flights mirror - main JS
(function() {
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

  // ---- Auto-dismiss flash messages ----
  setTimeout(() => {
    document.querySelectorAll('.flash').forEach(f => {
      f.style.transition = 'opacity 0.4s';
      f.style.opacity = '0';
      setTimeout(() => f.remove(), 400);
    });
  }, 4500);

  // ---- Search tab toggles (Round trip / One way / Multi-city) ----
  document.querySelectorAll('.search-tab').forEach(tab => {
    tab.addEventListener('click', (e) => {
      e.preventDefault();
      const siblings = tab.parentElement.querySelectorAll('.search-tab');
      siblings.forEach(s => s.classList.remove('active'));
      tab.classList.add('active');
      const type = tab.dataset.type;
      document.querySelectorAll('[data-return-field]').forEach(el => {
        el.style.display = (type === 'oneway' ? 'none' : '');
      });
    });
  });

  // ---- City origin tab switching (home) ----
  document.querySelectorAll('.city-tab').forEach(tab => {
    tab.addEventListener('click', (e) => {
      e.preventDefault();
      tab.parentElement.querySelectorAll('.city-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const iata = tab.dataset.iata;
      // Visually filter deals - optional, server re-renders on explicit search
      document.querySelectorAll('.deal-card[data-origin]').forEach(card => {
        card.style.display = (iata && card.dataset.origin !== iata) ? 'none' : '';
      });
    });
  });

  // ---- Swap from/to ----
  const swapBtn = document.querySelector('.search-swap');
  if (swapBtn) {
    swapBtn.addEventListener('click', () => {
      const from = document.querySelector('input[name="from"]');
      const to = document.querySelector('input[name="to"]');
      if (from && to) { const t = from.value; from.value = to.value; to.value = t; }
    });
  }

  // ---- Track / Untrack flight (wishlist) ----
  document.querySelectorAll('[data-track-flight]').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      const flightId = parseInt(btn.dataset.trackFlight);
      try {
        const r = await fetch('/api/track/toggle', {
          method: 'POST',
          headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken},
          body: JSON.stringify({flight_id: flightId}),
        });
        if (r.status === 401) { window.location.href = '/login'; return; }
        const data = await r.json();
        if (data.success) {
          btn.classList.toggle('tracked', data.tracked);
          btn.querySelector('.material-symbols-outlined').textContent = data.tracked ? 'bookmark_added' : 'bookmark_border';
          showToast(data.tracked ? 'Added to tracked flights' : 'Removed from tracked');
        }
      } catch (err) {
        console.error(err);
      }
    });
  });

  // ---- Add to bag ----
  document.querySelectorAll('[data-add-bag]').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      const flightId = parseInt(btn.dataset.addBag);
      const passengers = parseInt(document.querySelector('[name="passengers"]')?.value || 1);
      const cabin = document.querySelector('[name="cabin_class"]')?.value || 'Economy';
      try {
        const r = await fetch('/api/cart/add', {
          method: 'POST',
          headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken},
          body: JSON.stringify({flight_id: flightId, passengers, cabin_class: cabin}),
        });
        if (r.status === 401) { window.location.href = '/login'; return; }
        const data = await r.json();
        if (data.success) {
          updateBagBadge(data.cart_count);
          showToast(data.message || 'Added to your bag');
        }
      } catch (err) { console.error(err); }
    });
  });

  // ---- Bag quantity +/- ----
  document.querySelectorAll('[data-qty]').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      const itemId = parseInt(btn.dataset.item);
      const delta = parseInt(btn.dataset.qty);
      const qtyEl = document.querySelector(`[data-qty-display="${itemId}"]`);
      if (!qtyEl) return;
      const newQty = Math.max(1, parseInt(qtyEl.textContent) + delta);
      try {
        const r = await fetch('/api/cart/update', {
          method: 'POST',
          headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken},
          body: JSON.stringify({item_id: itemId, passengers: newQty}),
        });
        const data = await r.json();
        if (data.success) {
          qtyEl.textContent = newQty;
          const totalEl = document.querySelector(`[data-line-total="${itemId}"]`);
          if (totalEl) totalEl.textContent = '$' + data.line_total.toLocaleString('en-US', {minimumFractionDigits: 0, maximumFractionDigits: 0});
          // Force reload to refresh totals
          setTimeout(() => window.location.reload(), 500);
        }
      } catch (err) { console.error(err); }
    });
  });

  // ---- Bag remove ----
  document.querySelectorAll('[data-remove-bag]').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      const itemId = parseInt(btn.dataset.removeBag);
      try {
        const r = await fetch('/api/cart/remove', {
          method: 'POST',
          headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken},
          body: JSON.stringify({item_id: itemId}),
        });
        const data = await r.json();
        if (data.success) {
          window.location.reload();
        }
      } catch (err) { console.error(err); }
    });
  });

  // ---- Helpers ----
  function updateBagBadge(count) {
    let badge = document.querySelector('.gbar-badge');
    const icon = document.querySelector('.gbar-icon-btn[title="Your bag"]');
    if (count > 0) {
      if (!badge && icon) {
        badge = document.createElement('span');
        badge.className = 'gbar-badge';
        icon.appendChild(badge);
      }
      if (badge) badge.textContent = count;
    } else if (badge) {
      badge.remove();
    }
  }

  function showToast(msg) {
    const t = document.createElement('div');
    t.className = 'flash flash-info';
    t.innerHTML = '<span class="material-symbols-outlined">info</span><span>' + msg + '</span>';
    let container = document.querySelector('.flash-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'flash-container';
      document.body.appendChild(container);
    }
    container.appendChild(t);
    setTimeout(() => {
      t.style.transition = 'opacity 0.4s';
      t.style.opacity = '0';
      setTimeout(() => t.remove(), 400);
    }, 3500);
  }

  // ---- Star rating widget ----
  document.querySelectorAll('.star-rating').forEach(rating => {
    const inputs = rating.querySelectorAll('input');
    inputs.forEach(input => {
      input.addEventListener('change', () => {
        const val = parseInt(input.value);
        rating.querySelectorAll('label').forEach((label, i) => {
          label.classList.toggle('filled', i < val);
        });
      });
    });
  });
})();
