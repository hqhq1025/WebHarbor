"""bbc_news mirror health check."""
from healthcheck import random_user


# A real article slug from seeded data. expand_catalog.py builds this article
# in build_task_articles() via slugify() of the headline:
#   "UN warns deforestation is accelerating global climate tipping points"
ARTICLE_SLUG = "un-warns-deforestation-is-accelerating-global-climate-tipping-points"


def run(p):
    # Public pages
    p.assert_get('home', '/', must_contain='BBC')
    p.assert_get('search', '/search?q=climate', must_contain='climate')
    p.assert_get('article detail', '/article/' + ARTICLE_SLUG, must_contain='deforestation')
    # /sport is a redirect to /section/sport; accept either
    p.assert_get('sport section', '/sport', accept_status=(200, 301, 302, 303))
    p.assert_get('sport section page', '/section/sport', must_contain='Sport')

    # Registration
    user = random_user()
    html = p.assert_get('register page', '/register', must_contain='csrf_token')
    token = p.csrf(html)
    if not token:
        p.check('register csrf', False, 'no csrf token on /register')
        return
    p.check('register csrf', True)

    p.assert_post('register submit', '/register', {
        'csrf_token': token,
        'username': user['username'],
        'full_name': user['name'],
        'email': user['email'],
        'password': user['password'],
        'confirm_password': user['password'],
    }, accept_status=(200, 302, 303))

    # Logout so /login renders a real form (register auto-logs-in).
    p.get('/logout')

    # Login (register auto-logs-in, but we log out-in-effect by re-logging to
    # exercise the login path as well).
    html = p.assert_get('login page', '/login', must_contain='csrf_token')
    token = p.csrf(html)
    if not token:
        p.check('login csrf', False, 'no csrf token on /login')
        return
    p.check('login csrf', True)

    p.assert_post('login submit', '/login', {
        'csrf_token': token,
        'email': user['email'],
        'password': user['password'],
    }, accept_status=(200, 302, 303))

    # Authenticated read
    p.assert_get('account (auth)', '/account', accept_status=(200, 302))
    p.assert_get('authenticated article read', '/article/' + ARTICLE_SLUG,
                 must_contain='deforestation')
