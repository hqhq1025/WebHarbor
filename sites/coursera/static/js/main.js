// Coursera Mirror — main.js
(function() {
  'use strict';

  // Flash auto-dismiss
  document.querySelectorAll('.flash').forEach(function(el) {
    setTimeout(function() { el.remove(); }, 5000);
  });

  // Enroll button
  var enrollBtn = document.querySelector('.btn-enroll[data-course-id]');
  if (enrollBtn) {
    enrollBtn.addEventListener('click', function() {
      var courseId = this.dataset.courseId;
      var btn = this;
      btn.textContent = 'Enrolling...';
      btn.disabled = true;
      fetch('/api/enroll', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ course_id: parseInt(courseId) })
      })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (data.success) {
          btn.textContent = '✓ Enrolled';
          btn.classList.add('enrolled-btn');
        } else {
          btn.textContent = 'Enroll Now';
          btn.disabled = false;
        }
      })
      .catch(function() {
        btn.textContent = 'Enroll Now';
        btn.disabled = false;
      });
    });
  }

  // Save/wishlist toggle
  var saveBtn = document.querySelector('.btn-save[data-course-id]');
  if (saveBtn) {
    saveBtn.addEventListener('click', function() {
      var courseId = this.dataset.courseId;
      var btn = this;
      fetch('/api/wishlist/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ course_id: parseInt(courseId) })
      })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (data.saved) {
          btn.textContent = '♥ Saved';
          btn.classList.add('saved');
        } else {
          btn.textContent = '♡ Save';
          btn.classList.remove('saved');
        }
      });
    });
  }

  // Filter form: auto-submit on select change
  document.querySelectorAll('.search-filters select').forEach(function(sel) {
    sel.addEventListener('change', function() {
      document.getElementById('filter-form').submit();
    });
  });

  // Filter pills (search page): only one open at a time, ESC closes,
  // outside-click closes, AND any input change auto-submits the form
  // — so picking a radio actually filters (matches user expectation).
  var pillRow = document.querySelector('.filter-pill-row');
  var pills   = pillRow ? pillRow.querySelectorAll('.filter-pill') : [];
  if (pills.length) {
    pills.forEach(function(d) {
      d.addEventListener('toggle', function() {
        if (!d.open) return;
        pills.forEach(function(other) {
          if (other !== d && other.open) other.open = false;
        });
      });
    });
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') {
        pills.forEach(function(d) { if (d.open) d.open = false; });
      }
    });
    document.addEventListener('click', function(e) {
      if (e.target.closest('.filter-pill')) return;
      pills.forEach(function(d) { if (d.open) d.open = false; });
    });

    // Auto-submit form on any filter input change so picking a radio
    // (rating, level, type, …) actually applies the filter immediately.
    var form = document.getElementById('filter-form');
    if (form) {
      form.querySelectorAll('input[type=radio], input[type=checkbox], select')
          .forEach(function(el) {
        el.addEventListener('change', function() {
          form.submit();
        });
      });
    }
  }

  // Scroll fade-in
  if ('IntersectionObserver' in window) {
    var fadeEls = document.querySelectorAll('.course-card, .degree-card, .benefit-card, .pf-item');
    var observer = new IntersectionObserver(function(entries) {
      entries.forEach(function(e) {
        if (e.isIntersecting) {
          e.target.style.opacity = '1';
          e.target.style.transform = 'translateY(0)';
          observer.unobserve(e.target);
        }
      });
    }, { threshold: 0.05 });
    fadeEls.forEach(function(el) {
      el.style.opacity = '0';
      el.style.transform = 'translateY(16px)';
      el.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      observer.observe(el);
    });
    // Ensure visible after short timeout (for test clients)
    setTimeout(function() {
      fadeEls.forEach(function(el) {
        el.style.opacity = '1';
        el.style.transform = 'translateY(0)';
      });
    }, 300);
  }

  /* ─── R5 polish ─────────────────────────────────────────────────────── */

  // Course-card hover preview (800ms intent delay so it doesn't fire on
  // accidental mouse-over).
  var previewTimer = null;
  document.querySelectorAll('.result-card[data-preview-url]').forEach(function(card) {
    card.addEventListener('mouseenter', function() {
      if (previewTimer) clearTimeout(previewTimer);
      previewTimer = setTimeout(function() {
        card.classList.add('is-preview-on');
      }, 800);
    });
    card.addEventListener('mouseleave', function() {
      if (previewTimer) clearTimeout(previewTimer);
      card.classList.remove('is-preview-on');
    });
    card.addEventListener('focusin', function() {
      card.classList.add('is-preview-on');
    });
    card.addEventListener('focusout', function() {
      card.classList.remove('is-preview-on');
    });
  });

  // Sticky filter pill row — drop a shadow once it sticks.
  var pillFormSticky = document.querySelector('.search-page .filter-pill-row');
  if (pillFormSticky && 'IntersectionObserver' in window) {
    var sentinel = document.createElement('div');
    sentinel.style.height = '1px';
    pillFormSticky.parentNode.insertBefore(sentinel, pillFormSticky);
    var stickObs = new IntersectionObserver(function(entries) {
      entries.forEach(function(e) {
        pillFormSticky.classList.toggle('is-stuck', !e.isIntersecting);
      });
    });
    stickObs.observe(sentinel);
  }

  // In-quiz timer with auto-save (assignment page only).
  var qBar = document.querySelector('.quiz-timer-bar');
  var qAns = document.querySelector('.quiz-answer');
  if (qBar && qAns) {
    var qKey = 'coursera_quiz_' + (qBar.dataset.quizKey || 'default');
    var qClock = qBar.querySelector('.qt-clock');
    var qState = qBar.querySelector('.qt-state');
    // Restore prior draft
    try {
      var saved = JSON.parse(localStorage.getItem(qKey) || 'null');
      if (saved && typeof saved.body === 'string') {
        qAns.value = saved.body;
        qState.textContent = 'Restored draft from ' + new Date(saved.t).toLocaleTimeString();
      }
    } catch (e) { /* ignore */ }
    // Tick clock (counts up; due in N minutes shown alongside).
    var startT = Date.now();
    function tick() {
      var s = Math.floor((Date.now() - startT) / 1000);
      var mm = String(Math.floor(s / 60)).padStart(2, '0');
      var ss = String(s % 60).padStart(2, '0');
      qClock.textContent = mm + ':' + ss;
    }
    tick();
    setInterval(tick, 1000);
    // Auto-save every 30s + every input pause.
    var saveTimer = null;
    function persist() {
      try {
        localStorage.setItem(qKey, JSON.stringify({
          body: qAns.value, t: Date.now()
        }));
        qState.classList.add('is-saved');
        qState.textContent = 'Auto-saved at ' + new Date().toLocaleTimeString();
        setTimeout(function() { qState.classList.remove('is-saved'); }, 1500);
      } catch (e) { /* quota or disabled */ }
    }
    qAns.addEventListener('input', function() {
      if (saveTimer) clearTimeout(saveTimer);
      saveTimer = setTimeout(persist, 1000);
    });
    setInterval(persist, 30000);
  }

  // Certificate share modal trigger.
  var shareBtn = document.querySelector('[data-share-cert]');
  var shareModal = document.querySelector('.cert-share-modal');
  if (shareBtn && shareModal) {
    shareBtn.addEventListener('click', function() {
      shareModal.classList.add('is-open');
    });
    shareModal.addEventListener('click', function(e) {
      if (e.target === shareModal || e.target.classList.contains('csm-close')) {
        shareModal.classList.remove('is-open');
      }
    });
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') shareModal.classList.remove('is-open');
    });
  }

  // Continue Learning panel — dismiss button persists choice in localStorage.
  var clp = document.querySelector('.continue-learning-panel');
  if (clp) {
    var dismissed = false;
    try { dismissed = localStorage.getItem('coursera_clp_dismissed') === '1'; }
    catch (e) { /* ignore */ }
    if (dismissed) clp.style.display = 'none';
    var closeBtn = clp.querySelector('.clp-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', function() {
        clp.style.display = 'none';
        try { localStorage.setItem('coursera_clp_dismissed', '1'); } catch (e) {}
      });
    }
  }

  /* ─── R8 polish: keyboard shortcuts, command palette, glossary ───── */

  // The shortcut command-set powering both the command palette (Cmd+K)
  // and the keyboard map (j/k/space/etc.). Static commands first; the
  // catalogue surface (courses, partners, skills) is fetched once from
  // /api/v1 endpoints on first palette open and cached on `window`.
  var R8_STATIC_COMMANDS = [
    { label: 'Home',                    href: '/',                                kind: 'page' },
    { label: 'Search courses',          href: '/search',                          kind: 'page' },
    { label: 'Browse: Computer Science',href: '/browse/computer-science',         kind: 'category' },
    { label: 'Browse: Data Science',    href: '/browse/data-science',             kind: 'category' },
    { label: 'Browse: Business',        href: '/browse/business',                 kind: 'category' },
    { label: 'Browse: Information Technology', href: '/browse/information-technology', kind: 'category' },
    { label: 'Browse: Language Learning', href: '/browse/language-learning',      kind: 'category' },
    { label: 'Browse: Health',          href: '/browse/health',                   kind: 'category' },
    { label: 'Browse: Personal Development', href: '/browse/personal-development', kind: 'category' },
    { label: 'Degrees list',            href: '/degrees',                         kind: 'page' },
    { label: 'Professional Certificates', href: '/professional-certificates',     kind: 'page' },
    { label: 'Coursera Plus',           href: '/coursera-plus',                   kind: 'page' },
    { label: 'Partners',                href: '/partners',                        kind: 'page' },
    { label: 'Blog',                    href: '/blog',                            kind: 'page' },
    { label: 'Help Center',             href: '/help',                            kind: 'page' },
    { label: 'Careers',                 href: '/careers',                         kind: 'page' },
    { label: 'Mobile app',              href: '/mobile',                          kind: 'page' },
    { label: 'Accessibility statement', href: '/accessibility',                   kind: 'page' },
    { label: 'Public API v1 docs',      href: '/api/v1/docs',                     kind: 'page' },
    { label: 'Developer LTI integration', href: '/developer/lti-integration',     kind: 'page' },
    { label: 'Health endpoint (healthz)', href: '/healthz',                       kind: 'api' },
    { label: 'Uptime status',           href: '/api/uptime',                      kind: 'api' },
    { label: 'GraphQL v2 endpoint',     href: '/api/v2/graphql?query={courses(first:5){slug,title}}', kind: 'api' },
    { label: 'Enrollment webhook docs', href: '/webhook/enrollment',              kind: 'api' },
    { label: 'Wishlist',                href: '/wishlist',                        kind: 'page' },
    { label: 'My Account',              href: '/account',                         kind: 'page' },
    { label: 'Log in',                  href: '/login',                           kind: 'page' },
    { label: 'Open keyboard shortcut overlay', href: '#kbd',                      kind: 'shortcut' },
  ];

  // Skill glossary — used by tooltips and palette completion.
  var R8_SKILL_GLOSSARY = {
    'python':         'High-level, dynamically-typed programming language; the lingua franca of data science and machine learning.',
    'sql':            'Structured Query Language; the standard for relational databases.',
    'java':           'Strongly-typed, object-oriented language widely used in enterprise back-ends and Android.',
    'javascript':     'The language of the web — runs in browsers and Node.js back-ends.',
    'machine-learning':'A class of algorithms that learn patterns from data to make predictions or decisions.',
    'deep-learning':  'A subset of machine learning built on multi-layer neural networks.',
    'agentic-ai':     'Autonomous AI agents that plan, act with tools, and reflect to complete multi-step tasks.',
    'multimodal-rag': 'Retrieval-augmented generation extended across text, image, audio and video modalities.',
    'on-device-genai':'Generative AI inference that runs entirely on a phone, laptop or edge device with no server roundtrip.',
    'cybersecurity':  'The practice of protecting systems, networks and data from digital attacks.',
    'cloud-computing':'On-demand delivery of computing infrastructure and services over the internet.',
    'project-management':'The discipline of planning, executing and closing projects to meet defined goals.',
    'k-12-reading':   'Foundational reading instruction for kindergarten through twelfth grade learners.',
    'k-12-sel':       'Social-emotional learning — the K-12 curriculum for self-awareness, empathy and decision making.',
    'public-speaking':'The skill of preparing and delivering structured oral presentations to a live audience.',
    'negotiation':    'The structured process of reaching agreement between two or more parties with different interests.',
  };
  // Expose for any inline scripts that want to consult the glossary.
  window.R8_SKILL_GLOSSARY = R8_SKILL_GLOSSARY;

  // ── Command palette wiring ────────────────────────────────────────
  var palette = document.getElementById('r8-cmd-palette');
  var paletteInput = document.getElementById('r8-cmd-input');
  var paletteResults = document.getElementById('r8-cmd-results');
  var kbdOverlay = document.getElementById('r8-kbd-overlay');
  var kbdClose = kbdOverlay ? kbdOverlay.querySelector('.r8-kbd-close') : null;
  var paletteSelectedIdx = 0;
  var paletteItems = [];
  var paletteDynamicCache = null;

  function r8OpenPalette() {
    if (!palette) return;
    palette.hidden = false;
    paletteInput.value = '';
    paletteSelectedIdx = 0;
    r8FillPalette('');
    setTimeout(function() { paletteInput.focus(); }, 30);
  }
  function r8ClosePalette() { if (palette) palette.hidden = true; }
  function r8OpenKbd()      { if (kbdOverlay) kbdOverlay.hidden = false; }
  function r8CloseKbd()     { if (kbdOverlay) kbdOverlay.hidden = true; }

  function r8FillPalette(q) {
    if (!paletteResults) return;
    var qN = (q || '').trim().toLowerCase();
    // Augment static list with cached dynamic catalog rows on first open.
    var all = R8_STATIC_COMMANDS.slice();
    if (paletteDynamicCache) {
      all = all.concat(paletteDynamicCache);
    } else {
      // Kick off async load (don't block first render).
      paletteDynamicCache = []; // mark in-flight
      fetch('/api/v1/partners').then(function(r) { return r.json(); })
        .then(function(rows) {
          if (!Array.isArray(rows)) return;
          paletteDynamicCache = rows.map(function(p) {
            return { label: 'Partner: ' + p.name, href: '/partner/' + p.slug, kind: 'partner' };
          });
          if (!palette.hidden) r8FillPalette(paletteInput.value);
        })
        .catch(function() {});
    }
    var matches = !qN ? all.slice(0, 20)
        : all.filter(function(c) { return c.label.toLowerCase().indexOf(qN) !== -1; })
             .slice(0, 25);
    paletteItems = matches;
    paletteResults.innerHTML = '';
    matches.forEach(function(c, i) {
      var li = document.createElement('li');
      li.setAttribute('role', 'option');
      li.dataset.idx = String(i);
      li.className = 'r8-cmd-item' + (i === paletteSelectedIdx ? ' is-active' : '');
      li.innerHTML = '<span class="r8-cmd-kind">' + c.kind + '</span><span class="r8-cmd-label">'
        + c.label.replace(/</g, '&lt;') + '</span>';
      li.addEventListener('click', function() { r8RunPalette(c); });
      paletteResults.appendChild(li);
    });
    if (matches.length === 0) {
      paletteResults.innerHTML = '<li class="r8-cmd-empty">No matches. Try "course", "partner", "category", or a skill name.</li>';
    }
  }
  function r8RunPalette(cmd) {
    if (!cmd) return;
    if (cmd.href === '#kbd') { r8ClosePalette(); r8OpenKbd(); return; }
    r8ClosePalette();
    window.location = cmd.href;
  }
  if (paletteInput) {
    paletteInput.addEventListener('input', function() {
      paletteSelectedIdx = 0;
      r8FillPalette(this.value);
    });
    paletteInput.addEventListener('keydown', function(e) {
      if (e.key === 'ArrowDown') {
        paletteSelectedIdx = Math.min(paletteSelectedIdx + 1, paletteItems.length - 1);
        r8FillPalette(this.value); e.preventDefault();
      } else if (e.key === 'ArrowUp') {
        paletteSelectedIdx = Math.max(paletteSelectedIdx - 1, 0);
        r8FillPalette(this.value); e.preventDefault();
      } else if (e.key === 'Enter') {
        if (paletteItems[paletteSelectedIdx]) r8RunPalette(paletteItems[paletteSelectedIdx]);
        e.preventDefault();
      }
    });
  }
  if (palette) {
    palette.addEventListener('click', function(e) {
      if (e.target.classList.contains('r8-cmd-backdrop')) r8ClosePalette();
    });
  }
  if (kbdClose) kbdClose.addEventListener('click', r8CloseKbd);
  if (kbdOverlay) {
    kbdOverlay.addEventListener('click', function(e) {
      if (e.target.classList.contains('r8-cmd-backdrop')) r8CloseKbd();
    });
  }

  // ── Global key handler ────────────────────────────────────────────
  var gChord = null, gChordTimer = null;
  function r8InEditable(el) {
    if (!el) return false;
    var t = el.tagName;
    return t === 'INPUT' || t === 'TEXTAREA' || t === 'SELECT' || el.isContentEditable;
  }
  document.addEventListener('keydown', function(e) {
    // Cmd/Ctrl + K — palette
    if ((e.key === 'k' || e.key === 'K') && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      if (palette && !palette.hidden) { r8ClosePalette(); } else { r8OpenPalette(); }
      return;
    }
    // Esc — close overlays
    if (e.key === 'Escape') {
      if (palette && !palette.hidden) { r8ClosePalette(); return; }
      if (kbdOverlay && !kbdOverlay.hidden) { r8CloseKbd(); return; }
    }
    // Suppress single-key shortcuts when editing or when a modal is open
    if (r8InEditable(e.target)) return;
    if (palette && !palette.hidden) return;
    if (kbdOverlay && !kbdOverlay.hidden) return;
    // '/' — focus search
    if (e.key === '/') {
      var srch = document.querySelector('.nav-search input[type=text]');
      if (srch) { srch.focus(); srch.select(); e.preventDefault(); return; }
    }
    // '?' — open kbd overlay (Shift+/)
    if (e.key === '?') { r8OpenKbd(); e.preventDefault(); return; }
    // Two-key chords: g h, g s
    if (e.key === 'g' && !gChord) {
      gChord = 'g';
      if (gChordTimer) clearTimeout(gChordTimer);
      gChordTimer = setTimeout(function() { gChord = null; }, 800);
      return;
    }
    if (gChord === 'g') {
      gChord = null;
      if (gChordTimer) clearTimeout(gChordTimer);
      if (e.key === 'h') { window.location = '/'; return; }
      if (e.key === 's') { window.location = '/wishlist'; return; }
    }
    // Lecture-page navigation: j next, k prev
    if (e.key === 'j' || e.key === 'k') {
      // Detect lecture page by presence of week nav buttons in the cd-breadcrumb sibling nav
      var nextLink = document.querySelector('.lecture-page nav a[href*="/lecture/"]:last-of-type');
      var prevLinks = document.querySelectorAll('.lecture-page nav a[href*="/lecture/"]');
      if (prevLinks.length) {
        // Robust selection: first link whose label starts with '←' is prev, last with '→' is next
        var prevLink = null, nextLinkX = null;
        prevLinks.forEach(function(a) {
          if (/&larr;|←/.test(a.innerHTML) || a.textContent.trim().charAt(0) === '←') prevLink = a;
          else nextLinkX = a;
        });
        if (e.key === 'j' && nextLinkX) { window.location = nextLinkX.href; return; }
        if (e.key === 'k' && prevLink) { window.location = prevLink.href; return; }
      }
    }
    // Video mock-controls on lecture page
    if (document.querySelector('.lecture-page')) {
      if (e.key === ' ' || e.key === 'Spacebar') {
        // Toggle a body-level data attribute so the agent can verify the play/pause state.
        var st = document.body.getAttribute('data-video-state') || 'paused';
        document.body.setAttribute('data-video-state', st === 'paused' ? 'playing' : 'paused');
        e.preventDefault();
        return;
      }
      if (e.key === 'm' || e.key === 'M') {
        var ms = document.body.getAttribute('data-video-muted') === '1' ? '0' : '1';
        document.body.setAttribute('data-video-muted', ms);
        return;
      }
      if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
        var pos = parseInt(document.body.getAttribute('data-video-pos') || '0', 10);
        pos += (e.key === 'ArrowRight' ? 10 : -10);
        if (pos < 0) pos = 0;
        document.body.setAttribute('data-video-pos', String(pos));
        return;
      }
    }
  });

  // ── Skill glossary tooltip ────────────────────────────────────────
  var gloss = document.getElementById('r8-skill-glossary-tooltip');
  // Auto-decorate any .pill / .skill-chip / [data-skill] element whose
  // text matches a glossary key. Keeps the tooltip wired even on pages
  // that don't explicitly add the .skill-glossary class.
  function r8SlugifyText(t) {
    return (t || '').toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  }
  document.querySelectorAll('.skill-chip, .skill-pill, .pill, [data-skill]').forEach(function(el) {
    var key = el.dataset.skill || r8SlugifyText(el.textContent);
    if (R8_SKILL_GLOSSARY[key]) {
      el.classList.add('skill-glossary');
      el.dataset.skill = key;
    }
  });
  document.addEventListener('mouseover', function(e) {
    if (!gloss) return;
    var t = e.target.closest && e.target.closest('.skill-glossary');
    if (!t) return;
    var key = t.dataset.skill;
    var def = R8_SKILL_GLOSSARY[key];
    if (!def) return;
    gloss.textContent = def;
    var r = t.getBoundingClientRect();
    gloss.style.left = Math.max(8, r.left + window.scrollX) + 'px';
    gloss.style.top = (r.bottom + window.scrollY + 6) + 'px';
    gloss.hidden = false;
  });
  document.addEventListener('mouseout', function(e) {
    if (!gloss) return;
    if (e.target.closest && e.target.closest('.skill-glossary')) gloss.hidden = true;
  });

})();
