"""huggingface mirror health check."""
from healthcheck import random_user


def run(p):
    p.assert_get('home', '/', must_contain='Hugging Face')
    p.assert_get('search bert', '/search?q=bert', must_contain='bert')
    p.assert_get(
        'model detail',
        '/google-bert/bert-base-uncased',
        must_contain='Model card',
    )

    user = random_user()
    html = p.assert_get('register page', '/register')
    token = p.csrf(html)
    if not token:
        p.check('register csrf', False, 'no csrf')
        return
    p.assert_post('register submit', '/register', {
        'csrf_token': token,
        'username': user['username'],
        'email':    user['email'],
        'password': user['password'],
        'confirm':  user['password'],
    }, accept_status=(200, 302, 303))

    # Log out first to force a real login round-trip.
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

    # /account requires authentication; good authenticated-read probe.
    p.assert_get('account page', '/account',
                 accept_status=(200, 302))
