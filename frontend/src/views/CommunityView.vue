<template>
  <section class="page-shell py-8">
    <div class="flex flex-col justify-between gap-4 md:flex-row md:items-end">
      <div>
        <p class="text-sm font-black text-emerald-600">투자자 커뮤니티</p>
        <h1 class="text-3xl font-black text-slate-950">의견을 나누고 관심 투자자를 팔로우하세요</h1>
        <p class="mt-2 max-w-3xl leading-7 text-slate-600">
          포트폴리오 추천 결과와 종목 리포트를 보며 생긴 생각을 게시글과 댓글로 공유할 수 있습니다.
          좋아요와 댓글은 화면 새로고침 없이 바로 반영됩니다.
        </p>
      </div>
      <RouterLink v-if="!auth.isAuthenticated" class="btn-primary" :to="{ path: '/login', query: { next: '/community' } }">
        로그인하고 참여
      </RouterLink>
    </div>

    <p v-if="error" class="mt-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 font-bold text-red-700">
      {{ error }}
    </p>

    <div class="mt-8 grid gap-6 lg:grid-cols-[320px_1fr]">
      <aside class="panel h-fit p-5">
        <div class="flex items-center justify-between gap-3">
          <div>
            <h2 class="text-xl font-black text-slate-950">사용자</h2>
            <p class="mt-1 text-sm text-slate-500">팔로워와 팔로잉 수를 확인하세요.</p>
          </div>
          <Users :size="24" class="text-emerald-600" />
        </div>

        <div class="mt-5 space-y-3">
          <article
            v-for="user in users"
            :key="user.id"
            class="rounded-lg border border-slate-200 bg-white p-4"
          >
            <div class="flex items-start justify-between gap-3">
              <div>
                <p class="font-black text-slate-950">{{ user.display_name }}</p>
                <p class="text-sm text-slate-500">@{{ user.username }}</p>
              </div>
              <span v-if="user.is_me" class="badge bg-slate-100 text-slate-600">나</span>
            </div>

            <div class="mt-3 grid grid-cols-2 gap-2 text-sm">
              <div class="rounded-lg bg-slate-50 p-2">
                <p class="text-slate-500">팔로워</p>
                <p class="font-black text-slate-950">{{ user.followers_count }}</p>
              </div>
              <div class="rounded-lg bg-slate-50 p-2">
                <p class="text-slate-500">팔로잉</p>
                <p class="font-black text-slate-950">{{ user.following_count }}</p>
              </div>
            </div>

            <button
              class="mt-3 w-full"
              :class="user.is_following ? 'btn-secondary' : 'btn-primary'"
              type="button"
              :disabled="user.is_me || followLoadingId === user.id"
              @click="toggleFollow(user)"
            >
              <UserPlus :size="17" />
              <span v-if="user.is_me">자기 자신 팔로우 불가</span>
              <span v-else-if="user.is_following">팔로잉</span>
              <span v-else>팔로우</span>
            </button>
          </article>
        </div>
      </aside>

      <main class="space-y-6">
        <form v-if="auth.isAuthenticated" class="panel p-5" @submit.prevent="createPost">
          <h2 class="text-xl font-black text-slate-950">새 게시글 작성</h2>
          <label class="mt-4 block text-sm font-bold text-slate-700">
            제목
            <input v-model.trim="postForm.title" class="field mt-2" maxlength="120" required />
          </label>
          <label class="mt-4 block text-sm font-bold text-slate-700">
            내용
            <textarea
              v-model.trim="postForm.content"
              class="field mt-2 min-h-28 resize-y"
              required
            />
          </label>
          <button class="btn-primary mt-4" type="submit" :disabled="isSubmittingPost">
            <Send :size="18" />
            게시글 등록
          </button>
        </form>
        <div v-else class="panel p-5">
          <h2 class="text-xl font-black text-slate-950">로그인이 필요합니다</h2>
          <p class="mt-2 text-slate-600">게시글 작성, 좋아요, 댓글, 팔로우는 로그인한 사용자만 사용할 수 있습니다.</p>
        </div>

        <div v-if="isLoading" class="panel p-8 text-center font-bold text-slate-500">
          커뮤니티 글을 불러오는 중입니다.
        </div>

        <article v-for="post in posts" :key="post.id" class="panel overflow-hidden">
          <div class="p-5">
            <div class="flex flex-col justify-between gap-3 md:flex-row md:items-start">
              <div>
                <p class="text-sm font-bold text-emerald-700">
                  {{ post.author.display_name }} · {{ formatDate(post.created_at) }}
                </p>
                <h2 class="mt-2 text-2xl font-black text-slate-950">{{ post.title }}</h2>
              </div>
              <span v-if="post.can_edit" class="badge bg-emerald-50 text-emerald-700">내 글</span>
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

            <form v-if="auth.isAuthenticated" class="mt-4 flex flex-col gap-2 sm:flex-row" @submit.prevent="createComment(post)">
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

        <div v-if="!isLoading && !posts.length" class="panel p-8 text-center text-slate-500">
          아직 게시글이 없습니다. 첫 의견을 남겨보세요.
        </div>
      </main>
    </div>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { Heart, MessageCircle, Send, Trash2, UserPlus, Users } from "@lucide/vue";

import { api, unwrapList } from "../api/client";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const router = useRouter();
const users = ref([]);
const posts = ref([]);
const error = ref("");
const isLoading = ref(false);
const isSubmittingPost = ref(false);
const followLoadingId = ref(null);
const commentDrafts = reactive({});
const postForm = reactive({
  title: "",
  content: "",
});

function requireLogin() {
  router.push({ path: "/login", query: { next: "/community" } });
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

async function loadPosts() {
  const { data } = await api.get("/community/posts/");
  posts.value = unwrapList(data).map((post) => ({
    ...post,
    comments: post.comments || [],
  }));
}

async function loadCommunity() {
  isLoading.value = true;
  error.value = "";
  try {
    await Promise.all([loadUsers(), loadPosts()]);
  } catch {
    error.value = "커뮤니티 데이터를 불러오지 못했습니다. 백엔드 서버 상태를 확인해주세요.";
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
  isSubmittingPost.value = true;
  error.value = "";
  try {
    const { data } = await api.post("/community/posts/", {
      title: postForm.title,
      content: postForm.content,
    });
    posts.value.unshift({ ...data, comments: data.comments || [] });
    postForm.title = "";
    postForm.content = "";
  } catch {
    error.value = "게시글을 등록하지 못했습니다. 제목과 내용을 확인해주세요.";
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

onMounted(() => {
  loadCommunity();
});
</script>
