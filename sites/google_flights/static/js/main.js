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

// ===========================================================
// R5 progressive enhancements
//   - Airport autocomplete (city-expand) on search inputs
//   - Saved-search heart animation
//   - Calendar grid drag-select range + ARIA
//   - Sticky filter toolbar with chip clear-all
//   - Mobile bottom-sheet filter panel
//   - Screen-reader live announcements on filter change
//   - Seat-map keyboard navigation
// All idempotent; safe if R5 hooks (.r5-*) are absent.
// ===========================================================
(function() {
  // Live region for screen-reader announcements
  let liveRegion = document.getElementById('r5-live');
  if (!liveRegion) {
    liveRegion = document.createElement('div');
    liveRegion.id = 'r5-live';
    liveRegion.setAttribute('aria-live', 'polite');
    liveRegion.setAttribute('aria-atomic', 'true');
    liveRegion.className = 'visually-hidden';
    document.body.appendChild(liveRegion);
  }
  function announce(msg) {
    if (!msg) return;
    liveRegion.textContent = '';
    setTimeout(() => { liveRegion.textContent = msg; }, 50);
  }
  window.r5Announce = announce;

  // ---- Airport autocomplete on search inputs ----
  function attachAutocomplete(input) {
    if (!input || input.__r5_autocomplete) return;
    input.__r5_autocomplete = true;
    input.setAttribute('autocomplete', 'off');
    input.setAttribute('aria-autocomplete', 'list');
    const list = document.createElement('ul');
    list.className = 'r5-autocomplete';
    list.setAttribute('role', 'listbox');
    list.hidden = true;
    input.insertAdjacentElement('afterend', list);
    let activeIndex = -1;
    let lastQuery = '';
    let timer = null;

    function render(items) {
      list.innerHTML = '';
      if (!items.length) { list.hidden = true; return; }
      items.forEach((it, i) => {
        const li = document.createElement('li');
        li.setAttribute('role', 'option');
        li.dataset.iata = it.iata;
        li.innerHTML = '<span class="r5-ac-iata">' + it.iata + '</span>' +
          '<span class="r5-ac-city">' + it.city + '</span>' +
          '<span class="r5-ac-country">' + it.country + '</span>';
        li.addEventListener('mousedown', (e) => {
          e.preventDefault();
          input.value = it.city + ' (' + it.iata + ')';
          list.hidden = true;
          announce('Selected ' + it.city + ' ' + it.iata);
        });
        list.appendChild(li);
      });
      list.hidden = false;
      activeIndex = -1;
    }
    async function lookup(q) {
      if (q === lastQuery) return;
      lastQuery = q;
      if (q.length < 2) { list.hidden = true; return; }
      try {
        const r = await fetch('/api/airports?q=' + encodeURIComponent(q));
        if (!r.ok) return;
        const data = await r.json();
        render(data.slice(0, 8));
      } catch (e) {}
    }
    input.addEventListener('input', () => {
      clearTimeout(timer);
      timer = setTimeout(() => lookup(input.value.trim()), 180);
    });
    input.addEventListener('keydown', (e) => {
      const opts = list.querySelectorAll('li');
      if (!opts.length || list.hidden) return;
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        activeIndex = (activeIndex + 1) % opts.length;
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        activeIndex = (activeIndex - 1 + opts.length) % opts.length;
      } else if (e.key === 'Enter' && activeIndex >= 0) {
        e.preventDefault();
        opts[activeIndex].dispatchEvent(new MouseEvent('mousedown'));
        return;
      } else if (e.key === 'Escape') {
        list.hidden = true; return;
      } else { return; }
      opts.forEach((o, i) => o.classList.toggle('active', i === activeIndex));
    });
    input.addEventListener('blur', () => setTimeout(() => { list.hidden = true; }, 150));
  }
  document.querySelectorAll('input[name="from"], input[name="to"], input.r5-airport-input').forEach(attachAutocomplete);

  // ---- Save-search heart animation ----
  document.querySelectorAll('[data-save-search]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      btn.classList.add('r5-heart-pop');
      setTimeout(() => btn.classList.remove('r5-heart-pop'), 600);
      announce('Search saved');
    });
  });

  // ---- Sticky filter toolbar: chip clear ----
  document.querySelectorAll('.r5-filter-chip [data-clear-filter]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const param = btn.dataset.clearFilter;
      const u = new URL(window.location.href);
      u.searchParams.delete(param);
      announce(param + ' filter removed');
      window.location.href = u.toString();
    });
  });

  // ---- Filter form: announce on change ----
  document.querySelectorAll('form.r5-filter-form, form.filters-form').forEach(form => {
    form.addEventListener('change', (e) => {
      const label = e.target.closest('label')?.textContent?.trim() || e.target.name || 'filter';
      announce('Filter updated: ' + label);
    });
  });

  // ---- Mobile bottom-sheet toggle ----
  document.querySelectorAll('[data-bottom-sheet-toggle]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const target = document.querySelector(btn.dataset.bottomSheetToggle);
      if (!target) return;
      const isOpen = target.classList.toggle('r5-sheet-open');
      target.setAttribute('aria-hidden', isOpen ? 'false' : 'true');
      announce(isOpen ? 'Filters opened' : 'Filters closed');
    });
  });

  // ---- Calendar grid: drag-select range + ARIA ----
  document.querySelectorAll('.r5-calendar-grid, .calendar-cheapest-grid').forEach(grid => {
    const cells = grid.querySelectorAll('[data-cal-date]');
    let dragStart = null;
    cells.forEach((cell, idx) => {
      cell.setAttribute('role', 'gridcell');
      cell.setAttribute('tabindex', cell.classList.contains('selected') ? '0' : '-1');
      const dateStr = cell.dataset.calDate;
      const priceEl = cell.querySelector('.price, .cal-price');
      const priceTxt = priceEl ? priceEl.textContent.trim() : '';
      cell.setAttribute('aria-label', dateStr + (priceTxt ? ', ' + priceTxt : ''));
      cell.addEventListener('mousedown', (e) => {
        dragStart = idx;
        cells.forEach(c => c.classList.remove('range-start', 'range-end', 'in-range'));
        cell.classList.add('range-start');
      });
      cell.addEventListener('mouseenter', (e) => {
        if (dragStart === null) return;
        const lo = Math.min(dragStart, idx), hi = Math.max(dragStart, idx);
        cells.forEach((c, i) => {
          c.classList.toggle('in-range', i > lo && i < hi);
          c.classList.toggle('range-end', i === hi && i !== lo);
        });
      });
      cell.addEventListener('mouseup', (e) => {
        if (dragStart === null) return;
        const lo = Math.min(dragStart, idx), hi = Math.max(dragStart, idx);
        const a = cells[lo].dataset.calDate;
        const b = cells[hi].dataset.calDate;
        dragStart = null;
        if (a && b) announce('Range selected ' + a + ' to ' + b);
      });
      cell.addEventListener('keydown', (e) => {
        let target = null;
        if (e.key === 'ArrowRight') target = cells[idx + 1];
        else if (e.key === 'ArrowLeft') target = cells[idx - 1];
        else if (e.key === 'ArrowDown') target = cells[idx + 7];
        else if (e.key === 'ArrowUp') target = cells[idx - 7];
        else if (e.key === 'Enter' || e.key === ' ') {
          cell.click();
          announce('Picked ' + cell.dataset.calDate);
          e.preventDefault();
          return;
        }
        if (target) {
          cell.setAttribute('tabindex', '-1');
          target.setAttribute('tabindex', '0');
          target.focus();
          e.preventDefault();
        }
      });
    });
    document.addEventListener('mouseup', () => { dragStart = null; });
  });

  // ---- Seat map: keyboard navigation + ARIA ----
  document.querySelectorAll('.seat-map, .r5-seat-map').forEach(map => {
    const seats = map.querySelectorAll('[data-seat]');
    seats.forEach((seat, idx) => {
      seat.setAttribute('role', 'button');
      seat.setAttribute('tabindex', idx === 0 ? '0' : '-1');
      const occupied = seat.classList.contains('occupied') || seat.dataset.occupied === '1';
      const label = seat.dataset.seat + (occupied ? ', occupied' : ', available');
      seat.setAttribute('aria-label', label);
      seat.setAttribute('aria-pressed', seat.classList.contains('selected') ? 'true' : 'false');
      seat.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          seat.click();
          announce('Seat ' + seat.dataset.seat + ' selected');
          e.preventDefault();
        }
      });
    });
  });

  // ---- Swipe between dates (mobile) ----
  document.querySelectorAll('.r5-date-swipe').forEach(el => {
    let sx = 0, sy = 0;
    el.addEventListener('touchstart', (e) => {
      sx = e.touches[0].clientX; sy = e.touches[0].clientY;
    }, { passive: true });
    el.addEventListener('touchend', (e) => {
      const dx = e.changedTouches[0].clientX - sx;
      const dy = e.changedTouches[0].clientY - sy;
      if (Math.abs(dx) > 60 && Math.abs(dy) < 40) {
        const dir = dx < 0 ? 'next' : 'prev';
        const target = el.querySelector('[data-swipe-' + dir + ']');
        if (target) { announce(dir === 'next' ? 'Next day' : 'Previous day'); target.click(); }
      }
    });
  });
})();

