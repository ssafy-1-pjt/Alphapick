<template>
  <section class="page-shell flex min-h-[calc(100vh-65px)] items-center justify-center py-8">
    <form class="panel w-full max-w-md p-6" @submit.prevent="submit">
      <h1 class="text-3xl font-black text-slate-950">로그인</h1>

      <label class="mt-6 block text-sm font-bold text-slate-700">
        아이디
        <input v-model="form.username" class="field mt-2" autocomplete="username" required />
      </label>

      <label class="mt-4 block text-sm font-bold text-slate-700">
        비밀번호
        <input
          v-model="form.password"
          class="field mt-2"
          type="password"
          autocomplete="current-password"
          required
        />
      </label>

      <p v-if="error" class="mt-4 text-sm font-bold text-red-600">{{ error }}</p>

      <button class="btn-primary mt-6 w-full" type="submit">로그인</button>
      <RouterLink class="btn-ghost mt-3 w-full" to="/register">새 계정 만들기</RouterLink>
    </form>
  </section>
</template>

<script setup>
import { reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();
const error = ref("");
const form = reactive({ username: "", password: "" });

async function submit() {
  error.value = "";
  try {
    await auth.login(form);
    router.push(route.query.next || "/");
  } catch {
    error.value = "로그인 정보를 확인해주세요.";
  }
}
</script>
