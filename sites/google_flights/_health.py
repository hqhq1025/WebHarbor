"""google_flights mirror health check."""
from healthcheck import random_user


def run(p):
    p.assert_get('home', '/', must_contain='flights')

    # Route seeded by expand_catalog.py: gf-2 JFK -> LHR on 2024-01-22 (one-way)
    html = p.assert_get(
        'flight search',
        '/flights?from=JFK&to=LHR&depart=2024-01-22&trip=one',
        must_contain='LHR',
    )

    # Pick a flight id from the search results for the detail page
    flight_id = None
    marker = 'href="/flight/'
    idx = html.find(marker)
    if idx != -1:
        start = idx + len(marker)
        end = html.find('"', start)
        token = html[start:end]
        # strip anything after a slash or query
        for sep in ('/', '?', '#'):
            if sep in token:
                token = token.split(sep)[0]
        if token.isdigit():
            flight_id = token
    p.check('flight link present', flight_id is not None, 'no /flight/<id> link on results page')
    if flight_id:
        p.assert_get('flight detail', '/flight/' + flight_id, must_contain='JFK')

    user = random_user()

    html = p.assert_get('register page', '/register', must_contain='first_name')
    token = p.csrf(html)
    p.assert_post('register submit', '/register', {
        'csrf_token': token,
        'first_name': user['first_name'],
        'last_name': user['last_name'],
        'email': user['email'],
        'password': user['password'],
    }, accept_status=(200, 302, 303))

    # Logout so login is a meaningful re-auth
    p.get('/logout')

    html = p.assert_get('login page', '/login', must_contain='email')
    token = p.csrf(html)
    p.assert_post('login submit', '/login', {
        'csrf_token': token,
        'email': user['email'],
        'password': user['password'],
    }, accept_status=(200, 302, 303))

    p.assert_get('account', '/account', accept_status=(200, 302))
