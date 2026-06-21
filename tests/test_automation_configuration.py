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


def test_weekly_workflow_runs_pipeline_and_sends_html_email() -> None:
    workflow = (ROOT / ".github/workflows/weekly-news-email.yml").read_text(
        encoding="utf-8"
    )

    assert "workflow_dispatch:" in workflow
    assert "cron: '0 23 * * 0'" in workflow
    assert "Monday 08:00 Asia/Seoul" in workflow
    assert "python run_pipeline.py --all" in workflow
    assert "python send_email.py" in workflow
    assert "GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}" in workflow
    assert "GEMINI_API_KEYS: ${{ secrets.GEMINI_API_KEYS }}" in workflow
    assert "GMAIL_REFRESH_TOKEN: ${{ secrets.GMAIL_REFRESH_TOKEN }}" in workflow
    assert "MAIL_FROM: ${{ secrets.MAIL_FROM }}" in workflow
    assert "MAIL_TO: ${{ secrets.MAIL_TO }}" in workflow
