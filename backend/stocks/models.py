from django.conf import settings
from django.db import models


class Stock(models.Model):
    ticker = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=120)
    market = models.CharField(max_length=20, db_index=True)
    sector = models.CharField(max_length=80, db_index=True)
    industry = models.CharField(max_length=120, blank=True)
    primary_theme = models.CharField(max_length=80, blank=True, db_index=True)
    is_universe_included = models.BooleanField(default=True, db_index=True)
    low_liquidity_flag = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_tradable = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("ticker",)
        indexes = [
            models.Index(fields=("market", "sector")),
            models.Index(fields=("name",)),
        ]

    def __str__(self):
        return f"{self.name} ({self.ticker})"


class ThemeGroup(models.Model):
    name = models.CharField(max_length=80, unique=True)
    icon = models.CharField(max_length=12, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ("sort_order", "name")

    def __str__(self):
        return self.name


class Theme(models.Model):
    group = models.ForeignKey(ThemeGroup, on_delete=models.CASCADE, related_name="themes")
    name = models.CharField(max_length=80)
    sort_order = models.PositiveSmallIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ("group__sort_order", "sort_order", "name")
        constraints = [
            models.UniqueConstraint(fields=("group", "name"), name="unique_theme_group_name"),
        ]

    def __str__(self):
        return f"{self.group.name} / {self.name}"


class StockTheme(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name="theme_links")
    theme = models.ForeignKey(Theme, on_delete=models.CASCADE, related_name="stock_links")
    is_primary = models.BooleanField(default=False, db_index=True)
    source = models.CharField(max_length=40, default="manual")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("stock_id", "theme__group__sort_order", "theme__sort_order")
        constraints = [
            models.UniqueConstraint(fields=("stock", "theme"), name="unique_stock_theme"),
        ]
        indexes = [
            models.Index(fields=("is_primary",)),
        ]

    def __str__(self):
        return f"{self.stock_id}:{self.theme_id}"


class PriceDaily(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name="prices")
    date = models.DateField(db_index=True)
    open_price = models.PositiveIntegerField()
    high_price = models.PositiveIntegerField()
    low_price = models.PositiveIntegerField()
    close_price = models.PositiveIntegerField()
    volume = models.PositiveIntegerField()
    ema20 = models.FloatField(null=True, blank=True)
    ema50 = models.FloatField(null=True, blank=True)
    ema200 = models.FloatField(null=True, blank=True)
    bb_upper = models.FloatField(null=True, blank=True)
    bb_lower = models.FloatField(null=True, blank=True)
    obv = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ("date",)
        constraints = [
            models.UniqueConstraint(fields=("stock", "date"), name="unique_stock_price_date"),
        ]

    def __str__(self):
        return f"{self.stock_id}:{self.date}"


class FinancialMetric(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name="financial_metrics")
    base_date = models.DateField(db_index=True)
    per = models.FloatField(null=True, blank=True)
    pbr = models.FloatField(null=True, blank=True)
    roe = models.FloatField(null=True, blank=True)
    eps_growth = models.FloatField(null=True, blank=True)
    operating_margin = models.FloatField(null=True, blank=True)
    debt_ratio = models.FloatField(null=True, blank=True)
    dividend_yield = models.FloatField(null=True, blank=True)
    market_cap = models.FloatField(null=True, blank=True)
    target_price = models.PositiveIntegerField(null=True, blank=True)
    current_price = models.PositiveIntegerField(null=True, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-base_date",)
        constraints = [
            models.UniqueConstraint(fields=("stock", "base_date"), name="unique_stock_metric_date"),
        ]

    def __str__(self):
        return f"{self.stock_id}:{self.base_date}"


class ScoreSnapshot(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name="scores")
    base_date = models.DateField(db_index=True)
    total_score = models.FloatField(db_index=True)
    company_score = models.FloatField()
    timing_score = models.FloatField()
    reliability_score = models.FloatField()
    financial_health_score = models.FloatField(default=0)
    valuation_score = models.FloatField(default=0)
    growth_score = models.FloatField(default=0)
    momentum_score = models.FloatField(default=0)
    technical_timing_score = models.FloatField(default=0)
    supply_score = models.FloatField(default=0)
    sentiment_score = models.FloatField(default=0)
    headline = models.CharField(max_length=180)
    verdict = models.CharField(max_length=40)
    signal = models.CharField(max_length=160, blank=True)
    key_reason = models.TextField(blank=True)
    rs_rank = models.PositiveSmallIntegerField(null=True, blank=True)
    rsi = models.FloatField(null=True, blank=True)
    volume_ratio = models.FloatField(default=1.0)
    target_upside = models.FloatField(null=True, blank=True)
    target_upside_clipped = models.BooleanField(default=False)
    consensus = models.CharField(max_length=40, blank=True)
    confidence = models.CharField(max_length=10, blank=True)
    fail_safe_flag = models.BooleanField(default=False)
    volume_surge_flag = models.BooleanField(default=False)
    area_scores = models.JSONField(default=dict, blank=True)
    scoring_log = models.JSONField(default=list, blank=True)
    reason = models.TextField()
    warning = models.TextField(blank=True)
    summary_metrics = models.JSONField(default=list, blank=True)
    timing_cards = models.JSONField(default=list, blank=True)
    score_cards = models.JSONField(default=list, blank=True)
    can_slim = models.JSONField(default=list, blank=True)
    technical_indicators = models.JSONField(default=list, blank=True)
    financial_indicators = models.JSONField(default=list, blank=True)
    news = models.JSONField(default=list, blank=True)
    disclosures = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-base_date", "-total_score")
        constraints = [
            models.UniqueConstraint(fields=("stock", "base_date"), name="unique_stock_score_date"),
        ]

    def __str__(self):
        return f"{self.stock_id}:{self.base_date}:{self.total_score}"


class PortfolioRun(models.Model):
    base_date = models.DateField(unique=True, db_index=True)
    threshold = models.FloatField(default=70)
    rebalance_type = models.CharField(max_length=20, default="daily")
    portfolio_score = models.FloatField(default=0)
    summary = models.TextField(blank=True)
    sector_warning = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-base_date",)

    def __str__(self):
        return f"Portfolio {self.base_date}"


class PortfolioItem(models.Model):
    portfolio_run = models.ForeignKey(PortfolioRun, on_delete=models.CASCADE, related_name="items")
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name="portfolio_items")
    score_snapshot = models.ForeignKey(ScoreSnapshot, on_delete=models.CASCADE, related_name="portfolio_items")
    score = models.FloatField()
    weight = models.FloatField()
    reason = models.TextField()
    warning = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-score", "stock_id")
        constraints = [
            models.UniqueConstraint(fields=("portfolio_run", "stock"), name="unique_portfolio_stock"),
        ]

    def __str__(self):
        return f"{self.portfolio_run_id}:{self.stock_id}"


class WatchlistFolder(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="watchlist_folders")
    name = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(fields=("user", "name"), name="unique_user_watchlist_folder"),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.name}"


class Watchlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="stock_watchlist")
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name="watchlisted_by")
    folder = models.ForeignKey(WatchlistFolder, on_delete=models.SET_NULL, related_name="items", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=("user", "stock"), name="unique_user_stock_watchlist"),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.stock_id}"


class AICommentCache(models.Model):
    class RiskType(models.TextChoices):
        AGGRESSIVE = "aggressive", "Aggressive"
        NEUTRAL = "neutral", "Neutral"
        STABLE = "stable", "Stable"

    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name="ai_comments")
    base_date = models.DateField(db_index=True)
    risk_type = models.CharField(max_length=20, choices=RiskType.choices, default=RiskType.NEUTRAL)
    positive = models.TextField()
    negative = models.TextField()
    conclusion = models.TextField()
    provider = models.CharField(max_length=40, default="local-mvp")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-base_date", "stock_id")
        constraints = [
            models.UniqueConstraint(fields=("stock", "base_date", "risk_type"), name="unique_ai_comment_stock_date_risk"),
        ]

    def __str__(self):
        return f"{self.stock_id}:{self.base_date}:{self.risk_type}"
