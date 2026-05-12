"""Apple mirror health check."""
from healthcheck import random_user


def run(p):
    # 1. Home page
    p.assert_get('home', '/', must_contain='Apple')

    # 2. Search (real query that returns >=1 product)
    p.assert_get('search iphone', '/search?q=iphone', must_contain='iPhone')

    # 3. Product detail (real existing slug)
    p.assert_get('product detail', '/product/iphone-15-pro',
                 must_contain='iPhone 15 Pro')

    # 4. Register page + CSRF
    user = random_user()
    html = p.assert_get('register page', '/register', must_contain='Apple ID')
    token = p.csrf(html)
    if not token:
        p.check('register csrf token', False, 'no csrf')
        return

    # 5. Register submit (DB write) - RegisterForm has first_name,
    # last_name, email, password, confirm_password
    p.assert_post('register submit', '/register', {
        'csrf_token': token,
        'first_name': user['first_name'],
        'last_name': user['last_name'],
        'email': user['email'],
        'password': user['password'],
        'confirm_password': user['password'],
    }, accept_status=(200, 302, 303))

    # Logout so /login renders a real form (register auto-logs-in).
    p.get('/logout')

    # 6. Login page + CSRF
    html = p.assert_get('login page', '/login', must_contain='Sign in')
    token = p.csrf(html)
    if not token:
        p.check('login csrf token', False, 'no csrf')
        return

    # 7. Login submit - LoginForm has email, password, remember
    p.assert_post('login submit', '/login', {
        'csrf_token': token,
        'email': user['email'],
        'password': user['password'],
    }, accept_status=(200, 302, 303))

    # 8. Authenticated page (DB read via @login_required /account)
    p.assert_get('account page', '/account',
                 must_contain=user['first_name'])
