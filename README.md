# AlphaPick

AlphaPick은 국내 주식 데이터를 기반으로 종목 점수와 포트폴리오 편입 결과를 보여주는 주식 분석 서비스입니다. Django REST API가 종목, 포트폴리오, 커뮤니티 데이터를 제공하고, Vue 3 프론트엔드가 금융 대시보드 형태로 화면을 구성합니다.

현재 프론트엔드는 기본 대시보드, 오늘의 포트폴리오 전체, 종목 검색, 종목 리포트, 커뮤니티 화면을 중심으로 구성되어 있습니다. 백테스트 화면은 사용자 화면에서 제거되어 있으며, 관련 API는 백엔드에만 남아 있습니다.

## 핵심 기능

- 기본 대시보드: 데이터 기준일, 투자 성향 선택, 편입 종목 TOP 15 표시
- 오늘의 포트폴리오: 편입 종목 전체, 점수, 추천 비중, 핵심 추천 사유 확인
- 종목 검색: 전체 종목 검색, 점수 필터, 섹터·2차 테마 필터, 리포트 이동
- 종목 리포트: 가격 차트, 점수 카드, 기술/재무 지표, 뉴스/공시, AI 코멘트 제공
- 커뮤니티: 종목별 게시글, 댓글, 좋아요, 팔로우 기능
- 사용자 기능: 로그인, 회원가입, 마이페이지, 관심 종목 확장 구조

## 화면 구조

| 화면 | 경로 | 설명 |
|---|---|---|
| 기본 대시보드 | `/` | 데이터 기준일, 투자 성향 선택, 편입 종목 TOP 15 |
| 오늘의 포트폴리오 | `/portfolio` | 편입 종목 전체 테이블 |
| 종목 검색 | `/stocks` | 종목 검색, 점수 필터, 섹터·테마 패널 |
| 종목 리포트 | `/stocks/:ticker` | 차트, 점수, 지표, 뉴스/공시, AI 코멘트 |
| 종목 커뮤니티 | `/stocks/:ticker/community` | 특정 종목 의견 |
| 커뮤니티 | `/community` | 전체 커뮤니티 |
| 사용자 기능 | `/login`, `/register`, `/mypage`, `/profile/edit` | 인증과 사용자 정보 |

## 기술 스택

### 프론트엔드

- Vue 3
- Vite
- Vue Router
- Pinia
- Axios
- Tailwind CSS
- PostCSS, Autoprefixer
- lucide-vue 아이콘
- SUIT 웹폰트

### 백엔드

- Python
- Django 4.2
- Django REST Framework
- Simple JWT
- django-cors-headers
- SQLite 기본 DB, `DATABASE_URL` 설정 시 PostgreSQL 등 외부 DB 지원
- psycopg
- pandas, numpy
- pykrx
- 네이버 뉴스 검색 API, GMS OpenAI Gateway 연동 옵션
- requests
- Pillow

### 주요 도구와 환경

- Node.js / npm
- PowerShell 기준 실행 명령
- Django 관리 명령어 `seed_alphapick`
- Vite 개발 서버: `http://127.0.0.1:5173`
- Django API 서버: `http://127.0.0.1:8000/api`

## 프로젝트 구조

```txt
Alphapick/
├─ backend/
│  ├─ accounts/        사용자 모델과 인증
│  ├─ community/       게시글, 댓글, 좋아요, 팔로우
│  ├─ config/          Django 설정과 URL
│  ├─ stocks/          종목, 테마, 점수, 포트폴리오 API
│  ├─ db.sqlite3       로컬 SQLite 데이터베이스
│  └─ manage.py
├─ frontend/
│  ├─ public/          favicon과 앱 로고
│  ├─ src/
│  │  ├─ api/          Axios 클라이언트
│  │  ├─ assets/       스타일과 폰트
│  │  ├─ components/   레이아웃과 공통 컴포넌트
│  │  ├─ router/       Vue Router
│  │  ├─ stores/       Pinia 스토어
│  │  └─ views/        화면 컴포넌트
│  └─ package.json
└─ docs/               요구사항, 설계, QA, 발표 문서
```

## 실행 방법

프로젝트는 백엔드 API 서버와 프론트엔드 개발 서버를 각각 실행해야 합니다. PowerShell 터미널을 2개 열고 아래 순서대로 실행합니다.

### 1. 백엔드 서버 실행

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

백엔드는 기본적으로 `http://127.0.0.1:8000/api`에서 실행됩니다.

로컬 데이터가 비어 있거나 초기 데이터를 다시 만들고 싶다면 서버 실행 전에 아래 명령을 추가로 실행합니다.

```powershell
.\.venv\Scripts\python.exe manage.py seed_alphapick --flush
```

국내 테마/섹터 추출본을 DB에 재가공해 넣을 때는 아래 명령을 사용합니다. `--source`에는 DevTools 등에서 복사한 국내 테마 텍스트 파일 경로를 넣습니다.

```powershell
.\.venv\Scripts\python.exe manage.py seed_themes --source "C:\path\to\domestic-themes.txt" --clear
```

### 2. 프론트엔드 서버 실행

```powershell
cd frontend
npm install
npm run dev
```

프론트엔드는 기본적으로 `http://127.0.0.1:5173`에서 실행됩니다. 브라우저에서 해당 주소로 접속하면 AlphaPick 화면을 확인할 수 있습니다.

### 3. API 주소 설정

프론트엔드는 기본적으로 `http://localhost:8000/api`를 백엔드 API 주소로 사용합니다. 다른 주소를 사용할 경우 `frontend/.env`에 다음 값을 설정합니다.

```txt
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

### 4. 뉴스 감성 데이터 갱신

네이버 뉴스 검색 API 키가 있을 때 종목별 최근 뉴스를 수집하고, `GMS_KEY`가 있으면 AI로 감성/영향도 점수를 계산합니다.

```powershell
cd backend
.\.venv\Scripts\python.exe manage.py refresh_news_sentiment --tickers 005930 --display 10 --days 14
```

필요 환경 변수는 `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`입니다. `GMS_KEY`가 없으면 제목/요약 키워드 기반 임시 분류로 동작합니다. OpenDART 공시까지 함께 수집하려면 `DART_API_KEY`를 설정하고 `--include-dart` 옵션을 추가합니다.

## 주요 API

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/api/portfolio/today/` | 오늘의 포트폴리오 조회 |
| GET | `/api/portfolio/today/?risk_type=aggressive` | 공격형 포트폴리오 조회 |
| GET | `/api/portfolio/today/?risk_type=stable` | 안정형 포트폴리오 조회 |
| GET | `/api/portfolio/history/` | 포트폴리오 이력 조회 |
| GET | `/api/portfolio/backtest/` | 백테스트 요약 API |
| GET | `/api/stocks/` | 종목 목록 |
| GET | `/api/stocks/?theme=대형 조선` | 2차 테마별 종목 목록 |
| GET | `/api/stocks/?theme_group=조선·해운` | 테마 그룹별 종목 목록 |
| GET | `/api/themes/` | 종목 검색 좌측 테마 패널 |
| GET | `/api/stocks/{ticker}/report/` | 종목 리포트 |
| GET | `/api/stocks/{ticker}/prices/` | 종목 가격 시계열 |
| POST | `/api/stocks/{ticker}/ai-comment/` | AI 코멘트 생성 또는 캐시 조회 |
| GET | `/api/watchlist/` | 내 관심 종목 |
| POST | `/api/watchlist/{ticker}/` | 관심 종목 추가 |
| DELETE | `/api/watchlist/{ticker}/` | 관심 종목 삭제 |
| GET/POST | `/api/community/posts/` | 커뮤니티 게시글 목록과 작성 |
| GET | `/api/community/users/` | 커뮤니티 사용자 목록 |
| POST | `/api/community/users/{user_id}/follow/` | 팔로우 토글 |
| DELETE | `/api/community/comments/{comment_id}/` | 댓글 삭제 |

## 문서 정리

| 문서 | 내용 |
|---|---|
| [docs/README.md](docs/README.md) | 문서 인덱스와 아키텍처 요약 |
| [docs/API.md](docs/API.md) | 화면별 API 매핑과 엔드포인트 명세 |
| [docs/EXTERNAL_APIS.md](docs/EXTERNAL_APIS.md) | 외부 데이터/API 연동 현황과 후보 |
| [docs/PRD.md](docs/PRD.md) | 제품 요구사항 정의서 |
| [docs/recommendation_requirements.md](docs/recommendation_requirements.md) | 추천 포트폴리오 정책 명세 |
| [docs/WIREFRAME.md](docs/WIREFRAME.md) | 화면 와이어프레임 |
| [docs/UML.md](docs/UML.md) | 유스케이스, ERD, 시퀀스 다이어그램 |
| [docs/WBS_GANTT.md](docs/WBS_GANTT.md) | 작업 분해와 일정 |
| [docs/QA.md](docs/QA.md) | 품질 검증 체크리스트 |
| [docs/ARCHITECTURE_CLEANUP.md](docs/ARCHITECTURE_CLEANUP.md) | 아키텍처 정리 내역 |
| [docs/PRESENTATION_SCRIPT.md](docs/PRESENTATION_SCRIPT.md) | 발표 대본 |
| [docs/AlphaPick_Final_PRD.pdf](docs/AlphaPick_Final_PRD.pdf) | 최종 PRD PDF |

## 검증

```powershell
cd backend
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test stocks

cd ..\frontend
npm run build
```

## 현재 UI 메모

- 좌측 사이드바의 AlphaPick 로고를 누르면 기본 대시보드(`/`)로 이동합니다.
- `오늘의 포트폴리오` 메뉴는 편입 종목 전체 화면(`/portfolio`)으로 이동합니다.
- `종목 검색` 화면은 좌측 패널에서 섹터 그룹과 2차 테마로 1,115개 종목을 필터링합니다.
- `백테스트` 메뉴와 화면은 사용자 화면에서 제거되었습니다.
- 웹사이트 favicon과 사이드바 로고는 `frontend/public/alphapick-icon.png`를 사용합니다.
- 점수 산정 기준 설명은 추후 기본 대시보드 제목 옆 `(i)` 버튼에서 제공할 예정입니다.

## 투자 유의 문구

AlphaPick은 교육용 분석 도구입니다. 투자 자문이 아니며, 수익을 보장하지 않고, 실제 매매 주문 기능을 제공하지 않습니다.
