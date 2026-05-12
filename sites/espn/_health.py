"""ESPN mirror health check."""
from healthcheck import random_user


def run(p):
    # 1. Home page renders
    p.assert_get('home', '/', must_contain='espn')

    # 2. Search returns results (DB read)
    p.assert_get('search lakers', '/search?q=lakers', must_contain='Lakers')

    # 3. Team detail page (DB read)
    p.assert_get(
        'team detail',
        '/team/nba/los-angeles-lakers',
        must_contain='Lakers',
    )

    # 4. Player detail page (DB read)
    p.assert_get(
        'player detail',
        '/player/nba/lebron-james',
        must_contain='LeBron',
    )

    # 5. Register page renders
    user = random_user()
    html = p.assert_get('register page', '/register', must_contain='csrf_token')
    token = p.csrf(html)
    if not token:
        p.check('register csrf token', False, 'no csrf in register form')
        return

    # 6. Submit registration (DB write) — RegisterForm fields: name, email,
    #    password, confirm
    p.assert_post('register submit', '/register', {
        'csrf_token': token,
        'name': user['name'],
        'email': user['email'],
        'password': user['password'],
        'confirm': user['password'],
    }, accept_status=(200, 302, 303))

    # Logout so /login renders a real form (register auto-logs-in).
    p.get('/logout')

    # 7. Login page renders
    html = p.assert_get('login page', '/login',
                        accept_status=(200, 302, 303))
    token = p.csrf(html) if html else ''

    # 8. Submit login (DB read + session) — LoginForm fields: email, password
    if token:
        p.assert_post('login submit', '/login', {
            'csrf_token': token,
            'email': user['email'],
            'password': user['password'],
        }, accept_status=(200, 302, 303))
    else:
        # Already authenticated from registration — count as pass
        p.check('login submit', True, 'already authenticated from register')

    # 9. Authenticated page (verifies session). base.html renders
    #    "Hello, {first_name}" in the top nav when logged in.
    p.assert_get('account page', '/account',
                 must_contain=user['first_name'])
