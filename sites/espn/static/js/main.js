/* ESPN Mirror - Main JavaScript */

document.addEventListener('DOMContentLoaded', function () {
    // Mobile navigation toggle
    const menuToggle = document.querySelector('.mobile-menu-toggle');
    const navLinks = document.querySelector('.nav-links');
    if (menuToggle && navLinks) {
        menuToggle.addEventListener('click', function () {
            navLinks.classList.toggle('open');
        });
    }

    // Flash message auto-dismiss
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            alert.style.opacity = '0';
            alert.style.transition = 'opacity 0.5s';
            setTimeout(function () { alert.remove(); }, 500);
        }, 4000);
    });

    // Scoreboard ticker auto-scroll
    const ticker = document.querySelector('.score-ticker-inner');
    if (ticker) {
        let pos = 0;
        const speed = 0.5;
        function scrollTicker() {
            pos -= speed;
            if (pos < -ticker.scrollWidth / 2) pos = 0;
            ticker.style.transform = 'translateX(' + pos + 'px)';
            requestAnimationFrame(scrollTicker);
        }
        if (ticker.children.length > 0) {
            scrollTicker();
        }
    }

    // Favorites toggle
    document.querySelectorAll('.btn-favorite').forEach(function (btn) {
        btn.addEventListener('click', function () {
            const type = btn.dataset.type;
            const id = btn.dataset.id;
            const csrfToken = document.querySelector('meta[name="csrf-token"]');
            fetch('/api/favorites/toggle', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken ? csrfToken.content : ''
                },
                body: JSON.stringify({ type: type, id: parseInt(id) })
            })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.success) {
                    btn.classList.toggle('active');
                    btn.textContent = data.action === 'added' ? '★ Favorited' : '☆ Favorite';
                }
            });
        });
    });

    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(function (tab) {
        tab.addEventListener('click', function () {
            const target = tab.dataset.target;
            document.querySelectorAll('.tab-btn').forEach(function (t) {
                t.classList.remove('active');
            });
            tab.classList.add('active');
            document.querySelectorAll('.tab-content').forEach(function (c) {
                c.style.display = 'none';
            });
            const el = document.getElementById(target);
            if (el) el.style.display = 'block';
        });
    });
});
