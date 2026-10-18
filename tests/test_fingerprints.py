"""Rule-engine constraints: signal provenance, versioning and deduplication."""
from scanner.fingerprints import apply_fingerprints
from scanner.models import blank_result


def technologies(category, obs):
    result = blank_result("https://example.test/")
    apply_fingerprints(result, obs)
    return result[category], result


def test_express_header_has_expected_heuristic():
    arr, result = technologies("backend_inferred", {"response_header": {"x-powered-by": "Express"}})
    assert arr == [{"name": "Express", "version": None, "confidence": 0.6, "evidence_ids": ["ev_001"]}]
    assert result["evidence"][0]["source"] == "response_header"


def test_version_only_when_explicit():
    arr, _ = technologies("infra", {"response_header": {"server": "nginx/1.24.0"}})
    assert arr[0]["version"] == "1.24.0"
    arr, _ = technologies("infra", {"response_header": {"server": "nginx"}})
    assert arr[0]["version"] is None


def test_repeated_scripts_do_not_raise_confidence():
    one, _ = technologies("frontend", {"script_src": ["https://site.test/_next/static/a.js" ]})
    many, result = technologies("frontend", {"script_src": [
        "https://site.test/_next/static/a.js", "https://site.test/_next/static/b.js",
        "https://site.test/_next/static/b.js"]})
    get_next = lambda items: next(x for x in items if x["name"] == "Next.js")
    assert get_next(one)["confidence"] == get_next(many)["confidence"]
    assert len(get_next(many)["evidence_ids"]) == 2


def test_react_vue_plain_text_not_evidence():
    cats, _ = technologies("frontend", {"html": ["React", "Vue", "A blog about Angular"]})
    assert [x["name"] for x in cats] == ["unknown"]


def test_all_required_technologies_present_in_rules():
    import json
    from scanner.fingerprints import RULES_PATH
    rules = json.loads(RULES_PATH.read_text(encoding="utf8"))["technologies"]
    assert {tech["name"] for tech in rules} >= {
        "React", "Next.js", "Vue", "Nuxt", "Angular",
        "PHP", "ASP.NET", "Express", "Django", "Laravel", "Java Servlet",
        "Cloudflare", "Vercel", "Netlify", "nginx", "Apache"}
