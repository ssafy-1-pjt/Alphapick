<template>
  <section class="page-shell py-8">
    <div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
      <div>
        <p class="text-xs font-bold uppercase tracking-[0.16em] text-mint break-keep">MY WATCHLIST</p>
        <h1 class="mt-1 text-3xl font-black text-slate-950 break-keep text-balance">관심 종목</h1>
        <p class="mt-2 text-slate-600 break-keep text-pretty">폴더와 검색으로 저장한 종목을 빠르게 관리하세요.</p>
      </div>
      <RouterLink class="btn-secondary" to="/stocks">종목 찾기</RouterLink>
    </div>

    <p v-if="error" class="mt-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 font-bold text-red-700">{{ error }}</p>
    <div v-if="loading" class="panel mt-6 p-8 text-center font-bold text-slate-500">관심 종목을 불러오는 중입니다.</div>

    <template v-else>
      <div class="panel mt-6 p-4">
        <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <input v-model.trim="query" class="field lg:max-w-md" placeholder="종목명, 티커, 업종으로 검색" />
          <form class="flex gap-2" @submit.prevent="createFolder"><input v-model.trim="folderName" class="field min-h-0 py-2" maxlength="40" placeholder="새 폴더 이름" /><button class="btn-primary min-h-0 shrink-0 px-4 py-2" type="submit">폴더 추가</button></form>
        </div>
        <div class="mt-4 flex flex-wrap gap-2">
          <button class="rounded-full px-3 py-1.5 text-sm font-black" :class="activeFolder === 'all' ? 'bg-mint text-white' : 'bg-slate-100 text-slate-600'" type="button" @click="activeFolder = 'all'">전체 {{ entries.length }}</button>
          <button class="rounded-full px-3 py-1.5 text-sm font-black" :class="activeFolder === 'none' ? 'bg-mint text-white' : 'bg-slate-100 text-slate-600'" type="button" @click="activeFolder = 'none'">미분류 {{ uncategorizedCount }}</button>
          <div v-for="folder in folders" :key="folder.id" class="inline-flex items-center rounded-full bg-slate-100 pr-1 text-sm font-black text-slate-600">
            <button class="px-3 py-1.5" :class="activeFolder === String(folder.id) ? 'text-mint' : ''" type="button" @click="activeFolder = String(folder.id)">{{ folder.name }} {{ folder.item_count }}</button>
            <button class="rounded-full px-2 py-1 text-slate-400 hover:bg-rose-50 hover:text-rose-600" type="button" :aria-label="`${folder.name} 폴더 삭제`" @click="deleteFolder(folder)">×</button>
          </div>
        </div>
      </div>

      <div v-if="filteredEntries.length" class="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <article v-for="entry in filteredEntries" :key="entry.id" class="panel p-5">
          <div class="flex items-start justify-between gap-3"><div><RouterLink class="text-xl font-black text-slate-950 hover:text-mint" :to="{ name: 'stock-report', params: { ticker: entry.stock.ticker } }">{{ entry.stock.name }}</RouterLink><p class="mt-1 text-sm text-slate-500">{{ entry.stock.ticker }} · {{ entry.stock.sector }}</p></div><button class="btn-ghost min-h-0 px-2 py-1 text-sm text-red-600" type="button" @click="remove(entry)">삭제</button></div>
          <div class="mt-4 flex items-end justify-between gap-3"><div><p class="text-xs font-bold text-slate-400">종합 점수</p><p class="mt-1 text-3xl font-black text-mint">{{ entry.stock.latest_score ?? "-" }}</p></div><p class="text-right text-sm font-bold text-slate-600">{{ entry.stock.key_reason || entry.stock.reason || "분석 데이터 준비 중" }}</p></div>
          <label class="mt-4 block text-xs font-black text-slate-500">폴더<select class="field mt-1 min-h-0 py-2 text-sm" :value="entry.folder?.id || ''" @change="moveEntry(entry, $event.target.value)"><option value="">미분류</option><option v-for="folder in folders" :key="folder.id" :value="folder.id">{{ folder.name }}</option></select></label>
        </article>
      </div>
      <div v-else class="panel mt-6 p-8 text-center"><h2 class="text-xl font-black text-slate-950">표시할 관심 종목이 없습니다.</h2><p class="mt-2 text-slate-600">검색어 또는 폴더 조건을 변경해 보세요.</p></div>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api, unwrapList } from "../api/client";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore(); const route = useRoute(); const router = useRouter();
const entries = ref([]); const folders = ref([]); const loading = ref(true); const error = ref("");
const query = ref(""); const folderName = ref(""); const activeFolder = ref("all");
const uncategorizedCount = computed(() => entries.value.filter((entry) => !entry.folder).length);
const filteredEntries = computed(() => {
  const normalized = query.value.toLowerCase();
  return entries.value.filter((entry) => {
    const folderMatches = activeFolder.value === "all" || (activeFolder.value === "none" ? !entry.folder : String(entry.folder?.id) === activeFolder.value);
    const searchSource = [entry.stock.name, entry.stock.ticker, entry.stock.sector, ...(entry.stock.themes || [])].join(" ").toLowerCase();
    return folderMatches && (!normalized || searchSource.includes(normalized));
  });
});
async function load() {
  if (!auth.isAuthenticated) return router.replace({ path: "/login", query: { next: route.fullPath } });
  try { const [entryResponse, folderResponse] = await Promise.all([api.get("/watchlist/"), api.get("/watchlist/folders/")]); entries.value = unwrapList(entryResponse.data); folders.value = unwrapList(folderResponse.data); }
  catch (err) { error.value = err.response?.data?.detail || "관심 종목을 불러오지 못했습니다."; }
  finally { loading.value = false; }
}
async function createFolder() {
  if (!folderName.value) return;
  try { await api.post("/watchlist/folders/", { name: folderName.value }); folderName.value = ""; await load(); }
  catch (err) { error.value = err.response?.data?.name?.[0] || "폴더를 만들지 못했습니다."; }
}
async function deleteFolder(folder) {
  try { await api.delete(`/watchlist/folders/${folder.id}/`); if (activeFolder.value === String(folder.id)) activeFolder.value = "all"; await load(); }
  catch { error.value = "폴더를 삭제하지 못했습니다."; }
}
async function moveEntry(entry, folderId) {
  try { await api.post(`/watchlist/${entry.stock.ticker}/`, { folder_id: folderId || null }); await load(); }
  catch { error.value = "종목 폴더를 변경하지 못했습니다."; }
}
async function remove(entry) {
  try { await api.delete(`/watchlist/${entry.stock.ticker}/`); await load(); }
  catch { error.value = "관심 종목을 삭제하지 못했습니다."; }
}
onMounted(load);
</script>
