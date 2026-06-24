"""Refresh the AlphaPick KOSPI universe using the latest completed KRX session.

This command is deliberately a small wrapper around ``seed_pykrx``.  It is
safe to run from Windows Task Scheduler: it never flushes user data and it
uses the most recent KOSPI trading day rather than blindly stamping a holiday
or an in-progress session as today's data.
"""

from datetime import date, datetime, timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


def latest_kospi_trading_day(today=None):
    """Return the last KOSPI session date available from pykrx.

    ``get_index_ohlcv_by_date`` is occasionally incompatible with Korean
    column-name decoding on Windows.  Samsung Electronics is a continuously
    traded KOSPI bellwether, so its OHLCV calendar is a more robust session
    probe for the batch job than the index endpoint itself.
    """
    try:
        from pykrx import stock as krx_stock

        today = today or date.today()
        start = today - timedelta(days=10)
        frame = krx_stock.get_market_ohlcv_by_date(
            start.strftime("%Y%m%d"),
            today.strftime("%Y%m%d"),
            "005930",  # Samsung Electronics, KOSPI session probe
        )
        if frame.empty:
            raise CommandError("KRX returned no recent KOSPI session.")
        return frame.index[-1].date()
    except CommandError:
        raise
    except Exception as exc:
        raise CommandError(f"Could not determine the latest KOSPI session: {exc}") from exc


class Command(BaseCommand):
    help = "Refresh market prices, scores, and the portfolio for the latest completed trading session."

    def add_arguments(self, parser):
        parser.add_argument("--market", default="KOSPI", choices=["KOSPI", "KOSDAQ"])
        parser.add_argument("--days", type=int, default=420, help="Calendar days of OHLCV history to retain.")
        parser.add_argument("--sleep", type=float, default=0.15, help="Delay between pykrx requests.")
        parser.add_argument("--limit", type=int, help="Limit tickers for a short verification run.")
        parser.add_argument("--skip-fundamentals", action="store_true")
        parser.add_argument("--end", help="Override the resolved trading day (YYYYMMDD).")

    def handle(self, *args, **options):
        base_date = options["end"] or latest_kospi_trading_day().strftime("%Y%m%d")
        market = options["market"]
        self.stdout.write(f"Refreshing {market} data for the completed session: {base_date}")

        command_options = {
            "market": market,
            "days": options["days"],
            "end": base_date,
            "sleep": options["sleep"],
            "skip_fundamentals": options["skip_fundamentals"],
        }
        if options["limit"]:
            command_options["limit"] = options["limit"]

        call_command("seed_pykrx", **command_options)
        call_command("rebuild_v4_scores", date=datetime.strptime(base_date, "%Y%m%d").strftime("%Y-%m-%d"))
        self.stdout.write(self.style.SUCCESS(f"{market} refresh completed for {base_date}."))
