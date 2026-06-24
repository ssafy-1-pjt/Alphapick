<template>
  <section class="page-shell py-8">
    <div class="mb-6">
      <p class="text-sm font-bold uppercase tracking-[0.18em] text-emerald-600">Stock Universe</p>
      <h1 class="mt-2 text-4xl font-bold text-slate-950">종목 검색과 스코어 필터</h1>
      <p class="mt-3 max-w-3xl leading-7 text-slate-600">
        회사 품질, 시장 검증, 매수 타이밍을 독립적으로 확인하고 종합 투자매력도 또는 각 축 점수 기준으로 종목을 비교할 수 있습니다.
      </p>
    </div>

    <div class="grid gap-5 xl:grid-cols-[260px_1fr]">
      <aside class="panel h-fit overflow-hidden xl:sticky xl:top-8">
        <div class="flex items-center justify-between border-b border-slate-100 px-4 py-3">
          <div>
            <p class="text-xs font-bold uppercase tracking-[0.16em] text-emerald-600">Theme</p>
            <h2 class="text-lg font-bold text-slate-950">섹터·테마</h2>
          </div>
          <button class="text-sm font-bold text-slate-500 hover:text-emerald-600" type="button" @click="clearTheme">
            초기화
          </button>
        </div>

        <div v-if="themeLoading" class="p-4 text-sm font-bold text-slate-500">테마를 불러오는 중입니다.</div>
        <div v-else class="max-h-[calc(100vh-180px)] overflow-auto">
          <section v-for="category in categorizedThemeGroups" :key="category.name" class="border-b border-slate-100 last:border-b-0">
            <button
              class="flex w-full items-center justify-between gap-3 bg-slate-50 px-4 py-3 text-left transition hover:bg-slate-100"
              type="button"
              @click="toggleCategory(category.name)"
            >
              <span class="min-w-0 truncate text-xs font-bold uppercase tracking-[0.12em] text-slate-500">{{ category.name }}</span>
              <span class="shrink-0 text-xs font-bold text-slate-400">{{ category.stockCount }}</span>
            </button>
            <div v-if="expandedCategories[category.name]">
              <div v-for="group in category.groups" :key="group.id" class="border-t border-slate-100 first:border-t-0">
                <button
                  class="flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition hover:bg-slate-50"
                  :class="isGroupSelected(group) ? 'bg-emerald-50 text-emerald-700' : 'text-slate-700'"
                  type="button"
                  @click="toggleGroup(group)"
                >
                  <span class="flex min-w-0 items-center gap-2">
                    <span class="w-5 text-center text-sm">{{ group.icon || "·" }}</span>
                    <span class="truncate text-sm font-bold">{{ group.name }}</span>
                  </span>
                  <span class="shrink-0 text-xs font-bold text-slate-400">{{ group.stock_count }}</span>
                </button>
                <div v-if="expandedGroups[group.name]" class="space-y-1 px-3 pb-3">
              <button
                class="flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm font-bold transition"
                :class="isGroupOnlySelected(group) ? 'bg-emerald-100 text-emerald-800' : 'text-slate-500 hover:bg-slate-50 hover:text-slate-800'"
                type="button"
                @click="selectGroup(group)"
              >
                <span>전체</span>
                <span>{{ group.stock_count }}</span>
              </button>
              <button
                v-for="theme in group.themes"
                :key="theme.id"
                class="flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm transition"
                :class="isThemeSelected(theme) ? 'bg-emerald-600 font-bold text-white' : 'font-semibold text-slate-600 hover:bg-slate-50 hover:text-slate-950'"
                type="button"
                @click="selectTheme(group, theme)"
              >
                <span class="truncate">{{ theme.name }}</span>
                <span class="ml-2 shrink-0 text-xs opacity-75">{{ theme.stock_count }}</span>
              </button>
                </div>
              </div>
            </div>
          </section>
        </div>
      </aside>

      <div>
        <div class="panel mb-6 grid gap-3 p-4 md:grid-cols-[1fr_180px_180px_160px]">
          <input v-model="filters.q" class="field" placeholder="종목명 또는 티커 검색" @keyup.enter="loadStocks" />
          <select v-model="filters.min_score" class="field">
            <option value="">전체 점수</option>
            <option value="90">90점 이상</option>
            <option value="80">80점 이상</option>
            <option value="70">70점 이상</option>
            <option value="60">60점 이상</option>
          </select>
          <select v-model="filters.sort" class="field">
            <option value="composite">종합 점수순</option>
            <option value="company">회사 품질순</option>
            <option value="market">시장 검증순</option>
            <option value="timing">매수 타이밍순</option>
            <option value="valuation">밸류 조정순</option>
          </select>
          <button class="btn-primary" type="button" @click="loadStocks">검색</button>
        </div>

        <div v-if="selectedThemeLabel" class="mb-4 flex flex-wrap items-center gap-2">
          <span class="badge bg-emerald-50 text-emerald-700">{{ selectedThemeLabel }}</span>
          <button class="text-sm font-bold text-slate-500 hover:text-emerald-600" type="button" @click="clearTheme">
            테마 필터 해제
          </button>
        </div>

        <div v-if="!loading" class="mb-4 flex flex-wrap items-center justify-between gap-3 text-sm font-bold text-slate-500">
          <span>전체 {{ totalCount }}개 중 {{ stocks.length }}개 표시</span>
          <span v-if="nextPage">스크롤하면 다음 종목을 계속 불러옵니다.</span>
          <span v-else>모든 조건의 종목을 불러왔습니다.</span>
        </div>

        <div v-if="loading" class="panel p-8 text-center font-bold text-slate-500">종목을 불러오는 중입니다.</div>
        <div v-else-if="error" class="panel border-red-200 bg-red-50 p-8 font-bold text-red-700">{{ error }}</div>
        <div v-else-if="!stocks.length" class="panel p-8 text-center font-bold text-slate-500">조건에 맞는 종목이 없습니다.</div>
        <template v-else>
          <div class="grid gap-4 md:grid-cols-2">
            <RouterLink
              v-for="stock in stocks"
              :key="stock.ticker"
              :to="{ name: 'stock-report', params: { ticker: stock.ticker } }"
              class="panel p-5 transition hover:-translate-y-0.5 hover:shadow-soft"
            >
              <div class="flex items-start justify-between gap-4">
                <div>
                  <div class="flex flex-wrap items-center gap-2">
                    <h2 class="text-2xl font-bold text-slate-950">{{ stock.name }}</h2>
                    <span class="badge bg-slate-100 text-slate-600">{{ stock.ticker }}</span>
                    <span class="badge bg-emerald-50 text-emerald-700">{{ stock.sector }}</span>
                    <span
                      v-for="theme in stockThemes(stock)"
                      :key="`${stock.ticker}-${theme}`"
                      class="badge bg-blue-50 text-blue-700"
                    >
                      {{ theme }}
                    </span>
                  </div>
                  <div class="mt-3 flex flex-wrap gap-2">
                    <span v-if="stock.signal" class="badge bg-slate-950 text-white">{{ stock.signal }}</span>
                    <span v-if="stock.low_liquidity_flag" class="badge bg-amber-100 text-amber-700">유동성 주의</span>
                    <span v-if="stock.fail_safe_flag" class="badge bg-red-100 text-red-700">Fail-safe</span>
                    <span v-if="stock.volume_surge_flag" class="badge bg-blue-100 text-blue-700">거래량 급증</span>
                    <span class="badge bg-slate-100 text-slate-700">{{ stock.action_label }}</span>
                  </div>
                  <p class="mt-3 text-sm leading-6 text-slate-600">{{ stock.key_reason || stock.reason }}</p>
                  <div class="mt-4 grid grid-cols-3 gap-2 text-center text-xs font-bold text-slate-500">
                    <div class="rounded-md bg-slate-50 p-2"><span class="block">회사</span><strong class="text-slate-900">{{ formatScore(stock.company_score) }}</strong></div>
                    <div class="rounded-md bg-slate-50 p-2"><span class="block">시장</span><strong class="text-slate-900">{{ formatScore(stock.market_validation_score) }}</strong></div>
                    <div class="rounded-md bg-slate-50 p-2"><span class="block">타이밍</span><strong class="text-slate-900">{{ formatScore(stock.timing_score) }}</strong></div>
                  </div>
                </div>
                <div class="w-24 shrink-0 text-right">
                  <p class="text-sm font-bold text-slate-500">점수</p>
                  <p class="text-4xl font-extrabold leading-none tabular-nums" :class="scoreTextClass(stock.latest_score)">
                    {{ formatScore(stock.latest_score) }}
                  </p>
                  <div class="mt-2 ml-auto h-1 w-20 overflow-hidden rounded-full bg-slate-100">
                    <div
                      class="h-full rounded-full"
                      :class="scoreLineClass(stock.latest_score)"
                      :style="{ width: `${scorePercent(stock.latest_score)}%` }"
                    ></div>
                  </div>
                </div>
              </div>
            </RouterLink>
          </div>

          <div ref="loadMoreSentinel" class="py-8 text-center">
            <p v-if="loadingMore" class="font-bold text-slate-500">다음 종목을 불러오는 중입니다.</p>
            <button v-else-if="nextPage" class="btn-secondary" type="button" @click="loadMore">더 불러오기</button>
            <p v-else class="font-bold text-slate-400">마지막 종목까지 모두 표시했습니다.</p>
          </div>
        </template>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from "vue";

import { api } from "../api/client";

const filters = reactive({
  q: "",
  min_score: "",
  sort: "composite",
  theme_group: "",
  theme: "",
});
const stocks = ref([]);
const themeGroups = ref([]);
const loading = ref(true);
const themeLoading = ref(true);
const loadingMore = ref(false);
const error = ref("");
const nextPage = ref(null);
const totalCount = ref(0);
const loadMoreSentinel = ref(null);
const expandedGroups = reactive({});
const expandedCategories = reactive({});
let observer = null;

const categoryOrder = [
  {
    name: "성장·첨단",
    groups: ["AI 인프라", "반도체", "양자컴퓨팅", "사이버보안", "로봇·자동화", "우주·위성"],
  },
  {
    name: "에너지·인프라",
    groups: ["전력 인프라", "이차전지·ESS", "정유·에너지", "유틸리티·가스", "스마트팜·애그테크"],
  },
  {
    name: "바이오·헬스케어",
    groups: ["바이오·헬스케어", "바이오 CDMO", "디지털헬스·AI의료"],
  },
  {
    name: "산업재·소재",
    groups: ["조선·해운", "K-방산", "건설기계·중공업", "건설·건자재", "철강·화학", "산업소재·부품", "제지·포장"],
  },
  {
    name: "소비·콘텐츠",
    groups: ["물류·유통", "K-소비재", "식품·수산", "패션·의류", "생활소비재", "콘텐츠·엔터", "미디어·광고"],
  },
  {
    name: "금융·기타",
    groups: ["금융·밸류업", "리츠·부동산", "IT서비스", "농업·사료"],
  },
];

function requestParams(page) {
  const params = { page };
  if (filters.q) params.q = filters.q;
  if (filters.min_score) params.min_score = filters.min_score;
  if (filters.sort) params.sort = filters.sort;
  if (filters.theme) params.theme = filters.theme;
  if (filters.theme_group) params.theme_group = filters.theme_group;
  return params;
}

const selectedThemeLabel = computed(() => {
  if (filters.theme) return `${filters.theme_group} · ${filters.theme}`;
  if (filters.theme_group) return `${filters.theme_group} 전체`;
  return "";
});

const categorizedThemeGroups = computed(() => {
  const groupMap = new Map(themeGroups.value.map((group) => [group.name, group]));
  const used = new Set();
  const categories = categoryOrder
    .map((category) => {
      const groups = category.groups.map((name) => groupMap.get(name)).filter(Boolean);
      groups.forEach((group) => used.add(group.name));
      return {
        name: category.name,
        groups,
        stockCount: groups.reduce((sum, group) => sum + Number(group.stock_count || 0), 0),
      };
    })
    .filter((category) => category.groups.length);

  const leftovers = themeGroups.value.filter((group) => !used.has(group.name));
  if (leftovers.length) {
    categories.push({
      name: "기타",
      groups: leftovers,
      stockCount: leftovers.reduce((sum, group) => sum + Number(group.stock_count || 0), 0),
    });
  }

  return categories;
});

function updatePagination(payload, page) {
  if (Array.isArray(payload)) {
    totalCount.value = payload.length;
    nextPage.value = null;
    return payload;
  }

  totalCount.value = payload?.count ?? 0;
  nextPage.value = payload?.next ? page + 1 : null;
  return payload?.results ?? [];
}

function setupInfiniteScroll() {
  observer?.disconnect();
  if (!loadMoreSentinel.value || !nextPage.value) return;

  observer = new IntersectionObserver(
    (entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        loadMore();
      }
    },
    { rootMargin: "500px 0px" },
  );
  observer.observe(loadMoreSentinel.value);
}

async function fetchStocksPage(page, append = false) {
  const response = await api.get("/stocks/", { params: requestParams(page) });
  const rows = updatePagination(response.data, page);
  stocks.value = append ? [...stocks.value, ...rows] : rows;
  await nextTick();
  setupInfiniteScroll();
}

async function loadStocks() {
  loading.value = true;
  error.value = "";
  stocks.value = [];
  nextPage.value = null;
  try {
    await fetchStocksPage(1);
  } catch {
    error.value = "종목 데이터를 불러오지 못했습니다. 백엔드 서버 상태를 확인해 주세요.";
  } finally {
    loading.value = false;
    await nextTick();
    setupInfiniteScroll();
  }
}

async function loadThemes() {
  themeLoading.value = true;
  try {
    const response = await api.get("/themes/");
    themeGroups.value = Array.isArray(response.data) ? response.data : response.data?.results ?? [];
    for (const category of categorizedThemeGroups.value.slice(0, 2)) {
      expandedCategories[category.name] = true;
    }
    for (const group of categorizedThemeGroups.value.flatMap((category) => category.groups).slice(0, 3)) {
      expandedGroups[group.name] = true;
    }
  } finally {
    themeLoading.value = false;
  }
}

function toggleCategory(categoryName) {
  expandedCategories[categoryName] = !expandedCategories[categoryName];
}

function toggleGroup(group) {
  expandedGroups[group.name] = !expandedGroups[group.name];
  if (!expandedGroups[group.name]) return;
  if (!filters.theme && filters.theme_group === group.name) return;
}

function selectGroup(group) {
  filters.theme_group = group.name;
  filters.theme = "";
  expandedGroups[group.name] = true;
  loadStocks();
}

function selectTheme(group, theme) {
  filters.theme_group = group.name;
  filters.theme = theme.name;
  expandedGroups[group.name] = true;
  loadStocks();
}

function clearTheme() {
  filters.theme_group = "";
  filters.theme = "";
  loadStocks();
}

function isGroupSelected(group) {
  return filters.theme_group === group.name;
}

function isGroupOnlySelected(group) {
  return filters.theme_group === group.name && !filters.theme;
}

function isThemeSelected(theme) {
  return filters.theme === theme.name;
}

function stockThemes(stock) {
  return stock.themes?.length ? stock.themes : [stock.primary_theme].filter(Boolean);
}

function formatScore(value) {
  const score = Number(value || 0);
  return Number.isInteger(score) ? score : score.toFixed(1);
}

function scoreTextClass(value) {
  const score = Number(value || 0);
  if (score >= 70) return "text-[#009e8e]";
  if (score >= 50) return "text-amber-600";
  return "text-rose-500";
}

function scoreLineClass(value) {
  const score = Number(value || 0);
  if (score >= 70) return "bg-[#12b8a6]";
  if (score >= 50) return "bg-amber-500";
  return "bg-rose-500";
}

function scorePercent(value) {
  const score = Number(value || 0);
  return Math.min(100, Math.max(0, score));
}

async function loadMore() {
  if (!nextPage.value || loadingMore.value || loading.value) return;
  loadingMore.value = true;
  const page = nextPage.value;
  try {
    await fetchStocksPage(page, true);
  } catch {
    error.value = "다음 종목을 불러오지 못했습니다.";
  } finally {
    loadingMore.value = false;
  }
}

onMounted(() => {
  loadThemes();
  loadStocks();
});
onBeforeUnmount(() => observer?.disconnect());
</script>
