<template>
  <section class="page-shell flex min-h-[calc(100vh-65px)] items-center justify-center py-8">
    <form class="panel w-full max-w-xl p-6" @submit.prevent="submit">
      <h1 class="text-3xl font-black text-slate-950">회원가입</h1>

      <div class="mt-6 grid gap-4 md:grid-cols-2">
        <label class="block text-sm font-bold text-slate-700">
          아이디
          <input v-model="form.username" class="field mt-2" autocomplete="username" required />
        </label>
        <label class="block text-sm font-bold text-slate-700">
          닉네임
          <input v-model="form.nickname" class="field mt-2" />
        </label>
        <label class="block text-sm font-bold text-slate-700 md:col-span-2">
          이메일
          <input v-model="form.email" class="field mt-2" type="email" autocomplete="email" />
        </label>
        <label class="block text-sm font-bold text-slate-700 md:col-span-2">
          비밀번호
          <input
            v-model="form.password"
            class="field mt-2"
            type="password"
            minlength="8"
            autocomplete="new-password"
            required
          />
        </label>
        <label class="block text-sm font-bold text-slate-700 md:col-span-2">
          투자 성향
          <select v-model="form.risk_type" class="field mt-2">
            <option value="neutral">중립형: 회사 가치와 진입 타이밍을 균형 있게 반영</option>
            <option value="aggressive">공격형: 주도주와 타이밍을 더 중시</option>
            <option value="stable">안정형: 회사 가치와 신뢰도를 더 중시</option>
          </select>
        </label>
      </div>

      <p v-if="error" class="mt-4 text-sm font-bold text-red-600">{{ error }}</p>
      <button class="btn-primary mt-6 w-full" type="submit">가입하고 시작하기</button>
      <RouterLink class="btn-ghost mt-3 w-full" to="/login">이미 계정이 있습니다</RouterLink>
    </form>
  </section>
</template>

<script setup>
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";

import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const router = useRouter();
const error = ref("");
const form = reactive({
  username: "",
  email: "",
  password: "",
  nickname: "",
  risk_type: "neutral",
});

async function submit() {
  error.value = "";
  try {
    await auth.register(form);
    router.push("/");
  } catch {
    error.value = "가입 정보를 확인해주세요.";
  }
}
</script>
