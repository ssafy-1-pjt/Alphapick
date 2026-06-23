<template>
  <section class="page-shell py-8">
    <div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
      <div>
        <p class="text-sm font-black text-emerald-600">내 활동</p>
        <h1 class="mt-1 text-3xl font-black text-slate-950">알림</h1>
        <p class="mt-2 text-slate-600">내 게시글과 댓글에 새로 달린 의견을 확인하세요.</p>
      </div>
      <button v-if="notifications.some((item) => !item.is_read)" class="btn-secondary" type="button" :disabled="markingAll" @click="markAllRead">
        모두 읽음 처리
      </button>
    </div>

    <p v-if="error" class="mt-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 font-bold text-red-700">{{ error }}</p>
    <div v-else-if="loading" class="panel mt-6 p-8 text-center font-bold text-slate-500">알림을 불러오는 중입니다.</div>

    <div v-else class="panel mt-6 overflow-hidden">
      <button
        v-for="notification in notifications"
        :key="notification.id"
        class="flex w-full items-start gap-4 border-b border-slate-100 px-5 py-4 text-left transition last:border-b-0 hover:bg-slate-50"
        :class="notification.is_read ? 'bg-white' : 'bg-emerald-50/60'"
        type="button"
        @click="openNotification(notification)"
      >
        <span class="mt-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-full" :class="notification.kind === 'reply' ? 'bg-violet-100 text-violet-700' : 'bg-emerald-100 text-emerald-700'">
          <MessageCircle :size="19" />
        </span>
        <span class="min-w-0 flex-1">
          <span class="flex flex-wrap items-center gap-x-2 gap-y-1">
            <strong class="font-black text-slate-950">{{ notification.actor.display_name }}</strong>
            <span class="text-sm text-slate-700">{{ notificationText(notification) }}</span>
            <span v-if="!notification.is_read" class="h-2 w-2 rounded-full bg-emerald-500" aria-label="읽지 않음"></span>
          </span>
          <span class="mt-1 block truncate text-sm font-bold text-slate-500">{{ contextText(notification) }}</span>
          <span class="mt-1 block text-xs text-slate-400">{{ formatDate(notification.created_at) }}</span>
        </span>
        <ChevronRight :size="18" class="mt-2 shrink-0 text-slate-400" />
      </button>

      <div v-if="!notifications.length" class="p-10 text-center">
        <Bell :size="36" class="mx-auto text-slate-300" />
        <p class="mt-3 font-black text-slate-700">새 알림이 없습니다.</p>
        <p class="mt-1 text-sm text-slate-500">게시글이나 댓글에 새 의견이 달리면 이곳에 표시됩니다.</p>
      </div>
    </div>
  </section>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { Bell, ChevronRight, MessageCircle } from "@lucide/vue";
import { api, unwrapList } from "../api/client";

const router = useRouter();
const notifications = ref([]);
const loading = ref(true);
const markingAll = ref(false);
const error = ref("");

function formatDate(value) {
  return value ? new Intl.DateTimeFormat("ko-KR", { month: "long", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(value)) : "";
}

function notificationText(notification) {
  if (notification.kind === "follow") return "님이 회원님을 팔로우했습니다.";
  if (notification.kind === "like") return "님이 회원님의 게시글을 좋아합니다.";
  return notification.kind === "reply" ? "님이 회원님의 댓글에 답글을 남겼습니다." : "님이 회원님의 게시글에 댓글을 남겼습니다.";
}

function contextText(notification) {
  if (notification.kind === "follow") return "프로필을 확인하고 작성한 활동을 둘러보세요.";
  return notification.post_title || "삭제된 게시글";
}

function notificationDestination(notification) {
  if (notification.kind === "follow") {
    return { name: "community-user-activity", params: { userId: notification.actor.id } };
  }
  const hash = notification.comment_id ? `#comment-${notification.comment_id}` : "";
  if (notification.post_stock) {
    return { name: "stock-community", params: { ticker: notification.post_stock }, hash };
  }
  return { name: "community", hash };
}

async function loadNotifications() {
  loading.value = true;
  error.value = "";
  try {
    const { data } = await api.get("/community/notifications/");
    notifications.value = unwrapList(data);
  } catch (err) {
    error.value = err.response?.data?.detail || "알림을 불러오지 못했습니다.";
  } finally {
    loading.value = false;
  }
}

async function openNotification(notification) {
  if (!notification.is_read) {
    try {
      await api.post(`/community/notifications/${notification.id}/read/`);
      notification.is_read = true;
      window.dispatchEvent(new Event("notifications-updated"));
    } catch {
      error.value = "알림 읽음 상태를 변경하지 못했습니다.";
      return;
    }
  }
  await router.push(notificationDestination(notification));
}

async function markAllRead() {
  markingAll.value = true;
  try {
    await api.post("/community/notifications/read-all/");
    notifications.value.forEach((notification) => { notification.is_read = true; });
    window.dispatchEvent(new Event("notifications-updated"));
  } catch {
    error.value = "알림을 읽음 처리하지 못했습니다.";
  } finally {
    markingAll.value = false;
  }
}

onMounted(loadNotifications);
</script>
