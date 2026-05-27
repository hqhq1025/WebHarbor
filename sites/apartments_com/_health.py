"""apartments_com mirror health check."""

def run(p):
    p.assert_get('home', '/', must_contain='Apartments')
    p.assert_get('search', '/search?q=Miami', must_contain='Miami')
    p.assert_get('cities index', '/cities', must_contain='cities')
    p.assert_get('city page', '/new-york-ny/', must_contain='New York')
    p.assert_get('schools', '/schools', must_contain='School')
    p.assert_get('renters guide', '/renters-guide', must_contain='Renters')
    p.assert_get('list property', '/list-your-property', must_contain='List')
    p.assert_get('draw search', '/search/draw', must_contain='Draw')
    p.assert_get('student housing', '/student-housing', must_contain='Student')


def health():
    return {"ok": True, "site": "apartments_com"}
