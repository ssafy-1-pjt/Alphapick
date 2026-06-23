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
        self.assertLessEqual(sum(item.weight for item in portfolio.items.all()), 100.1)
        self.assertTrue(
            all(
                item.score_snapshot.company_score >= PORTFOLIO_THRESHOLD
                and item.score_snapshot.timing_score >= PORTFOLIO_THRESHOLD
                for item in portfolio.items.select_related("score_snapshot")
            )
        )

    def test_public_api_supports_presentation_flow(self):
        client = APIClient()

        portfolio = client.get("/api/portfolio/today/")
        self.assertEqual(portfolio.status_code, 200)
        payload = portfolio.json()
        stock_weight = round(sum(item["weight"] for item in payload["items"]), 1)
        self.assertAlmostEqual(stock_weight + round(payload["cashWeight"], 1), 100, delta=0.2)
        self.assertEqual(portfolio.json()["userRiskType"], "neutral")
        self.assertTrue(
            all(item["company_score"] >= PORTFOLIO_THRESHOLD and item["timing_score"] >= PORTFOLIO_THRESHOLD for item in portfolio.json()["items"])
        )
        self.assertIn("allocationItems", payload)
        self.assertIn("sectorCap", payload)

        aggressive = client.get("/api/portfolio/today/?risk_type=aggressive")
        self.assertEqual(aggressive.status_code, 200)
        self.assertEqual(aggressive.json()["userRiskType"], "aggressive")
        stable = client.get("/api/portfolio/today/?risk_type=stable")
        self.assertEqual(stable.status_code, 200)
        self.assertEqual(stable.json()["userRiskType"], "stable")
        self.assertGreaterEqual(
            len(
                {
                    aggressive.json()["baseCashWeight"],
                    portfolio.json()["baseCashWeight"],
                    stable.json()["baseCashWeight"],
                }
            ),
            2,
        )

        stocks = client.get("/api/stocks/")
        self.assertEqual(stocks.status_code, 200)
        rows = stocks.json()["results"]
        self.assertEqual(len(rows), len({row["ticker"] for row in rows}))

        report = client.get("/api/stocks/105560.KS/report/")
        self.assertEqual(report.status_code, 200)
        self.assertGreater(len(report.json()["priceSeries"]), 0)
        self.assertLessEqual(len(report.json()["priceSeries"]), 1095)

        ai_comment = client.post("/api/stocks/105560.KS/ai-comment/", {"risk_type": "neutral"}, format="json")
        self.assertEqual(ai_comment.status_code, 200)
        self.assertIn("positive", ai_comment.json())

        backtest = client.get("/api/portfolio/backtest/")
        self.assertEqual(backtest.status_code, 200)
        self.assertGreater(len(backtest.json()["series"]), 0)
