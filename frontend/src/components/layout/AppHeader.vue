<template>
  <Transition name="toast">
    <div v-if="logoutNotice" class="fixed right-5 top-5 z-50 flex items-center gap-2 rounded-lg border border-[#b9efe7] bg-white px-4 py-3 text-sm font-black text-[#0b8f83] shadow-lg">
      <CircleCheck :size="19" class="text-[#12b8a6]" />
      로그아웃되었습니다.
    </div>
  </Transition>
  <header class="fixed inset-x-0 top-0 z-30 border-b border-white/10 bg-[#0b2454]/95 text-white backdrop-blur">
    <div class="mx-auto flex h-16 max-w-[1500px] items-center justify-between gap-4 px-4">
      <RouterLink to="/" class="flex shrink-0 items-center gap-2 text-xl font-extrabold tracking-tight text-white" aria-label="AlphaPick 홈으로 이동">
        <img class="h-9 w-9 rounded-lg object-cover shadow-lg shadow-cyan-950/20" src="/alphapick-icon.png" alt="AlphaPick 로고" />
        AlphaPick
      </RouterLink>

      <div class="ml-auto flex items-center gap-2">
        <nav class="flex items-center gap-1 overflow-x-auto" aria-label="주요 메뉴">
          <template v-for="item in primaryNav" :key="item.label">
            <RouterLink class="inline-flex min-h-10 items-center gap-2 rounded-lg px-3 text-sm font-bold text-[#d8e8f6] transition hover:bg-white/10 hover:text-white" exact-active-class="bg-[#12b8a6] text-white hover:bg-[#12b8a6] hover:text-white" :to="item.to">
              <component :is="item.icon" :size="19" />
              <span>{{ item.label }}</span>
              <span v-if="item.to === '/notifications' && unreadNotifications" class="inline-flex min-w-5 items-center justify-center rounded-full bg-rose-500 px-1.5 py-0.5 text-[11px] font-black leading-none text-white">
                {{ unreadNotifications > 99 ? "99+" : unreadNotifications }}
              </span>
            </RouterLink>
          </template>
        </nav>

        <div class="relative">
          <button class="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-white/10 bg-white/5 transition hover:bg-white/10" type="button" :aria-expanded="accountMenuOpen" aria-label="계정 메뉴" @click="accountMenuOpen = !accountMenuOpen">
            <img v-if="profileImageUrl" :src="profileImageUrl" class="h-8 w-8 rounded-full object-cover" alt="프로필 사진" />
            <span v-else-if="authStore.isAuthenticated" class="flex h-8 w-8 items-center justify-center rounded-full bg-white/15 text-sm font-black">{{ profileInitial }}</span>
            <User v-else :size="20" />
          </button>

          <div v-if="accountMenuOpen" class="absolute right-0 mt-3 w-56 rounded-lg border border-slate-200 bg-white p-3 text-slate-900 shadow-xl">
            <div class="mb-3 border-b border-slate-100 pb-3">
              <p class="text-sm font-extrabold">{{ authStore.isAuthenticated ? authStore.user?.nickname || authStore.user?.username : "방문자" }}</p>
              <p class="mt-1 text-xs font-bold text-slate-500">{{ authStore.isAuthenticated ? "로그인 중" : "로그인 전" }}</p>
            </div>
            <template v-if="authStore.isAuthenticated">
              <RouterLink class="block rounded-md px-3 py-2 text-sm font-bold hover:bg-slate-50" to="/mypage" @click="accountMenuOpen = false">내 정보</RouterLink>
              <button class="mt-1 block w-full rounded-md px-3 py-2 text-left text-sm font-bold text-rose-600 hover:bg-rose-50" type="button" @click="handleLogout">로그아웃</button>
            </template>
            <template v-else>
              <RouterLink class="block rounded-md px-3 py-2 text-center text-sm font-bold text-slate-700 hover:bg-slate-50" to="/login" @click="accountMenuOpen = false">로그인</RouterLink>
              <RouterLink class="mt-2 block rounded-md bg-[#12b8a6] px-3 py-2 text-center text-sm font-bold text-white hover:bg-[#0fa696]" to="/register" @click="accountMenuOpen = false">회원가입</RouterLink>
            </template>
          </div>
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
  Newspaper,
  User,
} from "@lucide/vue";
import { useAuthStore } from "../../stores/auth";
import { api } from "../../api/client";

const authStore = useAuthStore();
const router = useRouter();
const unreadNotifications = ref(0);
const logoutNotice = ref(false);
const accountMenuOpen = ref(false);
const profileInitial = computed(() => (authStore.user?.nickname || authStore.user?.username || "U").slice(0, 1).toUpperCase());
const profileImageUrl = computed(() => {
  const url = authStore.user?.profile_image_url;
  if (!url || url.startsWith("http")) return url;
  return `http://127.0.0.1:8000${url}`;
});
let notificationTimer = null;
let logoutNoticeTimer = null;

const primaryNav = computed(() => [
  ...(authStore.isAuthenticated
    ? [
        { to: "/watchlist", label: "관심 종목", icon: Heart },
        { to: "/community", label: "커뮤니티", icon: Newspaper },
        { to: "/notifications", label: "알림", icon: Bell },
      ]
    : []),
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
  accountMenuOpen.value = false;
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
