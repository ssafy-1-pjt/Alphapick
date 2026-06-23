<template>
  <section class="page-shell py-8">
    <div class="flex flex-col justify-between gap-4 md:flex-row md:items-end">
      <div>
        <p class="text-sm font-extrabold text-emerald-600">내 계정</p>
        <h1 class="mt-1 text-3xl font-extrabold text-slate-950">내 정보</h1>
        <p class="mt-2 text-slate-500">프로필과 투자 성향을 관리합니다.</p>
      </div>
    </div>

    <section class="panel mt-7 p-6">
      <div class="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
        <div class="flex items-center gap-4">
          <img v-if="profileImageUrl" :src="profileImageUrl" class="h-20 w-20 rounded-full border border-slate-200 object-cover" alt="프로필 사진" />
          <div v-else class="flex h-20 w-20 items-center justify-center rounded-full bg-emerald-100 text-2xl font-black text-emerald-700">{{ profileInitial }}</div>
          <div>
            <h2 class="text-2xl font-extrabold text-slate-950">{{ auth.user?.nickname || auth.user?.username }}</h2>
            <p class="mt-1 text-sm text-slate-500">@{{ auth.user?.username }}</p>
          </div>
        </div>
        <RouterLink class="btn-primary shrink-0" to="/profile/edit">
          <Settings :size="18" />
          프로필 수정
        </RouterLink>
      </div>

      <dl class="mt-6 grid gap-3 border-t border-slate-100 pt-5 sm:grid-cols-2">
        <div class="rounded-lg bg-slate-50 p-4"><dt class="text-xs font-bold text-slate-500">아이디</dt><dd class="mt-1 font-black text-slate-900">{{ auth.user?.username }}</dd></div>
        <div class="rounded-lg bg-slate-50 p-4"><dt class="text-xs font-bold text-slate-500">이메일</dt><dd class="mt-1 break-all font-black text-slate-900">{{ auth.user?.email || "등록된 이메일 없음" }}</dd></div>
        <div class="rounded-lg bg-slate-50 p-4"><dt class="text-xs font-bold text-slate-500">닉네임</dt><dd class="mt-1 font-black text-slate-900">{{ auth.user?.nickname || "미설정" }}</dd></div>
        <div class="rounded-lg bg-slate-50 p-4"><dt class="text-xs font-bold text-slate-500">투자 성향</dt><dd class="mt-1 font-black text-emerald-700">{{ riskLabel }}</dd></div>
      </dl>
    </section>

    <section class="panel mt-8 p-6">
      <h2 class="text-2xl font-extrabold text-slate-950">추천 정책</h2>
      <p class="mt-2 leading-7 text-slate-600">
        AlphaPick은 성향별 회사 가치와 진입 타이밍 기준을 적용하고, 시장 상태와 섹터 편중을 반영해
        주식과 현금 비중을 함께 제안합니다.
      </p>
      <div class="mt-5 grid gap-3 md:grid-cols-3">
        <div class="rounded-lg bg-slate-50 p-4">
          <p class="text-sm font-extrabold text-slate-500">공격형</p>
          <p class="mt-1 font-bold text-slate-900">회사 65점 · 타이밍 75점</p>
        </div>
        <div class="rounded-lg bg-slate-50 p-4">
          <p class="text-sm font-extrabold text-slate-500">중립형</p>
          <p class="mt-1 font-bold text-slate-900">회사 70점 · 타이밍 70점</p>
        </div>
        <div class="rounded-lg bg-slate-50 p-4">
          <p class="text-sm font-extrabold text-slate-500">안정형</p>
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
const profileInitial = computed(() => (auth.user?.nickname || auth.user?.username || "U").slice(0, 1).toUpperCase());
const profileImageUrl = computed(() => {
  const url = auth.user?.profile_image_url;
  if (!url || url.startsWith("http")) return url;
  return `http://127.0.0.1:8000${url}`;
});

onMounted(() => {
  auth.fetchMe();
});
</script>
