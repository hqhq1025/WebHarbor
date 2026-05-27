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

/* Wolfram Alpha Mirror — main.js */

// -------- Toast notification --------
function showToast(msg, duration) {
  duration = duration || 3000;
  const existing = document.querySelector('.toast-msg');
  if (existing) existing.remove();
  const t = document.createElement('div');
  t.className = 'toast-msg';
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => { if (t.parentNode) t.remove(); }, duration);
}

// -------- Flash message auto-dismiss --------
setTimeout(() => {
  const flashes = document.querySelectorAll('.flash');
  flashes.forEach(f => {
    f.style.transition = 'opacity 0.5s ease';
    f.style.opacity = '0';
    setTimeout(() => { if (f.parentNode) f.remove(); }, 500);
  });
}, 4000);

// -------- Mobile hamburger --------
const hamburger = document.getElementById('gnHamburger');
const mobileMenu = document.getElementById('gnMobileMenu');
if (hamburger && mobileMenu) {
  hamburger.addEventListener('click', () => {
    mobileMenu.classList.toggle('open');
  });
  document.addEventListener('click', (e) => {
    if (!hamburger.contains(e.target) && !mobileMenu.contains(e.target)) {
      mobileMenu.classList.remove('open');
    }
  });
}

// -------- Fade-in on scroll --------
document.addEventListener('DOMContentLoaded', () => {
  const fadeEls = document.querySelectorAll('.fade-in');
  if (!fadeEls.length) return;

  // Immediately visible ones
  setTimeout(() => {
    fadeEls.forEach(el => el.classList.add('visible'));
  }, 100);

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.classList.add('visible');
        observer.unobserve(e.target);
      }
    });
  }, { threshold: 0.1 });

  fadeEls.forEach(el => observer.observe(el));
});

// -------- CSRF token helper for fetch --------
function getCsrf() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute('content') : '';
}

// -------- Global search from nav --------
const gnSearchBtn = document.querySelector('.gn-search-btn');
if (gnSearchBtn) {
  gnSearchBtn.addEventListener('click', (e) => {
    e.preventDefault();
    const q = prompt('Enter a computation or question:');
    if (q && q.trim()) {
      window.location.href = '/input?i=' + encodeURIComponent(q.trim());
    }
  });
}

/* ========== R5 interactive polish ========== */

// Plot pod — zoom in/out/reset/pan via data attribute on wrapper.
document.addEventListener('click', (e) => {
  const btn = e.target.closest('.pod-plot-btn');
  if (!btn) return;
  const wrap = btn.closest('.pod-plot-wrapper');
  if (!wrap) return;
  const cur = parseFloat(wrap.dataset.zoom || '1.0');
  const action = btn.dataset.action;
  let next = cur;
  if (action === 'zoom-in') next = Math.min(2.0, cur + 0.25);
  else if (action === 'zoom-out') next = Math.max(0.5, cur - 0.25);
  else if (action === 'zoom-reset') next = 1.0;
  else if (action === 'pan-left' || action === 'pan-right') {
    const host = wrap.querySelector('.pod-plot-svg-host');
    const delta = action === 'pan-left' ? -20 : 20;
    const cx = parseInt(host.dataset.pan || '0', 10) + delta;
    host.dataset.pan = String(cx);
    const svg = host.querySelector('svg');
    if (svg) svg.style.transform = `translateX(${cx}px) scale(${cur})`;
    return;
  }
  wrap.dataset.zoom = next.toFixed(2);
  // Map to CSS via attribute selectors for predefined steps,
  // and also style.transform for in-between steps.
  const host = wrap.querySelector('.pod-plot-svg-host');
  const svg = host && host.querySelector('svg');
  if (svg) {
    const px = parseInt(host.dataset.pan || '0', 10);
    svg.style.transform = `translateX(${px}px) scale(${next})`;
  }
});

// Alternate-forms tab switching with smooth opacity transition.
document.addEventListener('click', (e) => {
  const tab = e.target.closest('.pod-altform-tab');
  if (!tab) return;
  const container = tab.closest('.result-pod--alternate');
  if (!container) return;
  container.querySelectorAll('.pod-altform-tab').forEach((t) => {
    t.classList.remove('pod-altform-tab--active');
    t.setAttribute('aria-selected', 'false');
  });
  tab.classList.add('pod-altform-tab--active');
  tab.setAttribute('aria-selected', 'true');
  const body = container.querySelector('.pod-altform-body');
  if (body) {
    const form = tab.dataset.form || 'standard';
    body.style.opacity = '0';
    setTimeout(() => {
      body.dataset.active = form;
      body.style.opacity = '1';
    }, 150);
  }
});

// Keyboard activation for span-based tabs / pills.
document.addEventListener('keydown', (e) => {
  if (e.key !== 'Enter' && e.key !== ' ') return;
  const t = document.activeElement;
  if (!t) return;
  if (t.matches('.pod-altform-tab, .wa-assumption-pill[role="tab"]:not(a), .builder-size-btn')) {
    e.preventDefault();
    t.click();
  }
});

// Embed size picker — sync the iframe code with chosen preset.
document.addEventListener('click', (e) => {
  const btn = e.target.closest('.builder-size-btn');
  if (!btn) return;
  document.querySelectorAll('.builder-size-btn').forEach((b) =>
    b.classList.remove('builder-size-btn--active'));
  btn.classList.add('builder-size-btn--active');
  const w = btn.dataset.w, h = btn.dataset.h;
  const wInput = document.getElementById('bf-width');
  const hInput = document.getElementById('bf-height');
  if (wInput) wInput.value = w;
  if (hInput) hInput.value = h;
  const code = document.getElementById('bf-embed');
  if (code) {
    code.innerHTML = code.innerHTML
      .replace(/width="\d+"/, `width="${w}"`)
      .replace(/height="\d+"/, `height="${h}"`);
  }
});
