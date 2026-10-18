import pytest

from scanner.sanitize import request_url, safe_text, safe_url


def test_url_userinfo_and_sensitive_params():
    url = "https://alice:PASS_PRIVATE@my.example.org:443/site?token=TOKEN_PRIVATE&api_key=API_PRIVATE&x=ok#FRAGMENT_PRIVATE"
    result = safe_url(url)
    assert "alice" not in result
    assert "PASS_PRIVATE" not in result
    assert "TOKEN_PRIVATE" not in result
    assert "API_PRIVATE" not in result
    assert "FRAGMENT_PRIVATE" not in result
    assert "x=ok" in result
    assert "REDACTED" in result
    req = request_url(url)
    assert "alice" not in req and "PASS_PRIVATE" not in req
    assert "TOKEN_PRIVATE" in req  # request may use the user's URL; results never persist it.


def test_text_redacts_auth_cookie_and_urls():
    result = safe_text("Bearer ABC_PRIVATE Cookie: sid=COOKIE_PRIVATE\n"
                       "https://bob:PASS_PRIVATE@foo.test?q=normal&session_id=QUERY_PRIVATE")
    for token in ("ABC_PRIVATE", "COOKIE_PRIVATE", "PASS_PRIVATE", "QUERY_PRIVATE"):
        assert token not in result


@pytest.mark.parametrize("url", ["ftp://example.com/x", "file:///etc/passwd", "javascript:alert(1)",
                                  "https:///no-host", "//example.com"])
def test_only_http_https(url):
    with pytest.raises(ValueError):
        request_url(url)


def test_text_is_bounded():
    assert len(safe_text("a" * 10000, max_length=100)) <= 101
