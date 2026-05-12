"""github mirror health check."""
from healthcheck import random_user


def run(p):
    # 1. Home page
    p.assert_get('home', '/', must_contain='GitHub')

    # 2. Search repositories (type=repositories per /search handler)
    p.assert_get('search react', '/search?q=react&type=repositories',
                 must_contain='react')

    # 3. Repo detail for a known seeded repo
    p.assert_get('repo detail facebook/react', '/facebook/react',
                 must_contain='react')

    # 4. Register new user
    user = random_user()
    html = p.assert_get('register page', '/register')
    token = p.csrf(html)
    if not token:
        p.check('register csrf', False, 'no csrf token on /register')
        return
    p.check('register csrf', True)
    p.assert_post('register submit', '/register', {
        'csrf_token': token,
        'username': user['username'],
        'email':    user['email'],
        'password': user['password'],
    }, accept_status=(200, 302, 303))

    # Logout so /login renders a real form (register auto-logs-in).
    p.get('/logout')

    # 5. Login (LoginForm field is `login`, accepts username or email)
    html = p.assert_get('login page', '/login')
    token = p.csrf(html)
    if not token:
        p.check('login csrf', False, 'no csrf token on /login')
        return
    p.check('login csrf', True)
    p.assert_post('login submit', '/login', {
        'csrf_token': token,
        'login':    user['username'],
        'password': user['password'],
    }, accept_status=(200, 302, 303))

    # 6. Authenticated read: own user profile
    p.assert_get('user profile', f'/{user["username"]}',
                 must_contain=user['username'],
                 accept_status=(200, 302))
