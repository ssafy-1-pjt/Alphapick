<template>
  <section class="min-h-screen bg-[radial-gradient(circle_at_top_left,#ffffff_0,#f6f8fb_36%,#eef3f7_100%)]">
    <div class="w-full px-20 py-5">
      <div class="grid gap-4 xl:grid-cols-[236px_1fr]">
        <aside class="panel h-fit overflow-hidden xl:sticky xl:top-20">
          <div class="flex items-center justify-between border-b border-slate-100 px-4 py-3">
            <div>
              <p class="text-xs font-bold uppercase tracking-[0.16em] text-[#12b8a6]">Theme</p>
              <h2 class="text-lg font-bold text-slate-950">섹터·테마</h2>
            </div>
            <button class="text-sm font-bold text-slate-500 transition hover:text-[#12b8a6] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#12b8a6]" type="button" @click="clearTheme">초기화</button>
          </div>

          <div v-if="themeLoading" class="p-4 text-sm font-bold text-slate-500">테마를 불러오는 중입니다.</div>
          <div v-else class="max-h-[calc(100vh-150px)] overflow-auto">
            <section v-for="category in categorizedThemeGroups" :key="category.name" class="border-b border-slate-100 last:border-b-0">
              <button class="flex w-full items-center justify-between gap-3 bg-slate-50 px-4 py-3 text-left transition hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inset focus-visible:outline-[#12b8a6]" type="button" :aria-expanded="!!expandedCategories[category.name]" @click="toggleCategory(category.name)">
                <span class="min-w-0 truncate text-xs font-bold uppercase tracking-[0.12em] text-slate-500">{{ category.name }}</span>
                <span class="shrink-0 text-xs font-bold text-slate-400">{{ category.stockCount }}</span>
              </button>
              <div v-if="expandedCategories[category.name]">
                <div v-for="group in category.groups" :key="group.id" class="border-t border-slate-100 first:border-t-0">
                  <button class="flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inset focus-visible:outline-[#12b8a6]" :class="isGroupSelected(group) ? 'bg-[#e8fbf7] text-[#0b8f83]' : 'text-slate-700'" type="button" :aria-expanded="!!expandedGroups[group.name]" @click="toggleGroup(group)">
                    <span class="flex min-w-0 items-center gap-2">
                      <span class="w-5 text-center text-sm">{{ group.icon || "·" }}</span>
                      <span class="truncate text-sm font-bold">{{ group.name }}</span>
                    </span>
                    <span class="shrink-0 text-xs font-bold text-slate-400">{{ group.stock_count }}</span>
                  </button>
                  <div v-if="expandedGroups[group.name]" class="space-y-1 px-3 pb-3">
                    <button class="flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm font-bold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#12b8a6]" :class="isGroupOnlySelected(group) ? 'bg-[#d7f8f2] text-[#0b8f83]' : 'text-slate-500 hover:bg-slate-50 hover:text-slate-800'" type="button" :aria-pressed="isGroupOnlySelected(group)" @click="selectGroup(group)">
                      <span>전체</span>
                      <span>{{ group.stock_count }}</span>
                    </button>
                    <button v-for="theme in group.themes" :key="theme.id" class="flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#12b8a6]" :class="isThemeSelected(theme) ? 'bg-[#12b8a6] font-bold text-white' : 'font-semibold text-slate-600 hover:bg-slate-50 hover:text-slate-950'" type="button" :aria-pressed="isThemeSelected(theme)" @click="selectTheme(group, theme)">
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
            <label class="sr-only" for="stock-search-input">종목명 또는 티커 검색</label>
            <input id="stock-search-input" v-model="filters.q" class="field" placeholder="종목명 또는 티커 검색" @keyup.enter="loadStocks" />
            <label class="sr-only" for="score-filter-select">최소 종합 점수</label>
            <select id="score-filter-select" v-model="filters.min_score" class="field" @change="loadStocks">
              <option value="">전체 점수</option>
              <option value="90">90점 이상</option>
              <option value="80">80점 이상</option>
              <option value="70">70점 이상</option>
              <option value="60">60점 이상</option>
            </select>
            <label class="sr-only" for="score-sort-select">정렬 기준</label>
            <select id="score-sort-select" v-model="filters.sort" class="field" @change="loadStocks">
              <option value="composite">종합 점수순</option>
              <option value="company">회사 품질순</option>
              <option value="market">시장 검증순</option>
              <option value="timing">매수 타이밍순</option>
              <option value="valuation">밸류 조정순</option>
            </select>
            <button class="btn-primary" type="button" :disabled="loading" @click="loadStocks">검색</button>
          </div>

          <div v-if="selectedThemeLabel" class="mb-4 flex flex-wrap items-center gap-2">
            <span class="badge bg-[#e8fbf7] text-[#0b8f83]">{{ selectedThemeLabel }}</span>
            <button class="text-sm font-bold text-slate-500 transition hover:text-[#12b8a6] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#12b8a6]" type="button" @click="clearTheme">테마 필터 해제</button>
          </div>

          <div v-if="!loading" class="mb-4 flex flex-wrap items-center justify-between gap-3 text-sm font-bold text-slate-500">
            <span>전체 {{ totalCount }}개 중 {{ stocks.length }}개 표시</span>
            <span v-if="nextPage">스크롤하면 다음 종목을 계속 불러옵니다.</span>
            <span v-else>모든 조건의 종목을 불러왔습니다.</span>
          </div>

          <div v-if="loading" class="panel p-8 text-center font-bold text-slate-500">종목을 불러오는 중입니다.</div>
          <div v-else-if="error" class="panel border-red-200 bg-red-50 p-8 font-bold text-red-700">{{ error }}</div>
          <div v-else-if="!stocks.length" class="panel p-8 text-center font-bold text-slate-500">조건에 맞는 종목이 없습니다.</div>
          <section v-else class="panel overflow-hidden">
            <div class="overflow-x-auto">
              <table class="w-full min-w-[1480px] table-fixed text-left">
                <caption class="sr-only">종합 점수와 세부 축 기준 전체 종목 목록</caption>
                <colgroup>
                  <col class="w-[64px]" />
                  <col class="w-[170px]" />
                  <col class="w-[120px]" />
                  <col class="w-[150px]" />
                  <col class="w-[260px]" />
                  <col class="w-[100px]" />
                  <col class="w-[96px]" />
                  <col class="w-[96px]" />
                  <col class="w-[110px]" />
                  <col />
                </colgroup>
                <thead class="bg-gradient-to-b from-slate-50 to-white text-xs font-bold text-slate-500">
                  <tr>
                    <th class="px-5 py-3 break-keep text-balance">순위</th>
                    <th class="px-4 py-3 break-keep text-balance">종목명</th>
                    <th class="px-4 py-3 break-keep text-balance">종목코드</th>
                    <th class="px-4 py-3 break-keep text-balance">섹터</th>
                    <th class="px-4 py-3 break-keep text-balance">테마</th>
                    <th class="px-4 py-3 break-keep text-balance">
                      <button type="button" class="whitespace-nowrap font-bold transition hover:text-slate-950" :class="sortHeaderClass('composite')" @click="toggleSort('composite')">종합 점수 {{ sortArrow('composite') }}</button>
                    </th>
                    <th class="px-3 py-3 break-keep text-balance">
                      <button type="button" class="whitespace-nowrap font-bold transition hover:text-slate-950" :class="sortHeaderClass('company')" @click="toggleSort('company')">회사 품질 {{ sortArrow('company') }}</button>
                    </th>
                    <th class="px-3 py-3 break-keep text-balance">
                      <button type="button" class="whitespace-nowrap font-bold transition hover:text-slate-950" :class="sortHeaderClass('market')" @click="toggleSort('market')">시장 검증 {{ sortArrow('market') }}</button>
                    </th>
                    <th class="px-3 py-3 break-keep text-balance">
                      <button type="button" class="whitespace-nowrap font-bold transition hover:text-slate-950" :class="sortHeaderClass('timing')" @click="toggleSort('timing')">매수 타이밍 {{ sortArrow('timing') }}</button>
                    </th>
                    <th class="px-5 py-3 break-keep text-balance">핵심 사유</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 text-sm">
                  <tr v-for="(stock, index) in stocks" :key="stock.ticker" class="transition-colors duration-200 hover:bg-[#f3faf8]">
                    <td class="px-5 py-4 font-bold text-[#172033] tabular-nums">{{ index + 1 }}</td>
                    <td class="px-4 py-4">
                      <RouterLink class="whitespace-nowrap font-bold text-[#172033] hover:text-mint" :to="{ name: 'stock-report', params: { ticker: stock.ticker } }">{{ stock.name }}</RouterLink>
                    </td>
                    <td class="px-4 py-4 font-bold text-slate-600 tabular-nums">{{ stock.ticker }}</td>
                    <td class="px-4 py-4 font-bold text-slate-600 break-keep">{{ stock.sector || "-" }}</td>
                    <td class="px-4 py-4">
                      <div class="flex flex-wrap gap-1">
                        <span v-for="theme in stockThemes(stock)" :key="`${stock.ticker}-${theme}`" class="rounded bg-blue-50 px-2 py-1 text-xs font-bold text-blue-700 break-keep">{{ theme }}</span>
                        <span v-if="!stockThemes(stock).length" class="font-bold text-slate-400">-</span>
                      </div>
                    </td>
                    <td class="px-4 py-4">
                      <div class="inline-flex min-w-14 flex-col items-start gap-1">
                        <span class="text-sm font-extrabold leading-none tabular-nums" :class="scoreTextClass(stock.latest_score)">{{ formatScore(stock.latest_score) }}</span>
                        <span class="h-0.5 w-full overflow-hidden rounded-full bg-slate-200">
                          <span class="block h-full rounded-full" :class="scoreLineClass(stock.latest_score)" :style="{ width: `${scorePercent(stock.latest_score)}%` }"></span>
                        </span>
                      </div>
                    </td>
                    <td class="px-3 py-4 font-extrabold tabular-nums text-emerald-700">{{ formatScore(stock.company_score) }}</td>
                    <td class="px-3 py-4 font-extrabold tabular-nums text-blue-700">{{ formatScore(stock.market_validation_score) }}</td>
                    <td class="px-3 py-4 font-extrabold tabular-nums text-amber-700">{{ formatScore(stock.timing_score) }}</td>
                    <td class="px-5 py-4">
                      <div v-if="stock.key_reason" class="flex flex-wrap gap-1.5">
                        <span
                          v-for="(tag, i) in parseReasons(stock.key_reason)"
                          :key="i"
                          class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-bold break-keep"
                          :class="tag.type === 'rs'
                            ? 'bg-teal-50 text-teal-700 ring-1 ring-teal-200'
                            : tag.type === 'signal'
                            ? 'bg-indigo-50 text-indigo-700 ring-1 ring-indigo-200'
                            : 'bg-slate-100 text-slate-600 ring-1 ring-slate-200'"
                        >{{ tag.label }}</span>
                      </div>
                      <span v-else class="font-bold text-slate-400">-</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <div ref="loadMoreSentinel" class="py-8 text-center">
            <p v-if="loadingMore" class="font-bold text-slate-500">다음 종목을 불러오는 중입니다.</p>
            <button v-else-if="nextPage" class="btn-secondary" type="button" @click="loadMore">더 불러오기</button>
            <p v-else-if="stocks.length" class="font-bold text-slate-400">마지막 종목까지 모두 표시했습니다.</p>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from "vue";

import { api } from "../api/client";

const filters = reactive({ q: "", min_score: "", sort: "composite", direction: "desc", theme_group: "", theme: "" });
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
  { name: "성장·첨단", groups: ["AI 인프라", "반도체", "양자컴퓨팅", "사이버보안", "로봇·자동화", "우주·위성"] },
  { name: "에너지·인프라", groups: ["전력 인프라", "이차전지·ESS", "정유·에너지", "유틸리티·가스", "스마트팜·애그테크"] },
  { name: "바이오·헬스케어", groups: ["바이오·헬스케어", "바이오 CDMO", "디지털헬스·AI의료"] },
  { name: "산업재·소재", groups: ["조선·해운", "K-방산", "건설기계·중공업", "건설·건자재", "철강·화학", "산업소재·부품", "제지·포장"] },
  { name: "소비·콘텐츠", groups: ["물류·유통", "K-소비재", "식품·수산", "패션·의류", "생활소비재", "콘텐츠·엔터", "미디어·광고"] },
  { name: "금융·기타", groups: ["금융·밸류업", "리츠·부동산", "IT서비스", "농업·사료"] },
];

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
      return { name: category.name, groups, stockCount: groups.reduce((sum, group) => sum + Number(group.stock_count || 0), 0) };
    })
    .filter((category) => category.groups.length);
  const leftovers = themeGroups.value.filter((group) => !used.has(group.name));
  if (leftovers.length) categories.push({ name: "기타", groups: leftovers, stockCount: leftovers.reduce((sum, group) => sum + Number(group.stock_count || 0), 0) });
  return categories;
});

function requestParams(page) {
  const params = { page };
  if (filters.q) params.q = filters.q;
  if (filters.min_score) params.min_score = filters.min_score;
  if (filters.sort) params.sort = filters.sort;
  if (filters.direction) params.direction = filters.direction;
  if (filters.theme) params.theme = filters.theme;
  if (filters.theme_group) params.theme_group = filters.theme_group;
  return params;
}

function toggleSort(sort) {
  filters.direction = filters.sort === sort && filters.direction === "desc" ? "asc" : "desc";
  filters.sort = sort;
  loadStocks();
}

function sortArrow(sort) {
  if (filters.sort !== sort) return "";
  return filters.direction === "asc" ? "↑" : "↓";
}

function sortHeaderClass(sort) {
  return filters.sort === sort ? "text-slate-950" : "text-slate-500";
}

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
  observer = new IntersectionObserver((entries) => {
    if (entries.some((entry) => entry.isIntersecting)) loadMore();
  }, { rootMargin: "500px 0px" });
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
    for (const category of categorizedThemeGroups.value.slice(0, 2)) expandedCategories[category.name] = true;
    for (const group of categorizedThemeGroups.value.flatMap((category) => category.groups).slice(0, 3)) expandedGroups[group.name] = true;
  } finally {
    themeLoading.value = false;
  }
}

function toggleCategory(categoryName) {
  expandedCategories[categoryName] = !expandedCategories[categoryName];
}

function toggleGroup(group) {
  expandedGroups[group.name] = !expandedGroups[group.name];
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
  if (score >= 70) return "text-mint";
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
  return Math.min(100, Math.max(0, Number(value || 0)));
}

function parseReasons(text) {
  if (!text) return [];
  const tags = text.split("·").map((s) => {
    const t = s.trim();
    if (!t) return null;
    if (/^RS\s*\d+/i.test(t)) return { label: t, type: "rs" };
    if (/52주|신고가|신저가|돌파|급등|급락|급증|이탈/.test(t)) return { label: t, type: "signal" };
    return { label: t, type: "default" };
  }).filter(Boolean);

  function tagOrder(tag) {
    if (tag.type === "rs") return 0;
    if (/52주/.test(tag.label)) return 1;
    if (/거래량/.test(tag.label)) return 2;
    return 3;
  }
  return [...tags].sort((a, b) => tagOrder(a) - tagOrder(b));
}

async function loadMore() {
  if (!nextPage.value || loadingMore.value || loading.value) return;
  loadingMore.value = true;
  try {
    await fetchStocksPage(nextPage.value, true);
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
