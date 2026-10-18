"""Each of the 50 genuine pattern signals has synthetic positive/negative evidence."""
import json
from scanner.fingerprints import RULES_PATH, _observation_matches

POSITIVE = {
    "react-root": "react_root", "react-script": "/js/react.production.js",
    "next-html": "next_data", "next-assets": "/_next/static/chunks/main.js",
    "next-root": "next_root", "vue-mount": "vue_mount",
    "vue-assets": "/js/vue.global.prod.js", "nuxt-html": "nuxt_payload",
    "nuxt-assets": "/_nuxt/entry.js", "angular-version": "angular_version",
    "angular-app": "angular_app", "php-header": "PHP/8.2.1",
    "php-cookie": "PHPSESSID", "asp-header": "ASP.NET",
    "asp-version": "4.0.3", "asp-cookie": "ASP.NET_SessionId",
    "express-header": "Express", "django-csrf": "csrftoken",
    "django-generator": "Django 4.2", "laravel-session": "laravel_session",
    "laravel-xsrf": "XSRF-TOKEN", "servlet-cookie": "JSESSIONID",
    "cloudflare-cf": "a1b2c3", "cloudflare-server": "cloudflare",
    "vercel-id": "sfo1:abc", "vercel-server": "Vercel",
    "netlify-id": "abc-def", "netlify-server": "Netlify",
    "nginx-server": "nginx/1.21", "apache-server": "Apache/2.4",
    "wp-generator": "WordPress 6.6", "wp-assets": "/wp-content/themes/hello/app.js",
    "drupal-generator": "Drupal 10", "joomla-generator": "Joomla! 5",
    "ghost-generator": "Ghost 5", "astro-script": "/_astro/page-a1.js",
    "sveltekit-immutable": "/_app/immutable/entry/start.js",
    "gatsby-generator": "Gatsby 5", "jquery-script": "/jquery-3.5.1.min.js",
    "bootstrap-css": "/bootstrap.min.css", "bulma-css": "/bulma.min.css",
    "alpine-script": "/alpine.min.js", "chartjs-script": "/chart.umd.js",
    "highcharts-script": "/highcharts.js", "d3-script": "/d3.v7.min.js",
    "caddy-server": "Caddy", "litespeed-server": "LiteSpeed",
    "iis-server": "Microsoft-IIS/10", "openresty-server": "openresty/1.19",
    "cloudfront-via": "1.1 abc.cloudfront.net (CloudFront)",
}


def test_rule_signal_count_unique_ids_and_metadata():
    technologies = json.loads(RULES_PATH.read_text(encoding="utf-8"))["technologies"]
    signals = [s for t in technologies for s in t["signals"]]
    assert len(signals) == 50
    assert len({s["id"] for s in signals}) == 50
    assert len({(s["source"], s.get("key"), s["pattern"], s["group"])
                for s in signals}) == 50
    assert set(POSITIVE) == {s["group"] for s in signals}
    for tech in technologies:
        assert tech["category"] in ("frontend", "backend_inferred", "infra")
        for s in tech["signals"]:
            assert s["id"].startswith("fp-")
            assert s["verification_note"]
            assert s["note"] and s["source"] and s["pattern"]
            assert 0 < s["weight"] <= 1


def test_each_signal_positive_and_negative():
    technologies = json.loads(RULES_PATH.read_text(encoding="utf-8"))["technologies"]
    for tech in technologies:
        for signal in tech["signals"]:
            key = signal.get("key") or "marker"
            evidence = {signal["source"]: (
                {key: POSITIVE[signal["group"]]} if "key" in signal
                else [POSITIVE[signal["group"]]]
            )}
            assert _observation_matches(evidence, signal), (tech["name"], signal["group"])
            negative = {signal["source"]: ({key: ""} if "key" in signal else [""])}
            assert not _observation_matches(negative, signal), signal["group"]


def test_ambiguous_cookies_are_not_framework_proof():
    # Convention-only cookies must not be interpreted as certain framework IDs.
    technologies = json.loads(RULES_PATH.read_text(encoding="utf-8"))["technologies"]
    names = {t["name"]: t for t in technologies}
    assert "Spring Boot" not in names
    assert names["Django"]["signals"][0]["weight"] < 0.5
    assert names["Laravel"]["signals"][1]["weight"] < 0.3
    assert names["Java Servlet"]["signals"][0]["weight"] < 0.7
