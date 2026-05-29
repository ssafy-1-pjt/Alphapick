# AlphaPick Wiki Directory & Onboarding Index

본 문서는 AlphaPick 프로젝트의 전체 요구사항, 설계 다이어그램, 아키텍처 개선 히스토리 및 개발자 온보딩 코스를 총괄하는 통합 위키 인덱스 문서입니다. 

이 프로젝트에 새로 합류한 개발자를 위한 **Principal-Level Guide** 및 **Zero-to-Hero Learning Path**를 포함합니다.

---

## 1. 🚀 Onboarding Guide

### 1.1. Principal-Level Guide (핵심 아키텍처 통찰)
AlphaPick의 핵심 설계 사상은 **"정량적 밸류·모멘텀 필터링"**과 **"리스크 제어식 동적 자산 배분"**의 결합입니다.

- **핵심 아키텍처 철학**: 
  개별 종목들의 스냅샷 점수(`ScoreSnapshot`)를 동적으로 검증하여 성향별 회사 가치·진입 타이밍·신뢰도 허들을 통과한 종목군만을 추려내고, 균형 점수와 리스크 상태에 따라 포트폴리오 비중을 분배합니다.
  만약 시장 강도가 약해 편입 종목 수가 줄어들거나 특정 섹터 쏠림이 생겨 분산이 불가능해질 경우, 초과 비중은 안전 자산인 **현금(Cash)**으로 강제 귀속시켜 리스크를 자동 하향 조정합니다.
- **수도코드 예시 (Python의 Django 로직을 Go 스타일로 추상화한 예)**:
  ```go
  // Go 스타일의 포트폴리오 동적 비중 배분 및 자산배분 통찰 예시
  type PortfolioItem struct {
      Ticker string
      Weight float64
  }

  func CalculatePortfolio(candidates []StockScore, riskType string) ([]PortfolioItem, float64) {
      // 1. 성향별 컴포넌트 컷오프 세분화 적용
      var filtered []StockScore
      for _, s := range candidates {
          if s.PassesComponentHurdle(riskType) {
              filtered = append(filtered, s)
          }
      }

      // 2. 성향별 현금 테이블로 기본 현금 비중 배정
      var cashWeight float64
      switch n := len(filtered); {
      case n >= 5: cashWeight = CashByRiskAndRegime(riskType, "strong")
      case n >= 3: cashWeight = CashByRiskAndRegime(riskType, "neutral")
      case n >= 1: cashWeight = CashByRiskAndRegime(riskType, "weak")
      default:     return nil, 100.0 // 100% 현금 대피
      }

      // 3. 주식 할당 비중(100 - cashWeight) 내에서 초과점수 비례 비중 배분
      totalExcess := 0.0
      for _, s := range filtered {
          totalExcess += math.Max(s.TotalScore - 70.0, 0.0)
      }

      var items []PortfolioItem
      for _, s := range filtered {
          var weight float64
          if totalExcess > 0 {
              weight = (math.Max(s.TotalScore - 70.0, 0.0) / totalExcess) * (100.0 - cashWeight)
          } else {
              weight = (100.0 - cashWeight) / float64(len(filtered))
          }
          items = append(items, PortfolioItem{Ticker: s.Ticker, Weight: weight})
      }

      // 4. Sector Cap 제한 및 분산 불가 비중의 현금 대피
      items, extraCash := ApplySectorCapAndRedistribute(items, riskType)
      cashWeight += extraCash

      return items, cashWeight
  }
  ```

- **도전형 시스템 아키텍처 다이어그램**:
  ```mermaid
  graph TD
    User([사용자]) <--> Vue[Vue 3 SPA 프론트엔드]
    Vue <--> Django[Django 4.2.30 DRF API]
    Django <--> Services[Portfolio / Backtest Engine]
    Services <--> DB[(SQLite Database)]
    Django <--> FastAPI[FastAPI AI Comment Server]
    FastAPI <--> LLM[LLM API / OpenAI SDK]
    
    %% 비동기 큐 스태킹
    Scheduler[Celery Beat Scheduler] --> Redis((Redis Message Broker))
    Redis --> Worker[Celery Worker]
    Worker --> DB
  ```

---

### 1.2. Zero-to-Hero Learning Path ( progressive depth )
신임 개발자가 이 코드를 분석하고 기여하기 위한 단계적 가이드라인입니다.

#### Part I: 기술 기반 학습
- **Backend (Python 3.10+ & Django 4.2.30 & DRF)**: 
  - Django Rest Framework(DRF) Serializer를 이용해 오늘의 포트폴리오 데이터를 엄격하게 타입 직렬화합니다.
  - JWT 토큰 기반 회원 인증은 `rest_framework_simplejwt` 라이브러리를 사용합니다.
- **보조 서비스 (FastAPI & Celery & Redis)**:
  - **FastAPI**: AI 추론 연산 처리를 격리하여 구동하는 보조 API 서버입니다.
  - **Celery & Redis**: 장 마감 후 주기적인 주가 데이터 업데이트 및 백테스트의 비동기 처리를 담당합니다.
- **Frontend (Vue 3 + Pinia + Vue Router + Tailwind CSS)**: 
  - 상태 관리는 Pinia를 기반으로 하며, 사용자 세션은 `frontend/src/stores/auth.js`에서 통합 관리합니다.
  - 가격 차트 및 백테스트 차트는 Canvas API를 래핑한 Lucide Icons 및 인라인 SVG 컴포넌트를 활용합니다.

#### Part II: 핵심 도메인 모델
- **Stock (주식 마스터)**: 국내 주식의 기본 인적 사항을 담는 모델 ([backend/stocks/models.py](../backend/stocks/models.py))
- **PriceDaily (일별 가격/기술지표)**: 1년치 일별 시가, 고가, 저가, 종가 및 EMA, 볼린저 밴드 등의 지표 저장 ([backend/stocks/models.py](../backend/stocks/models.py))
- **ScoreSnapshot (정량 분석 결과)**: 매일 장 마감 후 기업 점수, 타이밍 점수, 리스크 점수, 뉴스 감성 및 계산 근거 보관 ([backend/stocks/models.py](../backend/stocks/models.py))
- **PortfolioRun / PortfolioItem (자산 배분)**: 날짜별로 최종 선별되어 배정된 비중 보관 ([backend/stocks/models.py](../backend/stocks/models.py))

---

## 2. 📂 위키 문서 인덱스 (Directory Map)

AlphaPick 프로젝트의 요구사항 및 설계 문서는 다음과 같이 유기적으로 구조화되어 있습니다.

### 2.1. 요구사항 및 기획 (Requirements)
- **[PRD.md](PRD.md)**: AlphaPick의 최초 문제 정의, 코어 가치 제안, 평가지표 및 수용 기준을 설명하는 최상위 요구사항 정의서입니다.
- **[recommendation_requirements.md](recommendation_requirements.md)**: 성향별 다이내믹 허들, 시장 상황별 현금 비중, Sector Cap 및 재분배 등 포트폴리오 추천 로직의 고도화 스펙을 상세 기술한 기능 명세서입니다.
- **[WIREFRAME.md](WIREFRAME.md)**: 메인 포트폴리오 대시보드, 종목 스코어 리포트 상세화면, 백테스트 성과 분석 화면의 UI 레이아웃 설계도입니다.

### 2.2. 시스템 설계 및 일정 (Design & Timeline)
- **[UML.md](UML.md)**: 유스케이스, ERD 데이터베이스 관계도, 포트폴리오 및 비동기 배치 수집, AI 코멘트 캐싱 시퀀스 다이어그램 등 시스템 구성 설계서입니다.
- **[WBS_GANTT.md](WBS_GANTT.md)**: 프로젝트 개발 일정 관리 및 WBS 산출물 체크리스트입니다.

### 2.3. 품질 검증 및 리팩토링 (QA & Maintenance)
- **[QA.md](QA.md)**: 핵심 시나리오 및 수용 기준 통과 여부를 검증하기 위한 QA 테스트 시나리오 시트입니다.
- **[ARCHITECTURE_CLEANUP.md](ARCHITECTURE_CLEANUP.md)**: 이전 레거시 피트니스 앱 코드의 삭제 내역 및 정규화 리팩토링 히스토리를 기술한 문서입니다.
- **[PRESENTATION_SCRIPT.md](PRESENTATION_SCRIPT.md)**: 최종 관통 프로젝트 시연 및 아키텍처 발표를 위한 핵심 발표자료 대본 가이드입니다.

---

## 3. ⚙️ 로컬 개발 환경 및 실행 가이드 (Challenge Stack)

본 프로젝트는 여러 분산 컴포넌트를 사용하므로, 다음 지침에 따라 순서대로 실행하십시오.

### 3.1. 필수 인프라 구동 (Redis)
- Windows 환경에서는 WSL을 이용하거나 Windows용 Redis 포트 버전을 실행합니다.
  ```bash
  # Redis 서버 실행 (기본 포트: 6379)
  redis-server
  ```

### 3.2. 보조 AI 서버 구동 (FastAPI)
- `backend/ai_server/` 폴더 내 가상환경을 활성화하고 uvicorn을 기동합니다.
  ```bash
  # FastAPI 서버 구동
  cd backend/ai_server
  uvicorn main:app --reload --port 8080
  ```

### 3.3. 비동기 큐 구동 (Celery Worker)
- **중요**: Windows OS에서는 반드시 단일 스레드로 안정 실행을 지시하기 위해 `-P solo` 옵션을 기재해야 합니다.
  ```bash
  # Celery Worker 기동 (Django root 디렉토리에서 실행)
  celery -A config worker --loglevel=info -P solo
  ```

### 3.4. 메인 Django 백엔드 및 Vue 3 프론트엔드 구동
  ```bash
  # Django 서버 실행
  python manage.py runserver
  
  # Vue 3 프론트엔드 개발 서버 실행
  cd frontend
  npm run dev
  ```
