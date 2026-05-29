import { createRouter, createWebHistory } from "vue-router";

import BacktestView from "../views/BacktestView.vue";
import HomeView from "../views/HomeView.vue";
import LoginView from "../views/LoginView.vue";
import MyPageView from "../views/MyPageView.vue";
import ProfileEditView from "../views/ProfileEditView.vue";
import RegisterView from "../views/RegisterView.vue";
import StockMetricDetailView from "../views/StockMetricDetailView.vue";
import StockReportView from "../views/StockReportView.vue";
import StockSearchView from "../views/StockSearchView.vue";

const routes = [
  { path: "/", name: "home", component: HomeView },
  { path: "/stocks", name: "stocks", component: StockSearchView },
  { path: "/stocks/:ticker", name: "stock-report", component: StockReportView, props: true },
  { path: "/stocks/:ticker/details/:section/:index", name: "metric-detail", component: StockMetricDetailView, props: true },
  { path: "/backtest", name: "backtest", component: BacktestView },
  { path: "/login", name: "login", component: LoginView },
  { path: "/register", name: "register", component: RegisterView },
  { path: "/mypage", name: "mypage", component: MyPageView },
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
