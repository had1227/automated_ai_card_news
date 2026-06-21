# 주간 이메일 설정

이 문서는 개인 Gmail 계정으로 주간 AI 뉴스 메일을 자동 발송하는 방법을 설명합니다. GitHub Actions가 매주 정해진 시간에 파이프라인을 실행하고, Gemini로 뉴스 내용을 생성한 뒤 `output/news.html`을 HTML 메일 본문으로 전송합니다.

## 전체 흐름

1. 로컬 PC에서 Python 의존성을 설치합니다.
2. Google AI Studio에서 Gemini API 키를 발급합니다.
3. Google Cloud에서 Gmail API와 OAuth Desktop app을 설정합니다.
4. 로컬에서 `scripts/gmail_authorize.py`를 실행해 Gmail refresh token을 발급합니다.
5. GitHub Actions Secrets에 필요한 값을 6개 Secret으로 각각 등록합니다.
6. GitHub Actions에서 `Weekly AI news email` 워크플로를 수동 실행해 테스트합니다.
7. 이후에는 매주 월요일 오전 8시, Asia/Seoul 기준으로 자동 실행됩니다.

## 1. 로컬 설치

PowerShell에서 저장소 루트로 이동한 뒤 실행합니다.

```powershell
cd D:\news
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
playwright install
```

## 2. Gemini API 키 발급

Google AI Studio에서 Gemini API 키를 생성합니다. 이 값은 나중에 GitHub Actions Secret `GEMINI_API_KEY`에 등록합니다.

## 3. Gmail API와 OAuth 설정

Google Cloud Console에서 아래 순서대로 설정합니다.

1. 프로젝트를 새로 만들거나 기존 프로젝트를 선택합니다.
2. Gmail API를 활성화합니다.
3. OAuth 동의 화면을 설정합니다.
4. 개인 Gmail을 사용할 경우 사용자 유형은 보통 `External`로 둡니다.
5. 테스트 사용자에 발송할 Gmail 주소를 추가합니다.
6. OAuth 클라이언트를 생성합니다.
7. Application type은 `Desktop app`으로 선택합니다.
8. OAuth 클라이언트 JSON 파일을 다운로드합니다.
9. 다운로드한 파일 이름을 `credentials.json`으로 바꾸고 저장소 루트에 둡니다.

최종 위치는 아래와 같아야 합니다.

```text
D:\news\credentials.json
```

Windows에서 확장자 숨김이 켜져 있으면 파일명이 `credentials.json.json`이 되는 경우가 있습니다. 이 경우 `credentials.json`으로 다시 이름을 바꿔야 합니다.

## 4. Gmail 인증

로컬에서 아래 명령을 실행합니다.

```powershell
cd D:\news
.\.venv\Scripts\Activate.ps1
python scripts/gmail_authorize.py
```

브라우저가 열리면 메일을 보낼 Gmail 계정으로 로그인하고 Gmail send 권한을 승인합니다.

성공하면 터미널에 아래와 같은 값이 출력됩니다.

```text
GMAIL_CLIENT_ID=...
GMAIL_CLIENT_SECRET=...
GMAIL_REFRESH_TOKEN=...
```

이 출력은 로컬 `.env`나 PowerShell 환경변수 스타일입니다. GitHub Secrets에는 이 줄 전체를 그대로 넣지 않습니다. `=` 왼쪽은 Secret 이름, `=` 오른쪽은 Secret 값으로 나누어 등록합니다.

## 5. GitHub Actions Secrets 등록

GitHub 저장소에서 아래 메뉴로 이동합니다.

```text
Settings > Secrets and variables > Actions > New repository secret
```

Secret은 총 6개를 각각 따로 만들어야 합니다. `New repository secret`을 6번 눌러 아래 값을 하나씩 등록합니다.

### 등록해야 하는 Secret 목록

| GitHub Secret Name | Secret에 넣을 값 |
| --- | --- |
| `GEMINI_API_KEY` | Google AI Studio에서 발급한 Gemini API 키 |
| `GMAIL_CLIENT_ID` | `scripts/gmail_authorize.py` 출력 중 `GMAIL_CLIENT_ID=` 뒤의 값 |
| `GMAIL_CLIENT_SECRET` | `scripts/gmail_authorize.py` 출력 중 `GMAIL_CLIENT_SECRET=` 뒤의 값 |
| `GMAIL_REFRESH_TOKEN` | `scripts/gmail_authorize.py` 출력 중 `GMAIL_REFRESH_TOKEN=` 뒤의 값 |
| `MAIL_FROM` | 발신자 Gmail 주소 |
| `MAIL_TO` | 수신자 이메일 주소 |

### 입력 예시

GitHub Secret 입력 화면에는 `Name`과 `Secret` 칸이 따로 있습니다.

예를 들어 아래 출력이 있었다면:

```text
GMAIL_CLIENT_ID=1848...apps.googleusercontent.com
```

GitHub에는 이렇게 넣습니다.

```text
Name: GMAIL_CLIENT_ID
Secret: 1848...apps.googleusercontent.com
```

아래처럼 `Name`에 전체 줄을 넣으면 안 됩니다.

```text
Name: GMAIL_CLIENT_ID=1848...apps.googleusercontent.com
```

Secret 이름에는 하이픈 `-`을 쓰지 말고 언더스코어 `_`를 사용해야 합니다.

올바른 이름:

```text
GEMINI_API_KEY
GMAIL_CLIENT_ID
GMAIL_CLIENT_SECRET
GMAIL_REFRESH_TOKEN
MAIL_FROM
MAIL_TO
```

잘못된 이름:

```text
GEMINI-API-KEY
GMAIL-CLIENT-ID
MAIL-FROM
```

## 6. 수동 실행 테스트

GitHub 저장소에서 아래 메뉴로 이동합니다.

```text
Actions > Weekly AI news email > Run workflow
```

실행이 끝나면 `MAIL_TO`로 등록한 주소에 HTML 뉴스 메일이 도착해야 합니다.

## 7. 자동 실행 일정

워크플로는 Asia/Seoul 기준 매주 월요일 오전 8시에 실행되도록 설정되어 있습니다.

GitHub Actions cron은 UTC 기준으로 동작하므로 워크플로 파일에는 아래 값이 사용됩니다.

```text
0 23 * * 0
```

이는 UTC 기준 일요일 23:00이며, 한국 시간으로는 월요일 08:00입니다.

## 오류 해결

### `Place the downloaded OAuth desktop credential at credentials.json.`

`credentials.json` 파일을 찾지 못했다는 뜻입니다. 아래를 확인합니다.

```powershell
cd D:\news
Get-ChildItem credentials*
```

파일명이 `credentials.json.json`이면 `credentials.json`으로 바꿉니다.

```powershell
Rename-Item credentials.json.json credentials.json
```

### `403 오류: access_denied`

OAuth 앱이 테스트 모드인데 로그인한 Gmail 계정이 테스트 사용자로 등록되지 않은 경우입니다. Google Cloud Console의 OAuth 동의 화면에서 테스트 사용자에 발신자 Gmail 주소를 추가합니다.

### GitHub Secrets 이름 오류

Secret 이름에는 알파벳, 숫자, 언더스코어만 사용할 수 있습니다. `KEY=VALUE` 전체를 Name에 넣지 말고 `KEY`만 Name에 넣습니다.

### 보안 주의

API 키, Gmail client secret, refresh token을 채팅이나 공개 저장소에 노출했다면 새로 발급해서 교체하는 것이 안전합니다. `credentials.json`, `token.json`, API 키, refresh token은 커밋하지 않습니다.
