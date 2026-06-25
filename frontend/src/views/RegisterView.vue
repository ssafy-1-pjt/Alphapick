<template>
  <section class="page-shell flex min-h-[calc(100vh-65px)] items-center justify-center py-8">
    <form class="panel w-full max-w-xl p-6" novalidate @submit.prevent="submit">
      <h1 class="text-3xl font-extrabold text-slate-950">회원가입</h1>
      <p class="mt-2 text-sm text-slate-500">각 입력칸 아래의 안내를 확인해 주세요.</p>

      <div class="mt-6 grid gap-4 md:grid-cols-2">
        <label class="block text-sm font-bold text-slate-700">아이디
          <input v-model.trim="form.username" class="field mt-2" :class="fieldClass('username')" autocomplete="username" placeholder="영문, 숫자, 밑줄 3자 이상" @input="validateTouched('username')" @blur="touchAndValidate('username')" />
          <span class="mt-1 block text-xs font-medium text-slate-500">영문, 숫자, 밑줄(_)만 사용할 수 있습니다.</span>
          <span v-if="touched.username && errors.username" class="mt-1 block text-xs font-bold text-red-600">{{ errors.username }}</span>
        </label>
        <label class="block text-sm font-bold text-slate-700">닉네임
          <input v-model.trim="form.nickname" class="field mt-2" :class="fieldClass('nickname')" placeholder="선택 사항, 2자 이상" @input="validateTouched('nickname')" @blur="touchAndValidate('nickname')" />
          <span v-if="touched.nickname && errors.nickname" class="mt-1 block text-xs font-bold text-red-600">{{ errors.nickname }}</span>
        </label>
        <label class="block text-sm font-bold text-slate-700 md:col-span-2">이메일
          <input v-model.trim="form.email" class="field mt-2" :class="fieldClass('email')" type="text" inputmode="email" autocomplete="email" placeholder="name@gmail.com" @input="validateTouched('email')" @blur="touchAndValidate('email')" />
          <span class="mt-1 block text-xs font-medium text-slate-500">gmail.com, naver.com 등 지원 메일 서비스 주소를 입력해 주세요.</span>
          <span v-if="touched.email && errors.email" class="mt-1 block text-xs font-bold text-red-600">{{ errors.email }}</span>
        </label>
        <label class="block text-sm font-bold text-slate-700 md:col-span-2">비밀번호
          <input v-model="form.password" class="field mt-2" :class="fieldClass('password')" type="password" autocomplete="new-password" placeholder="8자 이상" @input="validateTouched('password')" @blur="touchAndValidate('password')" />
          <span class="mt-1 block text-xs font-medium text-slate-500">8자 이상 입력해 주세요.</span>
          <span v-if="touched.password && errors.password" class="mt-1 block text-xs font-bold text-red-600">{{ errors.password }}</span>
        </label>
      </div>

      <p v-if="formError" class="mt-4 text-sm font-bold text-red-600">{{ formError }}</p>
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
const formError = ref("");
const form = reactive({ username: "", email: "", password: "", nickname: "", risk_type: "neutral" });
const touched = reactive({ username: false, nickname: false, email: false, password: false });
const errors = reactive({ username: "", nickname: "", email: "", password: "" });
const allowedEmailDomains = new Set(["gmail.com", "google.com", "naver.com", "daum.net", "hanmail.net", "kakao.com", "outlook.com", "hotmail.com", "icloud.com", "yahoo.com"]);

function validateField(field) {
  const value = String(form[field] || "").trim();
  if (field === "username") {
    if (value.length < 3) return "아이디는 3자 이상 입력해 주세요.";
    if (!/^[A-Za-z0-9_]+$/.test(value)) return "아이디는 영문, 숫자, 밑줄(_)만 사용할 수 있습니다.";
  }
  if (field === "nickname" && value && value.length < 2) return "닉네임은 2자 이상 입력해 주세요.";
  if (field === "email") {
    const match = value.toLowerCase().match(/^[^\s@]+@([^\s@]+)$/);
    if (!value) return "이메일 주소를 입력해 주세요.";
    if (!match) return "이메일 형식을 확인해 주세요. 예: name@gmail.com";
    if (!allowedEmailDomains.has(match[1])) return "지원하는 메일 서비스 주소를 입력해 주세요. 예: name@gmail.com, name@naver.com";
    form.email = value.toLowerCase();
  }
  if (field === "password" && value.length < 8) return "비밀번호는 8자 이상 입력해 주세요.";
  return "";
}
function touchAndValidate(field) { touched[field] = true; errors[field] = validateField(field); }
function validateTouched(field) { if (touched[field]) errors[field] = validateField(field); }
function fieldClass(field) { return touched[field] && errors[field] ? "border-red-400 focus:border-red-500 focus:ring-red-100" : ""; }
function validateAll() {
  return Object.keys(errors).every((field) => { touchAndValidate(field); return !errors[field]; });
}
function applyServerErrors(data = {}) {
  Object.keys(errors).forEach((field) => { if (data[field]?.length) { touched[field] = true; errors[field] = data[field][0]; } });
}
async function submit() {
  formError.value = "";
  if (!validateAll()) return;
  try { await auth.register(form); router.push("/"); }
  catch (err) {
    if (!err.response) {
      formError.value = "회원가입 서버에 연결하지 못했습니다. 백엔드 서버가 실행 중인지 확인해 주세요.";
      return;
    }
    applyServerErrors(err.response.data);
    const hasFieldError = Object.values(errors).some(Boolean);
    if (!hasFieldError) formError.value = err.response.data?.detail || "회원가입 요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.";
  }
}
</script>
