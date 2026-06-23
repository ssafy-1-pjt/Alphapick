from django.db.models import Count, Prefetch, Q
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Stock, Theme, ThemeGroup, Watchlist, WatchlistFolder
from .serializers import (
    AICommentSerializer,
    PortfolioSerializer,
    PriceDailySerializer,
    StockReportSerializer,
    StockSummarySerializer,
    ThemeGroupSerializer,
    WatchlistEntrySerializer,
    WatchlistFolderSerializer,
)
from .services import (
    PRICE_HISTORY_DAYS,
    build_dynamic_portfolio_payload,
    calculate_backtest,
    generate_ai_comment,
    latest_score_date,
    normalize_risk_type,
    portfolio_history,
    stock_report,
)


class StockViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StockSummarySerializer
    lookup_field = "ticker"
    lookup_value_regex = r"[^/]+"
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        score_date = latest_score_date()
        queryset = Stock.objects.filter(is_active=True).prefetch_related(
            "scores",
            "financial_metrics",
            "theme_links__theme__group",
        )
        query = self.request.query_params.get("q")
        sector = self.request.query_params.get("sector")
        market = self.request.query_params.get("market")
        min_score = self.request.query_params.get("min_score")
        theme = self.request.query_params.get("theme")
        theme_group = self.request.query_params.get("theme_group")

        if query:
            queryset = queryset.filter(Q(name__icontains=query) | Q(ticker__icontains=query))
        if sector:
            queryset = queryset.filter(sector=sector)
        if market:
            queryset = queryset.filter(market=market)
        if theme:
            queryset = queryset.filter(theme_links__theme__name=theme)
        if theme_group:
            queryset = queryset.filter(theme_links__theme__group__name=theme_group)
        if score_date:
            queryset = queryset.filter(scores__base_date=score_date)
        if min_score:
            queryset = queryset.filter(scores__total_score__gte=float(min_score)).distinct()
        return queryset.order_by("-scores__total_score", "name").distinct()

    @action(detail=True, methods=["get"], url_path="report")
    def report(self, request, ticker=None):
        data = stock_report(ticker)
        return Response(StockReportSerializer(data).data)

    @action(detail=True, methods=["get"], url_path="prices")
    def prices(self, request, ticker=None):
        stock = self.get_object()
        prices = stock.prices.order_by("-date")[: int(request.query_params.get("limit", PRICE_HISTORY_DAYS))]
        return Response(PriceDailySerializer(reversed(list(prices)), many=True).data)

    @action(detail=True, methods=["post"], url_path="ai-comment")
    def ai_comment(self, request, ticker=None):
        risk_type = normalize_risk_type(request.data.get("risk_type") or request.query_params.get("risk_type"))
        try:
            comment, cached = generate_ai_comment(ticker, risk_type=risk_type)
        except ValueError:
            return Response({"detail": "아직 생성 가능한 스코어 리포트가 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        return Response({**AICommentSerializer(comment).data, "cached": cached})


class TodayPortfolioView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        if latest_score_date() is None:
            return Response(
                {
                    "detail": "아직 로드된 주식 데이터가 없습니다. python manage.py seed_alphapick 명령으로 샘플 fixtures를 적재하세요.",
                    "items": [],
                    "watchCandidates": [],
                },
                status=status.HTTP_200_OK,
            )
        risk_type = normalize_risk_type(request.query_params.get("risk_type"))
        return Response(build_dynamic_portfolio_payload(risk_type=risk_type))


class ThemeGroupListView(generics.ListAPIView):
    serializer_class = ThemeGroupSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        themes = Theme.objects.annotate(stock_count=Count("stock_links", distinct=True)).filter(stock_count__gt=0)
        return (
            ThemeGroup.objects.annotate(stock_count=Count("themes__stock_links", distinct=True))
            .prefetch_related(Prefetch("themes", queryset=themes))
            .filter(stock_count__gt=0)
        )


class PortfolioHistoryView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        limit = int(request.query_params.get("limit", 20))
        return Response(PortfolioSerializer(portfolio_history(limit), many=True).data)


class PortfolioBacktestView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        benchmark = request.query_params.get("benchmark", "KOSPI")
        period = request.query_params.get("period", "1y")
        risk_type = normalize_risk_type(request.query_params.get("risk_type"))
        return Response(calculate_backtest(benchmark=benchmark, period=period, risk_type=risk_type))


class WatchlistView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, ticker):
        stock = generics.get_object_or_404(Stock, ticker=ticker)
        folder_id = request.data.get("folder_id")
        folder = None
        if folder_id:
            folder = generics.get_object_or_404(WatchlistFolder, pk=folder_id, user=request.user)
        watchlist, created = Watchlist.objects.get_or_create(user=request.user, stock=stock)
        if watchlist.folder_id != (folder.id if folder else None):
            watchlist.folder = folder
            watchlist.save(update_fields=("folder",))
        return Response({"ticker": ticker, "saved": True, "folder": folder.id if folder else None}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def delete(self, request, ticker):
        Watchlist.objects.filter(user=request.user, stock_id=ticker).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WatchlistFolderListCreateView(generics.ListCreateAPIView):
    serializer_class = WatchlistFolderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WatchlistFolder.objects.filter(user=self.request.user).annotate(item_count=Count("items"))

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class WatchlistFolderDetailView(generics.DestroyAPIView):
    serializer_class = WatchlistFolderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WatchlistFolder.objects.filter(user=self.request.user)


class MyWatchlistView(generics.ListAPIView):
    serializer_class = WatchlistEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Watchlist.objects.filter(user=self.request.user)
            .select_related("stock", "folder")
            .prefetch_related("stock__scores", "stock__financial_metrics", "stock__theme_links__theme__group")
            .order_by("folder__name", "-created_at")
        )
