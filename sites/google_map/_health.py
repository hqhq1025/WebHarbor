"""google_map mirror health check."""
from healthcheck import random_user


def run(p):
    # 1. Home page
    p.assert_get('home', '/', must_contain='Google Maps')

    # 2. Place search — seeded query from run_tasks.py Task 3
    p.assert_get(
        'place search',
        '/search?q=central+park+zoo',
        must_contain='Central Park Zoo',
    )

    # 3. Place detail — slug from build_place(city_slug + name) in expand_catalog.py
    p.assert_get(
        'place detail',
        '/place/new-york-ny-central-park-zoo',
        accept_status=(200, 302),
    )

    # 4. Directions — seeded walking route from Task 3
    # NOTE: google_map uses `from` and `to` query params (not origin/destination)
    p.assert_get(
        'directions',
        '/directions?from=Central+Park+Zoo&to=Broadway+Theater&mode=walking',
        must_contain='Central Park Zoo',
    )

    # 5. Register
    user = random_user()
    html = p.assert_get('register page', '/register')
    token = p.csrf(html)
    if not token:
        p.check('register csrf', False, 'no csrf')
        return
    p.assert_post(
        'register submit',
        '/register',
        {
            'csrf_token': token,
            'name': user['name'],
            'email': user['email'],
            'password': user['password'],
            'password2': user['password'],
        },
        accept_status=(200, 302, 303),
    )

    # Logout so /login renders a real form (register auto-logs-in).
    p.get('/logout')

    # 6. Login (registration auto-logs in but we test the login flow too)
    html = p.assert_get('login page', '/login')
    token = p.csrf(html)
    if not token:
        p.check('login csrf', False, 'no csrf')
        return
    p.assert_post(
        'login submit',
        '/login',
        {
            'csrf_token': token,
            'email': user['email'],
            'password': user['password'],
        },
        accept_status=(200, 302, 303),
    )

    # 7. Authenticated read — /account requires login
    p.assert_get('account', '/account', accept_status=(200, 302))
