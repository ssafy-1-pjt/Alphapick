<template>
  <section class="page-shell py-8">
    <div v-if="isStockRoom" class="rounded-lg border border-[#b9efe7] bg-[#e8fbf7] p-6 md:p-7">
      <div class="flex flex-col justify-between gap-5 md:flex-row md:items-center">
        <div class="flex items-start gap-4">
          <span class="flex h-14 w-14 shrink-0 items-center justify-center rounded-lg bg-mint text-white">
            <MessageCircle :size="30" />
          </span>
          <div>
            <p class="text-sm font-black text-mint break-keep">종목 토론방</p>
            <h1 class="mt-1 text-3xl font-black text-slate-950 break-keep text-balance md:text-4xl">{{ stock?.name || "종목" }} 토론방</h1>
            <p class="mt-2 text-slate-600 break-keep text-pretty">실적, 수급, 주가 흐름과 투자 판단을 나누는 공간입니다.</p>
          </div>
        </div>
        <RouterLink class="btn-secondary shrink-0" :to="{ name: 'stock-report', params: { ticker } }">
          <ArrowLeft :size="18" />
          종목 리포트로 돌아가기
        </RouterLink>
      </div>
    </div>

    <div v-else class="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
      <div>
        <p class="text-xs font-bold uppercase tracking-[0.16em] text-mint break-keep">COMMUNITY</p>
        <h1 class="mt-1 text-3xl font-black text-slate-950 break-keep text-balance">투자자 커뮤니티</h1>
        <p class="mt-2 text-slate-600 break-keep text-pretty">종목별 투자 의견을 확인하고 토론방으로 이동하세요.</p>
      </div>
      <RouterLink class="btn-primary" to="/stocks">토론할 종목 찾기</RouterLink>
    </div>

    <p v-if="error" class="mt-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 font-bold text-red-700">{{ error }}</p>
    <div v-if="moderationAlert" class="fixed right-5 top-5 z-50 flex max-w-md items-start gap-3 rounded-lg border border-rose-200 bg-white p-4 text-rose-800 shadow-xl" role="alert">
      <span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-rose-100 font-black">!</span>
      <p class="text-sm font-bold leading-6">{{ moderationAlert }}</p>
      <button class="ml-auto text-lg font-black text-rose-500" type="button" aria-label="알림 닫기" @click="moderationAlert = ''">×</button>
    </div>

    <main class="mt-7 min-w-0 space-y-4">
      <form v-if="isStockRoom && auth.isAuthenticated" class="panel border-mint/30 p-5" @submit.prevent="createPost">
        <h2 class="text-lg font-black text-slate-950">{{ stock?.name }} 의견 작성</h2>
        <input v-model.trim="postForm.title" class="field mt-3" maxlength="120" placeholder="제목" required />
        <textarea v-model.trim="postForm.content" class="field mt-3 min-h-24 resize-y" placeholder="종목에 대한 의견과 근거를 작성해 주세요." required />
        <button class="btn-primary mt-3" type="submit" :disabled="isSubmittingPost">
          <Send :size="17" />
          {{ isSubmittingPost ? "등록 중" : "게시글 등록" }}
        </button>
      </form>

      <div v-else-if="isStockRoom" class="panel p-5">
        <h2 class="text-lg font-black text-slate-950">로그인하고 의견을 남겨 보세요</h2>
        <p class="mt-1 text-sm text-slate-600">게시글, 좋아요, 댓글, 팔로우는 로그인한 사용자만 사용할 수 있습니다.</p>
        <RouterLink class="btn-primary mt-4" :to="loginRoute">로그인</RouterLink>
      </div>

      <div v-if="isLoading" class="panel p-8 text-center font-bold text-slate-500">토론 내용을 불러오는 중입니다.</div>

      <article :id="`post-${post.id}`" v-for="post in posts" :key="post.id" class="panel scroll-mt-6 overflow-hidden">
        <div class="p-4 sm:p-5">
          <div class="flex flex-col justify-between gap-3 md:flex-row md:items-start">
            <div class="flex min-w-0 items-start gap-3">
              <RouterLink class="mt-0.5 shrink-0" :to="{ name: 'community-user-activity', params: { userId: post.author.id } }" :aria-label="`${post.author.display_name} 프로필`">
                <img v-if="profileImageUrl(post.author)" :src="profileImageUrl(post.author)" class="h-10 w-10 rounded-full border border-slate-200 object-cover" :alt="`${post.author.display_name} 프로필 사진`" />
                <span v-else class="flex h-10 w-10 items-center justify-center rounded-full bg-mint/10 text-sm font-black text-mint">{{ profileInitial(post.author) }}</span>
              </RouterLink>
              <div class="min-w-0">
                <div class="flex flex-wrap items-center gap-2 text-sm font-bold">
                  <RouterLink class="text-mint hover:underline" :to="{ name: 'community-user-activity', params: { userId: post.author.id } }">
                    {{ post.author.display_name }}
                  </RouterLink>
                  <span class="text-slate-400">{{ formatDate(post.created_at) }}</span>
                  <RouterLink v-if="!isStockRoom && post.stock" class="badge bg-mint/10 text-mint" :to="{ name: 'stock-community', params: { ticker: post.stock } }">
                    {{ post.stock_name || post.stock }} 토론방
                  </RouterLink>
                </div>
                <h2 class="mt-1 text-xl font-black leading-7 text-slate-950 break-keep text-balance">{{ post.title }}</h2>
              </div>
            </div>
            <div class="flex shrink-0 items-center gap-2">
              <button v-if="post.can_edit" class="btn-ghost min-h-0 px-2 py-1 text-sm text-red-600 hover:bg-red-50" type="button" @click="deletePost(post)">
                <Trash2 :size="16" />
                삭제
              </button>
            </div>
          </div>
          <p class="ml-[52px] mt-3 whitespace-pre-line text-sm leading-6 text-slate-700 break-keep text-pretty">{{ post.content }}</p>
          <div class="ml-[52px] mt-4 flex items-center gap-3">
            <button class="btn-secondary min-h-0 px-3 py-1.5 text-sm active:scale-[0.97]" :class="post.liked_by_me ? 'border-rose-200 bg-rose-50 text-rose-600' : ''" type="button" :disabled="likeLoadingIds[post.id]" @click="toggleLike(post)">
              <Heart :size="17" :fill="post.liked_by_me ? 'currentColor' : 'none'" /> 좋아요 {{ post.likes_count }}
            </button>
            <span class="inline-flex items-center gap-1 text-sm font-bold text-slate-500"><MessageCircle :size="16" /> 댓글 {{ post.comments_count }}</span>
          </div>
        </div>

        <div class="border-t border-slate-100 bg-slate-50/70 p-4 sm:p-5">
          <div class="flex items-center justify-between gap-3">
            <h3 class="text-sm font-black text-slate-950">댓글</h3>
            <button v-if="post.comments.length > commentPreviewCount" class="text-xs font-black text-mint" type="button" @click="post.commentsExpanded = !post.commentsExpanded">
              {{ post.commentsExpanded ? "댓글 접기" : `댓글 전체 보기 (${post.comments.length})` }}
            </button>
          </div>
          <div class="mt-2 space-y-2">
            <div :id="`comment-${comment.id}`" v-for="comment in visibleComments(post)" :key="comment.id" class="scroll-mt-6 rounded-lg border border-slate-200 bg-white px-3 py-2">
              <div class="flex items-start justify-between gap-3">
                <div>
                  <RouterLink class="text-xs font-black text-mint hover:underline" :to="{ name: 'community-user-activity', params: { userId: comment.author.id } }">{{ comment.author.display_name }}</RouterLink>
                  <span class="ml-1 text-xs text-slate-400">{{ formatDate(comment.created_at) }}</span>
                  <p class="mt-1 whitespace-pre-line text-sm leading-5 text-slate-700 break-keep text-pretty">{{ comment.content }}</p>
                </div>
                <div class="flex shrink-0 items-center gap-1">
                  <button v-if="auth.isAuthenticated" class="btn-ghost min-h-0 px-2 py-1 text-xs text-mint" type="button" @click="replyingToId = replyingToId === comment.id ? null : comment.id">답글</button>
                  <button v-if="comment.can_delete" class="btn-ghost min-h-0 px-2 py-1 text-xs text-red-600" type="button" @click="deleteComment(post, comment)">삭제</button>
                </div>
              </div>
              <div v-for="reply in comment.replies || []" :id="`comment-${reply.id}`" :key="reply.id" class="ml-5 mt-2 border-l-2 border-mint/20 pl-3">
                <div class="flex items-start justify-between gap-3"><div><RouterLink class="text-xs font-black text-mint hover:underline" :to="{ name: 'community-user-activity', params: { userId: reply.author.id } }">{{ reply.author.display_name }}</RouterLink><span class="ml-1 text-xs text-slate-400">{{ formatDate(reply.created_at) }}</span><p class="mt-1 whitespace-pre-line text-sm leading-5 text-slate-700 break-keep text-pretty">{{ reply.content }}</p></div><button v-if="reply.can_delete" class="btn-ghost min-h-0 px-2 py-1 text-xs text-red-600" type="button" @click="deleteComment(post, reply)">삭제</button></div>
              </div>
              <form v-if="auth.isAuthenticated && replyingToId === comment.id" class="mt-3 flex flex-col gap-2 border-t border-slate-100 pt-3 sm:flex-row" @submit.prevent="createReply(post, comment)">
                <input v-model.trim="replyDrafts[comment.id]" class="field min-h-0 py-2 text-sm" placeholder="답글을 입력하세요" maxlength="600" />
                <button class="btn-secondary min-h-0 shrink-0 px-3 py-2 text-sm active:scale-[0.97]" type="submit">답글 등록</button>
              </form>
            </div>
            <p v-if="!post.comments.length" class="rounded-lg bg-white px-3 py-2 text-sm text-slate-500">아직 댓글이 없습니다.</p>
          </div>
          <form v-if="auth.isAuthenticated" class="mt-3 flex flex-col gap-2 sm:flex-row" @submit.prevent="createComment(post)">
            <input v-model.trim="commentDrafts[post.id]" class="field min-h-0 py-2 text-sm" placeholder="댓글을 입력하세요" maxlength="600" />
            <button class="btn-primary min-h-0 shrink-0 px-3 py-2 text-sm active:scale-[0.97]" type="submit"><Send :size="16" /> 등록</button>
          </form>
        </div>
      </article>

      <div v-if="!isLoading && !posts.length" class="panel p-8 text-center">
        <MessageCircle :size="36" class="mx-auto text-slate-300" />
        <p class="mt-3 font-black text-slate-700">아직 작성된 게시글이 없습니다.</p>
      </div>
    </main>
  </section>
</template>

<script setup>
import { computed, nextTick, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ArrowLeft, Heart, MessageCircle, Send, Trash2 } from "@lucide/vue";
import { api, unwrapList } from "../api/client";
import { useAuthStore } from "../stores/auth";
import { containsProhibitedLanguage, moderationNotice } from "../utils/moderation";

const props = defineProps({ ticker: { type: String, default: "" } });
const auth = useAuthStore();
const route = useRoute();
const router = useRouter();
const stock = ref(null);
const posts = ref([]);
const error = ref("");
const moderationAlert = ref("");
const isLoading = ref(false);
const isSubmittingPost = ref(false);
const followLoadingId = ref(null);
const likeLoadingIds = reactive({});
const commentDrafts = reactive({});
const replyDrafts = reactive({});
const replyingToId = ref(null);
const postForm = reactive({ title: "", content: "" });
const commentPreviewCount = 2;
const isStockRoom = computed(() => Boolean(props.ticker));
const loginRoute = computed(() => ({ path: "/login", query: { next: route.fullPath } }));

function showModerationAlert() {
  moderationAlert.value = moderationNotice;
  window.setTimeout(() => { moderationAlert.value = ""; }, 4500);
}

function formatDate(value) {
  return value ? new Intl.DateTimeFormat("ko-KR", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(value)) : "";
}
function visibleComments(post) {
  return post.commentsExpanded ? post.comments : post.comments.slice(0, commentPreviewCount);
}
function profileImageUrl(user) {
  const url = user?.profile_image_url;
  if (!url || url.startsWith("http")) return url;
  return `http://127.0.0.1:8000${url}`;
}
function profileInitial(user) {
  return (user?.display_name || user?.username || "U").slice(0, 1).toUpperCase();
}
function requireLogin() { router.push(loginRoute.value); }
async function loadStock() {
  if (!props.ticker) return (stock.value = null);
  const { data } = await api.get(`/stocks/${props.ticker}/report/`);
  stock.value = data.stock;
}
async function loadPosts() {
  const { data } = await api.get("/community/posts/", { params: props.ticker ? { ticker: props.ticker } : {} });
  posts.value = unwrapList(data).map((post) => ({ ...post, comments: post.comments || [], commentsExpanded: false }));
}
async function loadCommunity() {
  if (!auth.isAuthenticated) return requireLogin();
  isLoading.value = true;
  error.value = "";
  try {
    await Promise.all([loadStock(), loadPosts()]);
    await nextTick();
    if (route.hash) document.getElementById(route.hash.slice(1))?.scrollIntoView({ block: "center" });
  }
  catch { error.value = "토론방 데이터를 불러오지 못했습니다. 백엔드 서버 상태를 확인해 주세요."; }
  finally { isLoading.value = false; }
}
async function toggleFollow(user) {
  if (!auth.isAuthenticated) return requireLogin();
  followLoadingId.value = user.id;
  try {
    const { data } = await api.post(`/community/users/${user.id}/follow/`);
    posts.value.forEach((post) => { if (post.author.id === user.id) post.author = data.user; });
  } catch (err) { error.value = err.response?.data?.detail || "팔로우 상태를 변경하지 못했습니다."; }
  finally { followLoadingId.value = null; }
}
async function createPost() {
  if (!auth.isAuthenticated) return requireLogin();
  if (containsProhibitedLanguage(postForm.title) || containsProhibitedLanguage(postForm.content)) return showModerationAlert();
  isSubmittingPost.value = true;
  try {
    const { data } = await api.post("/community/posts/", { stock: props.ticker, title: postForm.title, content: postForm.content });
    posts.value.unshift({ ...data, comments: [], commentsExpanded: false });
    postForm.title = ""; postForm.content = "";
  } catch (err) {
    const message = err.response?.data?.title?.[0] || err.response?.data?.content?.[0] || err.response?.data?.stock?.[0];
    if (message?.includes("욕설") || message?.includes("비속어")) showModerationAlert();
    else error.value = message || "게시글을 등록하지 못했습니다.";
  }
  finally { isSubmittingPost.value = false; }
}
async function deletePost(post) {
  try { await api.delete(`/community/posts/${post.id}/`); posts.value = posts.value.filter((item) => item.id !== post.id); }
  catch { error.value = "작성자만 게시글을 삭제할 수 있습니다."; }
}
async function toggleLike(post) {
  if (!auth.isAuthenticated) return requireLogin();
  likeLoadingIds[post.id] = true;
  try { const { data } = await api.post(`/community/posts/${post.id}/like/`); post.liked_by_me = data.liked; post.likes_count = data.likes_count; }
  catch { error.value = "좋아요 상태를 변경하지 못했습니다."; }
  finally { likeLoadingIds[post.id] = false; }
}
async function createComment(post) {
  if (!auth.isAuthenticated) return requireLogin();
  const content = (commentDrafts[post.id] || "").trim();
  if (!content) return;
  if (containsProhibitedLanguage(content)) return showModerationAlert();
  try { const { data } = await api.post(`/community/posts/${post.id}/comments/`, { content }); post.comments.push(data.comment); post.comments_count = data.comments_count; post.commentsExpanded = true; commentDrafts[post.id] = ""; }
  catch (err) {
    const message = err.response?.data?.content?.[0];
    if (message?.includes("욕설") || message?.includes("비속어")) showModerationAlert();
    else error.value = message || "댓글을 등록하지 못했습니다.";
  }
}
async function createReply(post, parent) {
  if (!auth.isAuthenticated) return requireLogin();
  const content = (replyDrafts[parent.id] || "").trim();
  if (!content) return;
  if (containsProhibitedLanguage(content)) return showModerationAlert();
  try {
    const { data } = await api.post(`/community/posts/${post.id}/comments/`, { content, parent_id: parent.id });
    parent.replies = [...(parent.replies || []), data.comment];
    post.comments_count = data.comments_count;
    replyDrafts[parent.id] = "";
    replyingToId.value = null;
  } catch (err) {
    const message = err.response?.data?.content?.[0] || err.response?.data?.parent_id?.[0];
    if (message?.includes("욕설") || message?.includes("비속어")) showModerationAlert();
    else error.value = message || "답글을 등록하지 못했습니다.";
  }
}
async function deleteComment(post, comment) {
  try { await api.delete(`/community/comments/${comment.id}/`); await loadPosts(); }
  catch { error.value = "작성자만 댓글을 삭제할 수 있습니다."; }
}
watch(() => props.ticker, loadCommunity, { immediate: true });
</script>
