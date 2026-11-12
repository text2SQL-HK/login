# tts_service + login 통합 실행 가이드 (Linux/Ubuntu)

이 README는 `tts_service`, `login` 두 서비스만 다룹니다.

목표는 다른 컴퓨터(새 Ubuntu/Linux 환경)에서 동일한 구성을 재현할 수 있게 하는 것입니다. 로컬 직접 실행과 Nginx 게이트웨이 실행을 모두 포함합니다.

## 1. 프로젝트 개요

- `login`
  - 인증/회원가입/로그인/로그아웃 API 제공
  - 세션 쿠키(`session_token`) 발급
  - 기본 채팅 로그 API(`/api/login/chat`) 제공
- `tts_service`
  - TTS/SQL 챗 기능 UI(`/tts`)와 API(`/api/tts/*`) 제공
  - 로그인 쿠키를 `LOGIN_AUTH_ME_URL`로 검증하여 인증 연동

핵심 인증 흐름:
1. 사용자가 `login`에서 로그인
2. 브라우저에 `session_token` 쿠키 저장
3. `tts_service`가 요청마다 `LOGIN_AUTH_ME_URL`로 쿠키 유효성 확인
4. 인증 실패 시 `/tts`는 리다이렉트, `/api/tts/*`는 `401`

## 2. 아키텍처 한눈에 보기

- 기본 포트
  - `login`: `8001`
  - `tts_service`: `8000`
  - `nginx gateway`: `80`
- 주요 경로
  - `/login`
  - `/tts`
  - `/api/auth/*`
  - `/api/tts/*`
  - `/healthz`

```text
Browser
  -> Nginx(:80)
      -> /login, /api/auth/*, /api/users/*, /api/login/* -> login(:8001)
      -> /tts, /api/tts/*                                  -> tts_service(:8000)

tts_service
  -> PostgreSQL (session/chat/tool/event 저장)
  -> Redis (선택: 캐시, 실패 시 DB-only fallback)
  -> Docker (plot 컨테이너)
  -> Oracle DB / Qdrant / 외부 Rerank API (SQL 관련 기능 사용 시)
```

## 3. 사전 준비 (Prerequisites)

필수:
- Ubuntu/Linux
- Python 3.10+
- PostgreSQL
- Docker + Docker Compose plugin

권장/선택:
- Redis (없으면 `tts_service`는 DB-only fallback으로 동작)
- Node.js 18+ (프론트 수정 후 재빌드 시 필요)
- Oracle Instant Client (SQL 실행/조회 기능 사용 시)
- `plot` Docker 이미지 (`tts_service`의 그래프/코드 실행 기능 사용 시)

주의:
- 현재 `tts_service` 코드에는 Oracle Client 경로 하드코딩(`oracledb.init_oracle_client`)이 있으므로 환경에 맞게 경로 조정이 필요할 수 있습니다.

## 4. 저장소 클론 및 기본 Git 사용

통합 저장소로 운영한다는 가정 예시:

```bash
git clone <YOUR_REPO_URL> workspace3
cd workspace3
git pull origin main
```

기본 작업 흐름:

```bash
git checkout -b chore/readme-setup
# 작업
git add .
git commit -m "docs: add unified setup guide for tts_service and login"
git push -u origin chore/readme-setup
```

커밋 금지 대상(원칙):
- `.env`
- DB dump / sqlite / redis dump
- 캐시/세션 산출물
- 로그 파일

## 5. 환경변수 설정

민감값은 절대 README에 실값으로 넣지 말고, 각 서비스의 `.env`에만 설정하세요.

### 5.1 `login/.env` 템플릿

```dotenv
POSTGRE_HOST=<YOUR_POSTGRES_HOST>
POSTGRE_PORT=<YOUR_POSTGRES_PORT>
POSTGRE_NAME=<YOUR_LOGIN_DB_NAME>
POSTGRE_USER=<YOUR_POSTGRES_USER>
POSTGRE_PWD=<YOUR_POSTGRES_PASSWORD>

SESSION_EXPIRE_HOURS=24
```

### 5.2 `tts_service/.env` 템플릿

```dotenv
# main postgres (tts session/chat/tool/event)
POSTGRE_HOST=<YOUR_POSTGRES_HOST>
POSTGRE_PORT=<YOUR_POSTGRES_PORT>
POSTGRE_NAME=<YOUR_TTS_DB_NAME>
POSTGRE_USER=<YOUR_POSTGRES_USER>
POSTGRE_PWD=<YOUR_POSTGRES_PASSWORD>
POSTGRE_POOL_MIN_CONN=1
POSTGRE_POOL_MAX_CONN=10

# bug report postgres (별도 DB 사용 가능)
BUG_REPORT_POSTGRE_HOST=<YOUR_BUG_DB_HOST>
BUG_REPORT_POSTGRE_PORT=<YOUR_BUG_DB_PORT>
BUG_REPORT_POSTGRE_NAME=<YOUR_BUG_DB_NAME>
BUG_REPORT_POSTGRE_USER=<YOUR_BUG_DB_USER>
BUG_REPORT_POSTGRE_PWD=<YOUR_BUG_DB_PASSWORD>

# redis (선택)
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=<YOUR_REDIS_PASSWORD_OR_EMPTY>
CACHE_TTL_SECONDS=3600
CACHE_HISTORY_LIMIT=100
CACHE_EVENTS_LIMIT=100

# auth 연동
AUTH_COOKIE_NAME=session_token
LOGIN_AUTH_ME_URL=http://127.0.0.1:8001/api/auth/me

# route prefix
TTS_UI_PREFIX=/tts
TTS_STATIC_PREFIX=/tts/static
TTS_API_PREFIX=/api/tts
LOGIN_UI_PREFIX=/login

# model/runtime
CHATBOT_RESPONSES_MODEL=gpt-5.2
OPENAI_API_KEY=<YOUR_OPENAI_API_KEY>
ENABLE_RERANK=false
RERANK_TOP_K=7

# optional (Qdrant 사용 시)
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

## 6. 의존성 설치

### 6.1 `login`

```bash
cd <REPO_ROOT>/login
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
deactivate
```

### 6.2 `tts_service`

```bash
cd <REPO_ROOT>/tts_service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
deactivate
```

### 6.3 `tts_service` 프론트 수정 시

기본 동작은 커밋된 `backend/static` 자산 기준으로 가능합니다.
프론트를 수정했을 때만 다시 빌드하세요.

```bash
cd <REPO_ROOT>/tts_service/frontend
npm install
npm run build
```

## 7. DB 준비

### 7.1 `login` DB

- 앱 시작 시 SQLAlchemy `create_all`로 테이블 자동 생성
- 별도 수동 마이그레이션 파일 없이 시작 가능

### 7.2 `tts_service` DB

`tts_service`는 스키마를 수동 적용해야 합니다.

```bash
psql \
  "host=<YOUR_POSTGRES_HOST> port=<YOUR_POSTGRES_PORT> dbname=<YOUR_TTS_DB_NAME> user=<YOUR_POSTGRES_USER> password=<YOUR_POSTGRES_PASSWORD>" \
  -f <REPO_ROOT>/tts_service/backend/db/schema.sql
```

### 7.3 `bug_reports` 테이블 주의

`tts_service`는 버그 리포트를 `BUG_REPORT_POSTGRE_*` DB에 저장합니다.
해당 DB에 `bug_reports` 테이블이 존재하는지 반드시 확인하세요.

확인 예시:

```sql
SELECT to_regclass('public.bug_reports');
```

없다면 운영 정책에 맞게 생성하세요. (예시)

```sql
CREATE TABLE IF NOT EXISTS bug_reports (
  id BIGSERIAL PRIMARY KEY,
  reporter_id TEXT NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'open',
  description TEXT NOT NULL,
  version VARCHAR(100) NOT NULL DEFAULT '',
  browser VARCHAR(200) NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## 8. 로컬 실행 절차 (백엔드 2개 직접 실행)

터미널 1 (`login`):

```bash
cd <REPO_ROOT>/login/backend
source ../.venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8001
```

터미널 2 (`tts_service`):

```bash
cd <REPO_ROOT>/tts_service
source .venv/bin/activate
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

접속:
- `http://localhost:8001/login`
- `http://localhost:8000/tts` (미로그인 시 리다이렉트/401 동작)

## 9. Nginx 게이트웨이 실행 절차

전제:
1. `login` 백엔드(`8001`) 실행 중
2. `tts_service` 백엔드(`8000`) 실행 중

실행:

```bash
cd <REPO_ROOT>/tts_service
docker compose -f docker-compose.nginx.yml up -d
```

중지:

```bash
cd <REPO_ROOT>/tts_service
docker compose -f docker-compose.nginx.yml down
```

게이트웨이 경유 접속:
- `http://localhost/login`
- `http://localhost/tts`

참고:
- 현재 구성은 `network_mode: host`를 사용하므로 Linux 호스트 기준입니다.

## 10. 동작 확인 체크리스트

```bash
curl -i http://localhost/healthz
curl -I http://localhost/
curl -I http://localhost/login
curl -I http://localhost/tts
curl -i http://localhost/api/tts/info
```

기대 결과:
1. `/healthz` -> `200 OK`
2. `/` -> `/login` 리다이렉트
3. 미로그인 `/tts` -> `/login` 리다이렉트
4. 미로그인 `/api/tts/*` -> `401`
5. 로그인 후 `/tts` 정상 접근

## 11. 트러블슈팅

- `POSTGRE_NAME(또는 POSTGRE_DB) ...` 오류
  - 원인: `.env` 누락/오타
  - 조치: 서비스별 `.env`에서 `POSTGRE_*` 재확인
- `401` 반복
  - 원인: `LOGIN_AUTH_ME_URL`, 쿠키 경로/도메인, 포트 불일치
  - 조치: `login(8001)` 정상 응답 여부와 쿠키(`session_token`) 확인
- SQL/플롯 기능 실패
  - 원인: Docker daemon 중지, `plot` 이미지 미구축, Oracle Client 경로 불일치
  - 조치:
    - Docker 상태 확인
    - `plot` 이미지 준비
      - 빌드: `docker build -f <REPO_ROOT>/tts_service/Dockerfile.plot -t plot <REPO_ROOT>/tts_service`
      - 또는 로드: `docker load -i <REPO_ROOT>/plot_image.tar`
    - Oracle Client 설치 및 코드 경로 점검
- Redis 연결 실패 로그
  - 원인: Redis 미실행/접속 실패
  - 조치: 필요 시 Redis 기동, 아니면 DB-only fallback 허용
- `data/redis` 권한 문제
  - 원인: 운영 데이터 디렉터리 소유권/권한 불일치
  - 조치: 디렉터리 권한과 프로세스 사용자 재점검

## 12. 보안/운영 주의사항

- 문서/코드 예시에 실제 비밀번호, API 키, 내부 IP를 넣지 마세요.
- `.env`는 레포에 커밋하지 마세요.
- 키/비밀번호 유출 시 즉시 폐기 후 재발급하세요.
- 운영 배포 시 최소 권한 원칙(DB 계정/네트워크 접근)을 적용하세요.

## 문서 범위와 변경 사항

- 코드 레벨 API/타입 변경: 없음
- 문서 레벨 변경:
  - 엔드포인트 계약 명확화
  - `.env` 인터페이스(필수/선택 변수) 명시

## 검증 시나리오

1. 새 Ubuntu 환경에서 이 README만 보고 `login` 실행
2. 같은 환경에서 `tts_service` 실행
3. 로그인 없이 `/tts` 접근 차단 확인
4. 로그인 후 `/tts`, `/api/tts/info` 확인
5. Nginx 게이트웨이로 `/login`, `/tts`, `/healthz` 확인
6. README 내 민감정보 미포함 확인

## Private configuration

See [SECURITY_SETUP.md](SECURITY_SETUP.md) before running. Private data and credentials must be supplied separately.
