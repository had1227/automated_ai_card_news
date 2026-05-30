# Weekly Email Setup

This guide configures the hosted weekly run for a personal Gmail account. The
workflow runs in GitHub Actions, uses Gemini for AI generation, renders
`output/news.html`, and sends that HTML as the email body.

## Google Services

1. Create or select a Google Cloud project.
2. Enable the Gmail API.
3. Create a Gemini API key in Google AI Studio.
4. Configure an External OAuth consent screen.
5. Add the sender Gmail address as a test user while the OAuth app is in testing mode.
6. Create an OAuth client of type Desktop app.
7. Download that OAuth client file as `credentials.json` in the repository root.

## Gmail Authorization

Run the one-time authorization from a trusted local machine:

```powershell
python -m pip install -r requirements.txt
python scripts/gmail_authorize.py
```

Sign into the Gmail account that should send the digest and approve Gmail send
access. The script writes `token.json` locally and prints these values:

```text
GMAIL_CLIENT_ID=...
GMAIL_CLIENT_SECRET=...
GMAIL_REFRESH_TOKEN=...
```

Copy the printed values into GitHub Actions secrets, then delete local
`credentials.json` and `token.json`.

## GitHub Secrets

Create these repository secrets under Settings > Secrets and variables > Actions:

| Secret | Value |
| --- | --- |
| `GEMINI_API_KEY` | Gemini API key |
| `GMAIL_CLIENT_ID` | Value printed by `scripts/gmail_authorize.py` |
| `GMAIL_CLIENT_SECRET` | Value printed by `scripts/gmail_authorize.py` |
| `GMAIL_REFRESH_TOKEN` | Value printed by `scripts/gmail_authorize.py` |
| `MAIL_FROM` | Authorized sender Gmail address |
| `MAIL_TO` | Recipient email address |

## Schedule

The workflow is configured for Monday 08:00 Asia/Seoul. GitHub Actions cron uses
UTC, so the workflow file uses `0 23 * * 0`, which is Sunday 23:00 UTC.

You can also send a digest manually from Actions > Weekly AI news email > Run
workflow.

## First Delivery Check

1. Open Actions > Weekly AI news email.
2. Choose Run workflow.
3. Confirm tests, pipeline generation, and Gmail delivery all complete.
4. Open the received email.
5. Confirm the body shows the date range, Korean article titles, Korean
   paragraphs, and source links.

## Failure Recovery

- If Gemini generation fails transiently, rerun the workflow.
- If Gmail authorization fails, run `python scripts/gmail_authorize.py` again and
  replace the Gmail OAuth secrets.
- Generated diagnostics are uploaded for seven days:
  `data/items.json`, `data/top_news.json`, `data/news_facts.json`, and
  `output/news.html`.
- Do not commit API keys, `credentials.json`, or `token.json`.
