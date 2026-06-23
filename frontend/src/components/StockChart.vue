<template>
  <div class="stock-chart-card rounded-lg border border-slate-100 bg-white shadow-sm overflow-hidden">
    <!-- Row 1: Chart Title + Data Timestamp -->
    <div class="flex items-center justify-between gap-4 border-b border-slate-100 px-5 py-3">
      <div class="flex items-center gap-2">
        <h3 class="text-sm font-extrabold text-slate-900">가격 차트 · 일봉</h3>
        <span class="text-[11px] font-bold text-slate-400">pykrx 일봉 기준</span>
      </div>
      <div class="flex items-center gap-2">
        <span class="text-[11px] font-bold text-slate-400 tabular-nums">
          {{ latestDateLabel }}
        </span>
        <button
          type="button"
          class="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-bold text-slate-500 transition hover:border-slate-300 hover:text-slate-700"
          @click="resetChart"
        >
          ↺ 초기화
        </button>
      </div>
    </div>

    <!-- Row 2: Chart Type + Period Selectors -->
    <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-50 bg-slate-50/30 px-5 py-2.5">
      <div class="flex flex-wrap items-center gap-3">
        <!-- Chart Type Toggle -->
        <div class="flex rounded-lg border border-slate-200 bg-white p-0.5">
          <button
            type="button"
            class="chart-toggle-btn"
            :class="chartType === 'candle' ? 'chart-toggle-btn--active' : ''"
            @click="setChartType('candle')"
          >
            캔들
          </button>
          <button
            type="button"
            class="chart-toggle-btn"
            :class="chartType === 'line' ? 'chart-toggle-btn--active' : ''"
            @click="setChartType('line')"
          >
            라인
          </button>
        </div>

        <!-- Period Selectors -->
        <div class="flex rounded-lg border border-slate-200 bg-white p-0.5">
          <button
            v-for="p in periods"
            :key="p.value"
            type="button"
            class="chart-toggle-btn"
            :class="activePeriod === p.value ? 'chart-toggle-btn--active' : ''"
            @click="changePeriod(p.value)"
          >
            {{ p.label }}
          </button>
        </div>
      </div>

      <!-- Indicator Chips -->
      <div class="flex flex-wrap items-center gap-1.5">
        <button
          v-for="indicator in indicatorToggles"
          :key="indicator.key"
          type="button"
          class="indicator-chip"
          :class="indicatorStates[indicator.key] ? 'indicator-chip--active' : ''"
          :style="indicatorStates[indicator.key] ? `--chip-color: ${indicator.color}` : ''"
          :aria-pressed="indicatorStates[indicator.key]"
          @click="toggleIndicator(indicator.key)"
        >
          <span
            class="inline-block w-3 h-0.5 rounded-full shrink-0"
            :style="{ background: indicatorStates[indicator.key] ? indicator.color : '#94a3b8' }"
          ></span>
          {{ indicator.label }}
        </button>
      </div>
    </div>

    <!-- EMA Legend (top of chart) -->
    <div v-if="hasAnyEmaVisible" class="flex flex-wrap items-center gap-4 px-5 py-2 text-[11px] font-bold tabular-nums">
      <span v-if="indicatorStates.ema20" class="flex items-center gap-1.5">
        <span class="inline-block w-2.5 h-0.5 rounded-full" style="background: #12b8a6"></span>
        <span class="text-slate-400">EMA20</span>
        <span class="text-slate-700">{{ formatAxisPrice(legendData.ema20) }}</span>
      </span>
      <span v-if="indicatorStates.ema50" class="flex items-center gap-1.5">
        <span class="inline-block w-2.5 h-0.5 rounded-full" style="background: #f59e0b"></span>
        <span class="text-slate-400">EMA50</span>
        <span class="text-slate-700">{{ formatAxisPrice(legendData.ema50) }}</span>
      </span>
      <span v-if="indicatorStates.ema200" class="flex items-center gap-1.5">
        <span class="inline-block w-2.5 h-0.5 rounded-full" style="background: #8b5cf6"></span>
        <span class="text-slate-400">EMA200</span>
        <span class="text-slate-700">{{ formatAxisPrice(legendData.ema200) }}</span>
      </span>
    </div>

    <!-- Chart Render Area -->
    <div class="relative">
      <div ref="chartContainerRef" class="chart-area w-full"></div>
    </div>

    <!-- OHLC Info Panel (2 lines, compressed) -->
    <div class="border-t border-slate-100 px-5 py-3">
      <!-- Line 1: Date + Daily Change -->
      <div class="flex items-center justify-between gap-4">
        <span class="text-xs font-bold text-slate-500 tabular-nums">
          {{ hoveredData.date || '-' }}
        </span>
        <span
          v-if="hoveredData.change !== null"
          class="text-xs font-extrabold tabular-nums"
          :class="changeColorClass"
        >
          {{ signedPrice(hoveredData.change) }}원 ({{ signedPercent(hoveredData.changePercent) }})
        </span>
      </div>
      <!-- Line 2: OHLCV -->
      <div class="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1 tabular-nums">
        <span class="text-xs">
          <span class="font-bold text-slate-400">시</span>
          <span class="ml-1 font-extrabold text-slate-800">{{ formatAxisPrice(hoveredData.open) }}</span>
        </span>
        <span class="text-xs">
          <span class="font-bold text-slate-400">고</span>
          <span class="ml-1 font-extrabold text-slate-800">{{ formatAxisPrice(hoveredData.high) }}</span>
        </span>
        <span class="text-xs">
          <span class="font-bold text-slate-400">저</span>
          <span class="ml-1 font-extrabold text-slate-800">{{ formatAxisPrice(hoveredData.low) }}</span>
        </span>
        <span class="text-xs">
          <span class="font-bold text-slate-400">종</span>
          <span class="ml-1 font-extrabold" :class="changeColorClass">{{ formatAxisPrice(hoveredData.close) }}</span>
        </span>
        <span class="text-xs">
          <span class="font-bold text-slate-400">거래량</span>
          <span class="ml-1 font-extrabold text-slate-600">{{ hoveredData.volume ? formatVolumeCompact(hoveredData.volume) + ' 주' : '-' }}</span>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { createChart, CandlestickSeries, LineSeries, HistogramSeries } from "lightweight-charts";

const props = defineProps({
  priceSeries: {
    type: Array,
    required: true,
    default: () => [],
  },
});

// --- Constants ---
const COLORS = {
  priceUp: "#ef4444",
  priceDown: "#3b82f6",
  ema20: "#12b8a6",
  ema50: "#f59e0b",
  ema200: "#8b5cf6",
  priceLine: "#0f172a",
  gridHorz: "#f1f5f9",
  gridVert: "#f8fafc",
  border: "#f1f5f9",
  bg: "#ffffff",
  text: "#334155",
  volumeUp: "rgba(239,68,68,0.55)",
  volumeDown: "rgba(59,130,246,0.55)",
};

// --- Refs ---
const chartContainerRef = ref(null);
const chartType = ref("candle");
const activePeriod = ref("1y");

const periods = [
  { label: "1개월", value: "1m" },
  { label: "3개월", value: "3m" },
  { label: "1년", value: "1y" },
  { label: "3년", value: "3y" },
];

const indicatorToggles = [
  { key: "ema20", label: "EMA20", color: COLORS.ema20 },
  { key: "ema50", label: "EMA50", color: COLORS.ema50 },
  { key: "ema200", label: "EMA200", color: COLORS.ema200 },
  { key: "volume", label: "거래량", color: "#64748b" },
];

const indicatorStates = reactive({
  ema20: true,
  ema50: true,
  ema200: true,
  volume: true,
});

// Hover state
const hoveredData = reactive({
  date: "",
  open: null,
  high: null,
  low: null,
  close: null,
  volume: null,
  change: null,
  changePercent: null,
});

// Legend state (EMA values for top legend)
const legendData = reactive({
  ema20: null,
  ema50: null,
  ema200: null,
});

// Lightweight Charts instances
let chart = null;
let candleSeries = null;
let lineSeries = null;
let volumeSeries = null;
let ema20Series = null;
let ema50Series = null;
let ema200Series = null;
let resizeObserver = null;

// --- Korean Number Formatters ---
const krNumberFormat = new Intl.NumberFormat("ko-KR", { maximumFractionDigits: 0 });

function formatAxisPrice(value) {
  if (value === null || value === undefined) return "-";
  return krNumberFormat.format(Math.round(Number(value)));
}

function priceFormatter(price) {
  return krNumberFormat.format(Math.round(price));
}

function formatVolumeAxis(vol) {
  const v = Number(vol);
  if (v >= 100000000) return `${(v / 100000000).toFixed(1).replace(".0", "")}억`;
  if (v >= 10000) return `${(v / 10000).toFixed(0)}만`;
  return krNumberFormat.format(v);
}

function formatVolumeCompact(vol) {
  const v = Number(vol || 0);
  if (v >= 100000000) return `${(v / 100000000).toFixed(1).replace(".0", "")}억`;
  if (v >= 10000) return `${Math.round(v / 10000)}만`;
  return krNumberFormat.format(v);
}

// --- Date Helpers ---
function normalizeDate(value) {
  if (!value) return "";
  const text = String(value);
  if (/^\d{4}-\d{2}-\d{2}/.test(text)) return text.slice(0, 10);
  if (/^\d{8}$/.test(text)) {
    return `${text.slice(0, 4)}-${text.slice(4, 6)}-${text.slice(6, 8)}`;
  }
  return text;
}

function formatDateKoreanFull(dateStr) {
  if (!dateStr) return "";
  const parts = String(dateStr).split("-");
  if (parts.length === 3) {
    return `${parts[0]}년 ${Number(parts[1])}월 ${Number(parts[2])}일`;
  }
  return dateStr;
}

function formatDateShort(dateStr) {
  if (!dateStr) return "-";
  const parts = String(dateStr).split("-");
  if (parts.length === 3) {
    return `${Number(parts[1])}월 ${Number(parts[2])}일`;
  }
  return dateStr;
}

// tickMarkFormatter for X axis
function tickMarkFormatter(time, tickMarkType, locale) {
  const parts = String(time).split("-");
  if (parts.length !== 3) return time;
  const year = parts[0];
  const month = Number(parts[1]);
  const day = Number(parts[2]);

  // tickMarkType: 0=Year, 1=Month, 2=DayOfMonth, 3=Time, 4=TimeWithSeconds
  if (tickMarkType === 0) return `${year}년`;
  if (tickMarkType === 1) return `${month}월`;
  if (tickMarkType === 2) return `${day}일`;
  return `${month}/${day}`;
}

// --- Sign helpers ---
function signedPrice(value) {
  if (value === null || value === undefined) return "";
  const n = Number(value);
  const sign = n > 0 ? "+" : "";
  return `${sign}${krNumberFormat.format(n)}`;
}

function signedPercent(value) {
  if (value === null || value === undefined) return "";
  const n = Number(value);
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(2)}%`;
}

// --- Computed ---
const hasAnyEmaVisible = computed(() => {
  return indicatorStates.ema20 || indicatorStates.ema50 || indicatorStates.ema200;
});

const changeColorClass = computed(() => {
  const change = hoveredData.change;
  if (change === null || change === undefined) return "text-slate-500";
  if (change > 0) return "text-red-600";
  if (change < 0) return "text-blue-600";
  return "text-slate-500";
});

const latestDateLabel = computed(() => {
  if (!props.priceSeries || !props.priceSeries.length) return "";
  const latest = props.priceSeries[props.priceSeries.length - 1];
  const dateStr = normalizeDate(latest.date || latest.trade_date || latest.base_date);
  return formatDateShort(dateStr) + " 기준";
});

// --- Chart Logic ---
function findPrevClose(dateStr) {
  if (!props.priceSeries || !props.priceSeries.length) return null;
  const idx = props.priceSeries.findIndex(
    (item) => normalizeDate(item.date || item.trade_date || item.base_date) === dateStr
  );
  if (idx > 0) return Number(props.priceSeries[idx - 1].close_price);
  return null;
}

function findEmaValues(dateStr) {
  if (!props.priceSeries || !props.priceSeries.length) return { ema20: null, ema50: null, ema200: null };
  const point = props.priceSeries.find(
    (item) => normalizeDate(item.date || item.trade_date || item.base_date) === dateStr
  );
  if (!point) return { ema20: null, ema50: null, ema200: null };
  return {
    ema20: point.ema20 !== null && point.ema20 !== undefined ? Number(point.ema20) : null,
    ema50: point.ema50 !== null && point.ema50 !== undefined ? Number(point.ema50) : null,
    ema200: point.ema200 !== null && point.ema200 !== undefined ? Number(point.ema200) : null,
  };
}

function setHoveredDataToLatest() {
  if (!props.priceSeries || !props.priceSeries.length) return;
  const latest = props.priceSeries[props.priceSeries.length - 1];
  const dateStr = normalizeDate(latest.date || latest.trade_date || latest.base_date);
  hoveredData.date = formatDateKoreanFull(dateStr);
  hoveredData.open = latest.open_price;
  hoveredData.high = latest.high_price;
  hoveredData.low = latest.low_price;
  hoveredData.close = latest.close_price;
  hoveredData.volume = latest.volume;

  const prevClose = findPrevClose(dateStr);
  if (prevClose !== null) {
    hoveredData.change = Number(latest.close_price) - prevClose;
    hoveredData.changePercent = (hoveredData.change / prevClose) * 100;
  } else {
    hoveredData.change = null;
    hoveredData.changePercent = null;
  }

  const emas = findEmaValues(dateStr);
  legendData.ema20 = emas.ema20;
  legendData.ema50 = emas.ema50;
  legendData.ema200 = emas.ema200;
}

const setChartType = (type) => {
  if (chartType.value === type) return;
  chartType.value = type;
  if (!chart) return;

  if (type === "candle") {
    if (lineSeries) chart.removeSeries(lineSeries);
    lineSeries = null;
    createCandleSeries();
  } else {
    if (candleSeries) chart.removeSeries(candleSeries);
    candleSeries = null;
    createLineSeries();
  }
};

const createCandleSeries = () => {
  if (!chart || candleSeries) return;
  candleSeries = chart.addSeries(CandlestickSeries, {
    upColor: COLORS.priceUp,
    downColor: COLORS.priceDown,
    borderUpColor: COLORS.priceUp,
    borderDownColor: COLORS.priceDown,
    wickUpColor: COLORS.priceUp,
    wickDownColor: COLORS.priceDown,
    lastValueVisible: true,
    priceLineVisible: true,
    priceFormat: {
      type: "price",
      precision: 0,
      minMove: 1,
    },
  });

  const data = props.priceSeries.map((item) => ({
    time: normalizeDate(item.date || item.trade_date || item.base_date),
    open: Number(item.open_price),
    high: Number(item.high_price),
    low: Number(item.low_price),
    close: Number(item.close_price),
  }));
  candleSeries.setData(data);
};

const createLineSeries = () => {
  if (!chart || lineSeries) return;
  lineSeries = chart.addSeries(LineSeries, {
    color: COLORS.priceLine,
    lineWidth: 2,
    lastValueVisible: true,
    priceLineVisible: true,
    priceFormat: {
      type: "price",
      precision: 0,
      minMove: 1,
    },
  });

  const data = props.priceSeries.map((item) => ({
    time: normalizeDate(item.date || item.trade_date || item.base_date),
    value: Number(item.close_price),
  }));
  lineSeries.setData(data);
};

const createEmaSeries = (key) => {
  if (!chart) return;

  const config = {
    ema20: { color: COLORS.ema20, title: "EMA20", field: "ema20", ref: () => ema20Series, set: (s) => { ema20Series = s; } },
    ema50: { color: COLORS.ema50, title: "EMA50", field: "ema50", ref: () => ema50Series, set: (s) => { ema50Series = s; } },
    ema200: { color: COLORS.ema200, title: "EMA200", field: "ema200", ref: () => ema200Series, set: (s) => { ema200Series = s; } },
  }[key];

  if (!config) return;
  if (config.ref()) return; // already exists

  const series = chart.addSeries(LineSeries, {
    color: config.color,
    lineWidth: 1.5,
    lastValueVisible: false,
    priceLineVisible: false,
    crosshairMarkerVisible: false,
    priceFormat: {
      type: "price",
      precision: 0,
      minMove: 1,
    },
  });

  const data = props.priceSeries
    .filter((item) => item[config.field] !== null && item[config.field] !== undefined)
    .map((item) => ({
      time: normalizeDate(item.date || item.trade_date || item.base_date),
      value: Number(item[config.field]),
    }));
  series.setData(data);
  config.set(series);
};

const toggleIndicator = (key) => {
  if (!chart) return;
  const isVisible = indicatorStates[key];

  if (key === "volume") {
    if (volumeSeries) volumeSeries.applyOptions({ visible: isVisible });
  } else {
    const seriesMap = { ema20: ema20Series, ema50: ema50Series, ema200: ema200Series };
    const current = seriesMap[key];
    if (current) {
      current.applyOptions({ visible: isVisible });
    } else if (isVisible) {
      createEmaSeries(key);
    }
  }
};

const changePeriod = (value) => {
  activePeriod.value = value;
  if (!chart || !props.priceSeries?.length) return;

  const series = props.priceSeries;
  const lastIndex = series.length - 1;
  const lastDateStr = normalizeDate(series[lastIndex].date || series[lastIndex].trade_date || series[lastIndex].base_date);
  const lastDate = new Date(lastDateStr);

  let months = 1;
  if (value === "1m") months = 1;
  else if (value === "3m") months = 3;
  else if (value === "1y") months = 12;
  else if (value === "3y") months = 36;

  const startDate = new Date(lastDate);
  startDate.setMonth(startDate.getMonth() - months);
  const startDateStr = startDate.toISOString().split("T")[0];

  chart.timeScale().setVisibleRange({
    from: startDateStr,
    to: lastDateStr,
  });
};

const resetChart = () => {
  if (!chart) return;
  changePeriod(activePeriod.value);
  setHoveredDataToLatest();
};

const renderChart = () => {
  if (!chartContainerRef.value || !props.priceSeries.length) return;

  // Cleanup existing chart
  if (chart) {
    chart.remove();
    chart = null;
    candleSeries = null;
    lineSeries = null;
    volumeSeries = null;
    ema20Series = null;
    ema50Series = null;
    ema200Series = null;
  }

  chart = createChart(chartContainerRef.value, {
    autoSize: true,
    layout: {
      background: { color: COLORS.bg },
      textColor: COLORS.text,
      fontFamily: "SUIT, -apple-system, BlinkMacSystemFont, sans-serif",
      panes: {
        separatorColor: "#e2e8f0",
        enableResize: true,
      },
    },
    grid: {
      vertLines: { color: COLORS.gridVert },
      horzLines: { color: COLORS.gridHorz },
    },
    crosshair: {
      mode: 0, // Normal
      vertLine: {
        labelBackgroundColor: "#334155",
      },
      horzLine: {
        labelBackgroundColor: "#334155",
      },
    },
    rightPriceScale: {
      borderColor: COLORS.border,
      autoScale: true,
    },
    timeScale: {
      borderColor: COLORS.border,
      rightOffset: 8,
      barSpacing: 6,
      minBarSpacing: 2,
      tickMarkFormatter: tickMarkFormatter,
    },
    localization: {
      locale: "ko-KR",
      priceFormatter: priceFormatter,
    },
  });

  // Create primary chart type (pane 0 — default)
  if (chartType.value === "candle") {
    createCandleSeries();
  } else {
    createLineSeries();
  }

  // Create EMA series (pane 0 — overlay)
  if (indicatorStates.ema20) createEmaSeries("ema20");
  if (indicatorStates.ema50) createEmaSeries("ema50");
  if (indicatorStates.ema200) createEmaSeries("ema200");

  // Create Volume series in separate pane (pane 1)
  volumeSeries = chart.addSeries(HistogramSeries, {
    lastValueVisible: false,
    priceLineVisible: false,
    priceFormat: {
      type: "volume",
      formatter: formatVolumeAxis,
    },
  }, 1); // paneIndex = 1

  const volumeData = props.priceSeries.map((item, index) => {
    const isUp = index > 0 && Number(item.close_price) >= Number(props.priceSeries[index - 1].close_price);
    return {
      time: normalizeDate(item.date || item.trade_date || item.base_date),
      value: Number(item.volume),
      color: isUp ? COLORS.volumeUp : COLORS.volumeDown,
    };
  });
  volumeSeries.setData(volumeData);

  // Set volume pane height
  try {
    const panes = chart.panes();
    if (panes && panes.length > 1) {
      panes[1].setHeight(80);
    }
  } catch (e) {
    // pane API may not be available in all builds
  }

  if (!indicatorStates.volume) {
    volumeSeries.applyOptions({ visible: false });
  }

  // Default display values
  setHoveredDataToLatest();

  // Crosshair move handler
  chart.subscribeCrosshairMove((param) => {
    if (
      !param ||
      !param.time ||
      param.point === undefined ||
      param.point.x < 0 ||
      param.point.y < 0
    ) {
      setHoveredDataToLatest();
      return;
    }

    const dateStr = param.time;
    hoveredData.date = formatDateKoreanFull(dateStr);

    // Price data
    const activeSrs = candleSeries || lineSeries;
    const priceData = param.seriesData.get(activeSrs);
    if (priceData) {
      if (chartType.value === "candle") {
        hoveredData.open = priceData.open;
        hoveredData.high = priceData.high;
        hoveredData.low = priceData.low;
        hoveredData.close = priceData.close;
      } else {
        hoveredData.close = priceData.value;
        const rawPoint = props.priceSeries.find(
          (item) => normalizeDate(item.date || item.trade_date || item.base_date) === dateStr
        );
        if (rawPoint) {
          hoveredData.open = rawPoint.open_price;
          hoveredData.high = rawPoint.high_price;
          hoveredData.low = rawPoint.low_price;
        }
      }
    }

    // Volume data
    const volData = param.seriesData.get(volumeSeries);
    hoveredData.volume = volData ? volData.value : null;

    // Daily change calculation
    const prevClose = findPrevClose(dateStr);
    if (prevClose !== null && hoveredData.close !== null) {
      hoveredData.change = Number(hoveredData.close) - prevClose;
      hoveredData.changePercent = (hoveredData.change / prevClose) * 100;
    } else {
      hoveredData.change = null;
      hoveredData.changePercent = null;
    }

    // EMA legend update
    const emas = findEmaValues(dateStr);
    legendData.ema20 = emas.ema20;
    legendData.ema50 = emas.ema50;
    legendData.ema200 = emas.ema200;
  });

  // Apply default zoom period
  changePeriod(activePeriod.value);
};

// Handle responsive resizing
const setupResizeObserver = () => {
  if (!chartContainerRef.value) return;
  resizeObserver = new ResizeObserver((entries) => {
    if (entries.length === 0 || !chart) return;
    const { width, height } = entries[0].contentRect;
    chart.resize(width, height);
  });
  resizeObserver.observe(chartContainerRef.value);
};

// Watch for priceSeries data loading/change
watch(
  () => props.priceSeries,
  () => {
    if (props.priceSeries && props.priceSeries.length) {
      renderChart();
    }
  },
  { deep: true }
);

onMounted(() => {
  renderChart();
  setupResizeObserver();
});

onBeforeUnmount(() => {
  if (resizeObserver) {
    resizeObserver.disconnect();
    resizeObserver = null;
  }
  if (chart) {
    chart.remove();
    chart = null;
  }
});
</script>

<style scoped>
.stock-chart-card {
  transition: all 0.2s ease-in-out;
}

.chart-area {
  height: 420px;
}

/* Toggle buttons (chart type & period) */
.chart-toggle-btn {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 11.5px;
  font-weight: 700;
  color: #64748b;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.chart-toggle-btn:hover {
  color: #1e293b;
  background: #f1f5f9;
}

.chart-toggle-btn--active {
  color: #ffffff;
  background: #12b8a6;
  box-shadow: 0 1px 2px rgba(18, 184, 166, 0.25);
}

.chart-toggle-btn--active:hover {
  background: #0d8f82;
  color: #ffffff;
}

/* Indicator chips */
.indicator-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  color: #94a3b8;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.indicator-chip:hover {
  border-color: #cbd5e1;
  color: #64748b;
}

.indicator-chip--active {
  color: #1e293b;
  background: color-mix(in srgb, var(--chip-color, #12b8a6) 8%, white);
  border-color: color-mix(in srgb, var(--chip-color, #12b8a6) 35%, transparent);
}

.indicator-chip--active:hover {
  background: color-mix(in srgb, var(--chip-color, #12b8a6) 14%, white);
}

/* Responsive */
@media (max-width: 640px) {
  .chart-area {
    height: 320px;
  }
}
</style>
