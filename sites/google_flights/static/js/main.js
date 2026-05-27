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

// ============================================================
// R8: Global keyboard shortcuts + Cmd+K command palette
// ============================================================
(function r8KeyboardLayer() {
  'use strict';
  if (typeof document === 'undefined') return;

  function inEditable(el) {
    if (!el) return false;
    const tag = (el.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'textarea' || tag === 'select') return true;
    if (el.isContentEditable) return true;
    return false;
  }

  const palette = document.getElementById('r8-palette');
  const paletteInput = document.getElementById('r8-palette-input');
  const paletteList = document.getElementById('r8-palette-list');
  let paletteItems = [];
  let paletteIndex = 0;
  let paletteFetchTimer = null;
  let paletteOpen = false;

  function renderPalette() {
    if (!paletteList) return;
    paletteList.innerHTML = '';
    if (paletteItems.length === 0) {
      const li = document.createElement('li');
      li.style.padding = '14px';
      li.style.color = '#5f6368';
      li.textContent = 'No matches.';
      paletteList.appendChild(li);
      return;
    }
    paletteItems.forEach((item, i) => {
      const li = document.createElement('li');
      li.setAttribute('role', 'option');
      li.dataset.url = item.url || '';
      li.style.cssText = 'padding:10px 14px;border-radius:6px;cursor:pointer;display:flex;align-items:center;gap:10px;';
      if (i === paletteIndex) {
        li.style.background = '#e8f0fe';
        li.setAttribute('aria-selected', 'true');
      }
      const kindBadge = document.createElement('span');
      kindBadge.style.cssText = 'font-size:10px;text-transform:uppercase;letter-spacing:0.04em;color:#5f6368;background:#f1f3f4;padding:2px 6px;border-radius:4px;min-width:54px;text-align:center;';
      kindBadge.textContent = item.kind || 'item';
      const main = document.createElement('div');
      main.style.cssText = 'flex:1;min-width:0;';
      const label = document.createElement('div');
      label.style.cssText = 'font-size:14px;color:#202124;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
      label.textContent = item.label || '';
      main.appendChild(label);
      if (item.hint) {
        const hint = document.createElement('div');
        hint.style.cssText = 'font-size:12px;color:#5f6368;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
        hint.textContent = item.hint;
        main.appendChild(hint);
      }
      li.appendChild(kindBadge);
      li.appendChild(main);
      li.addEventListener('click', () => {
        if (li.dataset.url) window.location.href = li.dataset.url;
      });
      paletteList.appendChild(li);
    });
  }

  function fetchPalette(q) {
    if (paletteFetchTimer) clearTimeout(paletteFetchTimer);
    paletteFetchTimer = setTimeout(() => {
      fetch('/api/command-palette?q=' + encodeURIComponent(q || ''))
        .then(r => r.json())
        .then(data => {
          paletteItems = (data.items || []).slice(0, 40);
          paletteIndex = 0;
          renderPalette();
        })
        .catch(() => {
          paletteItems = [];
          renderPalette();
        });
    }, 90);
  }

  function openPalette() {
    if (!palette) return;
    palette.hidden = false;
    paletteOpen = true;
    if (paletteInput) {
      paletteInput.value = '';
      paletteInput.focus();
    }
    fetchPalette('');
  }

  function closePalette() {
    if (!palette) return;
    palette.hidden = true;
    paletteOpen = false;
  }

  if (palette) {
    palette.addEventListener('click', (e) => {
      if (e.target === palette) closePalette();
    });
  }
  if (paletteInput) {
    paletteInput.addEventListener('input', (e) => fetchPalette(e.target.value));
    paletteInput.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') { closePalette(); e.preventDefault(); return; }
      if (e.key === 'ArrowDown') {
        paletteIndex = Math.min(paletteItems.length - 1, paletteIndex + 1);
        renderPalette(); e.preventDefault();
      } else if (e.key === 'ArrowUp') {
        paletteIndex = Math.max(0, paletteIndex - 1);
        renderPalette(); e.preventDefault();
      } else if (e.key === 'Enter') {
        const it = paletteItems[paletteIndex];
        if (it && it.url) {
          window.location.href = it.url;
        }
        e.preventDefault();
      }
    });
  }

  // ---- "g <key>" goto bindings ----
  let gPending = false;
  let gPendingTimer = null;
  const gMap = {
    'h': '/',
    'e': '/explore',
    't': '/trips',
    'b': '/bag',
    'd': '/deals',
    'a': '/alerts',
  };

  document.addEventListener('keydown', (e) => {
    if (e.defaultPrevented) return;
    // Cmd/Ctrl+K → open palette
    if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
      e.preventDefault();
      if (paletteOpen) { closePalette(); } else { openPalette(); }
      return;
    }
    if ((e.metaKey || e.ctrlKey) && e.key === '/') {
      e.preventDefault();
      window.location.href = '/keyboard-shortcuts';
      return;
    }
    if (paletteOpen) return;
    if (inEditable(document.activeElement)) return;
    // '/' → focus search field
    if (e.key === '/') {
      const target = document.querySelector('.search-field-from, input[name="from"], input[name="q"]');
      if (target) { target.focus(); target.select && target.select(); e.preventDefault(); }
      return;
    }
    // '?' → open help
    if (e.key === '?') {
      window.location.href = '/help';
      e.preventDefault();
      return;
    }
    // 'g' + key
    if (e.key === 'g' || e.key === 'G') {
      gPending = true;
      if (gPendingTimer) clearTimeout(gPendingTimer);
      gPendingTimer = setTimeout(() => { gPending = false; }, 1200);
      return;
    }
    if (gPending && gMap[e.key.toLowerCase()]) {
      window.location.href = gMap[e.key.toLowerCase()];
      gPending = false;
      e.preventDefault();
      return;
    }
    if (e.key === 'Escape') {
      gPending = false;
      if (paletteOpen) closePalette();
    }
  });

  // ---- Date keyboard nudges on inputs with [data-datepicker] ----
  document.addEventListener('keydown', (e) => {
    const t = e.target;
    if (!t || !(t.matches && t.matches('input[data-datepicker]'))) return;
    if (!['ArrowLeft', 'ArrowRight', 'PageUp', 'PageDown'].includes(e.key)) return;
    const v = (t.value || '').trim();
    if (!/^\d{4}-\d{2}-\d{2}$/.test(v)) return;
    const d = new Date(v + 'T00:00:00');
    if (isNaN(d.getTime())) return;
    let delta = 0;
    if (e.key === 'ArrowLeft')  delta = e.shiftKey ? -7 : -1;
    if (e.key === 'ArrowRight') delta = e.shiftKey ?  7 :  1;
    if (e.key === 'PageUp')    { d.setMonth(d.getMonth() - 1); delta = 0; }
    if (e.key === 'PageDown')  { d.setMonth(d.getMonth() + 1); delta = 0; }
    if (delta) d.setDate(d.getDate() + delta);
    const iso = d.toISOString().slice(0, 10);
    t.value = iso;
    t.dispatchEvent(new Event('input', { bubbles: true }));
    e.preventDefault();
  });

  // ---- Cabin-class glossary tooltip ----
  function attachCabinClassTooltip() {
    const sels = document.querySelectorAll('select[name="class"]');
    if (sels.length === 0) return;
    let glossary = null;
    function ensureGlossary() {
      if (glossary !== null) return Promise.resolve(glossary);
      return fetch('/api/cabin-class-glossary')
        .then(r => r.json())
        .then(d => { glossary = d.glossary || []; return glossary; })
        .catch(() => { glossary = []; return glossary; });
    }
    sels.forEach((sel) => {
      if (sel.dataset.r8CabinTip === '1') return;
      sel.dataset.r8CabinTip = '1';
      const wrap = document.createElement('span');
      wrap.style.cssText = 'position:relative;display:inline-block;margin-left:6px;';
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.setAttribute('aria-label', 'About cabin classes');
      btn.setAttribute('aria-expanded', 'false');
      btn.className = 'r8-cabin-tip-btn';
      btn.textContent = '?';
      btn.style.cssText = 'width:20px;height:20px;border-radius:50%;border:1px solid #dadce0;background:#fff;color:#5f6368;cursor:pointer;font-size:12px;line-height:18px;padding:0;';
      const tip = document.createElement('div');
      tip.className = 'r8-cabin-tip-panel';
      tip.setAttribute('role', 'tooltip');
      tip.hidden = true;
      tip.style.cssText = 'position:absolute;top:24px;left:0;background:#fff;border:1px solid #dadce0;border-radius:8px;box-shadow:0 4px 16px rgba(0,0,0,0.12);padding:14px;width:320px;z-index:1100;font-size:13px;color:#3c4043;';
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (!tip.hidden) {
          tip.hidden = true;
          btn.setAttribute('aria-expanded', 'false');
          return;
        }
        ensureGlossary().then(g => {
          tip.innerHTML = '<div style="font-weight:600;margin-bottom:8px;">Cabin classes</div>' +
            g.map(it => `<div style="margin-bottom:8px;"><strong style="color:#1a73e8;">${it.class}.</strong> ${it.description}</div>`).join('') +
            '<a href="/help/cabin-class" style="font-size:12px;color:#1a73e8;text-decoration:none;">Full glossary -</a>';
          tip.hidden = false;
          btn.setAttribute('aria-expanded', 'true');
        });
      });
      document.addEventListener('click', (e) => {
        if (tip.hidden) return;
        if (!wrap.contains(e.target)) {
          tip.hidden = true;
          btn.setAttribute('aria-expanded', 'false');
        }
      });
      wrap.appendChild(btn);
      wrap.appendChild(tip);
      if (sel.parentNode) sel.parentNode.insertBefore(wrap, sel.nextSibling);
    });
  }
  if (document.readyState !== 'loading') {
    attachCabinClassTooltip();
  } else {
    document.addEventListener('DOMContentLoaded', attachCabinClassTooltip);
  }
})();
