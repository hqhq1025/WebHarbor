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

// ── R5: file-tree async expand + keyboard navigation ──
// Folders are rows with data-ftype="folder". Clicking or pressing Enter/Space
// toggles a synthetic child list (mirror cosmetic; the real file API isn't
// wired up because the seed only ships latest_commit_files). Arrow keys move
// focus between rows. Esc collapses everything.
(function(){
  const folderChildren = [
    {name: 'index.ts',     additions: 12, deletions: 3, msg: 'Wire up entrypoint'},
    {name: 'helpers.ts',   additions: 6,  deletions: 1, msg: 'Add helper for normalization'},
    {name: 'constants.ts', additions: 4,  deletions: 0, msg: 'Move magic numbers'},
    {name: 'README.md',    additions: 8,  deletions: 2, msg: 'Document the contract'},
  ];

  function buildChildBlock() {
    const wrap = document.createElement('div');
    wrap.className = 'repo-file-children';
    wrap.setAttribute('role', 'group');
    folderChildren.forEach(function(ch){
      const row = document.createElement('div');
      row.className = 'repo-file-row';
      row.setAttribute('role', 'treeitem');
      row.setAttribute('tabindex', '-1');
      row.innerHTML = '<span class="repo-file-icon" aria-hidden="true">📄</span>'
        + '<span class="repo-file-name">' + ch.name + '</span>'
        + '<span class="repo-file-msg">' + ch.msg + '</span>'
        + '<span class="repo-file-date">+' + ch.additions + ' −' + ch.deletions + '</span>';
      wrap.appendChild(row);
    });
    return wrap;
  }

  const fileList = document.querySelector('.repo-file-list');
  if (!fileList) return;

  // Promote the list to a tree for screen readers.
  fileList.setAttribute('role', 'tree');
  fileList.setAttribute('aria-label', 'Repository files');

  Array.prototype.forEach.call(fileList.querySelectorAll('.repo-file-row'), function(row, idx){
    const nameEl = row.querySelector('.repo-file-name');
    const isFolder = nameEl && /\/$/.test(nameEl.textContent.trim());
    row.setAttribute('role', 'treeitem');
    row.setAttribute('tabindex', idx === 0 ? '0' : '-1');
    if (isFolder) {
      row.setAttribute('data-ftype', 'folder');
      row.setAttribute('aria-expanded', 'false');
      // Insert collapsed child block after the folder row.
      const children = buildChildBlock();
      row.parentNode.insertBefore(children, row.nextSibling);
    } else {
      row.setAttribute('data-ftype', 'file');
    }
  });

  function focusableRows() {
    return Array.prototype.slice.call(fileList.querySelectorAll('.repo-file-row'))
      .filter(function(r){
        // Skip child rows whose parent folder is collapsed.
        let prev = r.previousElementSibling;
        while (prev) {
          if (prev.classList && prev.classList.contains('repo-file-children')) {
            const parent = prev.previousElementSibling;
            if (parent && parent.getAttribute('aria-expanded') === 'false') return false;
            break;
          }
          prev = prev.previousElementSibling;
        }
        return true;
      });
  }

  function focusRow(row) {
    fileList.querySelectorAll('.repo-file-row').forEach(function(r){ r.setAttribute('tabindex','-1'); });
    row.setAttribute('tabindex','0');
    row.focus();
  }

  fileList.addEventListener('click', function(e){
    const row = e.target.closest('.repo-file-row');
    if (!row || row.getAttribute('data-ftype') !== 'folder') return;
    const open = row.getAttribute('aria-expanded') === 'true';
    row.setAttribute('aria-expanded', open ? 'false' : 'true');
  });

  fileList.addEventListener('keydown', function(e){
    const row = e.target.closest('.repo-file-row');
    if (!row) return;
    const rows = focusableRows();
    const i = rows.indexOf(row);
    if (e.key === 'Enter' || e.key === ' ') {
      if (row.getAttribute('data-ftype') === 'folder') {
        e.preventDefault();
        const open = row.getAttribute('aria-expanded') === 'true';
        row.setAttribute('aria-expanded', open ? 'false' : 'true');
      }
    } else if (e.key === 'ArrowDown' && i < rows.length - 1) {
      e.preventDefault(); focusRow(rows[i + 1]);
    } else if (e.key === 'ArrowUp' && i > 0) {
      e.preventDefault(); focusRow(rows[i - 1]);
    } else if (e.key === 'ArrowRight' && row.getAttribute('data-ftype') === 'folder') {
      e.preventDefault();
      row.setAttribute('aria-expanded', 'true');
    } else if (e.key === 'ArrowLeft' && row.getAttribute('data-ftype') === 'folder') {
      e.preventDefault();
      row.setAttribute('aria-expanded', 'false');
    } else if (e.key === 'Escape') {
      fileList.querySelectorAll('.repo-file-row[data-ftype="folder"]').forEach(function(r){
        r.setAttribute('aria-expanded', 'false');
      });
    }
  });
})();

// ── R5: code-search syntax highlight ──
// Wraps occurrences of the query string in every .code-search-snippet with
// <mark>. Server delivers raw text so this stays case-insensitive and safe.
(function(){
  const input = document.querySelector('.code-search-input');
  const snippets = document.querySelectorAll('.code-search-snippet');
  if (!snippets.length) return;
  const q = (input && input.value || '').trim();
  if (!q) return;
  const escaped = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const rx = new RegExp('(' + escaped + ')', 'gi');
  snippets.forEach(function(pre){
    // Avoid double-wrap.
    if (pre.dataset.r5Highlighted) return;
    pre.innerHTML = pre.textContent.replace(rx, '<mark>$1</mark>');
    pre.dataset.r5Highlighted = '1';
  });
  // Announce match count to screen readers.
  const heading = document.querySelector('.code-search-page h3');
  if (heading && !heading.getAttribute('aria-live')) {
    heading.setAttribute('aria-live', 'polite');
  }
})();

// ── R5: star button burst replay on toggle ──
(function(){
  document.querySelectorAll('.star-action-btn').forEach(function(btn){
    btn.addEventListener('click', function(){
      btn.classList.remove('star-burst');
      // Force reflow so the animation restarts.
      void btn.offsetWidth;
      btn.classList.add('star-burst');
    });
  });
})();

// ── R5: issue templates dropdown — auto-fills title + body on /<repo>/issues/new ──
(function(){
  const picker = document.getElementById('issue-template-picker');
  if (!picker) return;
  const titleField = document.querySelector('.new-issue-form-wrap input[name="title"]');
  const bodyField  = document.querySelector('.new-issue-form-wrap textarea[name="body"]');
  if (!titleField || !bodyField) return;
  const templates = {
    bug: {
      title: '[bug] short description of what broke',
      body: '## Description\n\n## Steps to reproduce\n1.\n2.\n3.\n\n## Expected behaviour\n\n## Actual behaviour\n\n## Environment\n- OS:\n- Version:\n'
    },
    feature: {
      title: '[feature] short description of the request',
      body: '## Motivation\n\n## Proposal\n\n## Alternatives considered\n\n## Additional context\n'
    },
    docs: {
      title: '[docs] section that needs improvement',
      body: '## Section\n\n## What is missing or wrong\n\n## Suggested change\n'
    },
    question: {
      title: '[question] short summary',
      body: '## What I tried\n\n## What I expected\n\n## Where I am stuck\n'
    },
    security: {
      title: '[security] CVE-style summary (use private disclosure first)',
      body: '## Affected versions\n\n## Impact\n\n## Reproduction steps\n\n## Workaround\n'
    },
  };
  picker.addEventListener('change', function(){
    const v = picker.value;
    if (!v || !templates[v]) return;
    titleField.value = templates[v].title;
    bodyField.value  = templates[v].body;
    titleField.focus();
  });
})();

// ── R5: mobile nav toggle ──
(function(){
  const btn = document.getElementById('gh-mobile-nav-toggle');
  const nav = document.querySelector('.gh-header-left .gh-nav');
  if (!btn || !nav) return;
  btn.addEventListener('click', function(){
    const open = nav.classList.toggle('gh-nav-mobile-open');
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
  });
})();
