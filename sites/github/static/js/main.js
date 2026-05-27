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

/* ─── R8: keyboard shortcuts, command palette, file finder, contextual help ─── */
(function(){
  'use strict';

  function $(id) { return document.getElementById(id); }
  function isEditable(el) {
    if (!el) return false;
    const tag = (el.tagName || '').toLowerCase();
    return tag === 'input' || tag === 'textarea' || tag === 'select' ||
           el.isContentEditable === true;
  }

  const backdrop = $('r8-modal-backdrop');
  const modals = {
    cmdk: $('r8-cmdk'),
    file: $('r8-filefinder'),
    help: $('r8-help'),
  };

  function openModal(name) {
    closeAllModals();
    const m = modals[name];
    if (!m || !backdrop) return;
    backdrop.hidden = false;
    m.hidden = false;
    const input = m.querySelector('.r8-modal-input');
    if (input) { input.value = ''; input.focus(); input.dispatchEvent(new Event('input')); }
  }
  function closeAllModals() {
    if (backdrop) backdrop.hidden = true;
    Object.values(modals).forEach(function(m){ if (m) m.hidden = true; });
  }
  if (backdrop) backdrop.addEventListener('click', closeAllModals);
  document.querySelectorAll('[data-r8-close]').forEach(function(b){
    b.addEventListener('click', closeAllModals);
  });

  // Command palette catalog — static destinations + DB-backed repo
  // suggestions (lazy-loaded from /api/repos on first focus).
  const STATIC_COMMANDS = [
    { label: 'Explore repositories',    href: '/explore',          meta: 'page' },
    { label: 'Trending',                href: '/trending',         meta: 'page' },
    { label: 'Topics',                  href: '/topics',           meta: 'page' },
    { label: 'Marketplace',             href: '/marketplace',      meta: 'page' },
    { label: 'Pricing',                 href: '/pricing',          meta: 'page' },
    { label: 'Sponsors',                href: '/sponsors',         meta: 'page' },
    { label: 'Skills',                  href: '/skills',           meta: 'page' },
    { label: 'Customer stories',        href: '/customer-stories', meta: 'page' },
    { label: 'Notifications',           href: '/notifications',    meta: 'page' },
    { label: 'Account dashboard',       href: '/account',          meta: 'page' },
    { label: 'Settings · profile',      href: '/settings/profile', meta: 'page' },
    { label: 'Settings · password',     href: '/settings/password',meta: 'page' },
    { label: 'New repository',          href: '/new',              meta: 'page' },
    { label: 'Codespaces',              href: '/codespaces',       meta: 'page' },
    { label: 'Copilot Chat',            href: '/copilot',          meta: 'page' },
    { label: 'Status page',             href: '/status/page',      meta: 'ops'  },
    { label: 'Healthz (liveness)',      href: '/healthz',          meta: 'ops'  },
    { label: 'Uptime · last 30 days',   href: '/api/uptime',       meta: 'ops'  },
    { label: 'Telemetry events',        href: '/api/events',       meta: 'ops'  },
    { label: 'Webhook · repository',    href: '/webhook/repository', meta: 'dev' },
    { label: 'GraphQL API stub',        href: '/api/graphql',      meta: 'dev'  },
    { label: 'OpenAPI spec',            href: '/api/openapi',      meta: 'dev'  },
    { label: 'OAuth Apps',              href: '/developer/oauth-app', meta: 'dev' },
    { label: 'Glossary',                href: '/help/glossary',    meta: 'help' },
    { label: 'Search syntax help',      href: '/search-syntax',    meta: 'help' },
    { label: 'Sitemap',                 href: '/sitemap.xml',      meta: 'seo'  },
    { label: 'Robots.txt',              href: '/robots.txt',       meta: 'seo'  },
    { label: 'Releases RSS',            href: '/releases.rss',     meta: 'seo'  },
  ];

  let repoSuggestions = [];
  function loadRepoSuggestions() {
    if (repoSuggestions.length) return Promise.resolve(repoSuggestions);
    return fetch('/api/repos').then(function(r){ return r.json(); }).then(function(rows){
      repoSuggestions = (rows || []).slice(0, 24).map(function(r){
        return { label: r.full_name, href: '/' + r.full_name,
                 meta: (r.language || 'repo') + ' · ★' + (r.stars || 0) };
      });
      return repoSuggestions;
    }).catch(function(){ return []; });
  }

  function renderCmdkList(filter) {
    const list = $('r8-cmdk-list');
    if (!list) return;
    const ql = (filter || '').trim().toLowerCase();
    const all = STATIC_COMMANDS.concat(repoSuggestions);
    const hits = all.filter(function(c){
      if (!ql) return true;
      return c.label.toLowerCase().indexOf(ql) >= 0 ||
             c.href.toLowerCase().indexOf(ql) >= 0;
    }).slice(0, 18);
    list.innerHTML = '';
    hits.forEach(function(c, i){
      const li = document.createElement('li');
      li.setAttribute('role', 'option');
      li.tabIndex = 0;
      if (i === 0) li.classList.add('r8-active');
      li.innerHTML = '<span>' + c.label + '</span>' +
                     '<span class="r8-mk-meta">' + (c.meta || '') + ' · ' + c.href + '</span>';
      li.addEventListener('click', function(){ window.location.href = c.href; });
      list.appendChild(li);
    });
  }

  const cmdkInput = $('r8-cmdk-input');
  if (cmdkInput) {
    cmdkInput.addEventListener('input', function(){ renderCmdkList(cmdkInput.value); });
    cmdkInput.addEventListener('focus', function(){
      loadRepoSuggestions().then(function(){ renderCmdkList(cmdkInput.value); });
    });
    cmdkInput.addEventListener('keydown', function(e){
      const list = $('r8-cmdk-list'); if (!list) return;
      const items = Array.prototype.slice.call(list.querySelectorAll('li'));
      let idx = items.findIndex(function(li){ return li.classList.contains('r8-active'); });
      if (e.key === 'ArrowDown') { e.preventDefault(); if (idx >= 0) items[idx].classList.remove('r8-active'); idx = (idx + 1) % items.length; items[idx].classList.add('r8-active'); items[idx].scrollIntoView({block:'nearest'}); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); if (idx >= 0) items[idx].classList.remove('r8-active'); idx = (idx - 1 + items.length) % items.length; items[idx].classList.add('r8-active'); items[idx].scrollIntoView({block:'nearest'}); }
      else if (e.key === 'Enter')  { e.preventDefault(); if (items[idx]) items[idx].click(); }
    });
  }

  // File finder: pulls a deterministic per-repo file list from the
  // server's existing code-search endpoint when on a repo page.
  function detectRepoPath() {
    const m = window.location.pathname.match(/^\/([^/]+)\/([^/]+)(?:\/|$)/);
    if (!m) return null;
    const reserved = new Set(['settings','notifications','search','new',
      'topics','trending','explore','marketplace','pricing','sponsors',
      'codespaces','copilot','skills','customer-stories','resources',
      'about','contact','privacy','terms','login','register','logout',
      'docs','api','blog','status','enterprise','education','solutions',
      'i18n','sitemap.xml','robots.txt','releases.rss','help','developer',
      'webhook','healthz','account','stars','watching','orgs']);
    if (reserved.has(m[1])) return null;
    return { owner: m[1], repo: m[2] };
  }

  function renderFileList(filter, files) {
    const list = $('r8-filefinder-list');
    if (!list) return;
    const ql = (filter || '').trim().toLowerCase();
    const hits = (files || []).filter(function(f){
      return !ql || f.toLowerCase().indexOf(ql) >= 0;
    }).slice(0, 30);
    list.innerHTML = '';
    if (!hits.length) {
      list.innerHTML = '<li class="r8-mk-meta">No files match.</li>';
      return;
    }
    hits.forEach(function(f, i){
      const li = document.createElement('li');
      li.setAttribute('role','option');
      if (i === 0) li.classList.add('r8-active');
      li.textContent = f;
      list.appendChild(li);
    });
  }

  function openFileFinder() {
    const ctx = detectRepoPath();
    const input = $('r8-filefinder-input');
    const list  = $('r8-filefinder-list');
    if (!ctx) {
      openModal('file');
      if (list) list.innerHTML = '<li class="r8-mk-meta">Open a repository page first, then press t.</li>';
      return;
    }
    // Deterministic stub list — mirrors the file shapes used in repo_code_search.
    const FILES_BY_LANG = ['src/main.py','src/cli.py','src/__init__.py',
      'tests/test_main.py','tests/test_cli.py',
      'README.md','LICENSE','CHANGELOG.md',
      'docs/architecture.md','docs/api.md','docs/contributing.md',
      'pyproject.toml','package.json','tsconfig.json',
      'Cargo.toml','go.mod','Dockerfile','.github/workflows/ci.yml'];
    openModal('file');
    if (input) {
      input.value = '';
      renderFileList('', FILES_BY_LANG);
      input.oninput = function(){ renderFileList(input.value, FILES_BY_LANG); };
      input.onkeydown = function(e){
        if (e.key === 'Enter') {
          const li = list.querySelector('li.r8-active') || list.querySelector('li');
          if (li && li.textContent && !li.classList.contains('r8-mk-meta')) {
            window.location.href = '/' + ctx.owner + '/' + ctx.repo +
                                   '/blob/main/' + li.textContent;
          }
        }
      };
    }
  }

  // Vim-style chord state for g<key>.
  let chordPrefix = null;
  let chordTimer = null;
  function resetChord() { chordPrefix = null; if (chordTimer) clearTimeout(chordTimer); chordTimer = null; }

  document.addEventListener('keydown', function(e){
    if (isEditable(e.target)) return;
    // Modifier handling for Cmd+K / Ctrl+K
    if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
      e.preventDefault();
      openModal('cmdk');
      return;
    }
    if (e.metaKey || e.altKey || e.ctrlKey) return;

    // Esc closes any open modal
    if (e.key === 'Escape') { closeAllModals(); resetChord(); return; }

    if (chordPrefix === 'g') {
      const ctx = detectRepoPath();
      const k = e.key.toLowerCase();
      if (k === 'i' && ctx) { e.preventDefault(); window.location.href = '/' + ctx.owner + '/' + ctx.repo + '/issues'; resetChord(); return; }
      if (k === 'p' && ctx) { e.preventDefault(); window.location.href = '/' + ctx.owner + '/' + ctx.repo + '/pulls'; resetChord(); return; }
      if (k === 'b' && ctx) { e.preventDefault(); window.location.href = '/' + ctx.owner + '/' + ctx.repo + '/branches'; resetChord(); return; }
      if (k === 's') { e.preventDefault(); window.location.href = '/settings/profile'; resetChord(); return; }
      if (k === 'n') { e.preventDefault(); window.location.href = '/notifications'; resetChord(); return; }
      resetChord();
      return;
    }

    switch (e.key) {
      case '/':
        e.preventDefault();
        const s = document.querySelector('.gh-search-input');
        if (s) { s.focus(); s.select(); }
        break;
      case '?':
        e.preventDefault();
        openModal('help');
        break;
      case 't':
        e.preventDefault();
        openFileFinder();
        break;
      case 'g':
        chordPrefix = 'g';
        if (chordTimer) clearTimeout(chordTimer);
        chordTimer = setTimeout(resetChord, 1200);
        break;
    }
  });

  // Contextual-help tooltips. For every glossary term, wrap its first
  // occurrence inside <main> with a hover-tip. Skip headings, inputs, code
  // blocks and pre — those carry too much risk of broken DOM.
  (function applyGlossaryTooltips(){
    const dict = window.R8_GLOSSARY || {};
    const terms = Object.keys(dict).sort(function(a,b){ return b.length - a.length; });
    if (!terms.length) return;
    const main = document.querySelector('main.gh-main') || document.body;
    const SKIP_TAGS = new Set(['SCRIPT','STYLE','CODE','PRE','KBD','INPUT',
                               'TEXTAREA','H1','H2','H3','BUTTON','A']);
    const seen = new Set();
    const walker = document.createTreeWalker(main, NodeFilter.SHOW_TEXT, {
      acceptNode: function(n){
        if (!n.nodeValue || !n.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        const p = n.parentNode;
        if (!p || SKIP_TAGS.has(p.tagName)) return NodeFilter.FILTER_REJECT;
        if (p.classList && p.classList.contains('r8-help-term')) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    const nodes = [];
    let cur;
    while ((cur = walker.nextNode())) nodes.push(cur);
    nodes.forEach(function(node){
      let text = node.nodeValue;
      let frag = null;
      let cursor = 0;
      for (let ti = 0; ti < terms.length; ti++) {
        const term = terms[ti];
        if (seen.has(term)) continue;
        const idx = text.toLowerCase().indexOf(term.toLowerCase(), cursor);
        if (idx < 0) continue;
        // Avoid partial-word matches for short single tokens.
        if (term.length < 5 && !/^\W/.test(text[idx-1] || ' ')) continue;
        seen.add(term);
        frag = frag || document.createDocumentFragment();
        if (idx > cursor) frag.appendChild(document.createTextNode(text.slice(cursor, idx)));
        const span = document.createElement('span');
        span.className = 'r8-help-term';
        span.title = dict[term];
        span.textContent = text.slice(idx, idx + term.length);
        frag.appendChild(span);
        cursor = idx + term.length;
      }
      if (frag) {
        if (cursor < text.length) frag.appendChild(document.createTextNode(text.slice(cursor)));
        node.parentNode.replaceChild(frag, node);
      }
    });
  })();
})();
