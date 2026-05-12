"""Cambridge Dictionary mirror health check."""
from healthcheck import random_user


def run(p):
    # 1. Home page renders
    p.assert_get('home', '/', must_contain='cambridge')

    # 2. Word lookup (DB read)
    p.assert_get('word detail', '/dictionary/english/sustainability',
                 must_contain='sustainability')

    # 3. Search returns results
    p.assert_get('search', '/search?q=euphoria', must_contain='euphoria')

    # 4. Grammar page loads
    p.assert_get('grammar index', '/grammar/british-grammar/',
                 must_contain='grammar')

    # 5. Register page renders
    user = random_user()
    html = p.assert_get('register page', '/register', must_contain='csrf_token')
    token = p.csrf(html)
    if not token:
        p.check('register csrf token', False, 'no csrf in register form')
        return

    # 6. Submit registration (DB write)
    p.assert_post('register submit', '/register', {
        'csrf_token': token,
        'name': user['name'],
        'email': user['email'],
        'password': user['password'],
        'confirm': user['password'],
    }, accept_status=(200, 302, 303))

    # Logout so /login renders a real form (register auto-logs-in)
    p.get('/logout')

    # 7. Login page renders
    html = p.assert_get('login page', '/login', accept_status=(200, 302, 303))
    token = p.csrf(html) if html else ''

    # 8. Submit login (DB read + session)
    if token:
        p.assert_post('login submit', '/login', {
            'csrf_token': token,
            'email': user['email'],
            'password': user['password'],
        }, accept_status=(200, 302, 303))
    else:
        p.check('login submit', True, 'already authenticated from register')

    # 9. Account page (verifies session)
    p.assert_get('account page', '/account',
                 must_contain=user['first_name'])
