<template>
  <section class="min-h-screen bg-[#f3f6f9]">
    <div class="page-shell py-6">
      <div v-if="loading" class="panel p-8 text-center font-bold text-slate-500">스코어 리포트를 불러오는 중입니다.</div>
      <div v-else-if="error" class="panel border-red-200 bg-red-50 p-8 text-red-700">{{ error }}</div>

      <template v-else>
        <!-- TOPBAR HEADER -->
        <div class="mb-5 flex flex-wrap items-start justify-between gap-4">
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <h1 class="text-3xl font-bold text-[#172033] md:text-4xl break-keep text-balance">{{ report.stock.name }}</h1>
              <span class="badge bg-slate-100 text-slate-600 tabular-nums">{{ report.stock.ticker }}</span>
              <span class="badge bg-mint/10 text-mint break-keep">{{ report.stock.sector }}</span>
              <span
                v-for="theme in stockThemes"
                :key="theme"
                class="badge bg-blue-50 text-blue-700 break-keep"
              >
                {{ theme }}
              </span>
            </div>
            <div class="mt-2 flex flex-wrap items-center gap-2">
              <p class="text-4xl font-extrabold leading-none text-slate-950 tabular-nums">{{ latestPrice }}원</p>
              <p class="text-sm font-bold text-slate-500 tabular-nums">{{ latestTradeDateText }}</p>
              <p class="text-sm font-extrabold tabular-nums" :class="dailyChangeClass">{{ dailyChangeSummaryText }}</p>
              <!-- 주도주: 전일대비 로 오른쪽 (signal 필드에서 판단) -->
              <span v-if="isLeader" class="inline-flex items-center rounded-full bg-slate-900 px-2.5 py-0.5 text-xs font-bold text-white break-keep">주도주</span>
              <!-- key_reason 파싱 배지 순서대로 -->
              <template v-for="tag in keyReasonBadges" :key="tag.label">
                <span
                  class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-bold break-keep"
                  :class="tag.type === 'rs'
                    ? 'bg-teal-50 text-teal-700 ring-1 ring-teal-200'
                    : tag.type === 'signal'
                    ? 'bg-indigo-50 text-indigo-700 ring-1 ring-indigo-200'
                    : 'bg-slate-100 text-slate-600 ring-1 ring-slate-200'"
                >{{ tag.label }}</span>
              </template>
              <span v-if="report.stock.low_liquidity_flag" class="badge bg-amber-100 text-amber-700 break-keep">유동성 주의</span>
              <span v-if="report.score.fail_safe_flag" class="badge bg-red-100 text-red-700 break-keep">Fail-safe</span>
              <span v-if="report.score.target_upside_clipped" class="badge bg-amber-100 text-amber-700 break-keep">목표가 200%+ 클리핑</span>
            </div>
          </div>
          <div class="flex w-full flex-wrap gap-2 md:w-auto md:justify-end">
            <RouterLink
              :to="{ name: 'stock-community', params: { ticker: report.stock.ticker } }"
              class="inline-flex min-h-12 flex-1 items-center justify-center gap-2 rounded-lg bg-[#12b8a6] px-5 text-base font-extrabold text-white shadow-lg shadow-mint/15 transition-transform duration-200 hover:-translate-y-0.5 hover:scale-[1.02] hover:bg-mint/90 active:scale-[0.97] md:flex-none"
            >
              <MessageCircle :size="20" />
              토론방
            </RouterLink>
            <button
              class="inline-flex min-h-12 flex-1 items-center justify-center gap-2 rounded-lg border px-5 text-base font-extrabold transition-all duration-200 hover:-translate-y-0.5 hover:scale-[1.02] active:scale-[0.97] md:flex-none"
              :class="watchlistSaved ? 'border-rose-200 bg-rose-50 text-rose-600' : 'border-slate-200 bg-white text-slate-700 hover:border-mint/30 hover:text-mint'"
              type="button"
              :disabled="watchlistLoading"
              @click="toggleWatchlist"
            >
              <Heart :size="20" :fill="watchlistSaved ? 'currentColor' : 'none'" />
              {{ watchlistSaved ? "관심 종목 저장됨" : "관심 종목 저장" }}
            </button>
          </div>
        </div>

        <!-- HERO CARD (Circular Gauge & Summary columns) -->
        <section class="panel overflow-hidden mb-5">
          <div class="grid md:grid-cols-[240px_1fr] gap-6 p-5 md:p-6 bg-white border-b border-slate-100">
            <!-- Left Side: Circular Gauge -->
            <div class="flex flex-col items-center text-center border-r-0 md:border-r border-slate-100 md:pr-6">
              <div class="relative w-36 h-36 flex items-center justify-center">
                <svg viewBox="0 0 148 148" class="w-full h-full transform -rotate-90">
                  <!-- Grey track -->
                  <circle cx="74" cy="74" r="60" fill="none" stroke="#e2e8f0" stroke-width="12" />
                  <!-- Mint active gauge -->
                  <circle
                    cx="74"
                    cy="74"
                    r="60"
                    fill="none"
                    stroke="#12b8a6"
                    stroke-width="12"
                    stroke-linecap="round"
                    :stroke-dasharray="gaugeDashArray"
                  />
                </svg>
                <div class="absolute flex flex-col items-center justify-center">
                  <b class="text-3xl font-extrabold text-[#172033] tabular-nums leading-none">
                    {{ formatScore(report.score.total_score) }}
                  </b>
                  <span class="text-[11px] text-slate-400 font-bold mt-1">/ 100점</span>
                </div>
              </div>
              <div class="mt-4">
                <span class="rounded-full bg-mint/10 px-3.5 py-1 text-sm font-extrabold text-mint">
                  {{ report.score.verdict }}
                </span>
              </div>
              <p class="mt-2 text-xs font-bold text-slate-500">
                {{ report.score.signal }} · {{ report.score.consensus || "컨센서스 없음" }}
              </p>
              <p v-if="report.score.warning" class="mt-2 text-[11px] font-bold text-slate-400 max-w-[200px]">
                {{ report.score.warning }}
              </p>
            </div>

            <!-- Right Side: Report Highlights & Cautions -->
            <div class="flex flex-col justify-between">
              <div>
                <span class="text-2xs font-extrabold uppercase tracking-widest text-mint">AlphaPick Report</span>
                <h2 class="mt-1 text-2xl font-extrabold leading-tight text-[#172033] break-keep text-balance">
                  {{ reportTitle }}
                </h2>
                <p class="mt-1.5 text-sm font-bold text-slate-500 break-keep text-pretty">
                  {{ reportSubtitle }}
                </p>
              </div>

              <div class="mt-4 grid md:grid-cols-2 gap-6">
                <div>
                  <span class="text-xs font-extrabold text-mint block mb-2 break-keep">핵심 근거</span>
                  <ul class="space-y-2">
                    <li v-for="item in decisionHighlights" :key="item" class="flex items-start gap-2 text-sm font-semibold text-slate-700 break-keep text-pretty">
                      <span class="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[#12b8a6]"></span>
                      <span>{{ item }}</span>
                    </li>
                  </ul>
                </div>
                <div>
                  <span class="text-xs font-extrabold text-amber-700 block mb-2 break-keep">주의 요인</span>
                  <ul class="space-y-2">
                    <li v-for="item in riskHighlights" :key="item" class="flex items-start gap-2 text-sm font-semibold text-slate-700 break-keep text-pretty">
                      <span class="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500"></span>
                      <span>{{ item }}</span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
          <div v-if="summaryMetricText" class="bg-slate-50/70 px-5 py-3 text-sm font-semibold leading-6 text-slate-500 break-keep text-pretty md:px-6">
            {{ summaryMetricText }}
          </div>
        </section>

        <!-- LAYERS SCORE CARDS (Collapsible components breakdown) -->
        <section class="mb-6">
          <p class="text-sm font-extrabold text-slate-900 mb-1">종합 {{ formatScore(report.score.total_score) }}점의 구성</p>
          <p class="text-xs font-bold text-slate-400 mb-3">
            아래 레이어 점수를 가중합산해 종합 점수를 산출합니다. 카드를 누르면 세부 신호를 볼 수 있습니다.
          </p>
          <div class="grid gap-3 md:grid-cols-4">
            <!-- 가치 / 퀄리티 Card -->
            <div
              class="panel p-4 cursor-pointer transition border border-slate-100 hover:border-slate-300"
              @click="openLayers.valueQuality = !openLayers.valueQuality"
            >
              <div class="flex items-center justify-between gap-2">
                <span class="text-sm font-extrabold text-slate-800">가치 / 퀄리티</span>
                <span class="text-xl font-extrabold text-amber-600 tabular-nums">
                  {{ formatScore(report.score.area_scores.valueQuality) }}
                </span>
              </div>
              <p class="text-xs text-slate-500 mt-1.5 leading-relaxed">
                유동성, 변동성 안정성, 52주 고점 거리로 가격 기반 퀄리티를 평가합니다.
              </p>
              <div class="mt-3.5 h-1.5 rounded-full bg-slate-100 overflow-hidden">
                <div
                  class="h-full bg-amber-500 rounded-full"
                  :style="{ width: `${scorePercent(report.score.area_scores.valueQuality)}%` }"
                ></div>
              </div>
              <div class="mt-2 text-[10px] text-slate-400 font-bold flex items-center gap-1">
                <span class="transition-transform duration-150 inline-block" :class="openLayers.valueQuality ? 'rotate-180' : ''">▾</span>
                세부 신호 보기
              </div>
              <div v-show="openLayers.valueQuality" class="mt-3 pt-3 border-t border-dashed border-slate-200 flex flex-col gap-2" @click.stop>
                <div class="flex items-center justify-between text-xs text-slate-600 font-bold">
                  <span>연간 ROE 대용</span>
                  <b class="text-slate-900">{{ formatScore(report.score.area_scores.annualRoeProxy) }}점</b>
                </div>
                <div class="flex items-center justify-between text-xs text-slate-600 font-bold">
                  <span>EPS 가속도</span>
                  <b class="text-slate-900">{{ formatScore(report.score.area_scores.epsAcceleration) }}점</b>
                </div>
              </div>
            </div>

            <!-- 주도주 모멘텀 Card -->
            <div
              class="panel p-4 cursor-pointer transition border border-slate-100 hover:border-slate-300"
              @click="openLayers.leadershipMomentum = !openLayers.leadershipMomentum"
            >
              <div class="flex items-center justify-between gap-2">
                <span class="text-sm font-extrabold text-slate-800">주도주 모멘텀</span>
                <span class="text-xl font-extrabold text-mint tabular-nums">
                  {{ formatScore(report.score.area_scores.leadershipMomentum) }}
                </span>
              </div>
              <p class="text-xs text-slate-500 mt-1.5 leading-relaxed">
                상대강도, 6개월 수익률, 52주 고점 근접도로 주도주 여부를 판단합니다.
              </p>
              <div class="mt-3.5 h-1.5 rounded-full bg-slate-100 overflow-hidden">
                <div
                  class="h-full bg-mint rounded-full"
                  :style="{ width: `${scorePercent(report.score.area_scores.leadershipMomentum)}%` }"
                ></div>
              </div>
              <div class="mt-2 text-[10px] text-slate-400 font-bold flex items-center gap-1">
                <span class="transition-transform duration-150 inline-block" :class="openLayers.leadershipMomentum ? 'rotate-180' : ''">▾</span>
                세부 신호 보기
              </div>
              <div v-show="openLayers.leadershipMomentum" class="mt-3 pt-3 border-t border-dashed border-slate-200 flex flex-col gap-2" @click.stop>
                <div class="flex items-center justify-between text-xs text-slate-600 font-bold">
                  <span>신고가 / 피벗</span>
                  <b class="text-slate-900">{{ formatScore(report.score.area_scores.pivotBreakout) }}점</b>
                </div>
                <div class="flex items-center justify-between text-xs text-slate-600 font-bold">
                  <span>수급 / 거래량</span>
                  <b class="text-slate-900">{{ formatScore(report.score.area_scores.smartMoney) }}점</b>
                </div>
              </div>
            </div>

            <!-- 리스크 제어 Card -->
            <div
              class="panel p-4 cursor-pointer transition border border-slate-100 hover:border-slate-300"
              @click="openLayers.riskControl = !openLayers.riskControl"
            >
              <div class="flex items-center justify-between gap-2">
                <span class="text-sm font-extrabold text-slate-800">리스크 제어</span>
                <span class="text-xl font-extrabold text-rose-500 tabular-nums">
                  {{ formatScore(report.score.sentiment_score) }}
                </span>
              </div>
              <p class="text-xs text-slate-500 mt-1.5 leading-relaxed">
                시장 방향, 단기 과열, 낙폭 위험으로 추격 매수 리스크를 제어합니다.
              </p>
              <div class="mt-3.5 h-1.5 rounded-full bg-slate-100 overflow-hidden">
                <div
                  class="h-full bg-rose-500 rounded-full"
                  :style="{ width: `${scorePercent(report.score.sentiment_score)}%` }"
                ></div>
              </div>
              <div class="mt-2 text-[10px] text-slate-400 font-bold flex items-center gap-1">
                <span class="transition-transform duration-150 inline-block" :class="openLayers.riskControl ? 'rotate-180' : ''">▾</span>
                세부 신호 보기
              </div>
              <div v-show="openLayers.riskControl" class="mt-3 pt-3 border-t border-dashed border-slate-200 flex flex-col gap-2" @click.stop>
                <div class="flex items-center justify-between text-xs text-slate-600 font-bold">
                  <span>시장 방향</span>
                  <b class="text-slate-900">{{ formatScore(report.score.area_scores.marketDirection) }}점</b>
                </div>
                <div class="flex items-center justify-between text-xs text-slate-600 font-bold">
                  <span>과열 방지</span>
                  <b class="text-slate-900">{{ formatScore(report.score.area_scores.meanReversion) }}점</b>
                </div>
                <div class="flex items-center justify-between text-xs text-slate-600 font-bold">
                  <span>낙폭 방지</span>
                  <b class="text-slate-900">{{ formatScore(report.score.area_scores.drawdownControl) }}점</b>
                </div>
              </div>
            </div>

            <!-- 뉴스 감성 Card -->
            <div
              class="panel p-4 cursor-pointer transition border border-slate-100 hover:border-slate-300"
              @click="openLayers.newsSentiment = !openLayers.newsSentiment"
            >
              <div class="flex items-center justify-between gap-2">
                <span class="text-sm font-extrabold text-slate-800">뉴스 감성</span>
                <span
                  class="text-xl font-extrabold tabular-nums"
                  :class="report.score.area_scores.newsSentiment !== null && report.score.area_scores.newsSentiment !== undefined ? 'text-indigo-600' : 'text-slate-400'"
                >
                  {{ report.score.area_scores.newsSentiment !== null && report.score.area_scores.newsSentiment !== undefined ? formatScore(report.score.area_scores.newsSentiment) : '-' }}
                </span>
              </div>
              <p class="text-xs text-slate-500 mt-1.5 leading-relaxed">
                최근 뉴스의 긍정/부정 감성을 계량화하여 투자 심리를 측정합니다.
              </p>
              <div class="mt-3.5 h-1.5 rounded-full bg-slate-100 overflow-hidden">
                <div
                  v-if="report.score.area_scores.newsSentiment !== null && report.score.area_scores.newsSentiment !== undefined"
                  class="h-full bg-indigo-500 rounded-full"
                  :style="{ width: `${scorePercent(report.score.area_scores.newsSentiment)}%` }"
                ></div>
                <div
                  v-else
                  class="h-full bg-slate-200 rounded-full w-0"
                ></div>
              </div>
              <div class="mt-2 text-[10px] text-slate-400 font-bold flex items-center gap-1">
                <span class="transition-transform duration-150 inline-block" :class="openLayers.newsSentiment ? 'rotate-180' : ''">▾</span>
                세부 신호 보기
              </div>
              <div v-show="openLayers.newsSentiment" class="mt-3 pt-3 border-t border-dashed border-slate-200 flex flex-col gap-2" @click.stop>
                <div v-if="report.score.news && report.score.news.length > 0" class="flex flex-col gap-2">
                  <div class="flex items-center justify-between text-xs text-slate-600 font-bold">
                    <span>긍정 뉴스</span>
                    <b class="text-slate-900">{{ countNewsSentiment(report.score.news || [], 'positive') }}건</b>
                  </div>
                  <div class="flex items-center justify-between text-xs text-slate-600 font-bold">
                    <span>중립 뉴스</span>
                    <b class="text-slate-900">{{ countNewsSentiment(report.score.news || [], 'neutral') }}건</b>
                  </div>
                  <div class="flex items-center justify-between text-xs text-slate-600 font-bold">
                    <span>부정 뉴스</span>
                    <b class="text-slate-900">{{ countNewsSentiment(report.score.news || [], 'negative') }}건</b>
                  </div>
                </div>
                <div v-else class="text-xs text-slate-400 font-bold py-1">
                  분석된 뉴스 데이터가 없습니다.
                </div>
              </div>
            </div>
          </div>
          <p class="text-center font-bold text-slate-400 text-xs mt-3">
            가치/퀄리티 · 주도주 모멘텀 · 리스크 제어 · 뉴스 감성을 가중합산 → <b>종합 {{ formatScore(report.score.total_score) }}점</b>
          </p>
        </section>

        <!-- CHART SECTION -->
        <section class="mb-6">
          <StockChart :price-series="report.priceSeries" />
        </section>

        <!-- TABS NAVIGATION -->
        <nav class="tabs flex gap-1 border-b border-slate-200 mb-6">
          <button
            v-for="tab in tabOptions"
            :key="tab.value"
            class="tab-btn pb-2.5 mr-6 text-sm font-extrabold border-b-2 transition-all"
            :class="currentTab === tab.value ? 'text-slate-900 border-[#12b8a6]' : 'text-slate-400 border-transparent hover:text-slate-600'"
            type="button"
            @click="currentTab = tab.value"
          >
            {{ tab.label }}
          </button>
        </nav>

        <!-- TAB PANELS -->
        <main class="space-y-6">
          <!-- 1. OVERVIEW (종합 진단) PANEL -->
          <div v-show="currentTab === 'overview'" class="space-y-6">
            <div class="grid gap-6 md:grid-cols-[320px_1fr]">
              <!-- Left side: Matrix card -->
              <div class="panel p-5 bg-white">
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <h4 class="text-sm font-extrabold text-slate-800">회사 가치 × 진입 타이밍</h4>
                    <p class="mt-1 text-[11px] font-bold text-slate-400">70점 기준 분류 · 현재 위치 표시</p>
                  </div>
                  <span class="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-2xs font-extrabold text-slate-500">70점 기준</span>
                </div>

                <div class="mt-4 rounded-lg bg-slate-50 p-3">
                  <div class="mb-2 text-center text-[10px] font-extrabold text-slate-500">진입 타이밍 높음 ↑</div>
                  <div class="relative aspect-square overflow-hidden rounded-md border border-slate-200 bg-white">
                    <div class="absolute left-0 top-0 flex items-center justify-center bg-yellow-300 text-center text-[11px] font-extrabold leading-5 text-yellow-950" :style="quadrantStyle('timingOnly')">
                      타이밍 우선<br />회사 가치 필요
                    </div>
                    <div class="absolute flex items-center justify-center bg-green-400 text-center text-[11px] font-extrabold leading-5 text-green-950" :style="quadrantStyle('pass')">
                      포트폴리오<br />후보
                    </div>
                    <div class="absolute left-0 flex items-center justify-center bg-red-300 text-center text-[11px] font-extrabold leading-5 text-red-950" :style="quadrantStyle('watch')">
                      보수적<br />관찰
                    </div>
                    <div class="absolute flex items-center justify-center bg-sky-300 text-center text-[11px] font-extrabold leading-5 text-sky-950" :style="quadrantStyle('companyOnly')">
                      좋은 회사<br />타이밍 대기
                    </div>
                    <div class="absolute top-0 h-full w-0.5 bg-slate-700/70" :style="{ left: `${componentThreshold}%` }"></div>
                    <div class="absolute left-0 h-0.5 w-full bg-slate-700/70" :style="{ top: `${100 - componentThreshold}%` }"></div>
                    <div
                      class="absolute h-5 w-5 rounded-full border-2 border-white bg-slate-950 shadow-lg ring-4 ring-white/80"
                      :style="quadrantPointStyle"
                      aria-label="현재 점수 위치"
                    ></div>
                  </div>
                  <div class="mt-2 grid grid-cols-3 items-center text-[10px] font-extrabold text-slate-500">
                    <span>회사 가치 낮음</span>
                    <span class="text-center">회사 가치 점수 →</span>
                    <span class="text-right">회사 가치 높음</span>
                  </div>
                  <div class="mt-2 text-center text-[10px] font-bold text-slate-400">진입 타이밍 낮음 ↓</div>
                </div>

                <p class="mt-3 text-xs font-bold text-slate-600 leading-normal">
                  현재 위치: <b>{{ quadrantLabel }}</b><br />
                  회사 {{ report.score.company_score }}점 · 타이밍 {{ report.score.timing_score }}점
                </p>
              </div>

              <!-- Right side: Valuation Summary card -->
              <div class="panel bg-white overflow-hidden">
                <div class="border-b border-slate-100 px-5 py-4">
                  <h4 class="text-sm font-extrabold text-slate-800">밸류에이션 요약</h4>
                </div>
                <div class="divide-y divide-slate-100">
                  <div class="flex justify-between p-4 text-sm font-bold">
                    <span class="text-slate-500">현재가</span>
                    <strong class="text-slate-900">{{ latestPrice }}원</strong>
                  </div>
                  <div class="flex justify-between p-4 text-sm font-bold">
                    <span class="text-slate-500">목표가</span>
                    <strong class="text-slate-900">{{ priceText(report.financialMetric.target_price) }}</strong>
                  </div>
                  <div class="flex justify-between p-4 text-sm font-bold">
                    <span class="text-slate-500">목표가 상승여력</span>
                    <strong :class="report.score.target_upside_clipped ? 'text-amber-600' : 'text-slate-900'">{{ targetUpsideText }}</strong>
                  </div>
                  <div class="flex justify-between p-4 text-sm font-bold">
                    <span class="text-slate-500">PER</span>
                    <strong class="text-slate-900">{{ ratioText(report.financialMetric.per, "배") }}</strong>
                  </div>
                  <div class="flex justify-between p-4 text-sm font-bold">
                    <span class="text-slate-500">ROE</span>
                    <strong class="text-slate-900">{{ ratioText(report.financialMetric.roe, "%") }}</strong>
                  </div>
                  <div class="flex justify-between p-4 text-sm font-bold">
                    <span class="text-slate-500">데이터 신뢰도</span>
                    <strong :class="scoreColor(report.score.reliability_score)">{{ formatScore(report.score.reliability_score) }}점</strong>
                  </div>
                </div>
              </div>
            </div>

            <!-- AI 3줄 코멘트 card -->
            <section class="panel overflow-hidden">
              <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
                <div>
                  <h2 class="text-xl font-bold text-[#172033]">AI 3줄 코멘트</h2>
                  <p class="mt-1 text-xs font-bold text-slate-400">기업 점수, 타이밍 점수, 리스크 할인 요인을 바탕으로 긍정 요인, 주의 요인, 종합 의견을 요약합니다.</p>
                </div>
                <button class="btn-primary" type="button" :disabled="aiLoading" @click="loadAiComment">
                  {{ aiLoading ? "분석 중" : aiLoadingLabel }}
                </button>
              </div>

              <div v-if="aiError" class="m-5 rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-bold text-red-700">
                {{ aiError }}
              </div>
              <div v-else-if="aiComment" class="grid gap-3 p-5">
                <div class="rounded-lg bg-mint/5 p-4">
                  <p class="text-xs font-extrabold text-mint">긍정 요인</p>
                  <p class="mt-1.5 text-sm font-bold leading-normal text-slate-800">{{ aiComment.positive }}</p>
                </div>
                <div class="rounded-lg bg-amber-50/50 p-4">
                  <p class="text-xs font-extrabold text-amber-700">주의 요인</p>
                  <p class="mt-1.5 text-sm font-bold leading-normal text-slate-800">{{ aiComment.negative }}</p>
                </div>
                <div class="rounded-lg bg-slate-100/60 p-4">
                  <p class="text-xs font-extrabold text-slate-600">종합 의견</p>
                  <p class="mt-1.5 text-sm font-bold leading-normal text-slate-800">{{ aiComment.conclusion }}</p>
                  <p class="mt-2 text-[10px] font-bold text-slate-400">
                    {{ aiComment.provider }} · {{ aiComment.cached ? "캐시 사용" : "새로 생성" }}
                  </p>
                </div>
              </div>
            </section>

            <!-- 상세 계산 근거 card -->
            <section class="panel overflow-hidden">
              <div class="border-b border-slate-100 px-5 py-4">
                <h2 class="text-xl font-bold text-[#172033]">상세 계산 근거</h2>
                <p class="mt-1 text-xs font-bold text-slate-400">종합 판단에 사용된 원천 신호와 세부 점수입니다.</p>
              </div>
              <div class="grid gap-3 p-5 md:grid-cols-2">
                <div class="rounded-lg bg-slate-50 p-4">
                  <p class="text-xs font-extrabold text-slate-500">Signal</p>
                  <p class="mt-1.5 text-sm font-extrabold text-slate-900">{{ report.score.signal }}</p>
                </div>
                <div class="rounded-lg bg-slate-50 p-4">
                  <p class="text-xs font-extrabold text-slate-500">Consensus / Confidence</p>
                  <p class="mt-1.5 text-sm font-extrabold text-slate-900">{{ report.score.consensus || "-" }} · {{ report.score.confidence || "-" }}</p>
                </div>
                <div class="rounded-lg bg-slate-50 p-4">
                  <p class="text-xs font-extrabold text-slate-500">세부 점수</p>
                  <p class="mt-1.5 text-xs font-bold text-slate-700 leading-normal">
                    {{ areaScoreText }}
                  </p>
                </div>
                <div class="rounded-lg bg-slate-50 p-4">
                  <p class="text-xs font-extrabold text-slate-500">RS / RSI / 거래량</p>
                  <p class="mt-1.5 text-xs font-bold text-slate-700 leading-normal">
                    RS {{ report.score.rs_rank ?? "-" }} · RSI {{ report.score.rsi ?? "-" }} · 거래량 {{ report.score.volume_ratio }}x
                  </p>
                </div>
              </div>
              <div class="space-y-2 px-5 pb-5">
                <p v-for="log in report.score.scoring_log" :key="log" class="rounded-lg border border-slate-100 p-3 text-xs font-bold text-slate-600 leading-relaxed">
                  {{ log }}
                </p>
              </div>
            </section>
          </div>

          <!-- 2. TECHNICAL INDICATORS PANEL -->
          <div v-show="currentTab === 'tech'" class="space-y-6">
            <IndicatorSection title="기술 지표" section="technical" :ticker="report.stock.ticker" :items="report.score.technical_indicators" />
          </div>

          <!-- 3. FINANCIAL INDICATORS PANEL -->
          <div v-show="currentTab === 'fin'" class="space-y-6">
            <IndicatorSection title="재무 지표" section="financial" :ticker="report.stock.ticker" :items="processedFinancialIndicators" />
            <p class="mt-4 rounded-lg bg-slate-100 p-4 text-xs font-bold text-slate-600 leading-relaxed">
              <b>PER · PBR · ROE · 영업이익률 · 목표가</b> — 증권사 컨센서스 데이터가 부족하면 자료 없음으로 표시될 수 있습니다.
            </p>
          </div>

          <!-- 4. NEWS & DISCLOSURES PANEL -->
          <div v-show="currentTab === 'news'" class="space-y-6">
            <div v-if="newsLoading" class="panel p-8 text-center text-sm font-bold text-slate-500">
              뉴스·공시를 불러오고 AI 감성을 분석하는 중입니다...
            </div>
            <div v-else-if="newsError" class="panel p-8 text-center text-sm font-bold text-rose-500">
              {{ newsError }}
            </div>
            <section v-else class="panel overflow-hidden">
              <div class="flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 px-5 py-4">
                <div>
                  <div class="flex items-center gap-3">
                    <h2 class="text-xl font-bold text-[#172033]">뉴스·공시</h2>
                    <button
                      type="button"
                      class="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-2xs font-extrabold text-slate-600 shadow-sm transition hover:border-[#12b8a6] hover:text-[#12b8a6] active:bg-slate-50"
                      @click="loadNewsPayload(true)"
                    >
                      <RefreshCw class="h-3 w-3" :class="newsLoading ? 'animate-spin' : ''" />
                      <span>새로고침</span>
                    </button>
                  </div>
                  <p class="mt-1 text-xs font-bold text-slate-400">감성 점수는 뉴스만 반영하고, 공시는 참고 목록으로 제공합니다.</p>
                </div>
                <div class="rounded-lg px-4 py-3 text-right" :class="sentimentSummary.className">
                  <p class="text-[10px] font-extrabold">뉴스 감성</p>
                  <p class="mt-0.5 text-base font-extrabold">{{ sentimentSummary.label }} 우위</p>
                </div>
              </div>

              <!-- Sentiment Distribution Bar -->
              <div class="px-5 pt-5">
                <div class="flex h-3 overflow-hidden rounded-full bg-slate-100">
                  <div
                    class="h-full bg-mint transition-all duration-300"
                    :style="{ width: `${sentimentShare(sentimentSummary.positive)}%` }"
                    title="긍정"
                  ></div>
                  <div
                    class="h-full bg-slate-300 transition-all duration-300"
                    :style="{ width: `${sentimentShare(sentimentSummary.neutral)}%` }"
                    title="중립"
                  ></div>
                  <div
                    class="h-full bg-rose-500 transition-all duration-300"
                    :style="{ width: `${sentimentShare(sentimentSummary.negative)}%` }"
                    title="부정"
                  ></div>
                </div>
              </div>

              <!-- Grid of Counts -->
              <div class="grid gap-3 p-5 md:grid-cols-3">
                <div class="rounded-lg bg-mint/10 p-4">
                  <p class="text-xs font-extrabold text-mint">긍정</p>
                  <p class="mt-1 text-2xl font-extrabold text-mint">{{ sentimentSummary.positive }}건</p>
                </div>
                <div class="rounded-lg bg-slate-100 p-4">
                  <p class="text-xs font-extrabold text-slate-600">중립</p>
                  <p class="mt-1 text-2xl font-extrabold text-slate-700">{{ sentimentSummary.neutral }}건</p>
                </div>
                <div class="rounded-lg bg-rose-50 p-4">
                  <p class="text-xs font-extrabold text-rose-700">부정</p>
                  <p class="mt-1 text-2xl font-extrabold text-rose-700">{{ sentimentSummary.negative }}건</p>
                </div>
              </div>

              <p class="mx-5 rounded-lg bg-slate-50 p-4 text-xs font-bold leading-relaxed text-slate-600">
                {{ sentimentSummary.reason }}
              </p>

              <div class="space-y-4 p-5">
                <div class="inline-flex rounded-lg border border-slate-200 bg-white p-1">
                  <button
                    v-for="section in newsSections"
                    :key="section.type"
                    type="button"
                    class="rounded-md px-4 py-2 text-sm font-extrabold transition"
                    :class="activeNewsTab === section.type ? 'bg-[#12b8a6] text-white shadow-sm' : 'text-slate-500 hover:bg-slate-50'"
                    @click="activeNewsTab = section.type"
                  >
                    {{ section.title }} {{ section.items.length }}
                  </button>
                </div>

                <div class="space-y-3">
                  <div class="flex items-center justify-between gap-3">
                    <h3 class="text-base font-extrabold text-slate-900">{{ currentNewsSection.title }}</h3>
                    <span class="rounded-full bg-slate-100 px-3 py-1 text-xs font-extrabold text-slate-500">{{ currentNewsSection.items.length }}건</span>
                  </div>
                  <article
                    v-for="item in currentNewsSection.items"
                    :key="`${item.type}-${item.title}`"
                    class="rounded-lg border border-slate-100 bg-white p-4"
                  >
                    <div class="flex items-start justify-between gap-3">
                      <div class="flex-1 min-w-0">
                        <div class="flex flex-wrap items-center gap-2">
                          <span v-if="item.type === '공시' || item.source" class="rounded bg-slate-100 px-2 py-0.5 text-2xs font-extrabold text-slate-600">{{ item.type === "공시" ? item.eventType || "공시" : item.source }}</span>
                          <span
                            v-if="item.type !== '공시'"
                            class="rounded px-2 py-0.5 text-2xs font-extrabold"
                            :class="item.scope === 'market' ? 'bg-amber-50 text-amber-700' : 'bg-blue-50 text-blue-700'"
                          >
                            {{ item.scope === "market" ? "시장 영향" : "기업 이슈" }}
                          </span>
                          <span class="text-2xs font-bold text-slate-400">{{ item.date }}</span>
                        </div>
                        <p class="mt-2 font-extrabold leading-relaxed text-slate-900">{{ item.title }}</p>
                        <p class="mt-1 text-xs font-bold leading-relaxed text-slate-500">{{ item.reason }}</p>
                        <a
                          v-if="item.url"
                          :href="item.url"
                          target="_blank"
                          rel="noreferrer"
                          class="mt-2 inline-flex text-xs font-extrabold text-mint"
                        >
                          원문 보기 ↗
                        </a>
                      </div>
                      <span v-if="item.sentiment" class="shrink-0 rounded-full px-3 py-1 text-xs font-extrabold" :class="sentimentBadgeClass(item.sentiment)">
                        {{ sentimentLabel(item.sentiment) }}
                      </span>
                    </div>
                  </article>
                  <div v-if="!currentNewsSection.items.length" class="rounded-lg border border-dashed border-slate-200 bg-white p-4 text-xs font-bold text-slate-400">
                    {{ currentNewsSection.empty }}
                  </div>
                </div>
              </div>
            </section>
          </div>
        </main>

        <p class="mt-6 rounded-lg bg-slate-100 p-4 text-xs font-bold text-slate-500 leading-relaxed">{{ report.investmentNotice }}</p>
      </template>
    </div>
  </section>
</template>

<script setup>
import { computed, defineComponent, h, onMounted, reactive, ref, watch } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { Heart, MessageCircle, RefreshCw } from "@lucide/vue";

import { api, unwrapList } from "../api/client";
import StockChart from "../components/StockChart.vue";
import { useAuthStore } from "../stores/auth";

const props = defineProps({
  ticker: {
    type: String,
    required: true,
  },
});

const report = ref(null);
const loading = ref(true);
const error = ref("");
const auth = useAuthStore();
const router = useRouter();
const watchlistSaved = ref(false);
const watchlistLoading = ref(false);
const aiComment = ref(null);
const aiLoading = ref(false);
const aiError = ref("");
const newsPayload = ref(null);
const newsLoading = ref(false);
const newsError = ref("");
const componentThreshold = 70;

const currentTab = ref("overview");
const activeNewsTab = ref("disclosure");
const tabOptions = [
  { value: "overview", label: "종합 진단" },
  { value: "tech", label: "기술 지표" },
  { value: "fin", label: "재무 지표" },
  { value: "news", label: "뉴스 · 공시" }
];

const openLayers = reactive({
  valueQuality: false,
  leadershipMomentum: true,
  riskControl: false,
  newsSentiment: false
});

const countNewsSentiment = (news, type) => {
  if (!news || !Array.isArray(news)) return 0;
  return news.filter(item => item.sentiment === type).length;
};

const aiLoadingLabel = computed(() => (aiComment.value ? "다시 보기" : "AI 분석 보기"));

const stockThemes = computed(() => {
  const themes = report.value?.stock?.themes || [];
  return themes.length ? themes : [report.value?.stock?.primary_theme].filter(Boolean);
});

const reportTitle = computed(() => `${report.value?.stock?.name || "종목"} 종합 리포트`);

const reportSubtitle = computed(() => {
  const score = formatScore(report.value?.score?.total_score);
  const reason = report.value?.score?.key_reason || "";
  return `${report.value?.stock?.market || "시장"} 1년 가격 데이터 기준 · 종합 ${score}점${reason ? ` · ${reason}` : ""}`;
});

const summaryMetricText = computed(() => {
  const metrics = report.value?.score?.summary_metrics || [];
  return metrics.map(summaryMetricTextFor).filter(Boolean).join(" · ");
});

const areaScoreText = computed(() => {
  const areaScores = report.value?.score?.area_scores || {};
  const labels = {
    valueQuality: "가치/퀄리티",
    annualRoeProxy: "연간 ROE 대용",
    epsAcceleration: "EPS 가속도",
    leadershipMomentum: "주도주 모멘텀",
    pivotBreakout: "신고가/피벗",
    smartMoney: "수급/거래량",
    marketDirection: "시장 방향",
    meanReversion: "과열 방지",
    drawdownControl: "낙폭 방어",
    momentum: "모멘텀",
    value: "밸류",
    quality: "퀄리티",
  };
  const rows = Object.entries(areaScores)
    .filter(([, value]) => value !== null && value !== undefined)
    .map(([key, value]) => `${labels[key] || key}: ${formatScore(value)}점`);
  return rows.length ? rows.join(" · ") : "세부 점수 데이터 없음";
});

const decisionHighlights = computed(() => {
  const score = report.value?.score || {};
  const rows = [
    score.key_reason,
    movingAverageSummary.value.label && `가격 흐름은 ${movingAverageSummary.value.label}으로 분류됩니다.`,
    volumeSummary.value.label && `거래량은 ${volumeSummary.value.label} 상태입니다.`,
    score.rs_rank ? `RS ${score.rs_rank}로 상대 강도가 확인됩니다.` : "",
  ].filter(Boolean);
  return uniqueRows(rows).slice(0, 3);
});

const riskHighlights = computed(() => {
  const score = report.value?.score || {};
  const weakCards = (score.score_cards || [])
    .filter((card) => Number(card.score) < 50)
    .map((card) => `${card.title} 점수가 ${formatScore(card.score)}점으로 낮습니다.`);
  const rows = [
    score.warning,
    bollingerSummary.value.label.includes("과열") ? "볼린저밴드 기준 단기 과열 가능성이 있습니다." : "",
    score.fail_safe_flag ? "Fail-safe 조건이 감지되어 보수적 확인이 필요합니다." : "",
    ...weakCards,
  ].filter(Boolean);
  const unique = uniqueRows(rows);
  return (unique.length ? unique : ["추가 위험 신호는 상세 지표에서 확인하세요."]).slice(0, 2);
});

const verdictBadgeClass = computed(() => {
  const score = Number(report.value?.score?.total_score || 0);
  if (score >= 70) return "bg-mint/10 text-mint";
  if (score >= 50) return "bg-amber-100 text-amber-700";
  return "bg-rose-100 text-rose-700";
});

const latestPrice = computed(() => {
  const price = report.value?.priceSeries?.at(-1)?.close_price;
  return formatNumber(price || report.value?.financialMetric?.current_price || 0);
});

const latestChartPoint = computed(() => report.value?.priceSeries?.at(-1) || {});
const firstChartPoint = computed(() => report.value?.priceSeries?.[0] || {});
const previousChartPoint = computed(() => {
  const prices = report.value?.priceSeries || [];
  return prices.length > 1 ? prices.at(-2) : {};
});

const chartReturn = computed(() => {
  const first = Number(firstChartPoint.value.close_price || 0);
  const latest = Number(latestChartPoint.value.close_price || 0);
  if (!first || !latest) return null;
  return ((latest - first) / first) * 100;
});

const dayChange = computed(() => {
  const previous = Number(previousChartPoint.value.close_price || 0);
  const latest = Number(latestChartPoint.value.close_price || 0);
  if (!previous || !latest) return null;
  return ((latest - previous) / previous) * 100;
});

const dailyChangeAmount = computed(() => {
  const previous = Number(previousChartPoint.value.close_price || 0);
  const latest = Number(latestChartPoint.value.close_price || 0);
  if (!previous || !latest) return null;
  return latest - previous;
});

const latestTradeDateText = computed(() => {
  const value = latestChartPoint.value.date || latestChartPoint.value.trade_date || latestChartPoint.value.base_date;
  const label = formatKoreanChartDateTime(value, report.value?.refreshedAt);
  return label === "-" ? "최신 일봉 기준" : `${label} 기준`;
});

const dailyChangeSummaryText = computed(() => {
  if (dayChange.value === null || dailyChangeAmount.value === null) return "전일대비 데이터 부족";
  return `전일대비 ${signedPriceText(dailyChangeAmount.value)}원 (${signedPercentText(dayChange.value)})`;
});

const dailyChangeClass = computed(() => {
  const value = dayChange.value || 0;
  if (value > 0) return "text-red-600";
  if (value < 0) return "text-blue-600";
  return "text-slate-500";
});

const isLeader = computed(() => {
  const signal = report.value?.score?.signal || "";
  const reason = report.value?.score?.key_reason || report.value?.score?.reason || "";
  return /주도주/.test(signal) || /주도주/.test(reason);
});

// key_reason 텍스트 파싱 + volume_surge_flag fallback + 가격 시리즈 52주 신고가 근접 fallback
const keyReasonBadges = computed(() => {
  const score = report.value?.score || {};
  const reasonText = score.key_reason || score.reason || "";

  // key_reason 분리 파싱
  const rawTags = reasonText
    ? reasonText.split("·").map((s) => {
        const t = s.trim();
        if (!t) return null;
        if (/^RS\s*\d+/i.test(t)) return { label: t, type: "rs" };
        if (/52주|\uc2e0고가|신저가|돌파|급등|급락|급증|이탈/.test(t)) return { label: t, type: "signal" };
        return { label: t, type: "default" };
      }).filter(Boolean)
    : [];

  // volume_surge_flag 이 true인데 텍스트에 거래량 태그가 없으면 추가
  const hasVolumeTag = rawTags.some((t) => /거래량/.test(t.label));
  if (score.volume_surge_flag && !hasVolumeTag) {
    rawTags.push({ label: "거래량 급증", type: "signal" });
  }

  // 가격 시리즈에서 52주 신고가 근접 직접 계산 (key_reason에 없을 때 fallback)
  const has52wTag = rawTags.some((t) => /52주/.test(t.label));
  if (!has52wTag) {
    const prices = report.value?.priceSeries || [];
    const closes = prices.map((p) => Number(p.close_price || 0)).filter(Boolean);
    if (closes.length >= 20) {
      const max52w = Math.max(...closes);
      const latest = closes.at(-1);
      if (latest && max52w && latest >= max52w * 0.97) {
        const badge = { label: latest >= max52w * 0.999 ? "52주 신고가" : "52주 신고가 근접", type: "signal" };
        rawTags.push(badge);
      }
    }
  }

  // 고정 순서: RS → 52주 → 거래량 → 나머지
  function tagOrder(tag) {
    if (tag.type === "rs") return 0;
    if (/52주/.test(tag.label)) return 1;
    if (/거래량/.test(tag.label)) return 2;
    return 3;
  }
  return [...rawTags].sort((a, b) => tagOrder(a) - tagOrder(b));
});

const is52wHigh = computed(() => keyReasonBadges.value.some((t) => /52주/.test(t.label)));

const chartReturnText = computed(() => {
  const periodReturn = chartReturn.value;
  const dailyReturn = dayChange.value;
  if (periodReturn === null) return "수익률 데이터 부족";
  const dailyText = dailyReturn === null ? "" : ` · 전일 ${signedPercentText(dailyReturn)}`;
  return `차트 구간 ${signedPercentText(periodReturn)}${dailyText}`;
});

const chartReturnClass = computed(() => {
  const value = chartReturn.value || 0;
  if (value > 0) return "text-red-600";
  if (value < 0) return "text-blue-600";
  return "text-slate-500";
});

const movingAverageSummary = computed(() => {
  const latest = latestChartPoint.value;
  const close = Number(latest.close_price || 0);
  const ema20 = Number(latest.ema20 || 0);
  const ema50 = Number(latest.ema50 || 0);
  const ema200 = Number(latest.ema200 || 0);
  if (!close || !ema20 || !ema50 || !ema200) {
    return { label: "이동평균 데이터 부족", detail: "EMA20·50·200 중 일부 값이 없습니다." };
  }
  const bullish = close >= ema20 && ema20 >= ema50 && ema50 >= ema200;
  const pullback = close >= ema50 && close < ema20;
  const bearish = close < ema50;
  const label = bullish ? "정배열 추세" : pullback ? "단기 눌림 구간" : bearish ? "중기선 하회" : "혼조 배열";
  return {
    label,
    detail: `종가 ${formatNumber(close)} · EMA20 ${formatNumber(ema20)} · EMA50 ${formatNumber(ema50)} · EMA200 ${formatNumber(ema200)}`,
  };
});

const volumeSummary = computed(() => {
  const prices = report.value?.priceSeries || [];
  const latestVolume = Number(latestChartPoint.value.volume || 0);
  const recent = prices.slice(-21, -1).map((point) => Number(point.volume || 0)).filter(Boolean);
  if (!latestVolume || !recent.length) {
    return { label: "거래량 데이터 부족", detail: "최근 거래량 비교가 어렵습니다." };
  }
  const average = recent.reduce((sum, value) => sum + value, 0) / recent.length;
  const rawRatio = average ? latestVolume / average : 0;
  const ratio = Number(report.value?.score?.volume_ratio || rawRatio || 0);
  const label = ratio >= 2 ? "거래량 급증" : ratio >= 1.2 ? "평균 대비 증가" : ratio <= 0.7 ? "거래량 둔화" : "평균권 거래량";
  const basis = isLatestTradeDateToday() ? "장중 보정 기준" : "최근 일봉 기준";
  return {
    label,
    detail: `${basis} ${ratio.toFixed(1)}배 · 실제 누적 거래량 ${formatCompactNumber(latestVolume)}`,
  };
});

const bollingerSummary = computed(() => {
  const latest = latestChartPoint.value;
  const close = Number(latest.close_price || 0);
  const upper = Number(latest.bb_upper || 0);
  const lower = Number(latest.bb_lower || 0);
  if (!close || !upper || !lower || upper === lower) {
    return { label: "밴드 데이터 부족", detail: "볼린저 상·하단 계산값이 없습니다." };
  }
  const position = ((close - lower) / (upper - lower)) * 100;
  const label = position >= 90 ? "상단 과열권" : position >= 70 ? "상단 접근" : position <= 10 ? "하단 이탈권" : position <= 30 ? "하단 접근" : "중립권";
  return {
    label,
    detail: `밴드 내 위치 ${position.toFixed(0)}% · 상단 ${formatNumber(upper)} · 하단 ${formatNumber(lower)}`,
  };
});

const chartObservation = computed(() => {
  const trend = movingAverageSummary.value.label;
  const volume = volumeSummary.value.label;
  const bollinger = bollingerSummary.value.label;
  return `최신 일봉가는 ${latestPrice.value}원이며, ${trend}, ${volume}, ${bollinger}으로 해석됩니다.`;
});

const rawCurrentPrice = computed(() => {
  return report.value?.priceSeries?.at(-1)?.close_price || report.value?.financialMetric?.current_price || 0;
});

const computedTargetUpside = computed(() => {
  const current = rawCurrentPrice.value;
  const target = report.value?.financialMetric?.target_price;
  if (!current || !target) return null;
  return ((target - current) / current) * 100;
});

const targetUpsideText = computed(() => {
  const upside = computedTargetUpside.value;
  if (upside === null) return "목표가 미산정";
  const formatted = upside.toFixed(1);
  const sign = upside > 0 ? "+" : "";
  return report.value?.score?.target_upside_clipped ? `${sign}${formatted}%+` : `${sign}${formatted}%`;
});

const processedFinancialIndicators = computed(() => {
  const indicators = report.value?.score?.financial_indicators || [];
  const current = rawCurrentPrice.value;
  const target = report.value?.financialMetric?.target_price;
  return indicators.map((item) => {
    if (item.label === "목표가 상승여력" && current && target) {
      const upside = ((target - current) / current) * 100;
      const formatted = `${upside > 0 ? "+" : ""}${upside.toFixed(1)}%`;
      return {
        ...item,
        value: formatted,
        status: upside > 0 ? "상승여력" : "주의"
      };
    }
    return item;
  });
});

const quadrantPointStyle = computed(() => {
  const company = clampPercent(report.value?.score?.company_score);
  const timing = clampPercent(report.value?.score?.timing_score);
  return {
    left: `${company}%`,
    bottom: `${timing}%`,
    transform: "translate(-50%, 50%)",
  };
});

const quadrantLabel = computed(() => {
  const company = Number(report.value?.score?.company_score || 0);
  const timing = Number(report.value?.score?.timing_score || 0);
  if (company >= componentThreshold && timing >= componentThreshold) return "포트폴리오 후보";
  if (company >= componentThreshold && timing < componentThreshold) return "좋은 회사·타이밍 대기";
  if (company < componentThreshold && timing >= componentThreshold) return "타이밍은 좋지만 회사 가치 확인";
  return "회사 가치와 타이밍 모두 70점 미만";
});

const gaugeDashArray = computed(() => {
  const score = report.value?.score?.total_score || 0;
  const stroke = Math.round((score / 100) * 377);
  return `${stroke} 377`;
});

const newsItems = computed(() => {
  const score = newsPayload.value || report.value?.score || {};
  const news = (score.news || []).map((item) => normalizeNewsItem(item, "뉴스"));
  const disclosures = (score.disclosures || []).map((item) => normalizeNewsItem(item, "공시"));
  const rows = [...news, ...disclosures].filter((item) => item.title);
  if (rows.length) return rows;
  return [
    {
      type: "뉴스",
      title: "최근 수집된 종목 관련 뉴스가 없습니다.",
      date: score.base_date || "-",
      sentiment: "neutral",
      reason: "뉴스 API 키가 없거나 수집 조건에 맞는 최근 기사가 없어 감성 판단을 보류합니다.",
      isEmpty: true,
    },
  ];
});

const newsSections = computed(() => {
  const realItems = newsItems.value.filter((item) => !item.isEmpty);
  return [
    {
      type: "disclosure",
      title: "공시",
      items: realItems.filter((item) => item.type === "공시"),
      empty: "최근 수집된 공시가 없습니다.",
    },
    {
      type: "news",
      title: "뉴스",
      items: realItems.filter((item) => item.type !== "공시"),
      empty: "최근 수집된 종목 관련 뉴스가 없습니다.",
    },
  ];
});

const currentNewsSection = computed(() => {
  return newsSections.value.find((section) => section.type === activeNewsTab.value) || newsSections.value[0];
});

const sentimentSummary = computed(() => {
  const realItems = newsItems.value.filter((item) => !item.isEmpty && item.type !== "공시");
  const counts = realItems.reduce(
    (acc, item) => {
      acc[item.sentiment] += 1;
      return acc;
    },
    { positive: 0, neutral: 0, negative: 0 },
  );
  if (!realItems.length) {
    return {
      ...counts,
      winner: "neutral",
      label: "중립",
      className: "bg-slate-100 text-slate-700",
      reason: "최근 수집된 종목 관련 뉴스가 없어 뉴스 감성 점수를 중립으로 표시합니다.",
      total: 0,
    };
  }
  const maxCount = Math.max(counts.positive, counts.neutral, counts.negative);
  const winners = Object.entries(counts).filter(([, count]) => count === maxCount).map(([key]) => key);
  const winner = winners.length === 1 ? winners[0] : "neutral";
  const label = sentimentLabel(winner);
  const className = {
    positive: "bg-mint/10 text-mint",
    neutral: "bg-slate-100 text-slate-700",
    negative: "bg-rose-50 text-rose-700",
  }[winner];
  return {
    ...counts,
    winner,
    label,
    className,
    reason: `뉴스 ${realItems.length}건 중 긍정 ${counts.positive}건, 중립 ${counts.neutral}건, 부정 ${counts.negative}건으로 분류되어 ${label} 우위로 판단했습니다.`,
    total: realItems.length,
  };
});

function formatNumber(value) {
  return Number(value || 0).toLocaleString("ko-KR");
}

function formatCompactNumber(value) {
  const number = Number(value || 0);
  if (number >= 100000000) return `${(number / 100000000).toFixed(1).replace(".0", "")}억`;
  if (number >= 10000) return `${(number / 10000).toFixed(1).replace(".0", "")}만`;
  return formatNumber(number);
}

function formatKoreanChartDate(value) {
  if (!value) return "-";
  const text = String(value);
  if (/^\d{4}-\d{2}-\d{2}/.test(text)) {
    return `${Number(text.slice(5, 7))}월 ${Number(text.slice(8, 10))}일`;
  }
  if (/^\d{8}$/.test(text)) {
    return `${Number(text.slice(4, 6))}월 ${Number(text.slice(6, 8))}일`;
  }
  return text;
}

function formatKoreanChartDateTime(value, timestamp) {
  const dateText = formatKoreanChartDate(value);
  if (!timestamp) return dateText;
  const parsed = new Date(timestamp);
  if (Number.isNaN(parsed.getTime())) return dateText;
  const hours = String(parsed.getHours()).padStart(2, "0");
  const minutes = String(parsed.getMinutes()).padStart(2, "0");
  return `${dateText} ${hours}:${minutes}`;
}

function formatNewsDate(value) {
  if (!value) return "-";
  const parsed = new Date(value);
  if (!Number.isNaN(parsed.getTime())) {
    const year = parsed.getFullYear();
    const month = String(parsed.getMonth() + 1).padStart(2, "0");
    const day = String(parsed.getDate()).padStart(2, "0");
    const hours = String(parsed.getHours()).padStart(2, "0");
    const minutes = String(parsed.getMinutes()).padStart(2, "0");
    return `${year}.${month}.${day} ${hours}:${minutes}`;
  }
  const text = String(value);
  if (/^\d{4}-\d{2}-\d{2}/.test(text)) return text.slice(0, 10).replaceAll("-", ".");
  return text;
}

function isLatestTradeDateToday() {
  const value = latestChartPoint.value.date || latestChartPoint.value.trade_date || latestChartPoint.value.base_date;
  if (!value) return false;
  const text = String(value);
  const today = new Date();
  const todayText = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
  if (/^\d{4}-\d{2}-\d{2}/.test(text)) return text.slice(0, 10) === todayText;
  if (/^\d{8}$/.test(text)) return text === todayText.replaceAll("-", "");
  return false;
}

function signedPriceText(value) {
  const number = Number(value || 0);
  const sign = number > 0 ? "+" : "";
  return `${sign}${formatNumber(number)}`;
}

function signedPercentText(value) {
  const number = Number(value || 0);
  const sign = number > 0 ? "+" : "";
  return `${sign}${number.toFixed(1)}%`;
}

function clampPercent(value) {
  const number = Number(value || 0);
  if (Number.isNaN(number)) return 0;
  return Math.max(2, Math.min(98, number));
}

function quadrantStyle(type) {
  const leftWidth = componentThreshold;
  const rightWidth = 100 - componentThreshold;
  const topHeight = 100 - componentThreshold;
  const bottomHeight = componentThreshold;
  const styles = {
    timingOnly: {
      left: "0%",
      top: "0%",
      width: `${leftWidth}%`,
      height: `${topHeight}%`,
    },
    pass: {
      left: `${componentThreshold}%`,
      top: "0%",
      width: `${rightWidth}%`,
      height: `${topHeight}%`,
    },
    watch: {
      left: "0%",
      top: `${topHeight}%`,
      width: `${leftWidth}%`,
      height: `${bottomHeight}%`,
    },
    companyOnly: {
      left: `${componentThreshold}%`,
      top: `${topHeight}%`,
      width: `${rightWidth}%`,
      height: `${bottomHeight}%`,
    },
  };
  return styles[type] || {};
}

function normalizeNewsItem(item, type) {
  const title = item.title || item.headline || "";
  const isDisclosure = (item.type || type) === "공시";
  const sentiment = isDisclosure ? null : normalizeSentiment(item.sentiment || item.tone, title);
  return {
    type: item.type || type,
    title,
    sentiment,
    date: formatNewsDate(item.publishedAt || item.date || report.value?.score?.base_date),
    reason: isDisclosure
      ? item.summary || item.reason || ""
      : type === "뉴스" ? item.summary || item.reason || sentimentReason(sentiment, title) : item.reason || item.summary || sentimentReason(sentiment, title),
    url: item.url || "",
    source: item.source || "",
    eventType: item.eventType || "",
    scope: item.scope || "",
    isEmpty: Boolean(item.isEmpty),
  };
}

function normalizeSentiment(value, title = "") {
  const raw = String(value || "").toLowerCase();
  if (["positive", "good", "긍정"].some((keyword) => raw.includes(keyword))) return "positive";
  if (["negative", "bad", "부정"].some((keyword) => raw.includes(keyword))) return "negative";
  const text = String(title);
  const positiveKeywords = ["호재", "상승", "수주", "실적", "개선", "증가", "흑자", "성장", "매수", "신고가", "돌파"];
  const negativeKeywords = ["악재", "하락", "감소", "적자", "손실", "리스크", "매도", "과열", "낙폭", "경고", "주의"];
  if (positiveKeywords.some((keyword) => text.includes(keyword))) return "positive";
  if (negativeKeywords.some((keyword) => text.includes(keyword))) return "negative";
  return "neutral";
}

function sentimentLabel(sentiment) {
  return {
    positive: "긍정",
    neutral: "중립",
    negative: "부정",
  }[sentiment] || "중립";
}

function sentimentReason(sentiment, title) {
  if (sentiment === "positive") return "상승, 실적, 수주, 개선 등 긍정 키워드가 포함되어 있습니다.";
  if (sentiment === "negative") return "하락, 리스크, 과열, 주의 등 부정 키워드가 포함되어 있습니다.";
  if (title.includes("수집하지 않습니다") || title.includes("기준 산출")) return "데이터 출처나 산출 기준을 설명하는 항목이라 중립으로 분류했습니다.";
  return "명확한 호재·악재 키워드가 없어 중립으로 분류했습니다.";
}

function sentimentShare(count) {
  const total = sentimentSummary.value.total || 0;
  if (!total) return 0;
  return (count / total) * 100;
}

function sentimentBadgeClass(sentiment) {
  return {
    positive: "bg-mint/10 text-mint",
    neutral: "bg-slate-100 text-slate-700",
    negative: "bg-rose-100 text-rose-700",
  }[sentiment] || "bg-slate-100 text-slate-700";
}

function priceText(value) {
  if (value === null || value === undefined || value === 0) return "목표가 미산정";
  return `${formatNumber(value)}원`;
}

function ratioText(value, suffix) {
  if (value === null || value === undefined || value === "") return "자료 없음";
  const number = Number(value);
  if (Number.isNaN(number)) return "자료 없음";
  return `${number.toFixed(2).replace(".00", "")}${suffix}`;
}

function formatScore(value) {
  if (value === null || value === undefined || value === "") return "-";
  const number = Number(value);
  if (Number.isNaN(number)) return value;
  return number.toFixed(1).replace(".0", "");
}

function scorePercent(value) {
  const score = Number(value || 0);
  if (Number.isNaN(score)) return 0;
  return Math.min(100, Math.max(0, score));
}

function scoreColor(score) {
  if (score >= 70) return "text-mint";
  if (score >= 50) return "text-amber-600";
  return "text-rose-500";
}

function fmtTradeValue(rawValue) {
  // 이미 "16860억" 형태로 오는 경우 숫자 + 단위로 파싱 후 재포맷
  const str = String(rawValue || "");
  const eokMatch = str.match(/^([\d,]+)억$/);
  if (eokMatch) {
    const eok = Number(eokMatch[1].replace(/,/g, ""));
    if (eok >= 10000) return `${(eok / 10000).toFixed(1)}조`;
    if (eok >= 1000) return `${eok.toLocaleString("ko-KR")}억`;
    return `${eok}억`;
  }
  // 이미 조/만 단위면 그대로
  return str;
}

function summaryMetricTextFor(metric) {
  if (!metric) return "";
  if (typeof metric === "string") return metric;
  const label = metric.label || metric.name || "";
  let value = metric.value ?? metric.score ?? "";
  if (!label && !value) return "";
  if (label === "평균 거래대금") value = fmtTradeValue(value);
  return label ? `${label}: ${value}` : `${value}`;
}

function uniqueRows(rows) {
  return Array.from(new Set(rows.map((row) => String(row).trim()).filter(Boolean)));
}

async function loadAiComment() {
  aiLoading.value = true;
  aiError.value = "";
  try {
    const response = await api.post(`/stocks/${props.ticker}/ai-comment/`, { risk_type: "neutral" });
    aiComment.value = response.data;
  } catch (err) {
    aiError.value = "AI 코멘트를 생성하지 못했습니다. 잠시 후 다시 시도하세요.";
  } finally {
    aiLoading.value = false;
  }
}

async function loadNewsPayload(force = false) {
  if (!force && (newsPayload.value || newsLoading.value)) return;
  newsLoading.value = true;
  newsError.value = "";
  try {
    const url = `/stocks/${props.ticker}/news/` + (force ? "?refresh=true" : "");
    const response = await api.get(url);
    newsPayload.value = response.data;
    if (report.value?.score) {
      report.value.score.news = response.data.news || [];
      report.value.score.disclosures = response.data.disclosures || [];
      if (report.value.score.area_scores) {
        report.value.score.area_scores.newsSentiment = response.data.newsSentiment;
      }
    }
  } catch (err) {
    newsError.value = "뉴스·공시 데이터를 불러오지 못했습니다.";
  } finally {
    newsLoading.value = false;
  }
}

watch(currentTab, (tab) => {
  if (tab === "news") loadNewsPayload();
});

async function loadWatchlistStatus() {
  if (!auth.isAuthenticated) return;
  const { data } = await api.get("/watchlist/");
  watchlistSaved.value = unwrapList(data).some((entry) => entry.stock?.ticker === props.ticker);
}

async function toggleWatchlist() {
  if (!auth.isAuthenticated) {
    router.push({ path: "/login", query: { next: `/stocks/${props.ticker}` } });
    return;
  }
  watchlistLoading.value = true;
  try {
    if (watchlistSaved.value) {
      await api.delete(`/watchlist/${props.ticker}/`);
      watchlistSaved.value = false;
    } else {
      await api.post(`/watchlist/${props.ticker}/`);
      watchlistSaved.value = true;
    }
  } catch {
    error.value = "관심 종목 상태를 변경하지 못했습니다.";
  } finally {
    watchlistLoading.value = false;
  }
}

const IndicatorSection = defineComponent({
  props: {
    title: { type: String, required: true },
    section: { type: String, required: true },
    ticker: { type: String, required: true },
    items: { type: Array, default: () => [] },
  },
  setup(sectionProps) {
    return () =>
      h("section", { class: "panel overflow-hidden" }, [
        h("div", { class: "border-b border-slate-100 px-5 py-4" }, [
          h("h2", { class: "text-xl font-bold text-[#172033]" }, sectionProps.title),
        ]),
        h(
          "div",
          { class: "space-y-3 p-5" },
          sectionProps.items.map((item, index) =>
            h(RouterLink, {
              to: {
                name: "metric-detail",
                params: {
                  ticker: sectionProps.ticker,
                  section: sectionProps.section,
                  index,
                },
              },
              class: "flex items-center justify-between gap-4 rounded-lg border border-slate-100 bg-white p-4 transition hover:-translate-y-0.5 hover:border-mint/30 hover:bg-mint/5",
            }, () => [
              h("div", { class: "min-w-0" }, [
                h("p", { class: "font-extrabold text-slate-800" }, item.name || item.label || item.title || "지표"),
                h("p", { class: "mt-1 text-sm font-bold leading-6 text-slate-500" }, item.description || item.reason || ""),
                h("p", { class: "mt-1 text-xs font-extrabold text-mint" }, "계산 상세 보기 →"),
              ]),
              h("div", { class: "shrink-0 text-right" }, [
                h("p", { class: "text-lg font-extrabold text-slate-950" }, item.value),
                h("p", { class: "text-sm font-bold text-mint" }, item.status),
              ]),
            ]),
          ),
        ),
      ]);
  },
});

onMounted(async () => {
  try {
    const response = await api.get(`/stocks/${props.ticker}/report/`);
    report.value = response.data;
    await loadWatchlistStatus();
  } catch (err) {
    error.value = "종목 리포트를 불러오지 못했습니다.";
  } finally {
    loading.value = false;
  }
});
</script>
