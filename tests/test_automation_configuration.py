from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def declaration_lines(filename: str) -> set[str]:
    return {
        line.strip()
        for line in (ROOT / filename).read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def test_requirements_include_google_automation_dependencies() -> None:
    requirements = declaration_lines("requirements.txt")

    assert {
        "google-genai",
        "google-api-python-client",
        "google-auth-httplib2",
        "google-auth-oauthlib",
    }.issubset(requirements)


def test_gitignore_excludes_local_google_credentials() -> None:
    ignored_files = declaration_lines(".gitignore")

    assert {"credentials.json", "token.json"}.issubset(ignored_files)
