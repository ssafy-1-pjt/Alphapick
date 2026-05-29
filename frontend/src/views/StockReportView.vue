<template>
  <section class="page-shell py-8">
    <div v-if="loading" class="panel p-8 text-center font-bold text-slate-500">스코어 리포트를 불러오는 중입니다.</div>
    <div v-else-if="error" class="panel border-red-200 bg-red-50 p-8 text-red-700">{{ error }}</div>

    <template v-else>
      <div class="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div class="flex flex-wrap items-center gap-2">
            <h1 class="text-3xl font-black text-slate-950">{{ report.stock.name }}</h1>
            <span class="badge bg-slate-100 text-slate-600">{{ report.stock.ticker }}</span>
            <span class="badge bg-blue-50 text-blue-700">{{ report.stock.sector }}</span>
            <span class="badge bg-emerald-50 text-emerald-700">{{ report.stock.primary_theme }}</span>

            <!-- 관심종목 토글 별표 버튼 -->
            <button
              v-if="authStore.isAuthenticated"
              type="button"
              class="ml-2 flex items-center justify-center p-1.5 transition text-slate-400 hover:text-amber-500"
              :class="{ 'text-amber-500': isWatchlisted }"
              @click="toggleWatchlist"
              aria-label="관심종목 토글"
            >
              <Star :size="24" :fill="isWatchlisted ? '#f59e0b' : 'none'" />
            </button>
          </div>
          <div class="mt-2 flex flex-wrap gap-2">
            <span class="badge bg-slate-950 text-white">{{ report.score.signal }}</span>
            <span v-if="report.stock.low_liquidity_flag" class="badge bg-amber-100 text-amber-700">유동성 주의</span>
            <span v-if="report.score.fail_safe_flag" class="badge bg-red-100 text-red-700">Fail-safe</span>
            <span v-if="report.score.volume_surge_flag" class="badge bg-blue-100 text-blue-700">거래량 급증</span>
            <span v-if="report.score.target_upside_clipped" class="badge bg-amber-100 text-amber-700">목표가 200%+ 클리핑</span>
          </div>
          <p class="mt-2 text-sm font-bold text-slate-500">데이터 기준일 {{ report.score.base_date }}</p>
        </div>
      </div>

      <section class="rounded-lg border border-slate-800 bg-slate-300 p-7 text-center text-slate-950">
        <h2 class="text-4xl font-black leading-tight md:text-5xl">{{ report.score.headline }}</h2>
        <p class="mt-4 text-xl font-black text-slate-900">{{ report.score.key_reason }}</p>
        <p v-if="summaryMetricText" class="mt-4 text-lg font-black text-slate-700">{{ summaryMetricText }}</p>
      </section>

      <div class="mt-6 grid gap-4 md:grid-cols-4">
        <div v-for="card in report.score.timing_cards" :key="cardTitle(card)" class="panel p-4">
          <p class="text-sm font-black text-slate-500">{{ cardTitle(card) }}</p>
          <p class="mt-2 text-3xl font-black text-slate-950">{{ scoreText(card) }}</p>
          <p v-if="cardDescription(card)" class="mt-2 text-sm leading-6 text-slate-500">{{ cardDescription(card) }}</p>
        </div>
      </div>

      <div class="mt-6 panel p-5">
        <div class="mb-4 flex flex-wrap items-center justify-between gap-2">
          <h2 class="text-2xl font-black text-slate-950">{{ report.stock.name }} 가격 차트</h2>
          <div class="flex flex-wrap gap-3 text-sm font-bold text-slate-500">
            <span>Close</span>
            <span class="text-blue-500">EMA20</span>
            <span class="text-orange-500">EMA50</span>
            <span class="text-violet-500">EMA200</span>
          </div>
        </div>
        <svg class="h-[320px] w-full overflow-visible" viewBox="0 0 900 320" role="img" aria-label="stock price chart">
          <line x1="40" y1="270" x2="880" y2="270" stroke="#e2e8f0" />
          <line x1="40" y1="35" x2="40" y2="270" stroke="#e2e8f0" />
          <polyline :points="linePoints('bb_upper')" fill="none" stroke="#cbd5e1" stroke-dasharray="5 5" stroke-width="2" />
          <polyline :points="linePoints('bb_lower')" fill="none" stroke="#cbd5e1" stroke-dasharray="5 5" stroke-width="2" />
          <polyline :points="linePoints('ema200')" fill="none" stroke="#8b5cf6" stroke-dasharray="8 6" stroke-width="3" />
          <polyline :points="linePoints('ema50')" fill="none" stroke="#f97316" stroke-width="3" />
          <polyline :points="linePoints('ema20')" fill="none" stroke="#3b82f6" stroke-width="3" />
          <polyline :points="linePoints('close_price')" fill="none" stroke="#0f172a" stroke-width="4" />
          <g v-for="(bar, index) in volumeBars" :key="index">
            <rect :x="bar.x" :y="bar.y" :width="bar.width" :height="bar.height" :fill="bar.fill" opacity="0.7" />
          </g>
        </svg>
        <p class="mt-4 rounded-lg bg-slate-50 p-4 text-sm font-bold leading-6 text-slate-600">
          핵심 관찰: 현재가는 {{ latestPrice }}원이며, 종합 점수 {{ report.score.total_score }}점으로
          {{ report.score.verdict }} 상태입니다. {{ report.score.warning }}
        </p>
      </div>

      <div class="mt-6 grid gap-6 lg:grid-cols-[360px_1fr]">
        <aside class="space-y-4">
          <RouterLink :to="detailRoute('total', 0)" class="panel block p-5 transition hover:-translate-y-0.5 hover:shadow-soft">
            <p class="text-sm font-black text-slate-500">최종 종합 점수</p>
            <p class="mt-3 text-6xl font-black text-rose-500">{{ report.score.total_score }}</p>
            <p class="text-xl font-black text-slate-700">점</p>
            <p class="mt-3 inline-flex rounded-full bg-amber-100 px-3 py-1 text-sm font-black text-amber-700">{{ report.score.verdict }}</p>
            <p class="mt-3 text-xs font-black text-emerald-600">종합 점수 계산 상세 보기 →</p>
          </RouterLink>

          <div class="panel p-5">
            <div class="flex items-start justify-between gap-3">
              <div>
                <p class="text-sm font-black text-slate-500">회사 가치 × 진입 타이밍</p>
                <p class="mt-1 text-xs font-bold leading-5 text-slate-500">회사 가치와 진입 타이밍이 모두 70점 이상일 때 포트폴리오 후보입니다.</p>
              </div>
              <span class="shrink-0 rounded-full bg-slate-100 px-2 py-1 text-xs font-black text-slate-500">70점 기준</span>
            </div>

            <div class="mt-4 rounded-lg border border-slate-200 bg-white p-3">
              <div class="mb-2 text-center text-xs font-black text-slate-500">진입 타이밍 높음 ↑</div>
              <div class="relative aspect-square overflow-hidden rounded-md border border-slate-300">
                <div class="absolute left-0 top-0 flex items-center justify-center bg-yellow-300 text-center text-xs font-black leading-5 text-yellow-950" :style="quadrantStyle('timingOnly')">
                  타이밍 우선<br />회사 가치 필요
                </div>
                <div class="absolute flex items-center justify-center bg-green-400 text-center text-xs font-black leading-5 text-green-950" :style="quadrantStyle('pass')">
                  포트폴리오<br />후보
                </div>
                <div class="absolute left-0 flex items-center justify-center bg-red-300 text-center text-xs font-black leading-5 text-red-950" :style="quadrantStyle('watch')">
                  보수적<br />관찰
                </div>
                <div class="absolute flex items-center justify-center bg-sky-300 text-center text-xs font-black leading-5 text-sky-950" :style="quadrantStyle('companyOnly')">
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
              <div class="mt-2 grid grid-cols-3 items-center text-xs font-black text-slate-500">
                <span>회사 가치 낮음</span>
                <span class="text-center">회사 가치 점수 →</span>
                <span class="text-right">회사 가치 높음</span>
              </div>
              <div class="mt-2 text-center text-xs font-bold text-slate-400">진입 타이밍 낮음 ↓</div>
            </div>

            <p class="mt-3 text-sm font-bold text-slate-600">
              현재 위치: {{ quadrantLabel }} · 회사 {{ report.score.company_score }}점 · 타이밍 {{ report.score.timing_score }}점
            </p>
          </div>

          <div class="panel divide-y divide-slate-100">
            <div class="flex justify-between p-4">
              <span class="text-slate-500">현재가</span>
              <strong>{{ latestPrice }}원</strong>
            </div>
            <div class="flex justify-between p-4">
              <span class="text-slate-500">목표가</span>
              <strong>{{ priceText(report.financialMetric.target_price) }}</strong>
            </div>
            <div class="flex justify-between p-4">
              <span class="text-slate-500">목표가 상승여력</span>
              <strong :class="report.score.target_upside_clipped ? 'text-amber-600' : 'text-slate-900'">{{ targetUpsideText }}</strong>
            </div>
            <div class="flex justify-between p-4">
              <span class="text-slate-500">PER</span>
              <strong>{{ ratioText(report.financialMetric.per, "배") }}</strong>
            </div>
            <div class="flex justify-between p-4">
              <span class="text-slate-500">ROE</span>
              <strong>{{ ratioText(report.financialMetric.roe, "%") }}</strong>
            </div>
          </div>
        </aside>

        <main class="space-y-6">
          <section class="panel p-5">
            <h2 class="border-l-4 border-emerald-500 pl-3 text-2xl font-black text-slate-950">데이터 정제 및 계산 근거</h2>
            <div class="mt-5 grid gap-3 md:grid-cols-2">
              <div class="rounded-lg bg-slate-50 p-4">
                <p class="text-sm font-black text-slate-500">Signal</p>
                <p class="mt-1 font-black text-slate-900">{{ report.score.signal }}</p>
              </div>
              <div class="rounded-lg bg-slate-50 p-4">
                <p class="text-sm font-black text-slate-500">Consensus / Confidence</p>
                <p class="mt-1 font-black text-slate-900">{{ report.score.consensus || "-" }} · {{ report.score.confidence || "-" }}</p>
              </div>
              <div class="rounded-lg bg-slate-50 p-4">
                <p class="text-sm font-black text-slate-500">Area Scores</p>
                <p class="mt-1 font-bold text-slate-700">
                  {{ areaScoreText }}
                </p>
              </div>
              <div class="rounded-lg bg-slate-50 p-4">
                <p class="text-sm font-black text-slate-500">RS / RSI / 거래량</p>
                <p class="mt-1 font-bold text-slate-700">
                  RS {{ report.score.rs_rank ?? "-" }} · RSI {{ report.score.rsi ?? "-" }} · 거래량 {{ report.score.volume_ratio }}x
                </p>
              </div>
            </div>
            <div class="mt-4 space-y-2">
              <p v-for="log in report.score.scoring_log" :key="log" class="rounded-lg border border-slate-100 p-3 text-sm font-bold text-slate-600">
                {{ log }}
              </p>
            </div>
          </section>

          <section class="panel p-5">
            <div class="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 class="border-l-4 border-emerald-500 pl-3 text-2xl font-black text-slate-950">AI 3줄 코멘트</h2>
                <p class="mt-2 text-sm font-bold text-slate-500">기업 점수, 타이밍 점수, 리스크 할인 요인을 바탕으로 긍정 요인, 주의 요인, 종합 의견을 요약합니다.</p>
              </div>
              <button class="btn-primary" type="button" :disabled="aiLoading" @click="loadAiComment">
                {{ aiLoading ? "분석 중" : aiLoadingLabel }}
              </button>
            </div>

            <div v-if="aiError" class="mt-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-bold text-red-700">
              {{ aiError }}
            </div>
            <div v-else-if="aiComment" class="mt-5 grid gap-3">
              <div class="rounded-lg bg-emerald-50 p-4">
                <p class="text-sm font-black text-emerald-700">긍정 요인</p>
                <p class="mt-1 font-bold leading-7 text-slate-800">{{ aiComment.positive }}</p>
              </div>
              <div class="rounded-lg bg-amber-50 p-4">
                <p class="text-sm font-black text-amber-700">주의 요인</p>
                <p class="mt-1 font-bold leading-7 text-slate-800">{{ aiComment.negative }}</p>
              </div>
              <div class="rounded-lg bg-slate-100 p-4">
                <p class="text-sm font-black text-slate-600">종합 의견</p>
                <p class="mt-1 font-bold leading-7 text-slate-800">{{ aiComment.conclusion }}</p>
                <p class="mt-2 text-xs font-bold text-slate-400">
                  {{ aiComment.provider }} · {{ aiComment.cached ? "캐시 사용" : "새로 생성" }}
                </p>
              </div>
            </div>
          </section>

          <section>
            <div class="mb-4 flex flex-wrap items-end justify-between gap-3">
              <div>
                <h2 class="border-l-4 border-emerald-500 pl-3 text-2xl font-black text-slate-950">스코어 카드</h2>
                <p class="mt-2 text-sm font-bold text-slate-500">각 카드를 클릭하면 계산 방식과 최종 점수 반영 방식을 확인할 수 있습니다.</p>
              </div>
            </div>
            <div class="space-y-4">
              <RouterLink
                v-for="(card, index) in report.score.score_cards"
                :key="`${card.code || 'score'}-${card.title}`"
                :to="detailRoute('score', index)"
                class="panel block p-5 transition hover:-translate-y-0.5 hover:shadow-soft"
              >
                <article class="grid gap-4 md:grid-cols-[1fr_160px] md:items-center">
                  <div class="flex items-start gap-3">
                    <span class="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-blue-500 text-sm font-black text-white">
                      {{ card.code || "점수" }}
                    </span>
                    <div class="min-w-0">
                      <h3 class="text-lg font-black text-slate-900">{{ card.title }}</h3>
                      <p v-if="card.rawValue || card.description" class="mt-1 text-sm leading-6 text-slate-500">{{ card.rawValue || card.description }}</p>
                      <p v-if="card.reason" class="mt-2 text-sm leading-6 text-slate-600">{{ card.reason }}</p>
                      <p class="mt-2 text-xs font-black text-emerald-600">계산 상세 보기 →</p>
                    </div>
                  </div>
                  <div class="rounded-lg bg-slate-50 p-4 text-right">
                    <p class="text-xs font-black text-slate-400">레이어 점수</p>
                    <p class="mt-1 text-4xl font-black tabular-nums" :class="scoreColor(card.score)">{{ formatScore(card.score) }}</p>
                    <div class="mt-3 h-2 overflow-hidden rounded-full bg-slate-200">
                      <div class="h-full rounded-full" :class="scoreBar(card.score)" :style="{ width: `${card.score}%` }"></div>
                    </div>
                  </div>
                </article>
              </RouterLink>
            </div>
          </section>

          <!-- CAN SLIM 진단 카드 섹션 -->
          <section v-if="report.score.can_slim?.length" class="panel p-5">
            <h2 class="border-l-4 border-emerald-500 pl-3 text-2xl font-black text-slate-950">CAN SLIM 진단</h2>
            <p class="mt-2 text-sm font-bold text-slate-500">성장주 발굴 공식 CAN SLIM 지표별 준수 여부를 확인합니다.</p>
            <div class="mt-5 grid gap-3 sm:grid-cols-2 md:grid-cols-3">
              <div v-for="item in report.score.can_slim" :key="item.code" class="rounded-lg border border-slate-100 p-4">
                <div class="flex items-center justify-between gap-2">
                  <span class="flex h-8 w-8 items-center justify-center rounded bg-emerald-600 text-sm font-black text-white">
                    {{ item.code }}
                  </span>
                  <span class="badge" :class="item.status === 'PASS' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'">
                    {{ item.status }}
                  </span>
                </div>
                <p class="mt-3 font-black text-slate-900">{{ item.name }}</p>
                <p class="mt-1 text-sm font-bold text-slate-600">수치: {{ item.value }}</p>
                <p class="mt-2 text-sm text-slate-500 leading-6">{{ item.description }}</p>
              </div>
            </div>
          </section>

          <IndicatorSection title="기술 지표" section="technical" :ticker="report.stock.ticker" :items="report.score.technical_indicators" />
          <IndicatorSection title="재무 지표" section="financial" :ticker="report.stock.ticker" :items="report.score.financial_indicators" />

          <section class="panel p-5">
            <div class="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h2 class="border-l-4 border-emerald-500 pl-3 text-2xl font-black text-slate-950">공시·뉴스</h2>
                <p class="mt-2 text-sm font-bold text-slate-500">뉴스와 공시 제목을 키워드 기반으로 긍정/중립/부정 분류합니다.</p>
              </div>
              <div class="rounded-lg px-4 py-3 text-right" :class="sentimentSummary.className">
                <p class="text-xs font-black">종합 감성</p>
                <p class="mt-1 text-lg font-black">{{ sentimentSummary.label }} 우위</p>
              </div>
            </div>

            <div class="mt-5 grid gap-3 md:grid-cols-3">
              <div class="rounded-lg bg-emerald-50 p-4">
                <p class="text-sm font-black text-emerald-700">긍정</p>
                <p class="mt-1 text-3xl font-black text-emerald-700">{{ sentimentSummary.positive }}건</p>
              </div>
              <div class="rounded-lg bg-slate-100 p-4">
                <p class="text-sm font-black text-slate-600">중립</p>
                <p class="mt-1 text-3xl font-black text-slate-700">{{ sentimentSummary.neutral }}건</p>
              </div>
              <div class="rounded-lg bg-rose-50 p-4">
                <p class="text-sm font-black text-rose-700">부정</p>
                <p class="mt-1 text-3xl font-black text-rose-700">{{ sentimentSummary.negative }}건</p>
              </div>
            </div>

            <p class="mt-4 rounded-lg bg-slate-50 p-4 text-sm font-bold leading-6 text-slate-600">
              {{ sentimentSummary.reason }}
            </p>

            <div class="mt-5 space-y-3">
              <article
                v-for="item in newsItems"
                :key="`${item.type}-${item.title}`"
                class="rounded-lg border border-slate-100 p-4"
              >
                <div class="flex flex-wrap items-start justify-between gap-3">
                  <div class="min-w-0">
                    <div class="flex flex-wrap items-center gap-2">
                      <span class="rounded bg-slate-100 px-2 py-1 text-xs font-black text-slate-600">{{ item.type }}</span>
                      <span class="text-xs font-bold text-slate-400">{{ item.date }}</span>
                    </div>
                    <p class="mt-2 font-black leading-7 text-slate-900">{{ item.title }}</p>
                    <p class="mt-1 text-sm font-bold leading-6 text-slate-500">{{ item.reason }}</p>
                  </div>
                  <span class="shrink-0 rounded-full px-3 py-1 text-sm font-black" :class="sentimentBadgeClass(item.sentiment)">
                    {{ sentimentLabel(item.sentiment) }}
                  </span>
                </div>
              </article>
            </div>
          </section>
        </main>
      </div>

      <p class="mt-6 rounded-lg bg-slate-100 p-4 text-sm font-bold text-slate-600">{{ report.investmentNotice }}</p>
    </template>
  </section>
</template>

<script setup>
import { computed, defineComponent, h, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { Star } from "@lucide/vue";
import { useAuthStore } from "../../stores/auth";

import { api } from "../api/client";

const props = defineProps({
  ticker: {
    type: String,
    required: true,
  },
});

const authStore = useAuthStore();
const report = ref(null);
const loading = ref(true);
const error = ref("");
const isWatchlisted = ref(false);
const aiComment = ref(null);
const aiLoading = ref(false);
const aiError = ref("");
const componentThreshold = 70;

const aiLoadingLabel = computed(() => (aiComment.value ? "다시 보기" : "AI 분석 보기"));

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

const latestPrice = computed(() => {
  const price = report.value?.priceSeries?.at(-1)?.close_price;
  return formatNumber(price || report.value?.financialMetric?.current_price || 0);
});

const targetUpsideText = computed(() => {
  const upside = report.value?.score?.target_upside;
  if (upside === null || upside === undefined) return "목표가 미산정";
  return report.value?.score?.target_upside_clipped ? `${upside}%+` : `${upside}%`;
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

const newsItems = computed(() => {
  const score = report.value?.score || {};
  const news = (score.news || []).map((item) => normalizeNewsItem(item, "뉴스"));
  const disclosures = (score.disclosures || []).map((item) => normalizeNewsItem(item, "공시"));
  const rows = [...news, ...disclosures].filter((item) => item.title);
  if (rows.length) return rows;
  return [
    {
      type: "뉴스",
      title: "수집된 뉴스·공시 데이터가 없습니다.",
      date: score.base_date || "-",
      sentiment: "neutral",
      reason: "외부 뉴스 API가 연결되지 않아 감성 판단을 보류합니다.",
    },
  ];
});

const sentimentSummary = computed(() => {
  const counts = newsItems.value.reduce(
    (acc, item) => {
      acc[item.sentiment] += 1;
      return acc;
    },
    { positive: 0, neutral: 0, negative: 0 },
  );
  const maxCount = Math.max(counts.positive, counts.neutral, counts.negative);
  const winners = Object.entries(counts).filter(([, count]) => count === maxCount).map(([key]) => key);
  const winner = winners.length === 1 ? winners[0] : "neutral";
  const label = sentimentLabel(winner);
  const className = {
    positive: "bg-emerald-50 text-emerald-700",
    neutral: "bg-slate-100 text-slate-700",
    negative: "bg-rose-50 text-rose-700",
  }[winner];
  return {
    ...counts,
    winner,
    label,
    className,
    reason: `총 ${newsItems.value.length}건 중 긍정 ${counts.positive}건, 중립 ${counts.neutral}건, 부정 ${counts.negative}건으로 분류되어 ${label} 우위로 판단했습니다.`,
  };
});

const chartBounds = computed(() => {
  const prices = report.value?.priceSeries || [];
  const values = prices.flatMap((point) => [
    point.close_price,
    point.ema20,
    point.ema50,
    point.ema200,
    point.bb_upper,
    point.bb_lower,
  ]).filter(Boolean);
  const min = Math.min(...values);
  const max = Math.max(...values);
  return { min, max: max === min ? max + 1 : max };
});

const volumeBars = computed(() => {
  const prices = report.value?.priceSeries || [];
  const maxVolume = Math.max(...prices.map((point) => point.volume), 1);
  return prices.map((point, index) => {
    const x = 45 + (index / Math.max(prices.length - 1, 1)) * 820;
    const height = (point.volume / maxVolume) * 58;
    return {
      x,
      y: 270 - height,
      width: Math.max(2, 780 / Math.max(prices.length, 1)),
      height,
      fill: index > 0 && point.close_price >= prices[index - 1].close_price ? "#3b82f6" : "#fb7185",
    };
  });
});

function linePoints(field) {
  const prices = report.value?.priceSeries || [];
  const { min, max } = chartBounds.value;
  return prices
    .map((point, index) => {
      const value = point[field];
      const x = 45 + (index / Math.max(prices.length - 1, 1)) * 820;
      const y = 255 - ((value - min) / (max - min)) * 210;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString("ko-KR");
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
  const sentiment = normalizeSentiment(item.sentiment || item.tone, title);
  return {
    type,
    title,
    sentiment,
    date: item.publishedAt || item.date || report.value?.score?.base_date || "-",
    reason: sentimentReason(sentiment, title),
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

function sentimentBadgeClass(sentiment) {
  return {
    positive: "bg-emerald-100 text-emerald-700",
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

function summaryMetricTextFor(metric) {
  if (!metric) return "";
  if (typeof metric === "string") return metric;
  const label = metric.label || metric.name || "";
  const value = metric.value ?? metric.score ?? "";
  if (!label && !value) return "";
  return label ? `${label}: ${value}` : `${value}`;
}

function cardTitle(card) {
  return card.label || card.title || card.name || "지표";
}

function cardDescription(card) {
  return card.description || card.reason || "";
}

function scoreText(card) {
  const score = formatScore(card.score ?? card.value);
  return card.max ? `${score}/${card.max}점` : `${score}점`;
}

function detailRoute(section, index) {
  return {
    name: "metric-detail",
    params: {
      ticker: report.value?.stock?.ticker || props.ticker,
      section,
      index,
    },
  };
}

function scoreColor(score) {
  if (score >= 80) return "text-emerald-600";
  if (score >= 55) return "text-amber-500";
  return "text-rose-500";
}

function scoreBar(score) {
  if (score >= 80) return "bg-emerald-500";
  if (score >= 55) return "bg-amber-400";
  return "bg-rose-500";
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

const IndicatorSection = defineComponent({
  props: {
    title: { type: String, required: true },
    section: { type: String, required: true },
    ticker: { type: String, required: true },
    items: { type: Array, default: () => [] },
  },
  setup(sectionProps) {
    return () =>
      h("section", { class: "panel p-5" }, [
        h("h2", { class: "border-l-4 border-emerald-500 pl-3 text-2xl font-black text-slate-950" }, sectionProps.title),
        h(
          "div",
          { class: "mt-5 space-y-3" },
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
              class: "flex items-center justify-between gap-4 rounded-lg border border-slate-100 p-4 transition hover:-translate-y-0.5 hover:border-emerald-200 hover:bg-emerald-50/50",
            }, () => [
              h("div", { class: "min-w-0" }, [
                h("p", { class: "font-black text-slate-800" }, item.name || item.label || item.title || "지표"),
                h("p", { class: "text-sm text-slate-500" }, item.description || item.reason || ""),
                h("p", { class: "mt-1 text-xs font-black text-emerald-600" }, "계산 상세 보기 →"),
              ]),
              h("div", { class: "text-right" }, [
                h("p", { class: "text-lg font-black text-slate-950" }, item.value),
                h("p", { class: "text-sm font-bold text-emerald-600" }, item.status),
              ]),
            ]),
          ),
        ),
      ]);
  },
});

async function toggleWatchlist() {
  try {
    if (isWatchlisted.value) {
      await api.delete(`/watchlist/${props.ticker}/`);
      isWatchlisted.value = false;
    } else {
      await api.post(`/watchlist/${props.ticker}/`);
      isWatchlisted.value = true;
    }
  } catch (err) {
    console.error("관심종목 토글 실패", err);
  }
}

onMounted(async () => {
  try {
    const [reportResponse, watchlistResponse] = await Promise.all([
      api.get(`/stocks/${props.ticker}/report/`),
      authStore.isAuthenticated ? api.get("/watchlist/") : Promise.resolve({ data: { results: [] } }),
    ]);
    report.value = reportResponse.data;

    if (authStore.isAuthenticated && watchlistResponse.data) {
      const items = watchlistResponse.data.results || watchlistResponse.data;
      isWatchlisted.value = Array.isArray(items) && items.some((item) => item.ticker === props.ticker);
    }
  } catch (err) {
    error.value = "종목 리포트를 불러오지 못했습니다.";
  } finally {
    loading.value = false;
  }
});
</script>
