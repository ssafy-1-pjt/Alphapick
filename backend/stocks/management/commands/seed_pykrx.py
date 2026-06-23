import math
import re
import time
import warnings
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from html import unescape
from html.parser import HTMLParser

import numpy as np
import pandas as pd
import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

warnings.filterwarnings("ignore", message="pkg_resources is deprecated")
from pykrx import stock as krx_stock  # noqa: E402

from stocks.models import (
    AICommentCache,
    FinancialMetric,
    PortfolioItem,
    PortfolioRun,
    PriceDaily,
    ScoreSnapshot,
    Stock,
    Watchlist,
)
from stocks.services import ensure_portfolio_run


KOSPI_CORP_LIST_URL = "https://kind.krx.co.kr/corpgeneral/corpList.do?method=download&marketType=stockMkt"
WISE_REPORT_URL = "https://navercomp.wisereport.co.kr/v2/company/c1010001.aspx"
WISE_REPORT_AJAX_URL = "https://navercomp.wisereport.co.kr/v2/company/ajax/cF1001.aspx"
DEFAULT_MIN_TRADING_VALUE = 5_000_000_000


class CorpListParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_cell = False
        self.cell = []
        self.row = []
        self.rows = []

    def handle_starttag(self, tag, attrs):
        if tag in {"td", "th"}:
            self.in_cell = True
            self.cell = []

    def handle_data(self, data):
        if self.in_cell:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self.in_cell:
            value = re.sub(r"\s+", " ", "".join(self.cell)).strip()
            self.row.append(value)
            self.in_cell = False
        elif tag == "tr" and self.row:
            self.rows.append(self.row)
            self.row = []


@dataclass
class TickerMeta:
    ticker: str
    name: str
    sector: str
    industry: str


@dataclass
class CollectedStock:
    meta: TickerMeta
    prices: pd.DataFrame
    metrics: dict


def clamp(value, low=0, high=100):
    if value is None or pd.isna(value) or math.isinf(value):
        return low
    return max(low, min(high, float(value)))


def parse_number(value):
    if value is None:
        return None
    value = unescape(str(value)).replace(",", "").replace("%", "").strip()
    if value in {"", "N/A", "-", "nan"}:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_int(value):
    number = parse_number(value)
    return int(number) if number is not None else None


def to_yyyymmdd(value):
    if isinstance(value, str):
        return value.replace("-", "")
    return value.strftime("%Y%m%d")


def parse_base_date(value):
    if value:
        return datetime.strptime(value.replace("-", ""), "%Y%m%d").date()
    return date.today()


def fetch_kind_kospi_list():
    response = requests.get(KOSPI_CORP_LIST_URL, timeout=30)
    response.raise_for_status()
    response.encoding = "euc-kr"

    parser = CorpListParser()
    parser.feed(response.text)
    if len(parser.rows) < 2:
        raise CommandError("KIND KOSPI corp list returned no rows.")

    result = []
    for row in parser.rows[1:]:
        if len(row) < 4:
            continue
        ticker = row[2].zfill(6)
        result.append(
            TickerMeta(
                ticker=ticker,
                name=row[0],
                sector=row[3] or "KOSPI",
                industry=row[4] if len(row) > 4 else "",
            )
        )
    return result


def fetch_pykrx_ticker_list(base_date, market):
    tickers = krx_stock.get_market_ticker_list(to_yyyymmdd(base_date), market=market)
    result = []
    for ticker in tickers:
        name = krx_stock.get_market_ticker_name(ticker) or ticker
        result.append(TickerMeta(ticker=ticker, name=name, sector=market, industry=""))
    return result


def extract_summary_number(text, label):
    pattern = rf"{re.escape(label)}\s*<b class=\"num\">([^<]+)</b>"
    match = re.search(pattern, text)
    return parse_number(match.group(1)) if match else None


def extract_latest_finance_row_value(table_html, row_label):
    match = re.search(
        rf"<th[^>]*>\s*{re.escape(row_label)}\s*</th>(?P<cells>.*?)</tr>",
        table_html,
        re.S,
    )
    if not match:
        return None
    values = [parse_number(value) for value in re.findall(r'title="([^"]+)"', match.group("cells"))]
    values = [value for value in values if value is not None]
    return values[-1] if values else None


def fetch_naver_financial_snapshot(ticker):
    """Fetch consensus/fundamental display values from Naver CompanyGuide."""
    headers = {"User-Agent": "Mozilla/5.0"}
    result = {
        "target_price": None,
        "consensus_score": None,
        "consensus_label": "",
        "consensus_count": None,
        "per": None,
        "pbr": None,
        "roe": None,
        "eps": None,
        "bps": None,
        "dividend_yield": None,
        "operating_margin": None,
        "debt_ratio": None,
        "source": "네이버 금융/FnGuide",
    }

    try:
        response = requests.get(WISE_REPORT_URL, params={"cmp_cd": ticker}, headers=headers, timeout=12)
        response.raise_for_status()
        response.encoding = "utf-8"
        text = response.text
    except Exception:
        return result

    result["eps"] = extract_summary_number(text, "EPS")
    result["bps"] = extract_summary_number(text, "BPS")
    result["per"] = extract_summary_number(text, "PER")
    result["pbr"] = extract_summary_number(text, "PBR")
    result["dividend_yield"] = extract_summary_number(text, "현금배당수익률")

    consensus = re.search(
        r'id="cTB15".*?<span id="pointerVal"[^>]*>(?P<opinion>[0-9.]+)</span>.*?'
        r'<td class="noline-bottom line-right center">(?P<target>[0-9,]+)</td>.*?'
        r'<td class="noline-bottom center">(?P<count>[0-9]+)</td>',
        text,
        re.S,
    )
    if consensus:
        opinion = parse_number(consensus.group("opinion"))
        result["consensus_score"] = opinion
        result["target_price"] = parse_int(consensus.group("target"))
        result["consensus_count"] = parse_int(consensus.group("count"))
        if opinion is not None:
            if opinion >= 4.5:
                result["consensus_label"] = "강력매수"
            elif opinion >= 3.8:
                result["consensus_label"] = "매수"
            elif opinion >= 3:
                result["consensus_label"] = "중립"
            else:
                result["consensus_label"] = "보수적"

    encparam_match = re.search(r"encparam:\s*'([^']+)'", text)
    if encparam_match:
        try:
            ajax_response = requests.get(
                WISE_REPORT_AJAX_URL,
                params={
                    "cmp_cd": ticker,
                    "fin_typ": "0",
                    "freq_typ": "A",
                    "extY": "0",
                    "extQ": "0",
                    "encparam": encparam_match.group(1),
                    "id": "aFVlanREZS",
                },
                headers={**headers, "Referer": f"{WISE_REPORT_URL}?cmp_cd={ticker}"},
                timeout=12,
            )
            ajax_response.raise_for_status()
            ajax_response.encoding = "utf-8"
            table = ajax_response.text
            result["roe"] = extract_latest_finance_row_value(table, "ROE(%)")
            result["operating_margin"] = extract_latest_finance_row_value(table, "영업이익률")
            result["debt_ratio"] = extract_latest_finance_row_value(table, "부채비율")
        except Exception:
            pass

    return result


def resolve_tickers(options):
    if options["tickers"]:
        return [
            TickerMeta(ticker=ticker.strip().zfill(6), name=ticker.strip().zfill(6), sector=options["market"], industry="")
            for ticker in options["tickers"].split(",")
            if ticker.strip()
        ]

    if options["tickers_file"]:
        rows = []
        frame = pd.read_csv(options["tickers_file"], encoding="utf-8-sig", dtype=str).fillna("")
        for _, row in frame.iterrows():
            ticker = str(row.get("ticker") or row.get("종목코드") or row.get("code") or "").strip().zfill(6)
            if not ticker or ticker == "000nan":
                continue
            name = str(row.get("name") or row.get("회사명") or ticker).strip()
            if name.zfill(6) == ticker:
                name = ticker
            rows.append(
                TickerMeta(
                    ticker=ticker,
                    name=name,
                    sector=str(row.get("sector") or row.get("업종") or options["market"]).strip(),
                    industry=str(row.get("industry") or row.get("주요제품") or "").strip(),
                )
            )
        return rows

    try:
        pykrx_rows = fetch_pykrx_ticker_list(options["base_date"], options["market"])
        if pykrx_rows:
            return pykrx_rows
    except Exception:
        pykrx_rows = []

    if options["market"] == "KOSPI":
        return fetch_kind_kospi_list()

    raise CommandError(
        "pykrx ticker list is empty. Pass --tickers-file or --tickers for this market."
    )


def normalize_ohlcv(raw):
    if raw.empty or len(raw.columns) < 5:
        return pd.DataFrame()

    frame = raw.copy()
    frame = frame.iloc[:, :5]
    frame.columns = ["open", "high", "low", "close", "volume"]
    frame = frame.dropna()
    for column in frame.columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna()
    frame = frame[(frame["open"] > 0) & (frame["high"] > 0) & (frame["low"] > 0) & (frame["close"] > 0)]
    frame.index = pd.to_datetime(frame.index)
    return frame


def rsi(series, period=14):
    diff = series.diff()
    gain = diff.clip(lower=0).rolling(period).mean()
    loss = (-diff.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    value = 100 - (100 / (1 + rs))
    return value.fillna(50)


def hurst_exponent(series):
    values = np.asarray(series.dropna().tail(180), dtype=float)
    if len(values) < 80 or np.std(values) == 0:
        return 0.5
    lags = range(2, 20)
    tau = [np.std(values[lag:] - values[:-lag]) for lag in lags]
    tau = np.asarray([item for item in tau if item > 0], dtype=float)
    if len(tau) < 5:
        return 0.5
    slope = np.polyfit(np.log(list(lags)[: len(tau)]), np.log(tau), 1)[0]
    return clamp(slope * 2, 0, 1)


def trading_value_score(value):
    if value >= 50_000_000_000:
        return 100
    if value >= 20_000_000_000:
        return 88
    if value >= 10_000_000_000:
        return 78
    if value >= 5_000_000_000:
        return 66
    if value >= 1_000_000_000:
        return 45
    return 20


def score_from_return(value, scale=1.0):
    return clamp(50 + value * scale)


def signal_for(score, volume_surge, fail_safe):
    if fail_safe:
        return "관찰 필요 - 데이터 신뢰도 낮음"
    if score >= 80:
        return "강한 주도주"
    if score >= 74:
        return "주도주"
    if score >= 70:
        return "추천 후보 - 관찰 매수권"
    if score >= 60:
        return "중립 - 보유 관찰"
    if score >= 45:
        return "주의 - 비중 축소"
    return "부진 - 회피"


def pct_change(close, days):
    if len(close) <= days:
        return 0
    start = close.iloc[-days - 1]
    if not start:
        return 0
    return (close.iloc[-1] / start - 1) * 100


def build_price_frame(raw):
    frame = normalize_ohlcv(raw)
    if frame.empty:
        return frame

    close = frame["close"]
    volume = frame["volume"]
    frame["ema20"] = close.ewm(span=20, adjust=False).mean()
    frame["ema50"] = close.ewm(span=50, adjust=False).mean()
    frame["ema200"] = close.ewm(span=200, adjust=False).mean()
    ma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    frame["bb_upper"] = ma20 + std20 * 2
    frame["bb_lower"] = ma20 - std20 * 2
    direction = np.sign(close.diff()).fillna(0)
    frame["obv"] = (direction * volume).cumsum()
    return frame


def collect_metrics(frame, min_trading_value):
    close = frame["close"]
    high = frame["high"]
    volume = frame["volume"]
    daily_return = close.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
    current_price = float(close.iloc[-1])
    high_52w = float(high.tail(252).max())
    distance_to_high = (high_52w - current_price) / high_52w * 100 if high_52w else 100
    avg_trading_value_20 = float((close * volume).tail(20).mean())
    avg_volume_20 = float(volume.tail(20).mean()) or 1
    volume_ratio = float(volume.iloc[-1] / avg_volume_20)
    z_std = close.tail(20).std()
    z_score = float((current_price - close.tail(20).mean()) / z_std) if z_std else 0
    drawdown = (close / close.cummax() - 1).min() * 100
    volatility = daily_return.tail(120).std() * math.sqrt(252) * 100 if len(daily_return) else 0
    obv = frame["obv"]
    obv_trend = pct_change(obv.abs() + 1, min(60, max(1, len(obv) - 2)))
    rsi_value = float(rsi(close).iloc[-1])

    return {
        "current_price": current_price,
        "return_21": pct_change(close, 21),
        "return_63": pct_change(close, 63),
        "return_126": pct_change(close, 126),
        "return_252": pct_change(close, min(252, max(1, len(close) - 2))),
        "high_52w": high_52w,
        "distance_to_high": distance_to_high,
        "avg_trading_value_20": avg_trading_value_20,
        "volume_ratio": volume_ratio,
        "volume_surge": volume_ratio >= 2.0,
        "z_score": z_score,
        "mdd": float(drawdown),
        "volatility": float(volatility or 0),
        "obv_trend": float(obv_trend or 0),
        "rsi": rsi_value,
        "hurst": hurst_exponent(close),
        "above_ema20": current_price >= float(frame["ema20"].iloc[-1]),
        "above_ema50": current_price >= float(frame["ema50"].iloc[-1]),
        "above_ema200": current_price >= float(frame["ema200"].iloc[-1]) if not pd.isna(frame["ema200"].iloc[-1]) else False,
        "is_new_high": distance_to_high <= 3.0,
        "low_liquidity": avg_trading_value_20 < min_trading_value,
        "history_len": len(frame),
    }


def percentile_rank(value, values):
    finite = sorted(item for item in values if item is not None and not pd.isna(item))
    if not finite:
        return 50
    below = sum(1 for item in finite if item <= value)
    return int(round((below / len(finite)) * 99))


def score_stock(collected, rs_rank, market_direction):
    metrics = collected.metrics
    liquidity = trading_value_score(metrics["avg_trading_value_20"])
    inverse_vol = clamp(100 - metrics["volatility"])
    price_quality = clamp(70 - max(metrics["distance_to_high"] - 15, 0) * 1.5)
    value_quality = round(clamp(liquidity * 0.45 + inverse_vol * 0.30 + price_quality * 0.25), 1)

    annual_roe_proxy = round(clamp(50 + max(metrics["return_252"], -40) * 0.4 + liquidity * 0.15), 1)
    eps_acceleration = round(clamp(50 + metrics["return_63"] * 0.9 + (metrics["return_63"] - metrics["return_126"] / 2) * 0.35), 1)
    company_score = round(value_quality * 0.40 + annual_roe_proxy * 0.30 + eps_acceleration * 0.30, 1)

    momentum = round(
        clamp(
            rs_rank * 0.40
            + score_from_return(metrics["return_126"], 0.9) * 0.30
            + clamp(100 - metrics["distance_to_high"] * 3) * 0.30
        ),
        1,
    )
    trend_bonus = 12 if metrics["hurst"] > 0.5 else 0
    pivot = round(
        clamp(
            (72 if metrics["is_new_high"] else 48)
            + (10 if metrics["above_ema20"] else -8)
            + (8 if metrics["above_ema50"] else -6)
            + (6 if metrics["volume_surge"] else 0)
            + trend_bonus
        ),
        1,
    )
    smart_money = round(
        clamp(
            trading_value_score(metrics["avg_trading_value_20"]) * 0.45
            + clamp(metrics["volume_ratio"] * 30, 0, 100) * 0.35
            + score_from_return(metrics["obv_trend"], 0.6) * 0.20
        ),
        1,
    )
    timing_score = round(momentum * 0.40 + pivot * 0.30 + smart_money * 0.30, 1)

    mean_reversion = 82
    if metrics["z_score"] > 2.5:
        mean_reversion = 35
    elif metrics["z_score"] > 2.0:
        mean_reversion = 55
    elif metrics["z_score"] < -2.0:
        mean_reversion = 68

    drawdown_control = round(clamp(100 + metrics["mdd"] * 2.0 - max(metrics["volatility"] - 45, 0) * 0.7), 1)
    risk_layer = round(market_direction * 0.40 + mean_reversion * 0.30 + drawdown_control * 0.30, 1)
    reliability = round(
        clamp(min(metrics["history_len"] / 240 * 100, 100) * 0.65 + liquidity * 0.25 + 72 * 0.10),
        1,
    )

    total = company_score * 0.45 + timing_score * 0.55
    log = []
    if metrics["is_new_high"]:
        log.append("현재가가 52주 고점 3% 이내에 있어 주도주 흐름으로 판단했습니다.")
    if metrics["hurst"] > 0.5:
        log.append("허스트 지수가 0.5를 넘어 추세성이 있는 가격 흐름으로 분류했습니다.")
    if metrics["volume_surge"]:
        log.append("거래량 배율이 2.0배 이상이라 거래량 급증 신호를 표시했습니다.")
    if metrics["z_score"] > 2.0:
        total *= 0.8
        log.append("Z-Score가 과열 구간이라 최종 점수에 20% 할인을 적용했습니다.")
    elif risk_layer < 45:
        total *= 0.94
        log.append("리스크 제어 점수가 낮아 최종 점수에 6% 할인을 적용했습니다.")
    elif risk_layer < 60:
        total *= 0.97
        log.append("리스크 제어 점수가 보통보다 낮아 최종 점수에 3% 할인을 적용했습니다.")
    if metrics["mdd"] < -35:
        total -= 8
        log.append("최근 1년 낙폭이 깊어 직접 감점했습니다.")
    if market_direction < 45:
        total *= 0.97
        log.append("KOSPI 시장 방향성이 약해 최종 점수에 3% 할인을 적용했습니다.")
    if reliability < 70:
        total *= 0.9
        log.append("데이터 신뢰도가 70점 미만이라 최종 점수를 낮췄습니다.")

    fail_safe = metrics["history_len"] < 120 or reliability < 55
    if fail_safe:
        total = min(total, 55)
        log.append("가격 이력 또는 신뢰도가 부족해 Fail-safe 상한을 적용했습니다.")

    total = round(clamp(total), 1)
    key_reasons = []
    if rs_rank >= 80:
        key_reasons.append(f"RS {rs_rank}")
    if metrics["distance_to_high"] <= 5:
        key_reasons.append("52주 신고가 근접")
    if metrics["return_63"] > 10:
        key_reasons.append("3개월 모멘텀")
    if metrics["volume_surge"]:
        key_reasons.append("거래량 급증")
    if not key_reasons:
        key_reasons.append("1년 가격 데이터 유효")

    warning = ""
    if metrics["z_score"] > 2:
        warning = "단기 과열 구간이라 추격 매수에 주의해야 합니다."
    elif metrics["low_liquidity"]:
        warning = "평균 거래대금이 기준보다 낮아 유동성에 주의해야 합니다."
    elif metrics["mdd"] < -25:
        warning = "최근 낙폭이 커서 하방 리스크 점검이 필요합니다."

    return {
        "total_score": total,
        "company_score": company_score,
        "timing_score": timing_score,
        "reliability_score": reliability,
        "value_quality": value_quality,
        "annual_roe_proxy": annual_roe_proxy,
        "eps_acceleration": eps_acceleration,
        "momentum": momentum,
        "pivot": pivot,
        "smart_money": smart_money,
        "risk_layer": risk_layer,
        "drawdown_control": drawdown_control,
        "market_direction": market_direction,
        "mean_reversion": mean_reversion,
        "fail_safe": fail_safe,
        "signal": signal_for(total, metrics["volume_surge"], fail_safe),
        "key_reason": " · ".join(key_reasons),
        "headline": f"{collected.meta.name}: 실제 KOSPI 1년 가격 데이터 기준 종합 {total:.1f}점",
        "verdict": "추천 후보" if total >= 70 and not fail_safe and not metrics["low_liquidity"] else "관찰 후보",
        "reason": "실제 KOSPI 일봉 데이터를 바탕으로 모멘텀, 신고가/피벗, 거래량 수급, 리스크 제어를 종합 평가했습니다.",
        "warning": warning,
        "scoring_log": log,
        "rs_rank": rs_rank,
    }


class Command(BaseCommand):
    help = "Seed real KOSPI data through pykrx OHLCV and generate AlphaPick scores/portfolio."

    def add_arguments(self, parser):
        parser.add_argument("--market", default="KOSPI", choices=["KOSPI", "KOSDAQ"])
        parser.add_argument("--days", type=int, default=1095)
        parser.add_argument("--end")
        parser.add_argument("--limit", type=int)
        parser.add_argument("--sleep", type=float, default=0.25)
        parser.add_argument("--flush", action="store_true")
        parser.add_argument("--tickers")
        parser.add_argument("--tickers-file")
        parser.add_argument("--min-trading-value", type=int, default=DEFAULT_MIN_TRADING_VALUE)
        parser.add_argument("--skip-fundamentals", action="store_true")

    def handle(self, *args, **options):
        base_date = parse_base_date(options["end"])
        options["base_date"] = base_date
        start_date = base_date - timedelta(days=options["days"])

        metas = resolve_tickers(options)
        if options["limit"]:
            metas = metas[: options["limit"]]
        if not metas:
            raise CommandError("No tickers resolved.")

        if options["flush"]:
            self.flush_data()

        self.stdout.write(f"Resolved {len(metas)} {options['market']} tickers. Collecting {options['days']} days...")
        collected = []
        skipped = []
        for index, meta in enumerate(metas, start=1):
            try:
                raw = krx_stock.get_market_ohlcv_by_date(to_yyyymmdd(start_date), to_yyyymmdd(base_date), meta.ticker)
                frame = build_price_frame(raw)
                if frame.empty or len(frame) < 30:
                    skipped.append((meta.ticker, "empty price history"))
                    continue
                metrics = collect_metrics(frame, options["min_trading_value"])
                metrics["fundamentals"] = {} if options["skip_fundamentals"] else fetch_naver_financial_snapshot(meta.ticker)
                if meta.name == meta.ticker:
                    meta.name = krx_stock.get_market_ticker_name(meta.ticker) or meta.ticker
                collected.append(CollectedStock(meta=meta, prices=frame, metrics=metrics))
            except Exception as exc:
                skipped.append((meta.ticker, str(exc)))
            if options["sleep"] and index < len(metas):
                time.sleep(options["sleep"])
            if index % 50 == 0:
                self.stdout.write(f"  collected {index}/{len(metas)}")

        if not collected:
            raise CommandError(f"No valid pykrx price histories. First skips: {skipped[:5]}")

        returns_252 = [item.metrics["return_252"] for item in collected]
        market_direction = round(clamp(50 + np.nanmedian([item.metrics["return_63"] for item in collected]) * 1.4), 1)
        scored = [
            (item, score_stock(item, percentile_rank(item.metrics["return_252"], returns_252), market_direction))
            for item in collected
        ]

        with transaction.atomic():
            for item, score in scored:
                self.save_stock(item, score, base_date, options["market"])
            run = ensure_portfolio_run(base_date)

        self.stdout.write(self.style.SUCCESS(
            f"Saved {len(scored)} stocks, skipped {len(skipped)}, portfolio items {run.items.count()}."
        ))
        if skipped:
            sample = ", ".join(f"{ticker}:{reason}" for ticker, reason in skipped[:5])
            self.stdout.write(f"Skipped sample: {sample}")

    def flush_data(self):
        Watchlist.objects.all().delete()
        AICommentCache.objects.all().delete()
        PortfolioItem.objects.all().delete()
        PortfolioRun.objects.all().delete()
        ScoreSnapshot.objects.all().delete()
        FinancialMetric.objects.all().delete()
        PriceDaily.objects.all().delete()
        Stock.objects.all().delete()

    def save_stock(self, item, score, base_date, market):
        fundamentals = item.metrics.get("fundamentals") or {}
        target_price = fundamentals.get("target_price")
        current_price = int(item.metrics["current_price"])
        target_upside = None
        if target_price and current_price:
            target_upside = round((target_price - current_price) / current_price * 100, 1)
        consensus_count = fundamentals.get("consensus_count") or 0
        confidence = "HIGH" if consensus_count >= 3 else "MID" if consensus_count >= 1 else "LOW"
        consensus_label = fundamentals.get("consensus_label") or "컨센서스 없음"

        stock_obj, _ = Stock.objects.update_or_create(
            ticker=f"{item.meta.ticker}.KS" if market == "KOSPI" else f"{item.meta.ticker}.KQ",
            defaults={
                "name": item.meta.name,
                "market": market,
                "sector": item.meta.sector or market,
                "industry": item.meta.industry or "",
                "primary_theme": item.meta.sector or market,
                "is_universe_included": True,
                "low_liquidity_flag": item.metrics["low_liquidity"],
                "is_active": True,
                "is_tradable": True,
            },
        )

        PriceDaily.objects.filter(stock=stock_obj).delete()
        prices = []
        for row_date, row in item.prices.iterrows():
            prices.append(
                PriceDaily(
                    stock=stock_obj,
                    date=row_date.date(),
                    open_price=int(row["open"]),
                    high_price=int(row["high"]),
                    low_price=int(row["low"]),
                    close_price=int(row["close"]),
                    volume=int(row["volume"]),
                    ema20=None if pd.isna(row["ema20"]) else float(row["ema20"]),
                    ema50=None if pd.isna(row["ema50"]) else float(row["ema50"]),
                    ema200=None if pd.isna(row["ema200"]) else float(row["ema200"]),
                    bb_upper=None if pd.isna(row["bb_upper"]) else float(row["bb_upper"]),
                    bb_lower=None if pd.isna(row["bb_lower"]) else float(row["bb_lower"]),
                    obv=None if pd.isna(row["obv"]) else float(row["obv"]),
                )
            )
        PriceDaily.objects.bulk_create(prices, batch_size=1000)

        FinancialMetric.objects.update_or_create(
            stock=stock_obj,
            base_date=base_date,
            defaults={
                "per": fundamentals.get("per"),
                "pbr": fundamentals.get("pbr"),
                "roe": fundamentals.get("roe"),
                "eps_growth": score["eps_acceleration"],
                "operating_margin": fundamentals.get("operating_margin"),
                "debt_ratio": fundamentals.get("debt_ratio"),
                "dividend_yield": fundamentals.get("dividend_yield"),
                "market_cap": None,
                "target_price": target_price,
                "current_price": current_price,
                "payload": {
                    "source": "pykrx_ohlcv + naver_companyguide",
                    "avg_trading_value_20": round(item.metrics["avg_trading_value_20"], 0),
                    "fundamental_status": "PER/PBR/ROE/목표가는 네이버 금융과 FnGuide 기업정보에서 보강했습니다.",
                    "eps": fundamentals.get("eps"),
                    "bps": fundamentals.get("bps"),
                    "consensus_score": fundamentals.get("consensus_score"),
                    "consensus_count": fundamentals.get("consensus_count"),
                    "fundamental_source": fundamentals.get("source") or "네이버 금융/FnGuide",
                },
            },
        )

        ScoreSnapshot.objects.update_or_create(
            stock=stock_obj,
            base_date=base_date,
            defaults={
                "total_score": score["total_score"],
                "company_score": score["company_score"],
                "timing_score": score["timing_score"],
                "reliability_score": score["reliability_score"],
                "financial_health_score": score["annual_roe_proxy"],
                "valuation_score": score["value_quality"],
                "growth_score": score["eps_acceleration"],
                "momentum_score": score["momentum"],
                "technical_timing_score": score["pivot"],
                "supply_score": score["smart_money"],
                "sentiment_score": score["risk_layer"],
                "headline": score["headline"],
                "verdict": score["verdict"],
                "signal": score["signal"],
                "key_reason": score["key_reason"],
                "rs_rank": score["rs_rank"],
                "rsi": round(item.metrics["rsi"], 1),
                "volume_ratio": round(item.metrics["volume_ratio"], 2),
                "target_upside": target_upside,
                "target_upside_clipped": False,
                "consensus": consensus_label,
                "confidence": confidence,
                "fail_safe_flag": score["fail_safe"],
                "volume_surge_flag": item.metrics["volume_surge"],
                "area_scores": {
                    "valueQuality": score["value_quality"],
                    "annualRoeProxy": score["annual_roe_proxy"],
                    "epsAcceleration": score["eps_acceleration"],
                    "leadershipMomentum": score["momentum"],
                    "pivotBreakout": score["pivot"],
                    "smartMoney": score["smart_money"],
                    "marketDirection": score["market_direction"],
                    "meanReversion": score["mean_reversion"],
                    "drawdownControl": score["drawdown_control"],
                    "newsSentiment": None,
                },
                "scoring_log": score["scoring_log"],
                "reason": score["reason"],
                "warning": score["warning"],
                "summary_metrics": [
                    {"label": "RS 등급", "value": score["rs_rank"], "tone": "good" if score["rs_rank"] >= 70 else "neutral"},
                    {"label": "3개월 수익률", "value": f"{item.metrics['return_63']:.1f}%", "tone": "good" if item.metrics["return_63"] > 0 else "bad"},
                    {"label": "RSI", "value": f"{item.metrics['rsi']:.1f}", "tone": "neutral"},
                    {"label": "평균 거래대금", "value": f"{item.metrics['avg_trading_value_20'] / 100000000:.0f}억", "tone": "good" if not item.metrics["low_liquidity"] else "bad"},
                ],
                "timing_cards": [
                    {"title": "추세 필터", "score": round(item.metrics["hurst"] * 100, 1), "description": "허스트 지수로 가격 흐름이 추세장인지 판단합니다."},
                    {"title": "신고가/피벗", "score": score["pivot"], "description": "52주 고점 근접도와 EMA 정배열 여부를 함께 봅니다."},
                    {"title": "수급/거래량", "score": score["smart_money"], "description": "거래량 배율과 OBV 흐름을 수급 대용 지표로 사용합니다."},
                ],
                "score_cards": [
                    {
                        "title": "가치/퀄리티",
                        "score": score["value_quality"],
                        "description": "유동성, 변동성 안정성, 52주 고점 거리로 가격 기반 퀄리티를 평가합니다.",
                        "calculation": "가치/퀄리티 = 유동성 점수 45% + 변동성 안정성 30% + 52주 고점 거리 기반 가격 품질 25%",
                        "score_impact": "회사 점수의 40%로 반영되고, 회사 점수는 최종 총점의 45% 축입니다.",
                        "interpretation": "높을수록 거래가 충분하고 가격 변동성이 과도하지 않으며, 가격 품질이 안정적인 종목으로 봅니다.",
                    },
                    {
                        "title": "주도주 모멘텀",
                        "score": score["momentum"],
                        "description": "상대강도, 6개월 수익률, 52주 고점 근접도로 주도주 여부를 판단합니다.",
                        "calculation": "주도주 모멘텀 = RS 등급 40% + 6개월 수익률 30% + 52주 고점 근접도 30%",
                        "score_impact": "타이밍 점수의 40%로 반영되고, 타이밍 점수는 최종 총점의 55% 축입니다.",
                        "interpretation": "높을수록 시장 평균보다 강하게 움직이는 주도주 후보로 해석합니다.",
                    },
                    {
                        "title": "리스크 제어",
                        "score": score["risk_layer"],
                        "description": "시장 방향, 단기 과열, 낙폭 위험으로 추격 매수 리스크를 제어합니다.",
                        "calculation": "리스크 제어 = 시장 방향 40% + Z-Score 과열 방지 30% + 최대낙폭/변동성 방어 30%",
                        "score_impact": "정상 구간에서는 총점을 거의 건드리지 않고, 위험 구간에서는 최종 점수에 할인 또는 직접 감점을 적용합니다.",
                        "interpretation": "낮을수록 시장 환경이나 종목 변동성이 부담스러워 추천 강도를 낮춰야 합니다.",
                    },
                ],
                "can_slim": [
                    {"code": "C", "label": "현재 모멘텀", "score": score["eps_acceleration"], "status": "pass" if score["eps_acceleration"] >= 70 else "watch", "reason": "최근 3개월 흐름과 가속도를 EPS 가속도의 가격 대용 지표로 사용합니다."},
                    {"code": "A", "label": "연간 퀄리티 대용", "score": score["annual_roe_proxy"], "status": "pass" if score["annual_roe_proxy"] >= 70 else "watch", "reason": "1년 수익률과 유동성을 바탕으로 연간 수익성의 대용 점수를 계산합니다."},
                    {"code": "M", "label": "시장 방향", "score": score["market_direction"], "status": "pass" if score["market_direction"] >= 60 else "watch", "reason": "KOSPI 전체 종목의 중기 흐름으로 시장 환경을 판단합니다."},
                ],
                "technical_indicators": [
                    {
                        "label": "RSI(14)",
                        "value": round(item.metrics["rsi"], 1),
                        "status": "중립",
                        "description": "최근 상승폭과 하락폭을 비교한 과열/침체 지표입니다.",
                        "calculation": "최근 14일 평균 상승폭과 평균 하락폭을 비교해 0~100 범위로 환산합니다.",
                        "score_impact": "직접 가산점보다는 과열/침체 해석 보조 지표로 사용합니다.",
                        "interpretation": "보통 70 이상은 과열, 30 이하는 침체로 봅니다.",
                    },
                    {
                        "label": "Z-Score",
                        "value": round(item.metrics["z_score"], 2),
                        "status": "주의" if item.metrics["z_score"] > 2 else "정상",
                        "description": "현재가가 최근 20일 평균에서 표준편차 기준으로 얼마나 떨어져 있는지 봅니다.",
                        "calculation": "(현재가 - 20일 평균가) / 20일 표준편차",
                        "score_impact": "2.0을 넘으면 단기 과열로 보고 최종 점수에 20% 할인을 적용합니다.",
                        "interpretation": "값이 높을수록 단기 추격 매수 위험이 커집니다.",
                    },
                    {
                        "label": "최대낙폭(MDD)",
                        "value": f"{item.metrics['mdd']:.1f}%",
                        "status": "주의" if item.metrics["mdd"] < -25 else "정상",
                        "description": "최근 1년 고점 대비 가장 크게 빠진 비율입니다.",
                        "calculation": "1년 일별 종가를 누적 최고가와 비교해 가장 깊은 하락률을 계산합니다.",
                        "score_impact": "-35%보다 깊으면 최종 점수에서 직접 감점하고 리스크 제어에도 반영합니다.",
                        "interpretation": "음수가 클수록 과거 하방 위험이 컸다는 뜻입니다.",
                    },
                    {
                        "label": "거래량 배율",
                        "value": round(item.metrics["volume_ratio"], 2),
                        "status": "급증" if item.metrics["volume_surge"] else "보통",
                        "description": "오늘 거래량을 최근 20일 평균 거래량과 비교한 값입니다.",
                        "calculation": "당일 거래량 / 최근 20일 평균 거래량",
                        "score_impact": "수급/거래량 점수에 반영되며, 2배 이상이면 거래량 급증 태그가 붙습니다.",
                        "interpretation": "평소보다 거래가 몰리는지 확인하는 수급 이벤트 지표입니다.",
                    },
                    {
                        "label": "52주 고점 거리",
                        "value": f"{item.metrics['distance_to_high']:.1f}%",
                        "status": "근접" if item.metrics["distance_to_high"] <= 5 else "보통",
                        "description": "현재가가 최근 52주 고점에서 얼마나 떨어져 있는지 나타냅니다.",
                        "calculation": "(52주 최고가 - 현재가) / 52주 최고가 * 100",
                        "score_impact": "신고가/피벗 점수와 주도주 모멘텀 점수에 함께 반영됩니다.",
                        "interpretation": "낮을수록 주도주/돌파 후보에 가깝습니다.",
                    },
                ],
                "financial_indicators": [
                    {
                        "label": "목표가",
                        "value": f"{target_price:,}원" if target_price else "미산정",
                        "status": consensus_label,
                        "description": "최근 증권사 컨센서스 목표주가입니다.",
                        "calculation": "네이버 금융/FnGuide 기업정보에서 목표주가 컨센서스를 수집합니다.",
                        "score_impact": "목표가는 후행성이 있어 최종 점수에는 직접 반영하지 않고 참고 정보로 표시합니다.",
                        "interpretation": "추정기관이 부족하면 미산정으로 표시됩니다.",
                    },
                    {
                        "label": "목표가 상승여력",
                        "value": f"{target_upside:+.1f}%" if target_upside is not None else "미산정",
                        "status": "상승여력" if target_upside is not None and target_upside > 0 else "주의",
                        "description": "목표가와 현재가의 차이를 비율로 계산한 참고 지표입니다.",
                        "calculation": "(목표가 - 현재가) / 현재가 * 100",
                        "score_impact": "최종 점수에는 직접 반영하지 않고, 리포트 해석 보조 지표로 사용합니다.",
                        "interpretation": "양수면 목표가가 현재가보다 높고, 음수면 컨센서스 기준 고평가 가능성이 있습니다.",
                    },
                    {
                        "label": "PER",
                        "value": f"{fundamentals.get('per'):.2f}배" if fundamentals.get("per") is not None else "자료 없음",
                        "status": "낮음" if fundamentals.get("per") is not None and fundamentals.get("per") <= 15 else "확인",
                        "description": "주가를 주당순이익(EPS)으로 나눈 값입니다.",
                        "calculation": "PER = 현재 주가 / 주당순이익(EPS)",
                        "score_impact": "현재 실전 테스트 점수 엔진에서는 모든 KOSPI 종목 커버리지를 위해 가격/거래량 기반 점수를 우선 사용하며, PER은 해석 보강 지표로 표시합니다.",
                        "interpretation": "낮을수록 이익 대비 가격 부담이 작지만, 업종별 적정 PER 차이가 큽니다.",
                    },
                    {
                        "label": "PBR",
                        "value": f"{fundamentals.get('pbr'):.2f}배" if fundamentals.get("pbr") is not None else "자료 없음",
                        "status": "낮음" if fundamentals.get("pbr") is not None and fundamentals.get("pbr") <= 1 else "확인",
                        "description": "주가를 주당순자산(BPS)으로 나눈 값입니다.",
                        "calculation": "PBR = 현재 주가 / 주당순자산(BPS)",
                        "score_impact": "현재는 리포트 해석 보강 지표로 표시하고, 밸류에이션 판단에 참고합니다.",
                        "interpretation": "1배 이하면 장부가치 대비 저평가 가능성을 볼 수 있지만, 자산의 질도 함께 확인해야 합니다.",
                    },
                    {
                        "label": "ROE",
                        "value": f"{fundamentals.get('roe'):.2f}%" if fundamentals.get("roe") is not None else "자료 없음",
                        "status": "양호" if fundamentals.get("roe") is not None and fundamentals.get("roe") >= 10 else "확인",
                        "description": "자기자본 대비 순이익률입니다.",
                        "calculation": "ROE = 당기순이익 / 자기자본 * 100",
                        "score_impact": "현재는 회사 퀄리티 해석 보강 지표로 표시합니다. 값이 높을수록 품질 판단에 긍정적입니다.",
                        "interpretation": "높을수록 자본을 효율적으로 굴리는 회사로 해석합니다.",
                    },
                    {
                        "label": "영업이익률",
                        "value": f"{fundamentals.get('operating_margin'):.2f}%" if fundamentals.get("operating_margin") is not None else "자료 없음",
                        "status": "양호" if fundamentals.get("operating_margin") is not None and fundamentals.get("operating_margin") >= 10 else "확인",
                        "description": "매출에서 영업이익이 차지하는 비율입니다.",
                        "calculation": "영업이익률 = 영업이익 / 매출액 * 100",
                        "score_impact": "본업 수익성 해석에 사용합니다. 현재 점수 엔진에서는 직접 가산점보다 리포트 설명 근거로 표시합니다.",
                        "interpretation": "높을수록 본업에서 이익을 잘 남기는 기업입니다.",
                    },
                    {
                        "label": "유동성",
                        "value": f"{item.metrics['avg_trading_value_20'] / 100000000:.0f}억",
                        "status": "양호" if not item.metrics["low_liquidity"] else "주의",
                        "description": "최근 20일 평균 거래대금입니다.",
                        "calculation": "최근 20일 동안 일별 종가 * 거래량을 계산한 뒤 평균을 냅니다.",
                        "score_impact": "유동성이 낮으면 포트폴리오 편입에서 제외될 수 있고, 가치/퀄리티와 신뢰도 점수에도 반영됩니다.",
                        "interpretation": "낮으면 매수/매도 체결이 불리할 수 있습니다.",
                    },
                    {
                        "label": "데이터 신뢰도",
                        "value": score["reliability_score"],
                        "status": "양호" if score["reliability_score"] >= 70 else "주의",
                        "description": "가격 이력 길이, 유동성, 결측 여부를 합산한 내부 신뢰도 점수입니다.",
                        "calculation": "가격 이력 길이 65% + 유동성 25% + 기본 데이터 보정 10%로 계산합니다.",
                        "score_impact": "70점 미만이면 최종 점수를 할인하고, 55점 미만이면 Fail-safe 상한을 적용합니다.",
                        "interpretation": "낮을수록 이 종목의 점수 판단을 조심해서 봐야 합니다.",
                    },
                ],
                "news": [
                    {"title": "pykrx 실전 모드에서는 뉴스 감성 점수를 별도 수집하지 않습니다.", "sentiment": "중립"}
                ],
                "disclosures": [
                    {"title": "pykrx 일봉 가격 데이터 기준 산출", "date": base_date.isoformat(), "source": "pykrx"}
                ],
            },
        )
