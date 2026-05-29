<template>
  <header class="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
    <div class="page-shell flex min-h-16 items-center justify-between gap-4 py-3">
      <RouterLink to="/" class="flex items-center gap-2 text-xl font-black tracking-tight text-slate-950">
        <LineChart :size="26" class="text-emerald-600" />
        AlphaPick
      </RouterLink>

      <nav class="flex items-center gap-1 sm:gap-2">
        <RouterLink class="btn-ghost text-slate-700" to="/">
          <PieChart :size="18" />
          <span class="hidden sm:inline">포트폴리오</span>
        </RouterLink>
        <RouterLink class="btn-ghost text-slate-700" to="/stocks">
          <Search :size="18" />
          <span class="hidden sm:inline">종목 검색</span>
        </RouterLink>
        <RouterLink class="btn-ghost text-slate-700" to="/backtest">
          <Activity :size="18" />
          <span class="hidden sm:inline">백테스트</span>
        </RouterLink>

        <!-- 인증 관련 링크 -->
        <template v-if="authStore.isAuthenticated">
          <RouterLink class="btn-ghost text-slate-700" to="/mypage">
            <User :size="18" />
            <span class="hidden sm:inline">마이페이지</span>
          </RouterLink>
          <button class="btn-ghost text-rose-600" type="button" @click="handleLogout">
            <LogOut :size="18" />
            <span class="hidden sm:inline">로그아웃</span>
          </button>
        </template>
        <template v-else>
          <RouterLink class="btn-ghost text-slate-700" to="/login">
            <LogIn :size="18" />
            <span class="hidden sm:inline">로그인</span>
          </RouterLink>
          <RouterLink class="btn-ghost text-slate-700" to="/register">
            <UserPlus :size="18" />
            <span class="hidden sm:inline">회원가입</span>
          </RouterLink>
        </template>
      </nav>

      <div class="hidden rounded-full bg-emerald-50 px-3 py-1 text-sm font-bold text-emerald-700 lg:block">
        가치·타이밍 70점+
      </div>
    </div>
  </header>
</template>

<script setup>
import { useRouter } from "vue-router";
import { Activity, LineChart, LogIn, LogOut, PieChart, Search, User, UserPlus } from "@lucide/vue";
import { useAuthStore } from "../../stores/auth";

const authStore = useAuthStore();
const router = useRouter();

function handleLogout() {
  authStore.logout();
  router.push("/");
}
</script>
