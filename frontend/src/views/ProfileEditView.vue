<template>
  <section class="page-shell py-8">
    <form class="panel mx-auto max-w-2xl p-6" @submit.prevent="submit">
      <h1 class="text-3xl font-extrabold text-slate-950">프로필 수정</h1>

      <div class="mt-6 flex items-center gap-5">
        <img v-if="profilePreview" :src="profilePreview" class="h-20 w-20 rounded-full border border-slate-200 object-cover" alt="프로필 사진 미리보기" />
        <div v-else class="flex h-20 w-20 items-center justify-center rounded-full bg-mint/10 text-2xl font-black text-mint">
          {{ (auth.user?.nickname || auth.user?.username || "U").slice(0, 1).toUpperCase() }}
        </div>
        <div class="min-w-0">
          <label class="btn-secondary cursor-pointer">
            프로필 사진 선택
            <input class="sr-only" type="file" accept="image/png,image/jpeg,image/webp" @change="selectProfileImage" />
          </label>
          <p class="mt-2 text-xs text-slate-500">JPG, PNG, WebP 파일을 5MB 이하로 올릴 수 있습니다.</p>
          <button v-if="profilePreview" class="mt-1 text-xs font-bold text-rose-600 hover:underline" type="button" @click="removeProfileImage">사진 삭제</button>
        </div>
      </div>

      <label class="mt-6 block text-sm font-bold text-slate-700">
        닉네임
        <input v-model="form.nickname" class="field mt-2" />
      </label>

      <p v-if="error" class="mt-4 text-sm font-bold text-rose-600">{{ error }}</p>

      <button class="btn-primary mt-6 w-full" type="submit" :disabled="submitting">{{ submitting ? "저장 중..." : "저장" }}</button>
    </form>
  </section>
</template>

<script setup>
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";

import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const router = useRouter();
const form = reactive({
  nickname: auth.user?.nickname || "",
});
const profilePreview = ref(toMediaUrl(auth.user?.profile_image_url));
const profileFile = ref(null);
const shouldRemoveImage = ref(false);
const submitting = ref(false);
const error = ref("");

function toMediaUrl(url) {
  if (!url || url.startsWith("http")) return url;
  return `http://127.0.0.1:8000${url}`;
}

function selectProfileImage(event) {
  const [file] = event.target.files;
  if (!file) return;
  if (!file.type.startsWith("image/") || file.size > 5 * 1024 * 1024) {
    error.value = "JPG, PNG, WebP 형식의 5MB 이하 이미지 파일을 선택해 주세요.";
    event.target.value = "";
    return;
  }
  error.value = "";
  profileFile.value = file;
  shouldRemoveImage.value = false;
  profilePreview.value = URL.createObjectURL(file);
}

function removeProfileImage() {
  profileFile.value = null;
  shouldRemoveImage.value = true;
  profilePreview.value = null;
}

async function submit() {
  submitting.value = true;
  error.value = "";
  const payload = new FormData();
  payload.append("nickname", form.nickname);
  if (profileFile.value) payload.append("profile_image", profileFile.value);
  if (shouldRemoveImage.value) payload.append("remove_profile_image", "true");
  try {
    await auth.updateMe(payload);
    router.push("/mypage");
  } catch (err) {
    const data = err.response?.data || {};
    error.value = data.nickname?.[0] || data.profile_image?.[0] || data.detail || "프로필을 저장하지 못했습니다.";
  } finally {
    submitting.value = false;
  }
}
</script>
