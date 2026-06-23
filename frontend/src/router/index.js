import { createRouter, createWebHistory } from "vue-router";

import CommunityView from "../views/CommunityView.vue";
import CommunityUserActivityView from "../views/CommunityUserActivityView.vue";
import FollowingView from "../views/FollowingView.vue";
import HomeView from "../views/HomeView.vue";
import LoginView from "../views/LoginView.vue";
import MyPageView from "../views/MyPageView.vue";
import NotificationsView from "../views/NotificationsView.vue";
import PortfolioView from "../views/PortfolioView.vue";
import ProfileEditView from "../views/ProfileEditView.vue";
import RegisterView from "../views/RegisterView.vue";
import StockMetricDetailView from "../views/StockMetricDetailView.vue";
import StockReportView from "../views/StockReportView.vue";
import StockSearchView from "../views/StockSearchView.vue";
import WatchlistView from "../views/WatchlistView.vue";

const routes = [
  { path: "/", name: "home", component: HomeView },
  { path: "/portfolio", name: "portfolio", component: PortfolioView },
  { path: "/stocks", name: "stocks", component: StockSearchView },
  { path: "/stocks/:ticker/community", name: "stock-community", component: CommunityView, props: true },
  { path: "/stocks/:ticker", name: "stock-report", component: StockReportView, props: true },
  { path: "/stocks/:ticker/details/:section/:index", name: "metric-detail", component: StockMetricDetailView, props: true },
  { path: "/community", name: "community", component: CommunityView },
  { path: "/community/following", name: "community-following", component: FollowingView },
  { path: "/community/users/:userId", name: "community-user-activity", component: CommunityUserActivityView, props: true },
  { path: "/login", name: "login", component: LoginView },
  { path: "/register", name: "register", component: RegisterView },
  { path: "/mypage", name: "mypage", component: MyPageView },
  { path: "/notifications", name: "notifications", component: NotificationsView },
  { path: "/watchlist", name: "watchlist", component: WatchlistView },
  { path: "/profile/edit", name: "profile-edit", component: ProfileEditView },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 };
  },
});

export default router;
