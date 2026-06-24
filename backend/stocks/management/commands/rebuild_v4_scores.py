from datetime import datetime
from statistics import median

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Max, OuterRef, Subquery

from stocks.models import FinancialMetric, PriceDaily, ScoreSnapshot
from stocks.v4_scoring import calculate, prices_metrics


class Command(BaseCommand):
    help = "Rebuild V4 composite scores: company quality, market validation, and buy timing."

    def add_arguments(self, parser):
        parser.add_argument("--date", help="Score date in YYYY-MM-DD. Defaults to the newest snapshot.")
        parser.add_argument("--limit", type=int, help="Limit stocks for a short verification run.")

    def handle(self, *args, **options):
        requested_date = options.get("date")
        if requested_date:
            try:
                base_date = datetime.strptime(requested_date, "%Y-%m-%d").date()
            except ValueError as exc:
                raise CommandError("--date must use YYYY-MM-DD.") from exc
        else:
            base_date = ScoreSnapshot.objects.aggregate(latest=Max("base_date"))["latest"]

        if base_date is None:
            raise CommandError("No score snapshots exist. Run seed_pykrx first.")

        if requested_date:
            snapshot_queryset = ScoreSnapshot.objects.filter(base_date=base_date)
        else:
            newest_for_stock = (
                ScoreSnapshot.objects.filter(stock_id=OuterRef("stock_id"))
                .order_by("-base_date")
                .values("base_date")[:1]
            )
            snapshot_queryset = ScoreSnapshot.objects.filter(base_date=Subquery(newest_for_stock))

        snapshots = list(snapshot_queryset.select_related("stock").order_by("stock_id"))
        if options.get("limit"):
            snapshots = snapshots[: options["limit"]]
        if not snapshots:
            raise CommandError(f"No score snapshots exist for {base_date}.")

        stock_ids = [snapshot.stock_id for snapshot in snapshots]
        price_rows = PriceDaily.objects.filter(stock_id__in=stock_ids).order_by("stock_id", "date")
        prices_by_stock = {stock_id: [] for stock_id in stock_ids}
        for row in price_rows:
            prices_by_stock[row.stock_id].append(row)

        metrics_by_stock = {}
        for metric in FinancialMetric.objects.filter(stock_id__in=stock_ids).order_by("stock_id", "-base_date"):
            metrics_by_stock.setdefault(metric.stock_id, metric)

        price_metrics_by_stock = {
            stock_id: prices_metrics(rows)
            for stock_id, rows in prices_by_stock.items()
        }
        rs12_scores = [item["return_12_1"] for item in price_metrics_by_stock.values() if item]
        rs6_scores = [item["return_6_1"] for item in price_metrics_by_stock.values() if item]
        recent_returns = [item["return_6_1"] for item in price_metrics_by_stock.values() if item]
        # The cross-sectional median 6-1 return is a market-regime proxy, not a
        # stock return multiplier. A 10% median move should nudge the regime by
        # roughly 10 points rather than collapse it to an extreme.
        market_regime = max(0, min(100, 50 + (median(recent_returns) * 100 if recent_returns else 0)))

        updated = 0
        skipped = 0
        for snapshot in snapshots:
            result = calculate(
                snapshot,
                metrics_by_stock.get(snapshot.stock_id),
                prices_by_stock[snapshot.stock_id],
                rs12_scores,
                rs6_scores,
                market_regime,
            )
            if result is None:
                skipped += 1
                continue

            detail = dict(snapshot.area_scores or {})
            detail["v4"] = {
                "companyQuality": result["company"],
                "marketValidation": result["market"],
                "timingBase": result["timing_base"],
                "timing": result["timing"],
                "valuationStatus": result["valuation_status"],
                "valuationAdjustment": result["adjustment"],
                "compositeAvailable": result["composite"] is not None,
                "zScore": round(result["metrics"]["z_score"], 2),
                "mdd": round(result["metrics"]["mdd"], 2),
                "marketRegime": round(market_regime, 1),
                "actionReason": result["action_reason"],
            }
            snapshot.total_score = result["composite"] if result["composite"] is not None else 0
            snapshot.company_score = result["company"]
            snapshot.market_validation_score = result["market"]
            snapshot.timing_score = result["timing"]
            snapshot.valuation_adjustment = result["adjustment"]
            snapshot.action_signal = result["action"]
            snapshot.action_label = result["label"]
            snapshot.financial_data_status = result["financial_status"]
            snapshot.is_investment_ineligible = snapshot.is_investment_ineligible or result["composite"] is None
            snapshot.area_scores = detail
            snapshot.score_cards = [
                {
                    "title": "회사 품질 Q",
                    "score": result["company"],
                    "description": "중장기적으로 보유할 가치가 있는 기업인지 평가합니다.",
                    "calculation": "성장성 30% + 수익성·자본효율 30% + 재무안정성 25% + 현금흐름·이익의 질 15%",
                    "score_impact": "종합 점수 기하평균에서 40% 비중을 가집니다.",
                    "interpretation": "높을수록 성장성·수익성·재무안정성이 균형 잡힌 회사입니다.",
                },
                {
                    "title": "시장 검증 M",
                    "score": result["market"],
                    "description": "가격이 시장에서 상대적으로 검증받고 있는지 평가합니다.",
                    "calculation": "12-1개월 상대강도 40% + 6-1개월 상대강도 20% + 하방 변동성 방어 25% + MDD 방어 15%",
                    "score_impact": "종합 점수 기하평균에서 25% 비중을 가집니다.",
                    "interpretation": "높을수록 시장 대비 강하고 하락 방어력이 좋습니다.",
                },
                {
                    "title": "매수 타이밍 T",
                    "score": result["timing"],
                    "description": "지금 진입하기 적절한 가격 흐름과 수급인지 평가합니다.",
                    "calculation": "EMA 추세 30% + 수급 25% + 돌파 품질 25% + 진입 품질 20%, 과열·시장 약세 할인",
                    "score_impact": "종합 점수 기하평균에서 35% 비중을 가지며, 매수·관망 신호의 핵심입니다.",
                    "interpretation": "높을수록 추세·수급·돌파가 양호하고 단기 과열 위험이 낮습니다.",
                },
            ]
            snapshot.headline = f"회사 {result['company']:.1f} · 시장 {result['market']:.1f} · 타이밍 {result['timing']:.1f}"
            snapshot.verdict = result["label"]
            snapshot.key_reason = f"회사 품질 {result['company']:.1f}점, 시장 검증 {result['market']:.1f}점, 진입 타이밍 {result['timing']:.1f}점"
            snapshot.save(
                update_fields=(
                    "total_score", "company_score", "market_validation_score", "timing_score",
                    "valuation_adjustment", "action_signal", "action_label", "financial_data_status",
                    "is_investment_ineligible", "area_scores", "score_cards", "headline", "verdict", "key_reason",
                )
            )
            updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"V4 scores rebuilt through {base_date}: {updated} updated, {skipped} skipped, market regime {market_regime:.1f}."
        ))
