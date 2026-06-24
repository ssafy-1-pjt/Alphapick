from rest_framework import serializers

from .models import AICommentCache, FinancialMetric, PortfolioItem, PortfolioRun, PriceDaily, ScoreSnapshot, Stock, Theme, ThemeGroup, Watchlist, WatchlistFolder
from .services import PORTFOLIO_THRESHOLD, watch_candidates


class StockSummarySerializer(serializers.ModelSerializer):
    sector = serializers.SerializerMethodField()
    original_sector = serializers.CharField(source="sector")
    primary_theme = serializers.SerializerMethodField()
    themes = serializers.SerializerMethodField()
    theme_groups = serializers.SerializerMethodField()
    latest_score = serializers.SerializerMethodField()
    current_price = serializers.SerializerMethodField()
    reason = serializers.SerializerMethodField()
    signal = serializers.SerializerMethodField()
    key_reason = serializers.SerializerMethodField()
    rs_rank = serializers.SerializerMethodField()
    rsi = serializers.SerializerMethodField()
    volume_surge_flag = serializers.SerializerMethodField()
    fail_safe_flag = serializers.SerializerMethodField()
    company_score = serializers.SerializerMethodField()
    market_validation_score = serializers.SerializerMethodField()
    timing_score = serializers.SerializerMethodField()
    valuation_adjustment = serializers.SerializerMethodField()
    action_signal = serializers.SerializerMethodField()
    action_label = serializers.SerializerMethodField()
    financial_data_status = serializers.SerializerMethodField()

    class Meta:
        model = Stock
        fields = (
            "ticker",
            "name",
            "market",
            "sector",
            "original_sector",
            "industry",
            "primary_theme",
            "themes",
            "theme_groups",
            "is_universe_included",
            "low_liquidity_flag",
            "latest_score",
            "current_price",
            "reason",
            "signal",
            "key_reason",
            "rs_rank",
            "rsi",
            "volume_surge_flag",
            "fail_safe_flag",
            "company_score",
            "market_validation_score",
            "timing_score",
            "valuation_adjustment",
            "action_signal",
            "action_label",
            "financial_data_status",
        )

    def get_theme_links(self, obj):
        links = getattr(obj, "_prefetched_objects_cache", {}).get("theme_links")
        if links is None:
            links = obj.theme_links.select_related("theme__group").all()
        return list(links)

    def get_primary_theme_link(self, obj):
        links = self.get_theme_links(obj)
        primary = next((link for link in links if link.is_primary), None)
        return primary or (links[0] if links else None)

    def get_sector(self, obj):
        primary = self.get_primary_theme_link(obj)
        return primary.theme.group.name if primary else obj.sector

    def get_primary_theme(self, obj):
        primary = self.get_primary_theme_link(obj)
        return primary.theme.name if primary else obj.primary_theme

    def get_themes(self, obj):
        names = []
        for link in self.get_theme_links(obj):
            if link.theme.name not in names:
                names.append(link.theme.name)
        return names

    def get_theme_groups(self, obj):
        names = []
        for link in self.get_theme_links(obj):
            if link.theme.group.name not in names:
                names.append(link.theme.group.name)
        return names

    def get_latest_score(self, obj):
        score = getattr(obj, "prefetched_latest_score", None) or obj.scores.first()
        return round(score.total_score, 1) if score else None

    def get_current_price(self, obj):
        metric = obj.financial_metrics.first()
        if metric and metric.current_price:
            return metric.current_price
        price = obj.prices.order_by("-date").first()
        return price.close_price if price else None

    def get_reason(self, obj):
        score = getattr(obj, "prefetched_latest_score", None) or obj.scores.first()
        return score.reason if score else ""

    def get_signal(self, obj):
        score = getattr(obj, "prefetched_latest_score", None) or obj.scores.first()
        return score.signal if score else ""

    def get_key_reason(self, obj):
        score = getattr(obj, "prefetched_latest_score", None) or obj.scores.first()
        return score.key_reason if score else ""

    def get_rs_rank(self, obj):
        score = getattr(obj, "prefetched_latest_score", None) or obj.scores.first()
        return score.rs_rank if score else None

    def get_rsi(self, obj):
        score = getattr(obj, "prefetched_latest_score", None) or obj.scores.first()
        return score.rsi if score else None

    def get_volume_surge_flag(self, obj):
        score = getattr(obj, "prefetched_latest_score", None) or obj.scores.first()
        return score.volume_surge_flag if score else False

    def get_fail_safe_flag(self, obj):
        score = getattr(obj, "prefetched_latest_score", None) or obj.scores.first()
        return score.fail_safe_flag if score else False

    def get_company_score(self, obj):
        score = getattr(obj, "prefetched_latest_score", None) or obj.scores.first()
        return round(score.company_score, 1) if score else None

    def get_market_validation_score(self, obj):
        score = getattr(obj, "prefetched_latest_score", None) or obj.scores.first()
        return round(score.market_validation_score, 1) if score and score.market_validation_score is not None else None

    def get_timing_score(self, obj):
        score = getattr(obj, "prefetched_latest_score", None) or obj.scores.first()
        return round(score.timing_score, 1) if score else None

    def get_valuation_adjustment(self, obj):
        score = getattr(obj, "prefetched_latest_score", None) or obj.scores.first()
        return score.valuation_adjustment if score else 0

    def get_action_signal(self, obj):
        score = getattr(obj, "prefetched_latest_score", None) or obj.scores.first()
        return score.action_signal if score else "REVIEW"

    def get_action_label(self, obj):
        score = getattr(obj, "prefetched_latest_score", None) or obj.scores.first()
        return score.action_label if score else "평가 보류"

    def get_financial_data_status(self, obj):
        score = getattr(obj, "prefetched_latest_score", None) or obj.scores.first()
        return score.financial_data_status if score else "partial"


class WatchlistFolderSerializer(serializers.ModelSerializer):
    item_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = WatchlistFolder
        fields = ("id", "name", "item_count", "created_at")
        read_only_fields = ("id", "item_count", "created_at")

    def validate_name(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("폴더 이름을 입력해 주세요.")
        return cleaned


class WatchlistEntrySerializer(serializers.ModelSerializer):
    stock = StockSummarySerializer(read_only=True)
    folder = WatchlistFolderSerializer(read_only=True)

    class Meta:
        model = Watchlist
        fields = ("id", "stock", "folder", "created_at")


class ThemeSerializer(serializers.ModelSerializer):
    stock_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Theme
        fields = ("id", "name", "stock_count")


class ThemeGroupSerializer(serializers.ModelSerializer):
    themes = ThemeSerializer(many=True, read_only=True)
    stock_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ThemeGroup
        fields = ("id", "name", "icon", "stock_count", "themes")


class PriceDailySerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceDaily
        fields = (
            "date",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
            "ema20",
            "ema50",
            "ema200",
            "bb_upper",
            "bb_lower",
            "obv",
        )


class FinancialMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialMetric
        fields = (
            "base_date",
            "per",
            "pbr",
            "roe",
            "eps_growth",
            "operating_margin",
            "debt_ratio",
            "dividend_yield",
            "market_cap",
            "target_price",
            "current_price",
        )


class ScoreSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScoreSnapshot
        fields = (
            "base_date",
            "total_score",
            "company_score",
            "timing_score",
            "market_validation_score",
            "valuation_adjustment",
            "action_signal",
            "action_label",
            "financial_data_status",
            "is_investment_ineligible",
            "red_flag_reasons",
            "reliability_score",
            "financial_health_score",
            "valuation_score",
            "growth_score",
            "momentum_score",
            "technical_timing_score",
            "supply_score",
            "sentiment_score",
            "headline",
            "verdict",
            "signal",
            "key_reason",
            "rs_rank",
            "rsi",
            "volume_ratio",
            "target_upside",
            "target_upside_clipped",
            "consensus",
            "confidence",
            "fail_safe_flag",
            "volume_surge_flag",
            "area_scores",
            "scoring_log",
            "reason",
            "warning",
            "summary_metrics",
            "timing_cards",
            "score_cards",
            "can_slim",
            "technical_indicators",
            "financial_indicators",
            "news",
            "disclosures",
        )


class PortfolioItemSerializer(serializers.ModelSerializer):
    ticker = serializers.CharField(source="stock.ticker")
    name = serializers.CharField(source="stock.name")
    market = serializers.CharField(source="stock.market")
    sector = serializers.SerializerMethodField()
    original_sector = serializers.CharField(source="stock.sector")
    primary_theme = serializers.SerializerMethodField()
    themes = serializers.SerializerMethodField()
    low_liquidity_flag = serializers.BooleanField(source="stock.low_liquidity_flag")
    total_score = serializers.FloatField(source="score_snapshot.total_score")
    company_score = serializers.FloatField(source="score_snapshot.company_score")
    timing_score = serializers.FloatField(source="score_snapshot.timing_score")
    reliability_score = serializers.FloatField(source="score_snapshot.reliability_score")
    signal = serializers.CharField(source="score_snapshot.signal")
    key_reason = serializers.CharField(source="score_snapshot.key_reason")
    rs_rank = serializers.IntegerField(source="score_snapshot.rs_rank")
    rsi = serializers.FloatField(source="score_snapshot.rsi")
    target_upside = serializers.FloatField(source="score_snapshot.target_upside")
    target_upside_clipped = serializers.BooleanField(source="score_snapshot.target_upside_clipped")
    consensus = serializers.CharField(source="score_snapshot.consensus")
    confidence = serializers.CharField(source="score_snapshot.confidence")
    fail_safe_flag = serializers.BooleanField(source="score_snapshot.fail_safe_flag")
    volume_surge_flag = serializers.BooleanField(source="score_snapshot.volume_surge_flag")

    class Meta:
        model = PortfolioItem
        fields = (
            "ticker",
            "name",
            "market",
            "sector",
            "original_sector",
            "primary_theme",
            "themes",
            "low_liquidity_flag",
            "total_score",
            "company_score",
            "timing_score",
            "reliability_score",
            "signal",
            "key_reason",
            "rs_rank",
            "rsi",
            "target_upside",
            "target_upside_clipped",
            "consensus",
            "confidence",
            "fail_safe_flag",
            "volume_surge_flag",
            "weight",
            "reason",
            "warning",
        )

    def get_stock_summary(self, obj):
        return StockSummarySerializer(obj.stock)

    def get_sector(self, obj):
        return self.get_stock_summary(obj).get_sector(obj.stock)

    def get_primary_theme(self, obj):
        return self.get_stock_summary(obj).get_primary_theme(obj.stock)

    def get_themes(self, obj):
        return self.get_stock_summary(obj).get_themes(obj.stock)


class PortfolioSerializer(serializers.ModelSerializer):
    baseDate = serializers.DateField(source="base_date")
    portfolioScore = serializers.FloatField(source="portfolio_score")
    rebalanceType = serializers.CharField(source="rebalance_type")
    sectorWarning = serializers.CharField(source="sector_warning")
    items = PortfolioItemSerializer(many=True)
    watchCandidates = serializers.SerializerMethodField()
    benchmarkSummary = serializers.SerializerMethodField()

    class Meta:
        model = PortfolioRun
        fields = (
            "baseDate",
            "portfolioScore",
            "rebalanceType",
            "threshold",
            "summary",
            "sectorWarning",
            "items",
            "watchCandidates",
            "benchmarkSummary",
        )

    def get_watchCandidates(self, obj):
        candidates = [item.stock for item in watch_candidates(obj.base_date)]
        for stock in candidates:
            stock.prefetched_latest_score = stock.scores.filter(base_date=obj.base_date).first()
        return StockSummarySerializer(candidates, many=True).data

    def get_benchmarkSummary(self, obj):
        item_count = obj.items.count()
        return {
            "benchmark": "KOSPI",
            "rebalanceType": obj.rebalance_type,
            "threshold": PORTFOLIO_THRESHOLD,
            "itemCount": item_count,
            "message": "일별 리밸런싱 기준의 MVP 백테스트 요약은 /api/portfolio/backtest/에서 제공합니다.",
        }


class StockReportSerializer(serializers.Serializer):
    stock = serializers.SerializerMethodField()
    score = serializers.SerializerMethodField()
    financialMetric = serializers.SerializerMethodField()
    priceSeries = serializers.SerializerMethodField()
    refreshedAt = serializers.SerializerMethodField()
    investmentNotice = serializers.SerializerMethodField()

    def get_stock(self, obj):
        return StockSummarySerializer(obj["stock"]).data

    def get_score(self, obj):
        score = obj["score"]
        return ScoreSnapshotSerializer(score).data if score else None

    def get_financialMetric(self, obj):
        metric = obj["metric"]
        return FinancialMetricSerializer(metric).data if metric else None

    def get_priceSeries(self, obj):
        return PriceDailySerializer(obj["prices"], many=True).data

    def get_refreshedAt(self, obj):
        value = obj.get("refreshed_at")
        return value.isoformat() if value else None

    def get_investmentNotice(self, obj):
        return "본 서비스는 학습용 분석 도구이며 실제 투자 권유가 아닙니다. 모든 투자의 책임은 투자자 본인에게 있습니다."


class AICommentSerializer(serializers.ModelSerializer):
    ticker = serializers.CharField(source="stock.ticker")
    name = serializers.CharField(source="stock.name")
    baseDate = serializers.DateField(source="base_date")
    riskType = serializers.CharField(source="risk_type")

    class Meta:
        model = AICommentCache
        fields = (
            "ticker",
            "name",
            "baseDate",
            "riskType",
            "positive",
            "negative",
            "conclusion",
            "provider",
        )
