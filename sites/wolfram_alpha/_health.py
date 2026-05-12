"""wolfram_alpha mirror health check."""
from healthcheck import random_user


def run(p):
    # Home page
    p.assert_get('home', '/', must_contain='Wolfram')

    # Computational queries (seeded in expand_catalog.py).
    # Query 1: "derivative of x^2 when x=5.6" -> plaintext contains "11.2"
    p.assert_get(
        'compute derivative',
        '/input?i=derivative+of+x%5E2+when+x%3D5.6',
        must_contain='11.2',
    )
    # Query 2: "3^71 scientific notation" -> plaintext contains "1.5037"
    p.assert_get(
        'compute power scientific',
        '/input?i=3%5E71+scientific+notation+5+significant+figures',
        must_contain='1.5037',
    )

    # Topic browse (seeded subcategory topic slug)
    p.assert_get('topic browse', '/topic/calculus', must_contain='alculus')

    # Register
    user = random_user()
    html = p.assert_get('register page', '/register', must_contain='csrf_token')
    token = p.csrf(html)
    if not token:
        p.check('register csrf', False, 'no csrf token in register page')
        return
    p.check('register csrf', True)

    p.assert_post(
        'register submit',
        '/register',
        {
            'csrf_token': token,
            'email': user['email'],
            'username': user['username'],
            'password': user['password'],
            'confirm': user['password'],
        },
        accept_status=(200, 302, 303),
    )

    # Logout so /login renders a real form (register auto-logs-in).
    p.get('/logout')

    # Login (fresh session-level POST; cookies persist so we may already be
    # authenticated from register's auto-login, but exercise the login path).
    html = p.assert_get('login page', '/login', must_contain='csrf_token')
    token = p.csrf(html)
    if not token:
        p.check('login csrf', False, 'no csrf token in login page')
        return
    p.check('login csrf', True)

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

    # Authenticated read
    p.assert_get('account', '/account', accept_status=(200, 302))
    p.assert_get('history', '/history', accept_status=(200, 302))
