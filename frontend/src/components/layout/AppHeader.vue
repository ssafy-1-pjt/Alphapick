<template>
  <Transition name="toast">
    <div v-if="logoutNotice" class="fixed right-5 top-5 z-50 flex items-center gap-2 rounded-lg border border-emerald-200 bg-white px-4 py-3 text-sm font-black text-emerald-800 shadow-lg">
      <CircleCheck :size="19" class="text-emerald-600" />
      로그아웃되었습니다.
    </div>
  </Transition>
  <header class="z-30 border-b border-slate-200 bg-white/95 backdrop-blur lg:fixed lg:inset-y-0 lg:left-0 lg:w-[220px] lg:border-b-0 lg:border-r lg:border-white/10 lg:bg-[#0b2454] lg:text-white">
    <div class="flex min-h-16 items-center justify-between gap-4 px-4 py-3 lg:min-h-full lg:flex-col lg:items-stretch lg:px-4 lg:py-7">
      <RouterLink to="/" class="flex items-center gap-2 text-xl font-extrabold tracking-tight text-slate-950 lg:text-white">
        <img class="h-9 w-9 rounded-lg object-cover shadow-lg shadow-cyan-950/20" src="/alphapick-icon.png" alt="AlphaPick 로고" />
        AlphaPick
      </RouterLink>

      <nav class="flex items-center gap-1 overflow-x-auto lg:mt-7 lg:flex-1 lg:flex-col lg:items-stretch lg:gap-2 lg:overflow-visible">
        <template v-for="item in primaryNav" :key="item.label">
          <RouterLink class="side-nav-link" exact-active-class="side-nav-link-active" :to="item.to">
            <component :is="item.icon" :size="19" />
            <span>{{ item.label }}</span>
          </RouterLink>
        </template>

        <div class="hidden h-px bg-white/10 lg:my-3 lg:block"></div>

        <template v-if="authStore.isAuthenticated">
          <RouterLink class="side-nav-link" exact-active-class="side-nav-link-active" to="/community/following">
            <Users :size="19" />
            <span>팔로잉</span>
          </RouterLink>
          <RouterLink class="side-nav-link relative" exact-active-class="side-nav-link-active" to="/notifications">
            <Bell :size="19" />
            <span>알림</span>
            <span v-if="unreadNotifications" class="ml-auto inline-flex min-w-5 items-center justify-center rounded-full bg-rose-500 px-1.5 py-0.5 text-[11px] font-black leading-none text-white">
              {{ unreadNotifications > 99 ? "99+" : unreadNotifications }}
            </span>
          </RouterLink>
          <button class="side-nav-link text-left lg:mt-auto" type="button" @click="handleLogout">
            <LogOut :size="19" />
            <span>로그아웃</span>
          </button>
        </template>
        <template v-else>
          <RouterLink class="side-nav-link" exact-active-class="side-nav-link-active" to="/login">
            <LogIn :size="19" />
            <span>로그인</span>
          </RouterLink>
          <RouterLink class="side-nav-link" exact-active-class="side-nav-link-active" to="/register">
            <UserPlus :size="19" />
            <span>회원가입</span>
          </RouterLink>
        </template>
      </nav>

      <RouterLink v-if="authStore.isAuthenticated" class="hidden rounded-lg border border-white/10 bg-white/5 p-4 transition hover:border-[#35c5b8]/70 hover:bg-white/10 lg:block" to="/mypage">
        <div class="flex items-center gap-3">
          <img v-if="profileImageUrl" :src="profileImageUrl" class="h-11 w-11 rounded-full border border-white/20 object-cover" alt="프로필 사진" />
          <div v-else class="flex h-11 w-11 items-center justify-center rounded-full bg-white/15 font-black">
            {{ profileInitial }}
          </div>
          <div>
            <p class="text-sm font-bold">{{ authStore.user?.nickname || authStore.user?.username }}</p>
            <p class="mt-1 text-xs font-bold text-[#ddf7f2]">내 정보 · 프로필 수정</p>
          </div>
        </div>
      </RouterLink>
      <div v-else class="hidden rounded-lg border border-white/10 bg-white/5 p-4 lg:block">
        <div class="flex items-center gap-3">
          <div class="flex h-11 w-11 items-center justify-center rounded-full bg-white/15"><User :size="21" /></div>
          <div><p class="text-sm font-bold">방문자</p><p class="mt-1 text-xs font-bold text-[#ddf7f2]">로그인 후 프로필을 설정하세요</p></div>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import {
  Heart,
  Bell,
  CircleCheck,
  LogIn,
  LogOut,
  Newspaper,
  PieChart,
  Search,
  User,
  UserPlus,
  Users,
} from "@lucide/vue";
import { useAuthStore } from "../../stores/auth";
import { api } from "../../api/client";

const authStore = useAuthStore();
const router = useRouter();
const unreadNotifications = ref(0);
const logoutNotice = ref(false);
const profileInitial = computed(() => (authStore.user?.nickname || authStore.user?.username || "U").slice(0, 1).toUpperCase());
const profileImageUrl = computed(() => {
  const url = authStore.user?.profile_image_url;
  if (!url || url.startsWith("http")) return url;
  return `http://127.0.0.1:8000${url}`;
});
let notificationTimer = null;
let logoutNoticeTimer = null;

const primaryNav = computed(() => [
  { to: "/portfolio", label: "오늘의 포트폴리오", icon: PieChart },
  { to: "/stocks", label: "종목 검색", icon: Search },
  ...(authStore.isAuthenticated ? [{ to: "/watchlist", label: "관심 종목", icon: Heart }] : []),
  { to: "/community", label: "커뮤니티", icon: Newspaper },
]);

async function loadUnreadNotifications() {
  if (!authStore.isAuthenticated) {
    unreadNotifications.value = 0;
    return;
  }
  try {
    const { data } = await api.get("/community/notifications/unread-count/");
    unreadNotifications.value = data.unread_count || 0;
  } catch {
    unreadNotifications.value = 0;
  }
}

function startNotificationPolling() {
  window.clearInterval(notificationTimer);
  loadUnreadNotifications();
  if (authStore.isAuthenticated) {
    notificationTimer = window.setInterval(loadUnreadNotifications, 30000);
  }
}

watch(() => authStore.isAuthenticated, startNotificationPolling);
onMounted(() => {
  startNotificationPolling();
  window.addEventListener("notifications-updated", loadUnreadNotifications);
});
onBeforeUnmount(() => {
  window.clearInterval(notificationTimer);
  window.clearTimeout(logoutNoticeTimer);
  window.removeEventListener("notifications-updated", loadUnreadNotifications);
});

function handleLogout() {
  authStore.logout();
  unreadNotifications.value = 0;
  logoutNotice.value = true;
  window.clearTimeout(logoutNoticeTimer);
  logoutNoticeTimer = window.setTimeout(() => { logoutNotice.value = false; }, 2800);
  router.push("/");
}
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(-0.5rem);
}
</style>
