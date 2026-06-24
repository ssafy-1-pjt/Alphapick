<template>
  <section class="page-shell py-8">
    <p v-if="error" class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 font-bold text-red-700">{{ error }}</p>
    <div v-else-if="loading" class="panel p-8 text-center font-bold text-slate-500">투자자 활동을 불러오는 중입니다.</div>
    <template v-else-if="activity">
      <div class="panel p-6">
        <div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <p class="text-sm font-black text-mint">Investor Profile</p>
            <h1 class="mt-1 text-3xl font-black text-slate-950">{{ activity.user.display_name }}</h1>
            <p class="mt-1 text-slate-500">@{{ activity.user.username }} · 팔로워 {{ activity.user.followers_count }} · 팔로우 {{ activity.user.following_count }}</p>
          </div>
          <div class="flex flex-wrap gap-3">
            <button v-if="auth.isAuthenticated && !activity.user.is_me" class="inline-flex min-h-12 items-center gap-2 rounded-lg px-6 text-base font-black shadow-sm transition" :class="activity.user.is_following ? 'border border-mint/30 bg-mint/5 text-mint' : 'bg-mint text-white'" type="button" :disabled="followLoading" @click="toggleFollow">
              <UserCheck v-if="activity.user.is_following" :size="20" /><UserPlus v-else :size="20" />
              {{ activity.user.is_following ? "팔로우 중" : "팔로우" }}
            </button>
            <RouterLink class="btn-secondary min-h-12 px-5" to="/community/following">팔로잉 목록</RouterLink>
          </div>
        </div>
      </div>

      <div class="mt-6 grid gap-6 lg:grid-cols-2">
        <section>
          <h2 class="text-xl font-black text-slate-950">작성 게시글 <span class="text-mint">{{ activity.posts.length }}</span></h2>
          <div class="mt-3 space-y-3" :class="{ 'activity-scroll': activity.posts.length > 8 }">
            <article v-for="post in activity.posts" :key="post.id" class="panel p-4">
              <RouterLink v-if="post.stock" class="text-xs font-black text-mint hover:underline" :to="postDestination(post)">{{ post.stock_name || post.stock }} 토론방</RouterLink>
              <h3 class="mt-1 text-lg font-black text-slate-950">{{ post.title }}</h3>
              <p class="mt-2 whitespace-pre-line text-sm leading-6 text-slate-700">{{ post.content }}</p>
              <div class="mt-3 flex items-center justify-between gap-3"><p class="text-xs font-bold text-slate-400">{{ formatDate(post.created_at) }} · 댓글 {{ post.comments_count }}</p><RouterLink class="text-xs font-black text-mint hover:underline" :to="postDestination(post)">원문 보기</RouterLink></div>
            </article>
            <p v-if="!activity.posts.length" class="rounded-lg bg-slate-50 p-4 text-sm text-slate-500">작성한 게시글이 없습니다.</p>
          </div>
        </section>
        <section>
          <h2 class="text-xl font-black text-slate-950">작성 댓글 <span class="text-mint">{{ activity.comments.length }}</span></h2>
          <div class="mt-3 space-y-3" :class="{ 'activity-scroll': activity.comments.length > 8 }">
            <article v-for="comment in activity.comments" :key="comment.id" class="panel p-4">
              <p class="text-xs font-black text-slate-400">{{ comment.post_title }}</p>
              <p class="mt-2 whitespace-pre-line text-sm leading-6 text-slate-700">{{ comment.content }}</p>
              <div class="mt-3 flex items-center justify-between gap-3"><p class="text-xs font-bold text-slate-400">{{ formatDate(comment.created_at) }}</p><RouterLink class="text-xs font-black text-mint hover:underline" :to="commentDestination(comment)">원문 댓글 보기</RouterLink></div>
            </article>
            <p v-if="!activity.comments.length" class="rounded-lg bg-slate-50 p-4 text-sm text-slate-500">작성한 댓글이 없습니다.</p>
          </div>
        </section>
      </div>
    </template>
  </section>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { UserCheck, UserPlus } from "@lucide/vue";
import { api } from "../api/client";
import { useAuthStore } from "../stores/auth";

const props = defineProps({ userId: { type: [String, Number], required: true } });
const auth = useAuthStore(); const activity = ref(null); const loading = ref(true); const followLoading = ref(false); const error = ref("");
const formatDate = (value) => value ? new Intl.DateTimeFormat("ko-KR", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(value)) : "";
const postDestination = (post) => post.stock ? { name: "stock-community", params: { ticker: post.stock }, hash: `#post-${post.id}` } : { name: "community", hash: `#post-${post.id}` };
const commentDestination = (comment) => comment.post_stock ? { name: "stock-community", params: { ticker: comment.post_stock }, hash: `#comment-${comment.id}` } : { name: "community", hash: `#comment-${comment.id}` };
async function loadActivity() { try { const { data } = await api.get(`/community/users/${props.userId}/activity/`); activity.value = data; } catch (err) { error.value = err.response?.data?.detail || "투자자 활동을 불러오지 못했습니다."; } finally { loading.value = false; } }
async function toggleFollow() { followLoading.value = true; try { const { data } = await api.post(`/community/users/${activity.value.user.id}/follow/`); activity.value.user = data.user; } catch (err) { error.value = err.response?.data?.detail || "팔로우 상태를 변경하지 못했습니다."; } finally { followLoading.value = false; } }
onMounted(loadActivity);
</script>

<style scoped>
.activity-scroll {
  max-height: 44rem;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding-right: 0.5rem;
  scrollbar-gutter: stable;
}

.activity-scroll::-webkit-scrollbar {
  width: 0.55rem;
}

.activity-scroll::-webkit-scrollbar-track {
  background: #e2e8f0;
  border-radius: 999px;
}

.activity-scroll::-webkit-scrollbar-thumb {
  background: #94a3b8;
  border-radius: 999px;
}

.activity-scroll::-webkit-scrollbar-thumb:hover {
  background: #64748b;
}
</style>
