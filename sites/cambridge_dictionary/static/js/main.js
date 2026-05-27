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

/* Cambridge Dictionary Mirror — main.js
 * R5: adds inline autocomplete definition preview, audio playback-speed,
 * recently-viewed badge (localStorage), swipe-to-flashcard, smart-folder
 * dropdown, quiz progress save/resume. All client-side — no schema change.
 */

// ---------------------------------------------------------------------------
// Autocomplete — with optional inline definition preview (R5)
// ---------------------------------------------------------------------------
(function() {
  const input = document.getElementById('searchInput');
  const list = document.getElementById('autocomplete-list');
  if (!input || !list) return;

  let debounceTimer;
  input.addEventListener('input', function() {
    clearTimeout(debounceTimer);
    const q = this.value.trim();
    if (q.length < 2) { list.innerHTML = ''; return; }
    debounceTimer = setTimeout(function() {
      // R5: ask for detail=1 so the dropdown shows a definition preview.
      fetch('/autocomplete?detail=1&q=' + encodeURIComponent(q))
        .then(r => r.json())
        .then(items => {
          list.innerHTML = '';
          if (!items.length) return;
          items.forEach(it => {
            // Support both legacy (string) and R5 (object) shapes.
            const isObj = typeof it === 'object' && it !== null;
            const headword = isObj ? it.headword : it;
            const preview  = isObj ? (it.preview || '') : '';
            const level    = isObj ? (it.level || '') : '';
            const div = document.createElement('div');
            div.className = 'ac-item';
            if (preview) div.classList.add('ac-item--with-preview');
            const top = document.createElement('div');
            top.className = 'ac-item-top';
            const hw = document.createElement('span');
            hw.className = 'ac-item-hw';
            hw.textContent = headword;
            top.appendChild(hw);
            if (level) {
              const badge = document.createElement('span');
              badge.className = 'ac-item-level cefr cefr-' + level.toLowerCase();
              badge.textContent = level;
              top.appendChild(badge);
            }
            div.appendChild(top);
            if (preview) {
              const p = document.createElement('div');
              p.className = 'ac-item-preview';
              p.textContent = preview;
              div.appendChild(p);
            }
            div.addEventListener('click', function() {
              input.value = headword;
              list.innerHTML = '';
              input.form.submit();
            });
            list.appendChild(div);
          });
        })
        .catch(() => {});
    }, 180);
  });

  document.addEventListener('click', function(e) {
    if (!input.contains(e.target) && !list.contains(e.target)) {
      list.innerHTML = '';
    }
  });
})();

// ---------------------------------------------------------------------------
// TTS pronunciation with playback-speed (R5)
// ---------------------------------------------------------------------------
window.__pronSpeed = 1.0;
function setPlaybackSpeed(btn, speed) {
  window.__pronSpeed = speed;
  document.querySelectorAll('.ps-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  // Apply to any preload <audio> elements on the page.
  document.querySelectorAll('audio.pron-audio').forEach(a => {
    try { a.playbackRate = speed; } catch (e) {}
  });
}

function speakWord(word, lang, btn) {
  if (!window.speechSynthesis) return;
  // Cancel any in-flight utterance to avoid queue pile-up.
  window.speechSynthesis.cancel();
  const utt = new SpeechSynthesisUtterance(word);
  utt.lang = lang || 'en-GB';
  // R5: respect the current playback speed control.
  const base = 0.85;
  utt.rate = Math.max(0.3, Math.min(2.0, base * (window.__pronSpeed || 1)));
  window.speechSynthesis.speak(utt);
}

// ---------------------------------------------------------------------------
// Save word toggle (XHR — kept for compatibility with /api/save-word)
// ---------------------------------------------------------------------------
function toggleSaveWord(wordId) {
  const btn = document.getElementById('saveWordBtn');
  if (!btn) return;
  const csrfToken = document.querySelector('meta[name="csrf-token"]');
  const headers = {'Content-Type': 'application/json'};
  if (csrfToken) headers['X-CSRFToken'] = csrfToken.content;

  fetch('/api/save-word', {
    method: 'POST',
    headers: headers,
    body: JSON.stringify({word_id: wordId})
  })
  .then(r => r.json())
  .then(data => {
    if (data.success) {
      if (data.saved) {
        btn.textContent = '★ Saved';
        btn.classList.add('saved');
      } else {
        btn.textContent = '☆ Save';
        btn.classList.remove('saved');
      }
    }
  })
  .catch(() => {});
}

// ---------------------------------------------------------------------------
// R5: Smart-folder dropdown — folder names live in localStorage; a server
// round-trip is intentionally skipped so we don't add a schema column. The
// "Saved" button (above) still POSTs to /words/save/<id> for the canonical
// SavedWord row.
// ---------------------------------------------------------------------------
function addToSmartFolder(sel, headword, slug) {
  let folder = sel.value;
  if (!folder) return;
  if (folder === '__new__') {
    folder = (window.prompt('Folder name?') || '').trim();
    if (!folder) { sel.value = ''; return; }
  }
  const KEY = 'cd_smart_folders';
  let store = {};
  try { store = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) {}
  if (!store[folder]) store[folder] = [];
  if (!store[folder].find(x => x.slug === slug)) {
    store[folder].push({slug: slug, headword: headword, added: Date.now()});
  }
  try { localStorage.setItem(KEY, JSON.stringify(store)); } catch (e) {}
  const status = document.getElementById('smartFolderStatus');
  if (status) {
    status.textContent = '✓ Added to "' + folder + '" (' + store[folder].length + ' words).';
  }
  sel.value = '';
}

// ---------------------------------------------------------------------------
// R5: Recently-viewed badge — counts unique slugs seen this device, capped
// at 50. Updated on every word_detail render via the .recently-viewed-beacon.
// ---------------------------------------------------------------------------
(function() {
  const beacon = document.querySelector('.recently-viewed-beacon');
  const KEY = 'cd_recently_viewed';
  let store = [];
  try { store = JSON.parse(localStorage.getItem(KEY) || '[]'); } catch (e) {}
  if (beacon) {
    const slug = beacon.dataset.slug;
    const headword = beacon.dataset.headword;
    const ipa = beacon.dataset.ipa;
    const level = beacon.dataset.level;
    // Move-to-front behaviour: drop existing, prepend new.
    store = store.filter(x => x.slug !== slug);
    store.unshift({slug: slug, headword: headword, ipa: ipa, level: level, ts: Date.now()});
    if (store.length > 50) store = store.slice(0, 50);
    try { localStorage.setItem(KEY, JSON.stringify(store)); } catch (e) {}
    // Tell server so footer/back-nav can also surface a number without
    // peeking at localStorage (server-rendered badge then matches).
    const csrf = document.querySelector('meta[name="csrf-token"]');
    fetch('/api/recently-viewed', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(csrf ? {'X-CSRFToken': csrf.content} : {}),
      },
      body: JSON.stringify({count: store.length}),
    }).catch(() => {});
  }
  const badge = document.getElementById('rvBadge');
  if (badge) {
    const count = store.length || parseInt(badge.dataset.serverCount || '0', 10);
    badge.textContent = String(count);
    badge.classList.toggle('rv-badge--empty', count === 0);
  }
})();

// ---------------------------------------------------------------------------
// Quiz logic — with R5 progress save/resume via localStorage
// ---------------------------------------------------------------------------
var quizScore = 0;
var totalQuestions = 0;

(function() {
  // On quiz load, if there's a saved partial session, restore it.
  const quizRoot = document.querySelector('[data-quiz-slug]');
  if (!quizRoot) return;
  const slug = quizRoot.dataset.quizSlug;
  const KEY = 'cd_quiz_progress::' + slug;
  let saved = null;
  try { saved = JSON.parse(localStorage.getItem(KEY) || 'null'); } catch (e) {}
  if (saved && typeof saved.idx === 'number' && saved.idx > 0) {
    // Show "Resume from question N?" banner.
    const banner = document.createElement('div');
    banner.className = 'quiz-resume-banner';
    banner.innerHTML = 'You have a saved attempt at question ' + (saved.idx + 1) +
      ' with ' + (saved.score || 0) + ' correct so far. ' +
      '<button class="quiz-resume-yes" type="button">Resume</button> ' +
      '<button class="quiz-resume-no" type="button">Start over</button>';
    quizRoot.insertBefore(banner, quizRoot.firstChild);
    banner.querySelector('.quiz-resume-yes').addEventListener('click', function() {
      quizScore = saved.score || 0;
      const cur = document.getElementById('q0');
      if (cur) cur.style.display = 'none';
      const next = document.getElementById('q' + saved.idx);
      if (next) next.style.display = 'block';
      banner.remove();
    });
    banner.querySelector('.quiz-resume-no').addEventListener('click', function() {
      localStorage.removeItem(KEY);
      banner.remove();
    });
  }
})();

function _quizSaveProgress(idx) {
  const quizRoot = document.querySelector('[data-quiz-slug]');
  if (!quizRoot) return;
  const slug = quizRoot.dataset.quizSlug;
  try {
    localStorage.setItem('cd_quiz_progress::' + slug,
      JSON.stringify({idx: idx, score: quizScore, ts: Date.now()}));
  } catch (e) {}
}

function selectAnswer(btn, optIdx, correctIdx, qIdx) {
  const qDiv = document.getElementById('q' + qIdx);
  if (!qDiv) return;
  const allBtns = qDiv.querySelectorAll('.q-option-btn');
  allBtns.forEach(b => b.disabled = true);

  const feedback = document.getElementById('feedback' + qIdx);
  const nextBtn = document.getElementById('next' + qIdx);

  if (optIdx === correctIdx) {
    btn.classList.add('correct');
    quizScore++;
    if (feedback) {
      feedback.textContent = '✓ Correct!';
      feedback.className = 'q-feedback correct-fb';
      feedback.style.display = 'block';
    }
  } else {
    btn.classList.add('wrong');
    allBtns[correctIdx].classList.add('correct');
    if (feedback) {
      feedback.textContent = '✗ Incorrect. The correct answer is: ' + allBtns[correctIdx].textContent.trim();
      feedback.className = 'q-feedback wrong-fb';
      feedback.style.display = 'block';
    }
  }
  if (nextBtn) nextBtn.style.display = 'inline-block';
  _quizSaveProgress(qIdx);
}

function nextQuestion(currentIdx, total) {
  const current = document.getElementById('q' + currentIdx);
  if (current) current.style.display = 'none';

  const nextIdx = currentIdx + 1;
  if (nextIdx < total) {
    const next = document.getElementById('q' + nextIdx);
    if (next) next.style.display = 'block';
    _quizSaveProgress(nextIdx);
  } else {
    const result = document.getElementById('quiz-result');
    if (result) {
      result.style.display = 'block';
      const scoreEl = document.getElementById('final-score');
      if (scoreEl) scoreEl.textContent = quizScore;
      const msgEl = document.getElementById('result-message');
      if (msgEl) {
        const pct = Math.round((quizScore / total) * 100);
        if (pct >= 80) msgEl.textContent = 'Excellent! Great vocabulary knowledge.';
        else if (pct >= 60) msgEl.textContent = 'Good job! Keep practising to improve further.';
        else msgEl.textContent = 'Keep practising! You\'ll improve with more study.';
      }
    }
    // Quiz complete — wipe the resume snapshot.
    const quizRoot = document.querySelector('[data-quiz-slug]');
    if (quizRoot) {
      try { localStorage.removeItem('cd_quiz_progress::' + quizRoot.dataset.quizSlug); } catch (e) {}
    }
  }
}

// ---------------------------------------------------------------------------
// Word Scramble (unchanged from R4)
// ---------------------------------------------------------------------------
var scrambleTimer = null;
var scrambleTime = 30;

(function initScramble() {
  const game = document.getElementById('scrambleGame');
  if (!game) return;
  startTimer();
})();

function startTimer() {
  const display = document.getElementById('timerDisplay');
  const fill = document.getElementById('timerFill');
  if (!display) return;
  scrambleTime = 30;
  scrambleTimer = setInterval(function() {
    scrambleTime--;
    display.textContent = scrambleTime;
    if (fill) fill.style.width = (scrambleTime / 30 * 100) + '%';
    if (scrambleTime <= 0) {
      clearInterval(scrambleTimer);
      const fb = document.getElementById('scrambleFeedback');
      if (fb) {
        fb.textContent = '⏱ Time\'s up! Better luck next time.';
        fb.className = 'scramble-feedback wrong';
      }
      const input = document.getElementById('scrambleInput');
      if (input) input.disabled = true;
    }
  }, 1000);
}

function checkScramble(correctWord) {
  const input = document.getElementById('scrambleInput');
  const fb = document.getElementById('scrambleFeedback');
  if (!input || !fb) return;
  const answer = input.value.trim().toLowerCase();
  if (answer === correctWord.toLowerCase()) {
    clearInterval(scrambleTimer);
    fb.textContent = '\u{1F389} Correct! Well done!';
    fb.className = 'scramble-feedback correct';
    input.disabled = true;
  } else {
    fb.textContent = '✗ Not quite right. Try again!';
    fb.className = 'scramble-feedback wrong';
  }
}

function showHint(word) {
  const fb = document.getElementById('scrambleFeedback');
  if (fb) {
    fb.textContent = 'Hint: The word starts with "' + word[0] + '" and has ' + word.length + ' letters.';
    fb.className = 'scramble-feedback';
    fb.style.background = '#e8f4f8';
    fb.style.color = '#1a5276';
  }
}

// ---------------------------------------------------------------------------
// R5: Swipe-to-flashcard (touch + click + arrow keys)
// ---------------------------------------------------------------------------
window.__fcKnown = 0;
window.__fcUnknown = 0;
window.__fcIdx = 0;

function flipCard(btn) {
  const card = btn.closest('.fc-card');
  if (card) card.classList.toggle('fc-flipped');
}

function swipeCard(direction) {
  const deck = document.getElementById('flashcardDeck');
  if (!deck) return;
  const cards = deck.querySelectorAll('.fc-card');
  const idx = window.__fcIdx;
  if (idx >= cards.length) return;
  const card = cards[idx];
  card.classList.add(direction === 'left' ? 'fc-swipe-out-left' : 'fc-swipe-out-right');
  if (direction === 'right') window.__fcKnown++; else window.__fcUnknown++;
  setTimeout(function() {
    card.style.display = 'none';
    window.__fcIdx++;
    const next = cards[window.__fcIdx];
    if (next) {
      next.style.display = 'block';
      const prog = document.getElementById('fcProgress');
      if (prog) prog.textContent = (window.__fcIdx + 1);
    } else {
      const results = document.getElementById('fcResults');
      if (results) results.style.display = 'block';
      const k = document.getElementById('fcKnown');
      const u = document.getElementById('fcUnknown');
      if (k) k.textContent = window.__fcKnown;
      if (u) u.textContent = window.__fcUnknown;
    }
  }, 220);
}

(function initFlashcards() {
  const deck = document.getElementById('flashcardDeck');
  if (!deck) return;
  const cards = deck.querySelectorAll('.fc-card');
  cards.forEach(function(card, i) {
    if (i !== 0) card.style.display = 'none';

    // Touch swipe — track start X and decide direction on release.
    let startX = null;
    let curX = null;
    card.addEventListener('touchstart', function(e) {
      startX = e.touches[0].clientX;
    }, {passive: true});
    card.addEventListener('touchmove', function(e) {
      if (startX === null) return;
      curX = e.touches[0].clientX;
      const dx = curX - startX;
      card.style.transform = 'translateX(' + dx + 'px) rotate(' + (dx / 20) + 'deg)';
    }, {passive: true});
    card.addEventListener('touchend', function() {
      if (startX === null || curX === null) {
        card.style.transform = '';
        startX = curX = null;
        return;
      }
      const dx = curX - startX;
      card.style.transform = '';
      if (Math.abs(dx) > 80) {
        swipeCard(dx < 0 ? 'left' : 'right');
      }
      startX = curX = null;
    });
  });

  // Arrow keys
  document.addEventListener('keydown', function(e) {
    if (e.key === 'ArrowLeft') swipeCard('left');
    else if (e.key === 'ArrowRight') swipeCard('right');
    else if (e.key === ' ' || e.key === 'Enter') {
      const visible = Array.from(cards).find(c => c.style.display !== 'none');
      if (visible) visible.classList.toggle('fc-flipped');
      e.preventDefault();
    }
  });

  // If a focus slug was requested, jump straight to it.
  const focus = deck.dataset.focus;
  if (focus) {
    let target = -1;
    cards.forEach(function(c, i) { if (c.dataset.slug === focus) target = i; });
    if (target > 0) {
      cards.forEach((c, i) => { if (i !== target) c.style.display = 'none'; });
      cards[target].style.display = 'block';
      window.__fcIdx = target;
      const prog = document.getElementById('fcProgress');
      if (prog) prog.textContent = (target + 1);
    }
  }
})();

// ---------------------------------------------------------------------------
// Flash message auto-dismiss
// ---------------------------------------------------------------------------
document.querySelectorAll('.flash').forEach(function(el) {
  setTimeout(function() {
    el.style.opacity = '0';
    el.style.transition = 'opacity 0.5s';
    setTimeout(function() { el.remove(); }, 500);
  }, 5000);
});
