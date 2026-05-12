/* Cambridge Dictionary Mirror — main.js */

// Autocomplete
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
      fetch('/autocomplete?q=' + encodeURIComponent(q))
        .then(r => r.json())
        .then(words => {
          list.innerHTML = '';
          if (!words.length) return;
          words.forEach(w => {
            const div = document.createElement('div');
            div.className = 'ac-item';
            div.textContent = w;
            div.addEventListener('click', function() {
              input.value = w;
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

// TTS pronunciation
function speakWord(word, lang) {
  if (!window.speechSynthesis) return;
  const utt = new SpeechSynthesisUtterance(word);
  utt.lang = lang || 'en-GB';
  utt.rate = 0.85;
  window.speechSynthesis.speak(utt);
}

// Save word toggle
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

// Quiz logic
var quizScore = 0;
var totalQuestions = 0;

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
}

function nextQuestion(currentIdx, total) {
  const current = document.getElementById('q' + currentIdx);
  if (current) current.style.display = 'none';

  const nextIdx = currentIdx + 1;
  if (nextIdx < total) {
    const next = document.getElementById('q' + nextIdx);
    if (next) next.style.display = 'block';
  } else {
    // Show results
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
  }
}

// Word Scramble
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
    fb.textContent = '🎉 Correct! Well done!';
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

// Flash message auto-dismiss
document.querySelectorAll('.flash').forEach(function(el) {
  setTimeout(function() {
    el.style.opacity = '0';
    el.style.transition = 'opacity 0.5s';
    setTimeout(function() { el.remove(); }, 500);
  }, 5000);
});
