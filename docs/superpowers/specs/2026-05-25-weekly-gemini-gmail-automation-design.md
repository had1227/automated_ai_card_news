# Weekly Gemini Gmail Automation Design

## Purpose

Automate the AI news briefing so it runs without a local PC, produces a
Korean HTML digest every week, and sends the digest directly in the body of a
personal Gmail message.

The scheduled delivery time is every Monday at 08:00 Asia/Seoul. Each issue
summarizes the previous seven days of collected news.

## Chosen Approach

Use GitHub Actions as the scheduler and execution environment, Gemini API as
the hosted language-model provider, and Gmail API with delegated OAuth access
as the delivery mechanism.

This approach fits the repository because it is already connected to GitHub,
requires no always-on machine, retains workflow logs and manual retries, and
avoids introducing a separately billed application runtime. Personal Gmail
cannot use a service account alone for ordinary user mailbox sending, so a
one-time interactive OAuth grant is required to obtain a refresh token.

## User Experience

Every Monday morning, the recipient receives a Gmail message with:

- Subject: `[이번 주 AI 핵심 뉴스] YYYY.MM.DD - YYYY.MM.DD`
- A readable HTML email body containing the issue title, date range, ranked
  Korean news headlines, Korean article summaries, and source links.
- No attachment required for ordinary reading.

The workflow can also be manually triggered from GitHub Actions to test a
delivery or retry a failed scheduled run.

## Execution Flow

1. A scheduled GitHub Actions workflow starts every Monday at 08:00
   Asia/Seoul.
2. The workflow checks out the default branch, installs Python dependencies,
   and provides credentials through GitHub Secrets.
3. `collect.py` gathers news items from configured sources for the intended
   weekly collection window.
4. `cluster_rank.py` uses Gemini to rank stories and remove duplicated
   coverage.
5. `fact_extractor.py` fetches article content where available and uses Gemini
   to produce Korean titles and article-based Korean paragraphs.
6. `card_exporter.py` renders a Gmail-compatible HTML body.
7. `send_email.py` submits that HTML as a MIME `text/html` email through the
   Gmail API.
8. The workflow optionally uploads generated JSON and HTML as GitHub Actions
   artifacts for debugging, without committing runtime output to the
   repository.

## Components

### Gemini Client

Add `llm_client.py` as the single integration boundary for Gemini API calls.
It will:

- Read `GEMINI_API_KEY` from the environment.
- Use Google's supported Python SDK (`google-genai`).
- Request structured JSON outputs appropriate to ranking and article-writing
  tasks.
- Apply retry handling and raise clear failures when output cannot be
  validated.

The pipeline modules will call this client rather than embedding provider HTTP
details. Ollama-specific endpoints and model assumptions will be removed from
the scheduled path.

### Ranking And Summary Stages

`cluster_rank.py` and `fact_extractor.py` will migrate from local Ollama calls
to the Gemini client. Any collector stage that currently calls Ollama and is
part of the active collection workflow must migrate as well, or be disabled
from the hosted workflow until migrated.

The article-writing stage will retain the current safety boundary:

- Fetched webpage content is treated as untrusted input, not as instruction.
- Output is schema-validated before rendering.
- If a source page cannot be fetched, the stage can use collected excerpts and
  must keep its writing conservative.

### Email Rendering

`card_exporter.py` will render the digest as HTML intended for email delivery.
Because mail clients support less CSS than browsers, styles used in the email
body will be conservative and preferably inline or table-safe where needed.

The existing desired presentation remains:

- Main heading: `이번 주 AI 핵심 뉴스`
- Issue date range beneath the heading
- Large, non-linked Korean article titles
- Korean prose paragraphs for each article
- A source link shown separately for each item
- No internal category or confidence labels

### Gmail Delivery

Add `send_email.py` to:

- Load the rendered HTML body from `output/news.html`.
- Create a standards-compliant MIME message with a UTF-8 Korean subject.
- Send it through Gmail API `users.messages.send`.
- Use the minimal Gmail permission scope:
  `https://www.googleapis.com/auth/gmail.send`.

For personal Gmail, store a previously authorized OAuth refresh token. At run
time the Google authentication library exchanges it for an access token
without requiring user interaction.

Add a local setup utility, `scripts/gmail_authorize.py`, which performs
the one-time browser authorization and prints or writes the refresh token for
registration as a GitHub Secret. This setup utility is not executed in the
scheduled workflow.

## Scheduling

Add `.github/workflows/weekly-news-email.yml` with:

- `schedule` for Mondays at 08:00 using the `Asia/Seoul` timezone.
- `workflow_dispatch` so deliveries can be triggered manually.
- Python installation and dependency installation steps.
- Pipeline execution followed by email sending.
- Artifact upload on success or failure for diagnostics, with a limited
  retention period.

GitHub scheduled runs may start a few minutes late under load. The design
expects delivery near 08:00 rather than requiring exact-to-the-minute
delivery.

## Configuration And Secrets

Store sensitive values as GitHub repository Secrets:

| Name | Purpose |
| --- | --- |
| `GEMINI_API_KEY` | Authenticate Gemini API calls |
| `GMAIL_CLIENT_ID` | OAuth client identifier |
| `GMAIL_CLIENT_SECRET` | OAuth client secret |
| `GMAIL_REFRESH_TOKEN` | Offline delegated send authorization |
| `MAIL_FROM` | Authorized Gmail sender address |
| `MAIL_TO` | Digest recipient address |

No secret or OAuth token is written into source control, generated artifacts,
or workflow logs.

The Gemini model identifier, timezone, and subject prefix are non-sensitive
defaults and may live in code or workflow environment variables.

## Failure Handling

- A failed collection, ranking, writing, rendering, or sending stage fails the
  workflow rather than sending a misleading partial email.
- Individual article page-fetch failures may fall back to existing collected
  excerpts if the generated record still passes validation; the workflow logs
  a warning.
- Invalid Gemini JSON is retried and ultimately fails the relevant stage if it
  cannot be validated.
- Gmail authentication or send failures fail the workflow and preserve logs.
- A failed scheduled delivery can be rerun manually after fixing credentials
  or transient errors.

## Security

- Restrict Gmail OAuth access to the `gmail.send` scope.
- Treat article HTML and feed content as untrusted prompt input.
- Never print request headers, API keys, client secrets, or refresh tokens.
- Use GitHub Secrets only in the workflow steps that require them.
- Keep `data/` and `output/` as runtime artifacts, not committed weekly
  content.

## Testing And Validation

Add focused automated tests for:

- Gemini client response parsing, retry behavior, and schema validation using
  mocked API responses.
- Updated ranking and article-writing stages using the provider boundary
  rather than live Gemini calls.
- HTML email rendering rules, Korean title/body selection, date range, and
  removal of unwanted metadata.
- Email MIME construction, headers, HTML body, and Gmail API invocation using
  mocked credentials and service.
- Workflow-oriented configuration validation where practical.

Before enabling the schedule:

1. Run pipeline tests locally or in an initial manually triggered workflow.
2. Complete Gmail OAuth authorization and install repository Secrets.
3. Run `workflow_dispatch` to send one real test email.
4. Confirm the received Gmail HTML layout and source links.
5. Enable or retain the weekly schedule after the manual delivery is verified.

## Implementation Boundaries

This feature will implement automated hosted execution and email delivery. It
will not add a web dashboard, recipient management UI, historical newsletter
archive, billing controls, or multiple sender accounts.

## External References

- Gemini API quickstart: <https://ai.google.dev/gemini-api/docs/quickstart>
- Google OAuth offline access: <https://developers.google.com/identity/protocols/oauth2/web-server>
- Gmail API sending email: <https://developers.google.com/gmail/api/guides/sending>
- GitHub Actions scheduled workflows: <https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#onschedule>
- GitHub Actions secrets: <https://docs.github.com/en/actions/concepts/security/about-secrets>
