<template>
  <header class="z-30 border-b border-slate-200 bg-white/95 backdrop-blur lg:fixed lg:inset-y-0 lg:left-0 lg:w-[220px] lg:border-b-0 lg:border-r lg:border-white/10 lg:bg-[#0b2454] lg:text-white">
    <div class="flex min-h-16 items-center justify-between gap-4 px-4 py-3 lg:min-h-full lg:flex-col lg:items-stretch lg:px-4 lg:py-7">
      <RouterLink to="/" class="flex items-center gap-2 text-xl font-extrabold tracking-tight text-slate-950 lg:text-white">
        <img class="h-9 w-9 rounded-lg object-cover shadow-lg shadow-cyan-950/20" src="/alphapick-icon.png" alt="AlphaPick 로고" />
        AlphaPick
      </RouterLink>

      <nav class="mobile-nav flex items-center gap-1 lg:mt-7 lg:flex-1 lg:flex-col lg:items-stretch lg:gap-2">
        <template v-for="item in primaryNav" :key="item.label">
          <RouterLink v-if="item.to" class="side-nav-link" :to="item.to">
            <component :is="item.icon" :size="19" />
            <span>{{ item.label }}</span>
          </RouterLink>
          <button v-else class="side-nav-link side-nav-link-disabled nav-mobile-hidden" type="button" disabled>
            <component :is="item.icon" :size="19" />
            <span>{{ item.label }}</span>
          </button>
        </template>

        <div class="hidden h-px bg-white/10 lg:my-3 lg:block"></div>

        <template v-if="authStore.isAuthenticated">
          <RouterLink class="side-nav-link" to="/mypage">
            <User :size="19" />
            <span>마이페이지</span>
          </RouterLink>
          <button class="side-nav-link text-left lg:mt-auto" type="button" @click="handleLogout">
            <LogOut :size="19" />
            <span>로그아웃</span>
          </button>
        </template>
        <template v-else>
          <RouterLink class="side-nav-link nav-mobile-hidden" to="/login">
            <LogIn :size="19" />
            <span>로그인</span>
          </RouterLink>
          <RouterLink class="side-nav-link nav-mobile-hidden" to="/register">
            <UserPlus :size="19" />
            <span>회원가입</span>
          </RouterLink>
        </template>
      </nav>

      <div class="hidden rounded-lg border border-white/10 bg-white/5 p-4 lg:block">
        <div class="flex items-center gap-3">
          <div class="flex h-11 w-11 items-center justify-center rounded-full bg-white/15">
            <User :size="21" />
          </div>
          <div>
            <p class="text-sm font-bold">{{ authStore.user?.username || "홍길동" }}</p>
            <p class="mt-1 inline-flex rounded-full bg-[#128ba6]/30 px-2 py-0.5 text-xs font-bold text-[#ddf7f2]">
              {{ authStore.isAuthenticated ? "회원" : "방문자" }}
            </p>
          </div>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { useRouter } from "vue-router";
import {
  Bell,
  Heart,
  LogIn,
  LogOut,
  Newspaper,
  PieChart,
  Search,
  Settings,
  User,
  UserPlus,
} from "@lucide/vue";
import { useAuthStore } from "../../stores/auth";

const authStore = useAuthStore();
const router = useRouter();

const primaryNav = [
  { to: "/portfolio", label: "오늘의 포트폴리오", icon: PieChart },
  { to: "/stocks", label: "종목 검색", icon: Search },
  { label: "관심 종목", icon: Heart },
  { to: "/community", label: "커뮤니티", icon: Newspaper },
  { label: "알림", icon: Bell },
  { label: "설정", icon: Settings },
];

function handleLogout() {
  authStore.logout();
  router.push("/");
}
</script>
