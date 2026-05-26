/* =====================================================
   ALLRECIPES MIRROR — JavaScript
   ===================================================== */

document.addEventListener('DOMContentLoaded', function() {

    // --- Flash message auto-dismiss ---
    document.querySelectorAll('.flash-msg').forEach(function(msg) {
        setTimeout(function() {
            msg.style.opacity = '0';
            msg.style.transform = 'translateY(-10px)';
            setTimeout(function() { msg.remove(); }, 300);
        }, 4000);
    });
    document.querySelectorAll('.flash-close').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var msg = btn.closest('.flash-msg');
            msg.style.opacity = '0';
            setTimeout(function() { msg.remove(); }, 200);
        });
    });

    // --- Toast notifications ---
    window.showToast = function(message, duration) {
        duration = duration || 3000;
        var existing = document.querySelector('.toast');
        if (existing) existing.remove();
        var toast = document.createElement('div');
        toast.className = 'toast';
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(function() { toast.classList.add('show'); }, 10);
        setTimeout(function() {
            toast.classList.remove('show');
            setTimeout(function() { toast.remove(); }, 300);
        }, duration);
    };

    // --- Recipe Box toggle ---
    document.querySelectorAll('.recipe-card-save, .recipe-action-btn.save-btn').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            var recipeId = btn.dataset.recipeId;
            if (!recipeId) return;
            fetch('/api/recipe-box/toggle', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({recipe_id: parseInt(recipeId)})
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.success) {
                    showToast(data.message);
                    if (data.saved) {
                        btn.classList.add('saved');
                        btn.innerHTML = btn.dataset.savedIcon || '&#9829;';
                    } else {
                        btn.classList.remove('saved');
                        btn.innerHTML = btn.dataset.unsavedIcon || '&#9825;';
                    }
                    // Update badge
                    var badge = document.querySelector('.recipe-box-badge');
                    if (badge) badge.textContent = data.count;
                } else if (data.message) {
                    window.location.href = '/login';
                }
            })
            .catch(function() {
                window.location.href = '/login';
            });
        });
    });

    // --- Ingredient checkbox toggling ---
    document.querySelectorAll('.ingredients-list li').forEach(function(li) {
        li.addEventListener('click', function() {
            li.classList.toggle('checked');
        });
    });

    // --- Star rating input ---
    var starInputs = document.querySelectorAll('.star-rating-input input');
    starInputs.forEach(function(input) {
        input.addEventListener('change', function() {
            var val = input.value;
            document.getElementById('rating-value-display')
            && (document.getElementById('rating-value-display').textContent = val + ' star' + (val > 1 ? 's' : ''));
        });
    });

    // --- Meal plan add ---
    document.querySelectorAll('.meal-plan-add-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var day = btn.dataset.day;
            var mealType = btn.dataset.meal;
            var select = document.querySelector('#recipe-select-' + day + '-' + mealType);
            if (!select) return;
            var recipeId = select.value;
            if (!recipeId) return;
            fetch('/api/meal-plan/add', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({recipe_id: parseInt(recipeId), day: day, meal_type: mealType})
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.success) {
                    showToast(data.message);
                    window.location.reload();
                }
            });
        });
    });

    // --- Meal plan remove ---
    document.querySelectorAll('.remove-meal').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var day = btn.dataset.day;
            var mealType = btn.dataset.meal;
            fetch('/api/meal-plan/remove', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({day: day, meal_type: mealType})
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.success) {
                    showToast(data.message);
                    window.location.reload();
                }
            });
        });
    });

    // --- Shopping list item remove ---
    document.querySelectorAll('.remove-item').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var listId = btn.dataset.listId;
            var index = parseInt(btn.dataset.index);
            fetch('/api/shopping-list/' + listId + '/remove', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({index: index})
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.success) {
                    btn.closest('li').remove();
                    showToast('Item removed');
                }
            });
        });
    });

    // --- Live search suggestions ---
    var searchInput = document.querySelector('.nav-search input');
    if (searchInput) {
        var timeout = null;
        searchInput.addEventListener('input', function() {
            clearTimeout(timeout);
            var q = searchInput.value.trim();
            var dropdown = document.querySelector('.search-suggestions');
            if (q.length < 2) {
                if (dropdown) dropdown.remove();
                return;
            }
            timeout = setTimeout(function() {
                fetch('/api/search?q=' + encodeURIComponent(q))
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (dropdown) dropdown.remove();
                    if (data.results.length === 0) return;
                    dropdown = document.createElement('div');
                    dropdown.className = 'search-suggestions';
                    dropdown.style.cssText = 'position:absolute;top:100%;left:0;right:0;background:white;border:1px solid #e0e0e0;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.1);z-index:1000;max-height:300px;overflow-y:auto;';
                    data.results.forEach(function(r) {
                        var a = document.createElement('a');
                        a.href = '/recipe/' + r.slug;
                        a.style.cssText = 'display:flex;align-items:center;gap:12px;padding:10px 14px;text-decoration:none;color:#222;font-size:0.9rem;border-bottom:1px solid #f0f0f0;';
                        a.innerHTML = '<span>' + r.title + '</span>';
                        a.addEventListener('mouseenter', function() { a.style.background = '#f7f7f7'; });
                        a.addEventListener('mouseleave', function() { a.style.background = 'white'; });
                        dropdown.appendChild(a);
                    });
                    searchInput.parentElement.appendChild(dropdown);
                });
            }, 300);
        });
        document.addEventListener('click', function(e) {
            if (!e.target.closest('.nav-search')) {
                var dd = document.querySelector('.search-suggestions');
                if (dd) dd.remove();
            }
        });
    }

    // --- Scroll animations ---
    if ('IntersectionObserver' in window) {
        var observer = new IntersectionObserver(function(entries) {
            entries.forEach(function(e) {
                if (e.isIntersecting) {
                    e.target.style.opacity = '1';
                    e.target.style.transform = 'translateY(0)';
                    observer.unobserve(e.target);
                }
            });
        }, { threshold: 0.1 });

        document.querySelectorAll('.recipe-card, .pd-gallery-section, .category-card').forEach(function(el) {
            el.style.opacity = '0';
            el.style.transform = 'translateY(20px)';
            el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            observer.observe(el);
        });
    }

    // ==========================================================
    // R5: nav-toggle drawer + form validation + meal-plan AJAX
    // ==========================================================

    // --- Mobile nav drawer toggle ---
    var navToggle = document.querySelector('.nav-toggle');
    var navCategories = document.querySelector('.nav-categories');
    if (navToggle && navCategories) {
        navToggle.addEventListener('click', function() {
            var isOpen = navCategories.classList.toggle('is-open');
            navToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
            navToggle.setAttribute('aria-label', isOpen ? 'Close menu' : 'Open menu');
        });
        // Close on outside click.
        document.addEventListener('click', function(e) {
            if (!navCategories.contains(e.target) && !navToggle.contains(e.target)) {
                if (navCategories.classList.contains('is-open')) {
                    navCategories.classList.remove('is-open');
                    navToggle.setAttribute('aria-expanded', 'false');
                    navToggle.setAttribute('aria-label', 'Open menu');
                }
            }
        });
    }

    // --- Inline form validation helpers ---
    function showFieldError(field, message) {
        if (!field) return;
        field.setAttribute('aria-invalid', 'true');
        var id = field.id || ('f_' + Math.random().toString(36).slice(2, 8));
        field.id = id;
        var errId = id + '__err';
        var existing = document.getElementById(errId);
        if (!existing) {
            existing = document.createElement('span');
            existing.id = errId;
            existing.className = 'form-error-msg';
            existing.setAttribute('role', 'alert');
            field.setAttribute('aria-describedby', errId);
            if (field.parentNode) field.parentNode.insertBefore(existing, field.nextSibling);
        }
        existing.textContent = message;
        existing.removeAttribute('hidden');
    }
    function clearFieldError(field) {
        if (!field) return;
        field.removeAttribute('aria-invalid');
        var id = field.id;
        if (!id) return;
        var existing = document.getElementById(id + '__err');
        if (existing) existing.setAttribute('hidden', 'hidden');
    }
    function validateEmail(v) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test((v || '').trim());
    }

    // --- Register form client-side validation ---
    var registerForm = document.querySelector('form[action*="register"], form[data-form="register"]');
    if (!registerForm) {
        // Fallback: locate by field set.
        var maybe = document.querySelector('input[name="confirm_password"]');
        if (maybe) registerForm = maybe.closest('form');
    }
    if (registerForm) {
        var usernameField = registerForm.querySelector('input[name="username"]');
        var emailField = registerForm.querySelector('input[name="email"]');
        var passwordField = registerForm.querySelector('input[name="password"]');
        var confirmField = registerForm.querySelector('input[name="confirm_password"]');

        [usernameField, emailField, passwordField, confirmField].forEach(function(f) {
            if (!f) return;
            f.addEventListener('blur', function() {
                if (f === usernameField) {
                    if (!f.value.trim()) showFieldError(f, 'Username is required.');
                    else if (f.value.trim().length < 3) showFieldError(f, 'Username must be at least 3 characters.');
                    else clearFieldError(f);
                } else if (f === emailField) {
                    if (!validateEmail(f.value)) showFieldError(f, 'Please enter a valid email address.');
                    else clearFieldError(f);
                } else if (f === passwordField) {
                    if (!f.value || f.value.length < 6) showFieldError(f, 'Password must be at least 6 characters.');
                    else clearFieldError(f);
                } else if (f === confirmField) {
                    if (passwordField && f.value !== passwordField.value) showFieldError(f, 'Passwords do not match.');
                    else clearFieldError(f);
                }
            });
            f.addEventListener('input', function() {
                if (f.getAttribute('aria-invalid') === 'true') {
                    // Re-validate as user types so the error clears once fixed.
                    f.dispatchEvent(new Event('blur'));
                }
            });
        });

        registerForm.addEventListener('submit', function(e) {
            var bad = false;
            if (usernameField && (!usernameField.value.trim() || usernameField.value.trim().length < 3)) {
                showFieldError(usernameField, 'Username must be at least 3 characters.');
                bad = true;
            }
            if (emailField && !validateEmail(emailField.value)) {
                showFieldError(emailField, 'Please enter a valid email address.');
                bad = true;
            }
            if (passwordField && passwordField.value.length < 6) {
                showFieldError(passwordField, 'Password must be at least 6 characters.');
                bad = true;
            }
            if (confirmField && passwordField && confirmField.value !== passwordField.value) {
                showFieldError(confirmField, 'Passwords do not match.');
                bad = true;
            }
            if (bad) {
                e.preventDefault();
                var firstBad = registerForm.querySelector('[aria-invalid="true"]');
                if (firstBad) firstBad.focus();
            }
        });
    }

    // --- Review / comment form client-side validation ---
    document.querySelectorAll('form[data-form="review"], form.review-form').forEach(function(rf) {
        rf.addEventListener('submit', function(e) {
            var bodyField = rf.querySelector('textarea[name="body"], textarea[name="comment"]');
            var ratingChosen = rf.querySelector('input[name="rating"]:checked');
            var bad = false;
            if (!ratingChosen) {
                var ratingFieldset = rf.querySelector('.star-rating-input') || rf;
                showFieldError(ratingFieldset, 'Please choose a star rating before submitting.');
                bad = true;
            }
            if (bodyField && bodyField.value.trim().length < 8) {
                showFieldError(bodyField, 'Reviews must be at least 8 characters long.');
                bad = true;
            }
            if (bad) e.preventDefault();
        });
    });

    // --- AJAX add-to-meal-plan from recipe detail page ---
    document.querySelectorAll('.add-to-meal-plan').forEach(function(widget) {
        var btn = widget.querySelector('.add-to-meal-plan-btn');
        var daySel = widget.querySelector('select[name="day"]');
        var mealSel = widget.querySelector('select[name="meal_type"]');
        var status = widget.querySelector('.add-to-meal-plan-status');
        var recipeId = widget.dataset.recipeId;
        if (!btn || !recipeId) return;
        btn.addEventListener('click', function() {
            var day = daySel ? daySel.value : 'monday';
            var mealType = mealSel ? mealSel.value : 'dinner';
            if (status) {
                status.textContent = 'Adding…';
                status.dataset.state = '';
            }
            fetch('/api/meal-plan/add', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({recipe_id: parseInt(recipeId), day: day, meal_type: mealType})
            })
            .then(function(r) { return r.json().then(function(d) { return {ok: r.ok, body: d}; }); })
            .then(function(res) {
                if (res.ok && res.body.success) {
                    if (status) {
                        status.textContent = 'Added to meal plan for ' + day + ' ' + mealType + '.';
                        status.dataset.state = '';
                    }
                    showToast(res.body.message || 'Added to meal plan');
                } else {
                    if (status) {
                        status.textContent = res.body.message || 'Please log in to add to your meal plan.';
                        status.dataset.state = 'error';
                    }
                }
            })
            .catch(function() {
                if (status) {
                    status.textContent = 'Network error — please try again.';
                    status.dataset.state = 'error';
                }
            });
        });
    });

    // --- Make all alt-less recipe-card images get a sensible alt at runtime ---
    document.querySelectorAll('.recipe-card img').forEach(function(img) {
        if (!img.alt || img.alt === '') {
            var title = img.closest('.recipe-card');
            var titleEl = title && (title.querySelector('.recipe-card-title') || title.querySelector('h3') || title.querySelector('h2'));
            if (titleEl) img.alt = titleEl.textContent.trim() + ' recipe photo';
        }
    });
});
