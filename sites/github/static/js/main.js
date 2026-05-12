/* GitHub Mirror - Main JavaScript */
'use strict';

// ── Fade-in on scroll ──
const fadeObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
    }
  });
}, { threshold: 0.1 });

document.querySelectorAll('.fade-in').forEach(el => {
  fadeObserver.observe(el);
});

// Ensure all fade-ins are visible after 2s (prevents broken state)
setTimeout(() => {
  document.querySelectorAll('.fade-in').forEach(el => el.classList.add('visible'));
}, 2000);

// ── Nav dropdowns (touch support) ──
document.querySelectorAll('.gh-nav-dropdown').forEach(dropdown => {
  dropdown.addEventListener('click', (e) => {
    if (window.innerWidth < 768) {
      const menu = dropdown.querySelector('.gh-nav-dropdown-menu');
      if (menu) menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
    }
  });
});

// ── Flash message auto-dismiss ──
setTimeout(() => {
  document.querySelectorAll('.flash').forEach(el => {
    el.style.transition = 'opacity 0.5s';
    el.style.opacity = '0';
    setTimeout(() => el.remove(), 500);
  });
}, 5000);

// ── Star toggle (generic) ──
function toggleStar(btn) {
  const repoId = btn.dataset.repoId;
  if (!repoId) return;
  fetch('/api/star/toggle', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ repo_id: parseInt(repoId) })
  })
  .then(r => r.json())
  .then(data => {
    if (data.success) {
      showToast(data.starred ? 'Repository starred!' : 'Unstarred');
    }
  })
  .catch(err => console.error('Star toggle failed:', err));
}

// ── Toast notification ──
function showToast(message) {
  const toast = document.createElement('div');
  toast.className = 'flash flash-success';
  toast.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:9999;animation:slideIn 0.2s ease';
  toast.innerHTML = message + '<button class="flash-close" onclick="this.parentElement.remove()">&times;</button>';
  document.body.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 500);
  }, 3000);
}

// ── Keyboard shortcuts ──
document.addEventListener('keydown', (e) => {
  // '/' focuses search
  if (e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
    e.preventDefault();
    const searchInput = document.querySelector('.gh-search-input');
    if (searchInput) searchInput.focus();
  }
});

// ── Repo name validation ──
const repoNameInput = document.getElementById('repo-name');
if (repoNameInput) {
  const hint = document.createElement('div');
  hint.style.cssText = 'font-size:12px;margin-top:4px;';
  repoNameInput.parentElement.appendChild(hint);
  repoNameInput.addEventListener('input', () => {
    const val = repoNameInput.value;
    const valid = /^[a-zA-Z0-9_\-.]+$/.test(val) && val.length > 0;
    hint.style.color = valid ? '#3fb950' : '#f85149';
    hint.textContent = val.length === 0 ? '' : valid
      ? `The repository will be created as: ${val}`
      : 'Repository name can only contain ASCII letters, numbers, hyphens, underscores, and periods.';
  });
}

// ── Format numbers ──
function formatNum(n) {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k';
  return n.toString();
}

// ── Close dropdowns on outside click ──
document.addEventListener('click', (e) => {
  if (!e.target.closest('.gh-nav-dropdown')) {
    document.querySelectorAll('.gh-nav-dropdown-menu').forEach(m => {
      m.style.display = '';
    });
  }
});
