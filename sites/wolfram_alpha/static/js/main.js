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
