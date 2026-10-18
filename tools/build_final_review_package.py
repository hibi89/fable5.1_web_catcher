"""Final acceptance and reviewer ZIP builder. No product functionality changes.

Run only in clean venv from the repository, after installing requirements and
Playwright Chromium. Runs localhost fixture tests and produces ONLY redacted
fixture examples and repository-tracked source files. No paid API requests.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Running a script under tools/ does not automatically import repo-root tests/.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
REVIEW = ROOT / "final_review_dist"
EXAMPLES = REVIEW / "examples"
LOGS = REVIEW / "test_logs"
BANNED_FILES = {".env", ".env.example"}
BANNED_PARTS = {
    ".git", ".venv", ".venv-ci", ".venv-final", ".venv-smoke",
    "__pycache__", ".pytest_cache", "node_modules", "out", "artifacts",
    "final_review_dist", ".mypy_cache", ".ruff_cache", "cache"
}
SECRET_RE = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{25,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?im)^OPENAI_API_KEY\s*=\s*['\"]?[A-Za-z0-9_-]{15,}"),
]
PERSONAL_PATH_RE = [
    re.compile(r"(?i)[A-Z]:[\\/]+Users[\\/]+(?:haein|runneradmin|[A-Za-z0-9._-]+)[\\/]+"),
    re.compile(r"/(?:home|Users)/[^/\s]+/(?:Desktop|Documents|Downloads|OneDrive)/"),
    re.compile("/" + "mnt" + "/data/"),
]


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(label, argv, checks, *, max_seconds=240):
    """Never persist raw subprocess stdout/stderr, which can contain paths."""
    env = os.environ.copy()
    for key in ("OPENAI_API_KEY", "OPENAI_MODEL", "GITHUB_TOKEN", "GH_TOKEN"):
        env.pop(key, None)
    p = subprocess.run(argv, cwd=ROOT, env=env, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       errors="replace", timeout=max_seconds)
    if p.returncode:
        # Diagnostics stay on private CI console, not in reviewer log.
        print("FAILED_COMMAND=" + label, file=sys.stderr)
        print(p.stdout[-3500:], file=sys.stderr)
        print(p.stderr[-3500:], file=sys.stderr)
        raise RuntimeError(label + " failed; review CI job logs (not packaged).")
    counts = re.findall(r"(?m)\b(\d+) passed(?:, \d+ (?:skipped|deselected))? in \d", p.stdout)
    checks.append({"check": label, "result": "PASS",
                   "test_passed_count": int(counts[-1]) if counts else None})
    return p


def safe_fixture_copy(raw, dest):
    """Use Step 5 redaction when preparing demonstration report artifacts."""
    from scanner.batch import safe_batch_result
    from scanner.report import to_markdown
    source = json.loads(raw.read_text(encoding="utf-8"))
    sanitized = safe_batch_result(
        source, "https://batch-final-review-origin-001.batch.invalid")
    write_json(dest / "result.json", sanitized)
    try:
        report = to_markdown(sanitized)
    except (KeyError, ValueError, TypeError):
        raise RuntimeError("redacted fixture report render failed")
    (dest / "report.md").write_text(report, encoding="utf-8")
    return sanitized


def should_package(path):
    if path.name in BANNED_FILES or path.name.startswith(".env"):
        return False
    if any(part in BANNED_PARTS for part in path.parts):
        return False
    if path.suffix.lower() in (".zip", ".pem", ".key", ".pyc", ".p12", ".bak"):
        return False
    return path.is_file() and not path.is_symlink()


def check_sensitive(payload, *, include_paths=True):
    # Explicitly ban real credentials / absolute personal paths, regardless
    # of document vs code. Test fixtures may contain fake placeholder tokens.
    text = payload.decode("utf-8", errors="ignore")
    if any(regex.search(text) for regex in SECRET_RE):
        raise RuntimeError("potential credential detected in package candidate")
    if include_paths and any(regex.search(text) for regex in PERSONAL_PATH_RE):
        raise RuntimeError("personal absolute path detected in package candidate")


def main():
    if REVIEW.exists():
        raise RuntimeError("final_review_dist already exists; refuse overwrite")
    EXAMPLES.mkdir(parents=True)
    LOGS.mkdir()
    checks = []
    git = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    branch = subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()
    py = platform.python_version()
    pv = importlib.metadata.version("playwright")
    import playwright.sync_api as playwright_api
    with playwright_api.sync_playwright() as pw:
        with pw.chromium.launch(headless=True) as browser:
            chromium_version = browser.version
    versions = {
        "source_git_commit": git,
        "checkout_branch": branch or "detached",
        "python": py,
        "playwright": pv,
        "chromium": chromium_version,
        "operating_system": "ubuntu-24.04 (GitHub Actions clean virtualenv)",
        "install_commands": [
            "python3 -m venv .venv-final",
            ".venv-final/bin/python -m pip install -r requirements.txt",
            ".venv-final/bin/python -m playwright install --with-deps chromium",
        ],
        "validation_note": "Linux clean-install CI, not a Windows user-record test",
    }
    write_json(LOGS / "environment_versions.json", versions)
    run("123+ offline/fixture pytest", [sys.executable, "-m", "pytest", "-q"],
        checks, max_seconds=240)
    run("23 headed Chromium browser regressions", [
        "xvfb-run", "-a", sys.executable, "-m", "pytest", "-q",
        "tests/browser_runtime_check.py", "tests/browser_mapping_check.py",
        "tests/browser_bundle_check.py", "tests/browser_final_check.py",
        "tests/browser_record_check.py"
    ], checks, max_seconds=240)
    # A public-website 4-test smoke belongs to its separate *optional*
    # workflow and is NOT silently counted or rerun by this offline gate.
    checks.append({
        "check": "4 optional public-website smoke",
        "result": "NOT_RERUN (previous workflow run 39148097419)",
        "test_passed_count": None,
        "note": "separate from 123 and 23; continue-on-error=true in existing workflow"
    })

    from tests.fixture_server import fixture_server
    from scanner.models import blank_result
    from scanner.step5_common import safe_structure
    with tempfile.TemporaryDirectory(prefix="fable-final-clean-") as tmp:
        raw = Path(tmp)
        with fixture_server() as base:
            # Actual CLI commands, using only local fixture server.
            run("static single URL", [
                sys.executable, "scan.py", base + "/next",
                "--out", str(raw / "static"),
            ], checks)
            run("runtime Chromium single URL", [
                sys.executable, "scan.py", base + "/runtime-final",
                "--runtime", "--wait", "2", "--timeout", "20",
                "--out", str(raw / "runtime"),
            ], checks, max_seconds=90)
            urls = raw / "urls.txt"
            urls.write_text(
                base + "/next\n" + base + "/servlet\n" + base + "/plain\n",
                encoding="utf-8")
            run("3 URL sequential batch", [
                sys.executable, "scan.py", "--batch", str(urls),
                "--delay", "1", "--out", str(EXAMPLES / "batch")
            ], checks, max_seconds=100)
            manifest = json.loads(
                (EXAMPLES / "batch" / "batch_manifest.json")
                .read_text(encoding="utf-8"))
            assert len(manifest["targets"]) == 3
            assert all(t["status"] in ("success", "partial")
                       for t in manifest["targets"])
            rows = sorted((EXAMPLES / "batch" / "targets").glob("*/result.json"))
            assert len(rows) == 3
            run("offline result comparison", [
                sys.executable, "scan.py", "--compare",
                str(rows[0]), str(rows[1]), "--out",
                str(EXAMPLES / "comparison")
            ], checks)
            assert (EXAMPLES / "comparison" / "diff.md").is_file()
            safe_fixture_copy(raw / "static" / "result.json",
                              EXAMPLES / "single_static")
            observed = safe_fixture_copy(
                raw / "runtime" / "result.json",
                EXAMPLES / "single_runtime")
            # Data-contract examples from actually observed *local fixture*
            # browser JSON. If the runtime saw no JSON body, make no schema.
            contract_input = EXAMPLES / "single_runtime" / "result.json"
            run("offline observed contracts", [
                sys.executable, "scan.py", "--from-result",
                str(contract_input), "--export-contracts",
                "--out", str(EXAMPLES / "contracts"),
            ], checks)
            assert (EXAMPLES / "contracts" / "contracts.md").is_file()
            run("LLM offline dry-run (no API key)", [
                sys.executable, "scan.py", "--from-result",
                str(contract_input), "--llm-dry-run",
                "--out", str(EXAMPLES / "llm_dry_run"),
            ], checks)
            assert (EXAMPLES / "llm_dry_run"
                    / "llm_payload.preview.json").is_file()
            assert not (EXAMPLES / "llm_dry_run" / "llm_report.json").exists()

    # No source-specific scan data in logs. Examples are anonymized by
    # product code itself, and checked before releasing the package.
    files = []
    tracked = subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=ROOT).decode("utf-8").split("\0")
    for name in tracked:
        if not name:
            continue
        rel = Path(name)
        if should_package(rel):
            files.append(("source/" + rel.as_posix(), (ROOT / rel).read_bytes()))
    for file in sorted(EXAMPLES.rglob("*")):
        if file.is_file():
            files.append((file.relative_to(REVIEW).as_posix(), file.read_bytes()))
    checks_log = {
        "source_commit": git,
        "test_separation": "pytest -q base suite and headed Chromium suite are distinct; "
                           "4 optional public smoke are a third, separately invoked set",
        "checks": checks,
        "real_openai_api_called": False,
        "real_customer_website_accessed": False,
        "real_windows_interactive_record_tested": False,
    }
    write_json(LOGS / "acceptance_checks.json", checks_log)
    files.extend((
        file.relative_to(REVIEW).as_posix(), file.read_bytes()
    ) for file in sorted(LOGS.rglob("*")) if file.is_file())
    index = []
    for name, value in files:
        if name.startswith("/") or ".." in Path(name).parts:
            raise RuntimeError("unsafe ZIP archive path")
        check_sensitive(value, include_paths=True)
        index.append({"relative_path": name, "sha256": hashlib.sha256(value).hexdigest(),
                      "bytes": len(value)})
    files.append(("REVIEW_FILES_SHA256.json",
                  (json.dumps(index, indent=2) + "\n").encode("utf-8")))
    manifest = {
        "commit": git,
        "created_using": "tools/build_final_review_package.py",
        "source_file_count": len([x for x in files if x[0].startswith("source/")]),
        "total_entries": len(files),
        "sensitive_scan": "PASS (pattern audit; does not guarantee universal secret absence)",
        "excluded": [".env*", ".git", ".venv*", "__pycache__", ".pytest_cache",
                     "out", "browser binary", "*.pem", "*.key", "*.zip"],
        "demo_provenance": "localhost fixture only; sanitized / pseudo-origin alias",
        "no_live_llm_api_calls": True,
    }
    files.append(("REVIEW_PACKAGE_MANIFEST.json",
                  (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
                  .encode("utf-8")))
    filename = "fable5-final-review-" + git[:12] + ".zip"
    target = ROOT / filename
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=8) as archive:
        for name, raw in files:
            archive.writestr(name, raw)
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        names = archive.namelist()
        assert "source/README.md" in names
        assert "source/STATUS.md" in names
        assert "source/HANDOFF.md" in names
        assert "source/rules/fingerprints.json" in names
        assert "examples/comparison/diff.md" in names
        assert "examples/contracts/contracts.md" in names
        assert "examples/llm_dry_run/llm_payload.preview.json" in names
        assert not any(
            ".env" in name or "__pycache__" in name or name.endswith(".pyc")
            for name in names)
    # Printed value is only package basename; no local runner paths.
    print("FINAL_REVIEW_ZIP=" + filename)
    print("SOURCE_COMMIT=" + git)
    print("CLEAN_PYTHON=" + py)
    print("CLEAN_PLAYWRIGHT=" + pv)
    print("CLEAN_CHROMIUM=" + chromium_version)
    for c in checks:
        print("CHECK=" + c["check"] + " STATUS=" + c["result"] +
              " COUNT=" + str(c.get("test_passed_count")))
    print("PACKAGE_SANITIZED=PASS")


if __name__ == "__main__":
    main()
