from __future__ import annotations

import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow


SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
CLIENT_FILE = Path("credentials.json")
TOKEN_FILE = Path("token.json")


def main():
    if not CLIENT_FILE.exists():
        raise SystemExit(
            "Place the downloaded OAuth desktop credential at credentials.json."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_FILE), SCOPES)
    credentials = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    token_json = credentials.to_json()
    TOKEN_FILE.write_text(token_json, encoding="utf-8")

    token_data = json.loads(token_json)
    print("GMAIL_CLIENT_ID=" + token_data["client_id"])
    print("GMAIL_CLIENT_SECRET=" + token_data["client_secret"])
    print("GMAIL_REFRESH_TOKEN=" + token_data["refresh_token"])


if __name__ == "__main__":
    main()
