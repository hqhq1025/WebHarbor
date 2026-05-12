"""arxiv mirror health check."""
from healthcheck import random_user


def run(p):
    # 1. Home page
    p.assert_get('home', '/', must_contain='arXiv')

    # 2. Search — uses ?query= param (see app.py:999)
    p.assert_get(
        'search learning',
        '/search?searchtype=all&query=learning',
        must_contain='learning',
    )

    # 3. Paper detail — real arxiv_id from papers.json seed data
    p.assert_get('paper detail', '/abs/2604.08525', must_contain='Abstract')

    # 4. Register page
    user = random_user()
    html = p.assert_get('register page', '/register', must_contain='password')
    token = p.csrf(html)
    if not token:
        p.check('register csrf token', False, 'no csrf token in register form')
        return

    # 5. Register submit — fields: email, username, full_name, password, confirm_password
    p.assert_post(
        'register submit',
        '/register',
        {
            'csrf_token': token,
            'email': user['email'],
            'username': user['username'],
            'full_name': user['name'],
            'password': user['password'],
            'confirm_password': user['password'],
        },
        accept_status=(200, 302, 303),
    )

    # 6. Login page (log out first via fresh GET; register auto-logs-in but that's fine —
    # we still want to exercise the login path explicitly)
    p.get('/logout')
    html = p.assert_get('login page', '/login', must_contain='password')
    token = p.csrf(html)
    if not token:
        p.check('login csrf token', False, 'no csrf token in login form')
        return

    # 7. Login submit
    p.assert_post(
        'login submit',
        '/login',
        {
            'csrf_token': token,
            'email': user['email'],
            'password': user['password'],
        },
        accept_status=(200, 302, 303),
    )

    # 8. Authenticated page — /library requires login
    p.assert_get('library page', '/library', accept_status=(200, 302))
