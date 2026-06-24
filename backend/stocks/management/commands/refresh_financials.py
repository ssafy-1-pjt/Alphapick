import time

from django.core.management.base import BaseCommand
from django.db import transaction

from stocks.management.commands.seed_pykrx import fetch_naver_financial_snapshot
from stocks.models import FinancialMetric, ScoreSnapshot, Stock


def display_price(value):
    return f"{value:,}원" if value else "미산정"


def display_percent(value):
    return f"{value:+.1f}%" if value is not None else "미산정"


def display_ratio(value):
    return f"{value:.2f}배" if value is not None else "자료 없음"


def display_percent_plain(value):
    return f"{value:.2f}%" if value is not None else "자료 없음"


def consensus_confidence(count):
    if not count:
        return "LOW"
    if count >= 3:
        return "HIGH"
    return "MEDIUM"


def update_indicator_rows(rows, metric, fundamentals, target_upside, consensus_label):
    values = {
        "목표가": (display_price(metric.target_price), consensus_label),
        "목표가 상승여력": (
            display_percent(target_upside),
            "상승여력" if target_upside is not None and target_upside > 0 else "주의",
        ),
        "PER": (
            display_ratio(metric.per),
            "낮음" if metric.per is not None and metric.per <= 15 else "확인",
        ),
        "PBR": (
            display_ratio(metric.pbr),
            "낮음" if metric.pbr is not None and metric.pbr <= 1 else "확인",
        ),
        "ROE": (
            display_percent_plain(metric.roe),
            "양호" if metric.roe is not None and metric.roe >= 10 else "확인",
        ),
        "영업이익률": (
            display_percent_plain(metric.operating_margin),
            "양호" if metric.operating_margin is not None and metric.operating_margin >= 10 else "확인",
        ),
        "부채비율": (
            display_percent_plain(metric.debt_ratio),
            "안정" if metric.debt_ratio is not None and metric.debt_ratio <= 150 else "확인",
        ),
        "배당수익률": (
            display_percent_plain(metric.dividend_yield),
            "참고" if metric.dividend_yield is not None else "자료 없음",
        ),
        "EPS 성장률": (
            display_percent_plain(metric.eps_growth),
            "성장" if metric.eps_growth is not None and metric.eps_growth > 0 else "확인",
        ),
    }
    updated = []
    seen = set()
    for row in rows or []:
        label = row.get("label")
        if label in values:
            value, status = values[label]
            row = {**row, "value": value, "status": status}
            seen.add(label)
        updated.append(row)
    for label in ("목표가", "목표가 상승여력", "PER", "PBR", "ROE", "영업이익률", "부채비율", "배당수익률", "EPS 성장률"):
        if label not in seen:
            value, status = values[label]
            updated.append({"label": label, "value": value, "status": status, "description": "네이버 금융/FnGuide 기준 최신 수집값"})
    return updated


class Command(BaseCommand):
    help = "Refresh only financial metrics from Naver/FnGuide without touching prices or portfolio."

    def add_arguments(self, parser):
        parser.add_argument("--market", default="KOSDAQ", choices=["KOSPI", "KOSDAQ"])
        parser.add_argument("--tickers")
        parser.add_argument("--missing-only", action="store_true")
        parser.add_argument("--limit", type=int)
        parser.add_argument("--sleep", type=float, default=0.15)

    def handle(self, *args, **options):
        stocks = Stock.objects.filter(market=options["market"]).order_by("ticker")
        if options["tickers"]:
            requested = {
                ticker.strip().upper()
                for ticker in options["tickers"].split(",")
                if ticker.strip()
            }
            requested |= {ticker.split(".")[0] for ticker in requested}
            stocks = stocks.filter(ticker__regex=r"^(" + "|".join(sorted(requested)) + r")(\.|$)")
        if options["missing_only"]:
            stocks = stocks.filter(
                financial_metrics__target_price__isnull=True,
                financial_metrics__per__isnull=True,
                financial_metrics__pbr__isnull=True,
                financial_metrics__roe__isnull=True,
                financial_metrics__operating_margin__isnull=True,
            ).distinct()
        if options["limit"]:
            stocks = stocks[: options["limit"]]

        total = len(stocks)
        updated = 0
        skipped = 0
        for index, stock in enumerate(stocks, start=1):
            code = stock.ticker.split(".")[0]
            fundamentals = fetch_naver_financial_snapshot(code)
            has_value = any(
                fundamentals.get(key) is not None
                for key in ("target_price", "per", "pbr", "roe", "operating_margin")
            )
            if not has_value:
                skipped += 1
                self.stdout.write(f"[{index}/{total}] skip {stock.ticker} {stock.name}: no data")
                time.sleep(options["sleep"])
                continue

            with transaction.atomic():
                metric = stock.financial_metrics.order_by("-base_date").first()
                if metric is None:
                    skipped += 1
                    self.stdout.write(f"[{index}/{total}] skip {stock.ticker} {stock.name}: no metric row")
                    continue

                metric.target_price = fundamentals.get("target_price")
                metric.per = fundamentals.get("per")
                metric.pbr = fundamentals.get("pbr")
                metric.roe = fundamentals.get("roe")
                metric.operating_margin = fundamentals.get("operating_margin")
                metric.debt_ratio = fundamentals.get("debt_ratio")
                metric.dividend_yield = fundamentals.get("dividend_yield")
                metric.payload = {
                    **(metric.payload or {}),
                    "eps": fundamentals.get("eps"),
                    "bps": fundamentals.get("bps"),
                    "consensus_score": fundamentals.get("consensus_score"),
                    "consensus_count": fundamentals.get("consensus_count"),
                    "fundamental_source": fundamentals.get("source") or "네이버 금융/FnGuide",
                    "fundamental_status": "네이버 금융/FnGuide에서 재무 지표를 보강했습니다.",
                }
                metric.save()

                score = stock.scores.order_by("-base_date").first()
                if score:
                    target_upside = None
                    if metric.current_price and metric.target_price:
                        target_upside = round(
                            (metric.target_price - metric.current_price) / metric.current_price * 100,
                            1,
                        )
                    consensus_label = fundamentals.get("consensus_label") or "컨센서스 없음"
                    score.target_upside = target_upside
                    score.consensus = consensus_label
                    score.confidence = consensus_confidence(fundamentals.get("consensus_count"))
                    score.financial_indicators = update_indicator_rows(
                        score.financial_indicators,
                        metric,
                        fundamentals,
                        target_upside,
                        consensus_label,
                    )
                    score.financial_data_status = "partial"
                    score.save(update_fields=["target_upside", "consensus", "confidence", "financial_indicators", "financial_data_status"])

            updated += 1
            self.stdout.write(f"[{index}/{total}] updated {stock.ticker} {stock.name}")
            time.sleep(options["sleep"])

        self.stdout.write(self.style.SUCCESS(f"Updated {updated}, skipped {skipped}, total {total}."))
