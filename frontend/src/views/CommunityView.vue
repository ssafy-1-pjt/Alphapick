<template>
  <section class="page-shell py-8">
    <div v-if="isStockRoom" class="rounded-lg border border-emerald-200 bg-emerald-50 p-6 md:p-7">
      <div class="flex flex-col justify-between gap-5 md:flex-row md:items-center">
        <div class="flex items-start gap-4">
          <span class="flex h-14 w-14 shrink-0 items-center justify-center rounded-lg bg-emerald-600 text-white">
            <MessageCircle :size="30" />
          </span>
          <div>
            <div class="flex flex-wrap items-center gap-2">
              <p class="text-sm font-black text-emerald-700">종목 토론방</p>
              <span v-if="stock" class="badge bg-white text-slate-600">{{ stock.ticker }}</span>
              <span v-if="stock?.sector" class="badge bg-emerald-100 text-emerald-800">{{ stock.sector }}</span>
            </div>
            <h1 class="mt-1 text-3xl font-black text-slate-950 md:text-4xl">
              {{ stock?.name || "종목" }} 토론방
            </h1>
            <p class="mt-2 max-w-3xl leading-7 text-slate-600">
              {{ stock?.name || "이 종목" }}의 실적, 수급, 주가 흐름과 투자 의견을 나누는 공간입니다.
            </p>
          </div>
        </div>
        <RouterLink
          class="btn-secondary shrink-0"
          :to="{ name: 'stock-report', params: { ticker } }"
        >
          <ArrowLeft :size="18" />
          종목 리포트로 돌아가기
        </RouterLink>
      </div>
    </div>

    <div v-else class="flex flex-col justify-between gap-4 md:flex-row md:items-end">
      <div>
        <p class="text-sm font-black text-emerald-600">전체 종목 토론</p>
        <h1 class="text-3xl font-black text-slate-950">투자자들의 종목별 의견을 확인하세요</h1>
        <p class="mt-2 max-w-3xl leading-7 text-slate-600">
          게시글의 종목명을 눌러 리포트로 이동할 수 있습니다. 새 글은 각 종목 리포트의 토론방에서 작성합니다.
        </p>
      </div>
      <RouterLink class="btn-primary" to="/stocks">토론할 종목 선택</RouterLink>
    </div>

    <p v-if="error" class="mt-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 font-bold text-red-700">
      {{ error }}
    </p>

    <div class="mt-7 grid gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
      <main class="min-w-0 space-y-5">
        <form
          v-if="isStockRoom && auth.isAuthenticated"
          class="panel border-emerald-200 p-5"
          @submit.prevent="createPost"
        >
          <div class="flex items-center gap-3">
            <span class="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-100 text-emerald-700">
              <Send :size="20" />
            </span>
            <div>
              <h2 class="text-xl font-black text-slate-950">{{ stock?.name }} 의견 작성</h2>
              <p class="text-sm text-slate-500">투자 근거와 반대 의견을 구체적으로 남겨주세요.</p>
            </div>
          </div>
          <label class="mt-4 block text-sm font-bold text-slate-700">
            제목
            <input
              v-model.trim="postForm.title"
              class="field mt-2"
              maxlength="120"
              placeholder="예: 실적 발표 이후 흐름을 어떻게 보시나요?"
              required
            />
          </label>
          <label class="mt-4 block text-sm font-bold text-slate-700">
            내용
            <textarea
              v-model.trim="postForm.content"
              class="field mt-2 min-h-28 resize-y"
              placeholder="종목에 대한 의견과 근거를 작성해주세요."
              required
            />
          </label>
          <button class="btn-primary mt-4" type="submit" :disabled="isSubmittingPost">
            <Send :size="18" />
            {{ isSubmittingPost ? "등록 중" : "의견 등록" }}
          </button>
        </form>

        <div v-else-if="isStockRoom" class="panel p-5">
          <h2 class="text-xl font-black text-slate-950">로그인하고 의견을 남겨보세요</h2>
          <p class="mt-2 text-slate-600">게시글 작성, 좋아요, 댓글은 로그인한 사용자만 사용할 수 있습니다.</p>
          <RouterLink class="btn-primary mt-4" :to="loginRoute">로그인</RouterLink>
        </div>

        <div v-if="isLoading" class="panel p-8 text-center font-bold text-slate-500">
          토론 내용을 불러오는 중입니다.
        </div>

        <article v-for="post in posts" :key="post.id" class="panel overflow-hidden">
          <div class="p-5">
            <div class="flex flex-col justify-between gap-3 md:flex-row md:items-start">
              <div>
                <div class="flex flex-wrap items-center gap-2 text-sm font-bold">
                  <span class="text-emerald-700">{{ post.author.display_name }}</span>
                  <span class="text-slate-400">{{ formatDate(post.created_at) }}</span>
                  <RouterLink
                    v-if="!isStockRoom && post.stock"
                    class="badge bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
                    :to="{ name: 'stock-community', params: { ticker: post.stock } }"
                  >
                    {{ post.stock_name || post.stock }} 토론방
                  </RouterLink>
                </div>
                <h2 class="mt-2 text-2xl font-black text-slate-950">{{ post.title }}</h2>
              </div>
              <span v-if="post.can_edit" class="badge bg-slate-100 text-slate-600">내 글</span>
            </div>
            <p class="mt-4 whitespace-pre-line leading-7 text-slate-700">{{ post.content }}</p>

            <div class="mt-5 flex flex-wrap items-center gap-3">
              <button
                class="btn-secondary"
                :class="post.liked_by_me ? 'border-rose-200 bg-rose-50 text-rose-600' : ''"
                type="button"
                @click="toggleLike(post)"
              >
                <Heart :size="18" :fill="post.liked_by_me ? 'currentColor' : 'none'" />
                좋아요 {{ post.likes_count }}
              </button>
              <span class="inline-flex items-center gap-2 text-sm font-bold text-slate-500">
                <MessageCircle :size="18" />
                댓글 {{ post.comments_count }}
              </span>
            </div>
          </div>

          <div class="border-t border-slate-100 bg-slate-50/70 p-5">
            <h3 class="font-black text-slate-950">댓글</h3>
            <div class="mt-3 space-y-3">
              <div
                v-for="comment in post.comments"
                :key="comment.id"
                class="rounded-lg border border-slate-200 bg-white p-3"
              >
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <p class="text-sm font-black text-slate-900">
                      {{ comment.author.display_name }}
                      <span class="font-medium text-slate-400">· {{ formatDate(comment.created_at) }}</span>
                    </p>
                    <p class="mt-2 whitespace-pre-line text-slate-700">{{ comment.content }}</p>
                  </div>
                  <button
                    v-if="comment.can_delete"
                    class="btn-ghost min-h-0 px-2 py-1 text-red-600"
                    type="button"
                    @click="deleteComment(post, comment)"
                  >
                    <Trash2 :size="16" />
                    삭제
                  </button>
                </div>
              </div>
              <p v-if="!post.comments?.length" class="rounded-lg bg-white p-3 text-sm text-slate-500">
                아직 댓글이 없습니다.
              </p>
            </div>

            <form
              v-if="auth.isAuthenticated"
              class="mt-4 flex flex-col gap-2 sm:flex-row"
              @submit.prevent="createComment(post)"
            >
              <input
                v-model.trim="commentDrafts[post.id]"
                class="field"
                placeholder="댓글을 입력하세요"
                maxlength="600"
              />
              <button class="btn-primary shrink-0" type="submit">
                <Send :size="17" />
                등록
              </button>
            </form>
          </div>
        </article>

        <div v-if="!isLoading && !posts.length" class="panel p-8 text-center">
          <MessageCircle :size="36" class="mx-auto text-slate-300" />
          <p class="mt-3 font-black text-slate-700">
            {{ isStockRoom ? "아직 이 종목에 등록된 의견이 없습니다." : "아직 등록된 종목 토론이 없습니다." }}
          </p>
          <p class="mt-1 text-sm text-slate-500">
            {{ isStockRoom ? "첫 번째 의견을 남겨 토론을 시작해보세요." : "종목 리포트에서 토론방에 입장해보세요." }}
          </p>
        </div>
      </main>

      <aside class="panel h-fit p-5 lg:sticky lg:top-24">
        <div class="flex items-center justify-between gap-3">
          <div>
            <h2 class="text-xl font-black text-slate-950">참여 투자자</h2>
            <p class="mt-1 text-sm text-slate-500">관심 있는 투자자를 팔로우하세요.</p>
          </div>
          <Users :size="24" class="text-emerald-600" />
        </div>

        <div class="mt-5 space-y-3">
          <article v-for="user in users" :key="user.id" class="rounded-lg border border-slate-200 bg-white p-3">
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <p class="truncate font-black text-slate-950">{{ user.display_name }}</p>
                <p class="truncate text-sm text-slate-500">@{{ user.username }}</p>
              </div>
              <span v-if="user.is_me" class="badge bg-slate-100 text-slate-600">나</span>
            </div>
            <p class="mt-2 text-xs font-bold text-slate-500">
              팔로워 {{ user.followers_count }} · 팔로잉 {{ user.following_count }}
            </p>
            <button
              class="mt-3 w-full"
              :class="user.is_following ? 'btn-secondary' : 'btn-primary'"
              type="button"
              :disabled="user.is_me || followLoadingId === user.id"
              @click="toggleFollow(user)"
            >
              <UserPlus :size="16" />
              <span v-if="user.is_me">내 계정</span>
              <span v-else-if="user.is_following">팔로잉</span>
              <span v-else>팔로우</span>
            </button>
          </article>
        </div>
      </aside>
    </div>
  </section>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ArrowLeft, Heart, MessageCircle, Send, Trash2, UserPlus, Users } from "@lucide/vue";

import { api, unwrapList } from "../api/client";
import { useAuthStore } from "../stores/auth";

const props = defineProps({
  ticker: {
    type: String,
    default: "",
  },
});

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();
const stock = ref(null);
const users = ref([]);
const posts = ref([]);
const error = ref("");
const isLoading = ref(false);
const isSubmittingPost = ref(false);
const followLoadingId = ref(null);
const commentDrafts = reactive({});
const postForm = reactive({ title: "", content: "" });

const isStockRoom = computed(() => Boolean(props.ticker));
const loginRoute = computed(() => ({ path: "/login", query: { next: route.fullPath } }));

function requireLogin() {
  router.push(loginRoute.value);
}

function formatDate(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat("ko-KR", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

async function loadUsers() {
  const { data } = await api.get("/community/users/");
  users.value = unwrapList(data);
}

async function loadStock() {
  if (!props.ticker) {
    stock.value = null;
    return;
  }
  const { data } = await api.get(`/stocks/${props.ticker}/report/`);
  stock.value = data.stock;
}

async function loadPosts() {
  const params = props.ticker ? { ticker: props.ticker } : {};
  const { data } = await api.get("/community/posts/", { params });
  posts.value = unwrapList(data).map((post) => ({ ...post, comments: post.comments || [] }));
}

async function loadCommunity() {
  isLoading.value = true;
  error.value = "";
  posts.value = [];
  try {
    await Promise.all([loadUsers(), loadStock(), loadPosts()]);
  } catch {
    error.value = "토론방 데이터를 불러오지 못했습니다. 백엔드 서버 상태를 확인해주세요.";
  } finally {
    isLoading.value = false;
  }
}

async function toggleFollow(user) {
  if (!auth.isAuthenticated) return requireLogin();
  if (user.is_me) return;
  followLoadingId.value = user.id;
  error.value = "";
  try {
    await api.post(`/community/users/${user.id}/follow/`);
    await loadUsers();
  } catch (err) {
    error.value = err.response?.data?.detail || "팔로우 상태를 변경하지 못했습니다.";
  } finally {
    followLoadingId.value = null;
  }
}

async function createPost() {
  if (!auth.isAuthenticated) return requireLogin();
  if (!props.ticker) return;
  isSubmittingPost.value = true;
  error.value = "";
  try {
    const { data } = await api.post("/community/posts/", {
      stock: props.ticker,
      title: postForm.title,
      content: postForm.content,
    });
    posts.value.unshift({ ...data, comments: data.comments || [] });
    postForm.title = "";
    postForm.content = "";
  } catch (err) {
    error.value = err.response?.data?.stock?.[0] || "게시글을 등록하지 못했습니다. 제목과 내용을 확인해주세요.";
  } finally {
    isSubmittingPost.value = false;
  }
}

async function toggleLike(post) {
  if (!auth.isAuthenticated) return requireLogin();
  error.value = "";
  try {
    const { data } = await api.post(`/community/posts/${post.id}/like/`);
    post.liked_by_me = data.liked;
    post.likes_count = data.likes_count;
  } catch {
    error.value = "좋아요 상태를 변경하지 못했습니다.";
  }
}

async function createComment(post) {
  if (!auth.isAuthenticated) return requireLogin();
  const content = (commentDrafts[post.id] || "").trim();
  if (!content) return;
  error.value = "";
  try {
    const { data } = await api.post(`/community/posts/${post.id}/comments/`, { content });
    post.comments.push(data.comment);
    post.comments_count = data.comments_count;
    commentDrafts[post.id] = "";
  } catch {
    error.value = "댓글을 등록하지 못했습니다.";
  }
}

async function deleteComment(post, comment) {
  error.value = "";
  try {
    await api.delete(`/community/comments/${comment.id}/`);
    post.comments = post.comments.filter((item) => item.id !== comment.id);
    post.comments_count = Math.max(0, post.comments_count - 1);
  } catch {
    error.value = "댓글 작성자만 댓글을 삭제할 수 있습니다.";
  }
}

watch(() => props.ticker, loadCommunity, { immediate: true });
</script>
