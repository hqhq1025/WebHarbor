"""booking mirror health check."""
from healthcheck import random_user


def run(p):
    p.assert_get('home', '/', must_contain='Booking')
    p.assert_get('search Paris', '/search?dest=Paris', must_contain='Paris')
    p.assert_get('property detail', '/property/drawing-house-paris',
                 must_contain='night')

    user = random_user()
    html = p.assert_get('register page', '/register')
    token = p.csrf(html)
    if not token:
        p.check('register csrf', False, 'no csrf')
        return
    p.assert_post('register submit', '/register', {
        'csrf_token': token,
        'first_name': user['first_name'],
        'last_name':  user['last_name'],
        'email':      user['email'],
        'password':   user['password'],
        'confirm':    user['password'],
    }, accept_status=(200, 302, 303))

    # Logout so /login renders a real form (register auto-logs-in).
    p.get('/logout')

    html = p.assert_get('login page', '/login')
    token = p.csrf(html)
    if not token:
        p.check('login csrf', False, 'no csrf')
        return
    p.assert_post('login submit', '/login', {
        'csrf_token': token,
        'email':    user['email'],
        'password': user['password'],
    }, accept_status=(200, 302, 303))

    p.assert_get('account', '/account', accept_status=(200, 302))
