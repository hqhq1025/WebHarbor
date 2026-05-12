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
})();
