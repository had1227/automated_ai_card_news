# 주간 이메일 설정

이 문서는 개인 Gmail 계정으로 주간 AI 뉴스 메일을 자동 발송하는 설정 방법을 설명합니다. GitHub Actions에서 워크플로를 실행하고, Gemini로 뉴스 내용을 생성한 뒤 `output/news.html`을 렌더링하여 HTML 메일 본문으로 전송합니다.

## Google 서비스 설정

1. Google Cloud 프로젝트를 새로 만들거나 기존 프로젝트를 선택합니다.
2. Gmail API를 활성화합니다.
3. Google AI Studio에서 Gemini API 키를 생성합니다.
4. OAuth 동의 화면을 External 유형으로 설정합니다.
5. OAuth 앱이 테스트 모드인 동안 발신자로 사용할 Gmail 주소를 테스트 사용자로 추가합니다.
6. Desktop app 유형의 OAuth 클라이언트를 생성합니다.
7. OAuth 클라이언트 파일을 내려받아 저장소 루트에 `credentials.json` 이름으로 둡니다.

## Gmail 인증

신뢰할 수 있는 로컬 PC에서 최초 1회 인증을 실행합니다.

```powershell
python -m pip install -r requirements.txt
python scripts/gmail_authorize.py
```

뉴스 메일을 발송할 Gmail 계정으로 로그인하고 Gmail send 권한을 승인합니다. 스크립트는 로컬에 `token.json`을 생성하고 아래 값을 출력합니다.

```text
GMAIL_CLIENT_ID=...
GMAIL_CLIENT_SECRET=...
GMAIL_REFRESH_TOKEN=...
```

출력된 값을 GitHub Actions secrets에 복사한 뒤, 로컬의 `credentials.json`과 `token.json`은 삭제합니다.

## GitHub Secrets

저장소의 Settings > Secrets and variables > Actions에서 아래 secrets를 생성합니다.

| Secret | 값 |
| --- | --- |
| `GEMINI_API_KEY` | Gemini API 키 |
| `GMAIL_CLIENT_ID` | `scripts/gmail_authorize.py`가 출력한 값 |
| `GMAIL_CLIENT_SECRET` | `scripts/gmail_authorize.py`가 출력한 값 |
| `GMAIL_REFRESH_TOKEN` | `scripts/gmail_authorize.py`가 출력한 값 |
| `MAIL_FROM` | 인증된 발신자 Gmail 주소 |
| `MAIL_TO` | 수신자 이메일 주소 |

## 실행 일정

워크플로는 Asia/Seoul 기준 매주 월요일 오전 8시에 실행되도록 설정되어 있습니다. GitHub Actions cron은 UTC 기준으로 동작하므로, 워크플로 파일에는 한국 시간 월요일 오전 8시에 해당하는 `0 23 * * 0`이 사용됩니다.

수동 발송도 가능합니다. GitHub Actions에서 Weekly AI news email 워크플로를 열고 Run workflow를 선택하면 즉시 실행할 수 있습니다.

## 첫 발송 확인

1. GitHub 저장소에서 Actions > Weekly AI news email로 이동합니다.
2. Run workflow를 선택합니다.
3. 테스트, 뉴스 생성 파이프라인, Gmail 발송 단계가 모두 완료되는지 확인합니다.
4. 수신된 이메일을 엽니다.
5. 메일 본문에 날짜 구간, 한국어 기사 제목, 한국어 문단, 출처 링크가 잘 표시되는지 확인합니다.

## 오류 복구

- Gemini 생성이 일시적으로 실패했다면 워크플로를 다시 실행합니다.
- Gmail 인증이 실패했다면 `python scripts/gmail_authorize.py`를 다시 실행하고 Gmail OAuth secrets를 새 값으로 교체합니다.
- 생성 결과 진단 파일은 7일 동안 GitHub Actions artifact로 업로드됩니다: `data/items.json`, `data/top_news.json`, `data/news_facts.json`, `output/news.html`.
- API 키, `credentials.json`, `token.json`은 커밋하지 않습니다.
