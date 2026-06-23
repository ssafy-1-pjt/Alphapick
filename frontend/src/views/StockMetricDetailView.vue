<template>
  <section class="page-shell py-8">
    <RouterLink
      :to="{ name: 'stock-report', params: { ticker } }"
      class="inline-flex items-center rounded-full bg-slate-100 px-4 py-2 text-sm font-extrabold text-slate-600 transition hover:bg-slate-200"
    >
      ← 리포트로 돌아가기
    </RouterLink>

    <div v-if="loading" class="panel mt-5 p-8 text-center font-bold text-slate-500">상세 계산 근거를 불러오는 중입니다.</div>
    <div v-else-if="error" class="panel mt-5 border-red-200 bg-red-50 p-8 text-red-700">{{ error }}</div>

    <template v-else>
      <div class="mt-5 rounded-lg border border-slate-800 bg-slate-300 p-7">
        <p class="text-sm font-extrabold text-slate-700">{{ report.stock.name }} · {{ report.stock.ticker }} · {{ report.score.base_date }}</p>
        <h1 class="mt-3 text-4xl font-extrabold leading-tight text-slate-950">{{ detail.title }}</h1>
        <p class="mt-3 max-w-4xl text-lg font-bold leading-8 text-slate-700">{{ detail.summary }}</p>
        <div class="mt-5 flex flex-wrap gap-2">
          <span class="badge bg-slate-950 text-white">{{ sectionLabel }}</span>
          <span class="badge bg-emerald-50 text-emerald-700">현재값 {{ displayValue }}</span>
          <span v-if="detail.status" class="badge bg-blue-50 text-blue-700">{{ detail.status }}</span>
        </div>
      </div>

      <div class="mt-6 grid gap-6 lg:grid-cols-[320px_1fr]">
        <aside class="space-y-4">
          <div class="panel p-5">
            <p class="text-sm font-extrabold text-slate-500">현재 리포트 값</p>
            <p class="mt-3 text-5xl font-extrabold tabular-nums" :class="scoreColor(numericValue)">{{ displayValue }}</p>
            <p v-if="detail.status" class="mt-2 text-sm font-extrabold text-emerald-600">{{ detail.status }}</p>
          </div>

          <div class="panel p-5">
            <p class="text-sm font-extrabold text-slate-500">최종 종합 점수</p>
            <p class="mt-3 text-5xl font-extrabold text-slate-950">{{ formatScore(report.score.total_score) }}</p>
            <p class="mt-2 text-sm font-bold leading-6 text-slate-500">
              회사 점수 {{ formatScore(report.score.company_score) }}점과 타이밍 점수 {{ formatScore(report.score.timing_score) }}점을 합산한 뒤,
              과열·낙폭·시장 방향 리스크를 할인합니다.
            </p>
          </div>

          <div class="panel divide-y divide-slate-100">
            <div class="flex justify-between p-4">
              <span class="text-slate-500">회사 점수</span>
              <strong>{{ formatScore(report.score.company_score) }}</strong>
            </div>
            <div class="flex justify-between p-4">
              <span class="text-slate-500">타이밍 점수</span>
              <strong>{{ formatScore(report.score.timing_score) }}</strong>
            </div>
            <div class="flex justify-between p-4">
              <span class="text-slate-500">신뢰도</span>
              <strong>{{ formatScore(report.score.reliability_score) }}</strong>
            </div>
          </div>
        </aside>

        <main class="space-y-5">
          <DetailBlock title="1. 무엇을 보는 지표인가?" :body="detail.meaning" />
          <DetailBlock title="2. 어떻게 계산했나?" :body="detail.calculation" />
          <DetailBlock title="3. 점수에 어떻게 반영되나?" :body="detail.scoreImpact" />
          <DetailBlock title="4. 현재 종목 해석" :body="detail.interpretation" />

          <section class="panel p-5">
            <h2 class="border-l-4 border-emerald-500 pl-3 text-2xl font-extrabold text-slate-950">관련 계산 로그</h2>
            <div class="mt-5 space-y-2">
              <p
                v-for="log in relatedLogs"
                :key="log"
                class="rounded-lg border border-slate-100 p-3 text-sm font-bold leading-6 text-slate-600"
              >
                {{ log }}
              </p>
              <p v-if="!relatedLogs.length" class="rounded-lg bg-slate-50 p-4 text-sm font-bold text-slate-500">
                이 지표에 대한 별도 감점 로그는 없습니다. 정상 범위에서는 최종 점수에 추가 페널티를 주지 않습니다.
              </p>
            </div>
          </section>
        </main>
      </div>
    </template>
  </section>
</template>

<script setup>
import { computed, defineComponent, h, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";

import { api } from "../api/client";

const props = defineProps({
  ticker: { type: String, required: true },
  section: { type: String, required: true },
  index: { type: [String, Number], required: true },
});

const report = ref(null);
const loading = ref(true);
const error = ref("");

const sectionLabel = computed(() => {
  const labels = {
    total: "종합 점수",
    score: "스코어 카드",
    technical: "기술 지표",
    financial: "재무 지표",
  };
  return labels[props.section] || "상세 지표";
});

const items = computed(() => {
  if (!report.value) return [];
  if (props.section === "total") return [totalScoreItem(report.value)];
  if (props.section === "score") return report.value.score.score_cards || [];
  if (props.section === "technical") return report.value.score.technical_indicators || [];
  if (props.section === "financial") {
    const indicators = report.value.score.financial_indicators || [];
    const current = report.value.priceSeries?.at(-1)?.close_price || report.value.financialMetric?.current_price || 0;
    const target = report.value.financialMetric?.target_price;
    return indicators.map((item) => {
      if (item.label === "목표가 상승여력" && current && target) {
        const upside = ((target - current) / current) * 100;
        return {
          ...item,
          value: `${upside > 0 ? "+" : ""}${upside.toFixed(1)}%`,
          status: upside > 0 ? "상승여력" : "주의"
        };
      }
      return item;
    });
  }
  return [];
});

const item = computed(() => items.value[Number(props.index)] || null);

const numericValue = computed(() => {
  const raw = item.value?.score ?? item.value?.value;
  if (raw === null || raw === undefined) return null;
  const number = Number(String(raw).replace(/[^0-9.-]/g, ""));
  return Number.isNaN(number) ? null : number;
});

const displayValue = computed(() => {
  if (!item.value) return "-";
  if (props.section === "total") return `${formatScore(item.value.score)}점`;
  if (props.section === "score") return `${formatScore(item.value.score)}점`;
  return item.value.value ?? "-";
});

const detail = computed(() => {
  if (!item.value) {
    return {
      title: "지표를 찾을 수 없습니다",
      status: "",
      summary: "요청한 지표가 현재 리포트 데이터에 없습니다.",
      meaning: "종목 리포트로 돌아가 다시 선택해 주세요.",
      calculation: "-",
      scoreImpact: "-",
      interpretation: "-",
    };
  }
  return buildDetail(item.value, props.section, report.value);
});

const relatedLogs = computed(() => {
  const logs = report.value?.score?.scoring_log || [];
  const title = detail.value.title;
  const keywords = keywordFor(title, props.section);
  return logs.filter((log) => keywords.some((keyword) => log.includes(keyword)));
});

function buildDetail(rawItem, section, currentReport) {
  const title = rawItem.title || rawItem.label || rawItem.name || "지표";
  const status = rawItem.status || "";
  const base = {
    title,
    status,
    summary: rawItem.description || rawItem.reason || "현재 종목의 점수 산출에 사용되는 세부 판단 항목입니다.",
    meaning: rawItem.meaning || defaultMeaning(title, section),
    calculation: rawItem.calculation || defaultCalculation(title, section, currentReport),
    scoreImpact: rawItem.score_impact || rawItem.scoreImpact || defaultImpact(title, section),
    interpretation: rawItem.interpretation || defaultInterpretation(rawItem, title, section),
  };
  return base;
}

function totalScoreItem(currentReport) {
  const score = currentReport.score;
  return {
    title: "종합 점수",
    score: score.total_score,
    status: score.verdict,
    description: `${currentReport.stock.name}의 최종 추천 판단 점수입니다.`,
    meaning: "종합 점수는 회사 가치와 진입 타이밍을 합산한 뒤, 과열·낙폭·시장 방향 같은 위험 요인을 반영한 리스크 조정 참고 점수입니다. 포트폴리오 편입은 종합 점수 하나가 아니라 회사 가치 70점 이상, 진입 타이밍 70점 이상을 모두 통과했는지로 판단합니다.",
    calculation:
      `1차 점수 = 회사 점수 ${formatScore(score.company_score)}점 × 45% + 타이밍 점수 ${formatScore(score.timing_score)}점 × 55%\n` +
      `회사 점수는 가치/퀄리티, 연간 ROE 대용, EPS 가속도를 합산합니다.\n` +
      `타이밍 점수는 주도주 모멘텀, 신고가/피벗, 수급/거래량을 합산합니다.\n` +
      "이후 Z-Score 과열, 최대낙폭, 시장 방향, 데이터 신뢰도 조건에 따라 할인 또는 직접 감점을 적용합니다.",
    score_impact: "종합 점수는 위험도를 보여주는 참고 점수입니다. 실제 포트폴리오 편입은 회사 가치 70점 이상, 진입 타이밍 70점 이상, 신뢰도 70점 이상, 유동성/Fail-safe 조건 통과 여부로 결정합니다.",
    interpretation:
      `현재 종합 점수는 ${formatScore(score.total_score)}점이고 판정은 "${score.verdict}"입니다. ` +
      `회사 점수는 ${formatScore(score.company_score)}점, 타이밍 점수는 ${formatScore(score.timing_score)}점, 데이터 신뢰도는 ${formatScore(score.reliability_score)}점입니다.`,
  };
}

function defaultMeaning(title, section) {
  if (section === "total") {
    return "종합 점수는 회사 가치와 진입 타이밍을 합친 뒤 리스크를 반영한 참고 점수입니다. 편입 기준은 회사 가치와 타이밍이 각각 70점 이상인지입니다.";
  }
  if (section === "score") {
    if (title.includes("가치") || title.includes("퀄리티")) {
      return "회사가 가격 대비 얼마나 안정적이고 거래 가능한 품질을 갖췄는지 보는 레이어입니다. 현재 MVP에서는 재무 데이터가 없는 종목도 평가할 수 있도록 유동성, 변동성, 52주 고점 근접도를 가격 기반 대용 지표로 함께 사용합니다.";
    }
    if (title.includes("주도주") || title.includes("모멘텀")) {
      return "시장 안에서 이 종목이 상대적으로 강한 흐름을 보이는지 확인하는 레이어입니다. 많이 오른 종목을 무조건 좋게 보는 것이 아니라, 상대강도와 중기 수익률, 신고가 근접도를 같이 봅니다.";
    }
    if (title.includes("리스크")) {
      return "좋아 보이는 종목이라도 시장 약세, 단기 과열, 큰 낙폭이 있으면 추격 매수를 피하기 위해 점수를 낮추는 방어 레이어입니다.";
    }
  }
  if (section === "technical") return "가격과 거래량에서 현재 타이밍을 읽기 위한 기술적 지표입니다.";
  return "기업의 이익, 자산, 목표가, 유동성처럼 회사 자체를 해석하는 데 쓰는 재무/참고 지표입니다.";
}

function defaultCalculation(title, section, currentReport) {
  const area = currentReport?.score?.area_scores || {};
  if (section === "total") {
    const score = currentReport?.score || {};
    return `종합 점수 = 회사 점수 ${formatScore(score.company_score)}점 × 45% + 타이밍 점수 ${formatScore(score.timing_score)}점 × 55%입니다. 이후 리스크 제어, Z-Score 과열, 최대낙폭, 시장 방향, 신뢰도 조건으로 할인 또는 감점을 적용합니다.`;
  }
  if (section === "score") {
    if (title.includes("가치") || title.includes("퀄리티")) {
      return `가치/퀄리티 = 유동성 점수 45% + 변동성 안정성 30% + 52주 고점 거리 기반 가격 품질 25%로 계산합니다. 현재 이 종목의 레이어 점수는 ${formatScore(area.valueQuality)}점입니다.`;
    }
    if (title.includes("주도주") || title.includes("모멘텀")) {
      return `주도주 모멘텀 = RS 등급 40% + 6개월 수익률 30% + 52주 고점 근접도 30%로 계산합니다. 현재 이 종목의 레이어 점수는 ${formatScore(area.leadershipMomentum)}점입니다.`;
    }
    if (title.includes("리스크")) {
      return `리스크 제어 = 시장 방향 40% + Z-Score 과열 방지 30% + 최대낙폭/변동성 방어 30%입니다. 현재 리스크 레이어는 ${formatScore(area.marketDirection)} / ${formatScore(area.meanReversion)} / ${formatScore(area.drawdownControl)} 조합으로 계산됐습니다.`;
    }
  }

  if (title.includes("RSI")) return "최근 14일 평균 상승폭과 평균 하락폭을 비교해 0~100 범위로 환산합니다. 70 이상은 단기 과열, 30 이하는 단기 침체로 해석합니다.";
  if (title.includes("Z-Score")) return "현재가에서 최근 20일 평균을 뺀 뒤 20일 표준편차로 나눕니다. 값이 2를 넘으면 평균 대비 꽤 멀어진 과열 구간으로 봅니다.";
  if (title.includes("최대낙폭") || title.includes("MDD")) return "최근 1년 동안의 누적 고점 대비 현재까지 가장 크게 하락했던 비율을 계산합니다. 예를 들어 -30%면 고점 대비 최대 30% 하락한 구간이 있었다는 뜻입니다.";
  if (title.includes("거래량")) return "오늘 거래량을 최근 20일 평균 거래량으로 나눈 값입니다. 2.0이면 평소보다 거래량이 2배였다는 의미입니다.";
  if (title.includes("52주")) return "현재가가 최근 52주 최고가에서 몇 퍼센트 떨어져 있는지 계산합니다. 0%에 가까울수록 신고가 근처입니다.";
  if (title.includes("목표가 상승")) return "증권사 컨센서스 목표가와 현재가의 차이를 현재가로 나눠 백분율로 표시합니다.";
  if (title.includes("목표가")) return "네이버 금융/FnGuide에서 수집한 증권사 컨센서스 목표주가입니다. 추정기관이 없거나 값이 없으면 미산정으로 표시합니다.";
  if (title.includes("PER")) return "현재 주가를 주당순이익(EPS)으로 나눈 값입니다. 이익 1원에 대해 시장이 얼마를 지불하는지 보는 지표입니다.";
  if (title.includes("PBR")) return "현재 주가를 주당순자산(BPS)으로 나눈 값입니다. 장부가치 대비 주가 부담을 보는 지표입니다.";
  if (title.includes("ROE")) return "당기순이익을 자기자본으로 나눠 계산합니다. 회사가 자기자본으로 얼마나 효율적으로 이익을 내는지 봅니다.";
  if (title.includes("영업이익률")) return "영업이익을 매출액으로 나눠 계산합니다. 회사 본업의 수익성을 판단합니다.";
  if (title.includes("유동성")) return "최근 20거래일 동안의 평균 거래대금입니다. 가격과 거래량을 곱한 뒤 평균을 냅니다.";
  if (title.includes("신뢰도")) return "가격 이력 길이, 유동성, 결측 여부를 내부 기준으로 합산해 0~100점으로 환산합니다.";
  return "현재 수집된 원천 데이터를 정규화한 뒤 리포트 표시 값으로 변환합니다.";
}

function defaultImpact(title, section) {
  if (section === "total") {
    return "종합 점수는 리스크 조정 상태를 설명하는 값입니다. 메인 포트폴리오는 종합 점수와 무관하게 회사 가치 70점 이상, 진입 타이밍 70점 이상을 모두 통과한 종목을 편입합니다.";
  }
  if (section === "score") {
    if (title.includes("리스크")) return "리스크 점수는 정상 범위일 때는 점수를 거의 건드리지 않고, 과열·깊은 낙폭·시장 약세가 확인될 때 최종 총점에 할인 또는 직접 감점을 적용합니다.";
    if (title.includes("주도주")) return "주도주 모멘텀은 타이밍 점수의 핵심 축입니다. 타이밍 점수는 최종 총점에서 55% 비중으로 반영됩니다.";
    return "가치/퀄리티는 회사 점수의 핵심 축입니다. 회사 점수는 최종 총점에서 45% 비중으로 반영됩니다.";
  }
  if (title.includes("Z-Score")) return "2.0을 넘으면 단기 과열로 보고 최종 총점에 20% 할인을 적용합니다.";
  if (title.includes("최대낙폭") || title.includes("MDD")) return "-35%보다 깊으면 최종 점수에서 직접 감점하고, 리스크 제어 레이어에도 반영합니다.";
  if (title.includes("거래량")) return "거래량 배율은 수급/거래량 점수에 반영됩니다. 2배 이상이면 거래량 급증 태그가 붙습니다.";
  if (title.includes("52주")) return "52주 고점에 가까울수록 신고가/피벗 점수와 주도주 모멘텀 점수에 유리합니다.";
  if (title.includes("RSI")) return "RSI는 현재 MVP에서 직접 가산점보다는 과열/침체 해석 보조 지표로 표시합니다.";
  if (title.includes("목표가")) return "목표가와 상승여력은 투자 판단 참고 지표입니다. 애널리스트 목표가는 후행성이 있어 현재 최종 점수에는 직접 반영하지 않습니다.";
  if (title.includes("PER") || title.includes("PBR") || title.includes("ROE") || title.includes("영업이익률")) {
    return "재무 지표는 종목 해석과 리포트 근거 보강에 사용됩니다. 현재 실전 테스트 점수 엔진은 모든 KOSPI 종목을 평가하기 위해 가격/거래량 기반 점수를 우선 사용합니다.";
  }
  if (title.includes("유동성")) return "유동성이 낮으면 포트폴리오 편입에서 제외될 수 있고, 데이터 신뢰도와 가치/퀄리티 점수에도 영향을 줍니다.";
  if (title.includes("신뢰도")) return "신뢰도 70점 미만이면 최종 점수에 할인이 적용되고, 55점 미만이면 Fail-safe 상한이 걸립니다.";
  return "현재 지표는 리포트의 해석 근거로 사용되며, 위험 구간일 때 최종 점수 산출에 반영됩니다.";
}

function defaultInterpretation(rawItem, title, section) {
  const value = rawItem.value ?? `${formatScore(rawItem.score)}점`;
  if (section === "total") {
    const score = Number(rawItem.score);
    return `현재 종합 점수는 ${formatScore(score)}점입니다. 다만 포트폴리오 편입 판단은 이 숫자 하나가 아니라 회사 가치와 진입 타이밍이 각각 70점 이상인지로 결정합니다.`;
  }
  if (section === "score") {
    const score = Number(rawItem.score);
    if (score >= 80) return `현재 ${title} 점수는 ${formatScore(score)}점으로 강한 구간입니다. 이 레이어는 종목 추천에 긍정적으로 작용했습니다.`;
    if (score >= 55) return `현재 ${title} 점수는 ${formatScore(score)}점으로 보통 이상입니다. 추천 근거는 있지만 다른 리스크 지표와 함께 확인해야 합니다.`;
    return `현재 ${title} 점수는 ${formatScore(score)}점으로 약한 편입니다. 이 레이어는 최종 점수의 발목을 잡는 요인입니다.`;
  }
  return `현재 값은 ${value}입니다. 상태는 "${rawItem.status || "확인"}"으로 분류했으며, 이 값은 리포트의 판단 근거로 표시됩니다.`;
}

function keywordFor(title, section) {
  if (section === "total") return ["점수", "할인", "감점", "신뢰도", "시장", "과열", "낙폭", "Fail-safe", "52주", "허스트", "거래량"];
  if (title.includes("Z-Score")) return ["Z-Score", "과열"];
  if (title.includes("낙폭") || title.includes("MDD")) return ["낙폭", "MDD"];
  if (title.includes("거래량")) return ["거래량"];
  if (title.includes("52주") || title.includes("신고가")) return ["52주", "신고가"];
  if (title.includes("리스크")) return ["리스크", "과열", "낙폭", "시장"];
  if (title.includes("주도주") || title.includes("모멘텀")) return ["52주", "허스트", "거래량"];
  if (section === "financial") return ["신뢰도", "Fail-safe"];
  return [title];
}

function scoreColor(value) {
  if (value === null || value === undefined) return "text-slate-950";
  if (props.section === "technical" && value < 0) return "text-rose-500";
  if (value >= 80) return "text-emerald-600";
  if (value >= 55) return "text-amber-500";
  return "text-rose-500";
}

function formatScore(value) {
  if (value === null || value === undefined || value === "") return "-";
  const number = Number(value);
  if (Number.isNaN(number)) return value;
  return number.toFixed(1).replace(".0", "");
}

const DetailBlock = defineComponent({
  props: {
    title: { type: String, required: true },
    body: { type: String, required: true },
  },
  setup(blockProps) {
    return () =>
      h("section", { class: "panel p-5" }, [
        h("h2", { class: "border-l-4 border-emerald-500 pl-3 text-2xl font-extrabold text-slate-950" }, blockProps.title),
        h("p", { class: "mt-4 whitespace-pre-line text-base font-bold leading-8 text-slate-700" }, blockProps.body),
      ]);
  },
});

onMounted(async () => {
  try {
    const response = await api.get(`/stocks/${props.ticker}/report/`);
    report.value = response.data;
    if (!items.value[Number(props.index)]) {
      error.value = "요청한 상세 지표를 찾을 수 없습니다.";
    }
  } catch (err) {
    error.value = "상세 계산 근거를 불러오지 못했습니다.";
  } finally {
    loading.value = false;
  }
});
</script>
