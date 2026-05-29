<template>
  <section class="page-shell py-8">
    <form class="panel mx-auto max-w-2xl p-6" @submit.prevent="submit">
      <h1 class="text-3xl font-black text-slate-950">프로필 수정</h1>

      <label class="mt-6 block text-sm font-bold text-slate-700">
        닉네임
        <input v-model="form.nickname" class="field mt-2" />
      </label>

      <label class="mt-4 block text-sm font-bold text-slate-700">
        투자 성향
        <select v-model="form.risk_type" class="field mt-2">
          <option value="neutral">중립형: 회사 70점 · 타이밍 70점</option>
          <option value="aggressive">공격형: 회사 65점 · 타이밍 75점</option>
          <option value="stable">안정형: 회사 75점 · 타이밍 65점</option>
        </select>
      </label>

      <button class="btn-primary mt-6 w-full" type="submit">저장</button>
    </form>
  </section>
</template>

<script setup>
import { reactive } from "vue";
import { useRouter } from "vue-router";

import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const router = useRouter();
const form = reactive({
  nickname: auth.user?.nickname || "",
  risk_type: auth.user?.risk_type || "neutral",
});

async function submit() {
  await auth.updateMe(form);
  router.push("/mypage");
}
</script>
