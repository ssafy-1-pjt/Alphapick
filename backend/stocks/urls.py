from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    MyWatchlistView,
    PortfolioBacktestView,
    PortfolioHistoryView,
    StockViewSet,
    ThemeGroupListView,
    TodayPortfolioView,
    WatchlistFolderDetailView,
    WatchlistFolderListCreateView,
    WatchlistView,
)


router = DefaultRouter()
router.register("stocks", StockViewSet, basename="stock")

urlpatterns = [
    path("portfolio/today/", TodayPortfolioView.as_view(), name="portfolio-today"),
    path("portfolio/history/", PortfolioHistoryView.as_view(), name="portfolio-history"),
    path("portfolio/backtest/", PortfolioBacktestView.as_view(), name="portfolio-backtest"),
    path("themes/", ThemeGroupListView.as_view(), name="theme-groups"),
    path("watchlist/folders/", WatchlistFolderListCreateView.as_view(), name="watchlist-folders"),
    path("watchlist/folders/<int:pk>/", WatchlistFolderDetailView.as_view(), name="watchlist-folder-detail"),
    path("watchlist/", MyWatchlistView.as_view(), name="watchlist"),
    path("watchlist/<str:ticker>/", WatchlistView.as_view(), name="watchlist-toggle"),
    path("", include(router.urls)),
]
