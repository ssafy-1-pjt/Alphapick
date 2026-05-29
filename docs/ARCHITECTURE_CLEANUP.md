# AlphaPick Architecture Cleanup & Normalization Document

본 문서는 AlphaPick MVP 코드베이스에서 타 프로젝트의 피트니스 관련 레거시 요소를 정화하고, PRD 및 UML 설계 사양에 맞춰 주식 분석 및 포트폴리오 로직을 정상화한 내역을 기록한 아키텍처 정규화 문서입니다.

---

## 1. 아키텍처 정화 내역 (Cleanup)

주식 분석 플랫폼인 AlphaPick 도메인의 순수성을 해치고 리소스를 점유하던 이전 피트니스 관련 프로젝트("Outfit")의 잔재 코드를 완전히 제거했습니다.

### 1.1. 백엔드 앱 및 핏스처 삭제
- **삭제 앱**: `catalog`(피트니스 코스), `workouts`(운동 기록), `reviews`(리뷰), `recommendations`(코스 위치 추천) 앱 폴더 전체를 물리적으로 삭제했습니다.
- **설정 정리**: `config/settings.py`의 `INSTALLED_APPS` 및 `config/urls.py`의 API 라우트 매핑에서 해당 앱들의 바인딩을 모두 제거했습니다.
- **핏스처 정리**: `fixtures/demo_catalog.json` 피트니스 샘플 데이터를 삭제했습니다.

### 1.2. 사용자 모델 및 어드민 정규화
- **불필요 필드 제거**: `accounts.User` 모델에서 `level`, `preferred_location`, `preferred_categories`, `onboarding_completed` 필드를 삭제했습니다.
- **어드민 보정**: `accounts/admin.py`에서 불필요한 필드 바인딩을 제거하고 `risk_type` 필드를 노출하도록 `AlphaPickUserAdmin`으로 리팩토링했습니다.
- **토큰 시리얼라이저 정화**: JWT 로그인용 시리얼라이저 이름을 `OutfitTokenObtainPairSerializer`에서 `AlphaPickTokenObtainPairSerializer`로 리네이밍했습니다.

### 1.3. 프론트엔드 레거시 파일 삭제
- `frontend/src/views`에 방치되어 있던 `CourseDetailView.vue` 등 피트니스 관련 미사용 뷰 파일 7종을 완전히 삭제했습니다.

---

## 2. 비즈니스 로직 정규화 내역 (Normalization)

PRD 스펙 대비 불일치하거나 누락되었던 금융 비즈니스 로직 및 UI 연동을 사양에 맞게 올바르게 정규화했습니다.

### 2.1. 사용자 투자 성향(`risk_type`) 연동
- `accounts.User` 모델에 주식 투자 성향을 저장할 `risk_type` 필드를 추가했습니다.
- 회원가입 및 토큰 발급 시 `risk_type`이 입출력 스펙에 정상 포함되도록 하였습니다.

### 2.2. 포트폴리오 편입 조건 정규화
- `stocks/services.py`에서 회사 점수 및 타이밍 점수의 하한 필터 기준인 `MIN_COMPONENT_SCORE`를 `70`에서 `60`으로 원복하여 PRD 6.1절의 조건(`company_score >= 60`, `timing_score >= 60`)을 충족하도록 수정했습니다.

### 2.3. 포트폴리오 비중 산정 공식 수정
- 리스크 할인이 반영되지 않은 임시 점수(`eligibility_score`) 대신, 최종 리스크 제어 아키텍처가 적용된 `total_score`를 기준으로 편입 비중을 분배하도록 코드를 변경하였습니다.

### 2.4. 동적 일별 리밸런싱 백테스트 시뮬레이터 개편
- 기존 백테스트의 선행 편향(Look-ahead Bias)을 제거하기 위해, 시뮬레이션 기간 내 매 거래일마다 과거 시점의 가치·타이밍 점수를 바탕으로 포트폴리오를 구성하고 다음 거래일까지의 일별 가중 수익률을 동적으로 누적해 나가는 **실제 일별 리밸런싱 백테스트**를 구현하여 금융 도메인 신뢰성을 대폭 향상했습니다.

### 2.5. 프론트엔드 누락 기능 복구
- **CAN SLIM 진단**: 종목 리포트 하단에 누락되어 있던 **CAN SLIM** 지표(C-A-N-S-L-I-M 각 영역별 점수, 명칭, 수치 및 준수 여부) 렌더링 카드를 추가했습니다.
- **관심종목(Watchlist) 토글**: 상세 화면 상단에 별표 버튼을 배치하여 사용자가 관심 종목을 추가/해제할 수 있도록 백엔드 API와 연동했습니다.
- **인증 라우트 복구**: 로그인, 회원가입, 마이페이지, 프로필 수정 화면을 `router/index.js`에 정상 등록하고, `AppHeader.vue`를 통해 로그인 상태에 따라 내비게이션 바가 다이내믹하게 변하도록 처리했습니다.
- **임의 구현 제거**: PRD 명세 외에 임의로 구현되었던 상세 리포트 캡처 힌트와 캡처 버튼을 삭제했습니다.
