"""google_search mirror health check."""
from healthcheck import random_user


def run(p):
    p.assert_get('home', '/', must_contain='Google')

    # Seeded query 1: "Mount Kilimanjaro elevation" -> answer mentions "Kilimanjaro"
    p.assert_get('search query 1',
                 '/search?q=Mount+Kilimanjaro+elevation',
                 must_contain='Kilimanjaro')

    # Seeded query 2: "latest Fast and Furious movie release date" -> answer mentions "Fast X"
    p.assert_get('search query 2',
                 '/search?q=latest+Fast+and+Furious+movie+release+date',
                 must_contain='Fast X')

    user = random_user()
    html = p.assert_get('register page', '/register')
    token = p.csrf(html)
    if not token:
        p.check('register csrf', False, 'no csrf')
        return
    p.assert_post('register submit', '/register', {
        'csrf_token': token,
        'name':     user['name'],
        'email':    user['email'],
        'password': user['password'],
        'confirm':  user['password'],
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

    p.assert_get('search history', '/history', accept_status=(200, 302))
