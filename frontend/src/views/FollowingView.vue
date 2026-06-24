<template>
  <section class="page-shell py-8">
    <div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
      <div>
        <p class="text-sm font-black text-mint">Community Network</p>
        <h1 class="mt-1 text-3xl font-black text-slate-950">내가 팔로우한 투자자</h1>
        <p class="mt-2 text-slate-600">투자자를 선택하면 작성한 게시글과 댓글 활동을 확인할 수 있습니다.</p>
      </div>
      <RouterLink class="btn-secondary" to="/community">커뮤니티로 돌아가기</RouterLink>
    </div>
    <p v-if="error" class="mt-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 font-bold text-red-700">{{ error }}</p>
    <div v-if="loading" class="panel mt-6 p-8 text-center font-bold text-slate-500">팔로우 목록을 불러오는 중입니다.</div>
    <div v-else-if="users.length" class="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <RouterLink v-for="user in users" :key="user.id" class="panel block p-5 transition hover:-translate-y-0.5 hover:border-mint/50" :to="{ name: 'community-user-activity', params: { userId: user.id } }">
        <p class="text-xl font-black text-slate-950">{{ user.display_name }}</p>
        <p class="mt-1 text-sm text-slate-500">@{{ user.username }}</p>
        <p class="mt-4 text-sm font-bold text-slate-600">팔로워 {{ user.followers_count }} · 팔로우 {{ user.following_count }}</p>
        <span class="mt-4 inline-flex text-sm font-black text-mint">활동 보기</span>
      </RouterLink>
    </div>
    <div v-else class="panel mt-6 p-8 text-center">
      <h2 class="text-xl font-black text-slate-950">아직 팔로우한 투자자가 없습니다.</h2>
      <RouterLink class="btn-primary mt-5" to="/community">커뮤니티 둘러보기</RouterLink>
    </div>
  </section>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api, unwrapList } from "../api/client";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();
const users = ref([]); const loading = ref(true); const error = ref("");
async function loadFollowing() {
  if (!auth.isAuthenticated) return router.replace({ path: "/login", query: { next: route.fullPath } });
  try { const { data } = await api.get("/community/users/following/"); users.value = unwrapList(data); }
  catch (err) { error.value = err.response?.data?.detail || "팔로우 목록을 불러오지 못했습니다."; }
  finally { loading.value = false; }
}
onMounted(loadFollowing);
</script>
