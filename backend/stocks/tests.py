from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from .models import PortfolioRun
from .services import PORTFOLIO_THRESHOLD


class AlphaPickPortfolioTests(TestCase):
    def setUp(self):
        call_command("seed_alphapick", verbosity=0)

    def test_today_portfolio_uses_threshold_and_score_weights(self):
        portfolio = PortfolioRun.objects.order_by("-base_date").first()

        self.assertIsNotNone(portfolio)
        self.assertGreater(portfolio.items.count(), 0)
        self.assertAlmostEqual(sum(item.weight for item in portfolio.items.all()), 100, delta=0.1)
        self.assertTrue(
            all(
                item.score_snapshot.company_score >= 60
                and item.score_snapshot.timing_score >= 60
                for item in portfolio.items.select_related("score_snapshot")
            )
        )

    def test_public_api_supports_presentation_flow(self):
        client = APIClient()

        portfolio = client.get("/api/portfolio/today/")
        self.assertEqual(portfolio.status_code, 200)
        self.assertEqual(round(sum(item["weight"] for item in portfolio.json()["items"]), 1), 100)
        self.assertEqual(portfolio.json()["userRiskType"], "neutral")
        self.assertTrue(
            all(item["company_score"] >= 60 and item["timing_score"] >= 60 for item in portfolio.json()["items"])
        )

        aggressive = client.get("/api/portfolio/today/?risk_type=aggressive")
        self.assertEqual(aggressive.status_code, 200)
        self.assertEqual(aggressive.json()["userRiskType"], "aggressive")

        stocks = client.get("/api/stocks/")
        self.assertEqual(stocks.status_code, 200)
        rows = stocks.json()["results"]
        self.assertEqual(len(rows), len({row["ticker"] for row in rows}))

        report = client.get("/api/stocks/105560.KS/report/")
        self.assertEqual(report.status_code, 200)
        self.assertEqual(len(report.json()["priceSeries"]), 365)

        ai_comment = client.post("/api/stocks/105560.KS/ai-comment/", {"risk_type": "neutral"}, format="json")
        self.assertEqual(ai_comment.status_code, 200)
        self.assertIn("positive", ai_comment.json())

        backtest = client.get("/api/portfolio/backtest/")
        self.assertEqual(backtest.status_code, 200)
        self.assertGreater(len(backtest.json()["series"]), 0)
