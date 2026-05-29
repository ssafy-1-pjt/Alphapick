# Feature Specification - AlphaPick Challenge Recommendation Engine

본 문서는 AlphaPick 추천 포트폴리오를 고도화하기 위한 최종 기능 명세서입니다.

단순한 데이터 나열을 넘어 **성향별 편입 허들**, **시장 상태 기반 현금 자산 배분**, **Sector Cap 및 재분배**, 그리고 **분산 불가 비중의 현금 귀속 대피** 메커니즘을 정의합니다. 또한 이를 실제 서비스 아키텍처 수준으로 끌어올리기 위한 **보조 AI 서버(FastAPI)** 및 **비동기 배치 스케줄러(Celery + Redis)** 통합 명세를 규정합니다.

---

## 1. 아키텍처 구성 및 역할

추천 엔진은 Django 4.2.30 메인 백엔드를 핵심으로 하며, 추가로 허용된 Python 생태계 기술들을 활용해 마이크로서비스 및 비동기 처리 구조를 완성합니다.

- **Django (메인 백엔드)**: 자산 배분 연산, 종목 필터링, 데이터베이스 적재, 클라이언트 API 서비스 제공.
- **FastAPI (보조 AI 서버)**: OpenAI/Anthropic API 호출 등 무거운 텍스트 생성과 LangChain 에이전트 구동 격리.
- **Celery + Redis (비동기 및 배치 스케줄링)**: 매일 장 마감 후 pykrx 데이터 수집 스케줄링 배치 실행, 무거운 백테스트 연산 백그라운드 큐 처리.

---

## 2. 성향별 편입 허들

성향별로 가치와 타이밍, 데이터 신뢰도 허들을 개별화하여 투자 성향에 최적화된 종목 필터링을 수행합니다. 포트폴리오 최종 편입 최소 `total_score` 컷오프는 70점 공통 유지합니다.

| 투자 성향 | 회사 가치 | 진입 타이밍 | 신뢰도 | 섹터 최대 비중 (Sector Cap) |
|---|---:|---:|---:|---:|
| **공격형** | 65 | 75 | 65 | 35% |
| **중립형** | 70 | 70 | 70 | 30% |
| **안정형** | 75 | 65 | 75 | 25% |

- **공격형**: 주도주 성격의 모멘텀 및 진입 타이밍(75점 이상)을 더 강하게 평가합니다.
- **안정형**: 기업 자체의 펀더멘탈(75점 이상)과 데이터의 무결성(신뢰도 75점 이상)을 엄격하게 필터링합니다.

---

## 3. 시장 상태 기반 현금(Cash) 자산 배분

포트폴리오의 리스크 헤지를 위해 편입 후보 종목 수 및 시장 방향 점수(`marketDirection`)를 결합하여 가장 보수적인 현금 비중을 결정합니다.

### 3.1 편입 후보 수 기준 (A)
- **5개 이상** (강세장): 공격형 0% / 중립형 0% / 안정형 5%
- **3~4개** (중립장): 공격형 10% / 중립형 15% / 안정형 20%
- **1~2개** (약세장): 공격형 20% / 중립형 30% / 안정형 35%
- **0개** (위기장): 전 성향 100%

### 3.2 시장 방향 점수 기준 (B)
- **65점 이상** (강세장): 공격형 0% / 중립형 0% / 안정형 5%
- **50~64점** (중립장): 공격형 10% / 중립형 15% / 안정형 20%
- **40~49점** (약세장): 공격형 20% / 중립형 30% / 안정형 40%
- **40점 미만** (위기장): 공격형 35% / 중립형 50% / 안정형 60%

> [!TIP]
> **결정 공식**: `최종 기본 현금 비중 = Max(A 기준 현금 비중, B 기준 현금 비중)`  
> 후보 종목 수가 넉넉하더라도 시장 전반의 방향성 점수가 크게 꺾였을 경우 현금 비중을 높여 안정성을 확보합니다.

---

## 4. Sector Cap 비중 제한 및 재분배 / 현금 귀속

1. **초기 주식 예산 산정**: `100% - 최종 기본 현금 비중`을 주식 투자 예산(`equity_budget`)으로 설정합니다.
2. **1차 배분**: 성향별 균형 점수(`eligibility_score`)의 70점 초과 강도에 비례하여 주식 예산을 종목별로 배분합니다.
3. **Sector Cap 필터링**: 개별 섹터 비중의 합이 투자 성향별 한도를 초과하는지 검증합니다.
4. **점증적 재분배**: 초과분 비중(`excess`)을 잘라내어, 아직 Cap 한도에 여유가 있는 다른 섹터 종목들에 점수 비례로 누적 분산합니다.
5. **현금 귀속 대피**: 타 섹터 종목 또한 모두 Cap 한도에 달해 더 이상 분산이 불가능한 초과분은 자동으로 **안전 자산인 현금(Cash) 비중으로 최종 흡수**됩니다.

---

## 5. API 응답 필드 규격 (DRF Serializer 준수)

`GET /api/portfolio/today/?risk_type=neutral` API는 DRF의 Serializer 클래스를 활용하여 엄격히 정의된 데이터 구조를 반환해야 합니다.

```json
{
  "baseDate": "YYYY-MM-DD",
  "portfolioScore": 76.5,
  "eligibilityScore": 78.2,
  "userRiskType": "neutral",
  "riskTypeLabel": "중립형",
  "hurdles": {
    "company": 70,
    "timing": 70,
    "reliability": 70
  },
  "sectorCap": 30,
  "cashWeight": 15.0,
  "baseCashWeight": 15.0,
  "sectorCashWeight": 0.0,
  "cashReasons": [
    "중립형 편입 후보 3개 기준 중립장 판단: 현금 15%",
    "중립형 시장 방향 평균 54.0점 기준 중립장 판단: 현금 15%"
  ],
  "marketDirectionScore": 54.0,
  "marketRegime": "중립장",
  "allocationItems": [
    {
      "type": "stock",
      "ticker": "005930.KS",
      "name": "삼성전자",
      "sector": "반도체",
      "weight": 42.5
    },
    {
      "type": "cash",
      "ticker": "CASH",
      "name": "현금",
      "sector": "현금",
      "weight": 15.0
    }
  ],
  "items": [
    {
      "ticker": "005930.KS",
      "name": "삼성전자",
      "sector": "반도체",
      "weight": 42.5,
      "total_score": 75.0,
      "company_score": 72.0,
      "timing_score": 78.0,
      "reliability_score": 80.0,
      "raw_weight": 42.5,
      "sector_cap_applied": false,
      "sector_cap_reduction": 0.0
    }
  ],
  "watchCandidates": [
    {
      "ticker": "000660.KS",
      "name": "SK하이닉스",
      "latest_score": 68.0,
      "reason": "기술 지표 상 모멘텀이 상승세이나 신뢰도 기준치 하회"
    }
  ],
  "benchmarkSummary": {
    "benchmark": "KOSPI",
    "rebalanceType": "daily",
    "threshold": 70,
    "itemCount": 1,
    "cashWeight": 15.0,
    "message": "..."
  }
}
```

---

## 6. AI 에이전트 및 비동기 배치 연동 스펙

### 6.1 FastAPI AI 에이전트 서버 연동 (AI Comment Generation)
- **엔드포인트**: `POST /api/stocks/{ticker}/ai-comment/` 호출 시 Django는 FastAPI에 주식 원천 데이터(Score, FinancialMetric, Price)를 JSON 페이로드로 담아 전송합니다.
- **FastAPI 처리**: FastAPI는 전달받은 지표 데이터를 바인딩하여 LLM 프롬프트를 구성하고, OpenAI/Anthropic SDK를 사용해 총평 및 투자 위험 경고 텍스트를 구조화된 JSON으로 반환합니다.
- **Django 처리**: Django는 FastAPI가 생성한 코멘트 결과를 `AICommentCache` 테이블에 영구 저장(Caching)하여 중복 호출을 막고 API 응답 처리 속도를 보장합니다.

### 6.2 Celery + Redis 비동기 배치 수집 (Batch Scheduler)
- **배치 작업**: 매일 장 마감 후 외부 KOSPI/KOSDAQ 종가 데이터 및 리포트 점수를 크롤링 및 계산하는 태스크(`update_daily_stock_prices_and_scores`)를 Celery Beat로 예약 실행합니다.
- **비동기 큐**: Redis 인메모리 큐를 활용해 다량의 종목 시뮬레이션 및 백테스트 작업 연산을 Celery Worker로 분산 위임하여 Django API 웹 서버의 부하를 0에 수렴하도록 통제합니다.
