import re

from django.core.management.base import BaseCommand
from django.db.models import OuterRef, Subquery

from stocks.models import PriceDaily, ScoreSnapshot


class Command(BaseCommand):
    help = "Rebuild latest key_reason values from RS, 52-week high, 3-month momentum, and volume surge only."

    def handle(self, *args, **options):
        latest_date = ScoreSnapshot.objects.filter(stock=OuterRef("stock")).order_by("-base_date").values("base_date")[:1]
        updated = 0

        for score in ScoreSnapshot.objects.filter(base_date=Subquery(latest_date)).select_related("stock"):
            reasons = []
            if not (score.is_investment_ineligible or score.fail_safe_flag or not score.stock.is_tradable):
                if score.rs_rank >= 80:
                    reasons.append(f"RS {score.rs_rank}")

                prices = list(PriceDaily.objects.filter(stock=score.stock).order_by("-date")[:253])
                prices.reverse()
                if prices:
                    latest = prices[-1]
                    high_close = max(row.close_price for row in prices)
                    if high_close and latest.close_price >= high_close * 0.97:
                        reasons.append("52주 신고가 근접")
                    if len(prices) > 63 and prices[-64].close_price and latest.close_price / prices[-64].close_price - 1 > 0.10:
                        reasons.append("3개월 모멘텀")

                if score.volume_surge_flag:
                    reasons.append("거래량 급증")

            key_reason = " · ".join(reasons)
            if score.key_reason != key_reason:
                score.key_reason = key_reason
                score.save(update_fields=["key_reason"])
                updated += 1

        bad = 0
        allowed = [
            re.compile(r"^RS \d+$"),
            re.compile(r"^52주 신고가 근접$"),
            re.compile(r"^3개월 모멘텀$"),
            re.compile(r"^거래량 급증$"),
        ]
        for score in ScoreSnapshot.objects.filter(base_date=Subquery(latest_date)).exclude(key_reason=""):
            bad += sum(
                1
                for part in (item.strip() for item in score.key_reason.split("·"))
                if not any(pattern.match(part) for pattern in allowed)
            )

        self.stdout.write(self.style.SUCCESS(f"key_reason repaired: {updated} updated, {bad} invalid tags remaining."))
