<template>
  <section class="page-shell py-8">
    <div class="flex flex-col justify-between gap-4 md:flex-row md:items-end">
      <div>
        <p class="text-sm font-black text-emerald-600">마이페이지</p>
        <h1 class="text-3xl font-black text-slate-950">{{ auth.user?.nickname || auth.user?.username }}</h1>
        <p class="mt-2 text-slate-500">투자 성향: {{ riskLabel }}</p>
      </div>
      <div class="flex flex-wrap gap-2">
        <RouterLink class="btn-secondary" to="/community">커뮤니티로 이동</RouterLink>
        <RouterLink class="btn-primary" to="/profile/edit">
          <Settings :size="18" />
          프로필 수정
        </RouterLink>
      </div>
    </div>

    <section class="panel mt-8 p-6">
      <h2 class="text-2xl font-black text-slate-950">추천 정책</h2>
      <p class="mt-2 leading-7 text-slate-600">
        AlphaPick은 성향별 회사 가치와 진입 타이밍 기준을 적용하고, 시장 상태와 섹터 편중을 반영해
        주식과 현금 비중을 함께 제안합니다.
      </p>
      <div class="mt-5 grid gap-3 md:grid-cols-3">
        <div class="rounded-lg bg-slate-50 p-4">
          <p class="text-sm font-black text-slate-500">공격형</p>
          <p class="mt-1 font-bold text-slate-900">회사 65점 · 타이밍 75점</p>
        </div>
        <div class="rounded-lg bg-slate-50 p-4">
          <p class="text-sm font-black text-slate-500">중립형</p>
          <p class="mt-1 font-bold text-slate-900">회사 70점 · 타이밍 70점</p>
        </div>
        <div class="rounded-lg bg-slate-50 p-4">
          <p class="text-sm font-black text-slate-500">안정형</p>
          <p class="mt-1 font-bold text-slate-900">회사 75점 · 타이밍 65점</p>
        </div>
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed, onMounted } from "vue";
import { Settings } from "@lucide/vue";

import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const labels = {
  aggressive: "공격형",
  neutral: "중립형",
  stable: "안정형",
};
const riskLabel = computed(() => labels[auth.user?.risk_type] || "중립형");

onMounted(() => {
  auth.fetchMe();
});
</script>
