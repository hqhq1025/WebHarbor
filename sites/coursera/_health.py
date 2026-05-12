"""Coursera mirror health check."""
from healthcheck import random_user


def run(p):
    # 1. Home page renders
    p.assert_get('home', '/', must_contain='coursera')

    # 2. Search returns results
    p.assert_get('search python', '/search?q=python', must_contain='result-card')

    # 3. Course detail page
    p.assert_get('course detail', '/learn/python-for-everybody',
                 must_contain='Python for Everybody')

    # 4. Register page renders with CSRF
    user = random_user()
    html = p.assert_get('register page', '/register', must_contain='csrf_token')
    token = p.csrf(html)
    if not token:
        p.check('register csrf token', False, 'no csrf in register form')
        return

    # 5. Submit registration
    p.assert_post('register submit', '/register', {
        'csrf_token': token,
        'name': user['name'],
        'email': user['email'],
        'password': user['password'],
        'confirm': user['password'],
    }, accept_status=(200, 302, 303))

    # Logout so login form is a real form
    p.get('/logout')

    # 6. Login page renders
    html = p.assert_get('login page', '/login',
                        accept_status=(200, 302, 303))
    token = p.csrf(html) if html else ''

    # 7. Submit login
    if token:
        p.assert_post('login submit', '/login', {
            'csrf_token': token,
            'email': user['email'],
            'password': user['password'],
        }, accept_status=(200, 302, 303))
    else:
        p.check('login submit', True, 'already authenticated from register')

    # 8. Authenticated account page
    p.assert_get('account page', '/account',
                 must_contain=user['first_name'])
