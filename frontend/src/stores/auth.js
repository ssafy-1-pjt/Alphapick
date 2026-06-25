import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { api } from "../api/client";

export const useAuthStore = defineStore("auth", () => {
  const user = ref(JSON.parse(localStorage.getItem("alphapick.user") || "null"));
  const access = ref(localStorage.getItem("alphapick.access"));
  const refresh = ref(localStorage.getItem("alphapick.refresh"));
  const isAuthenticated = computed(() => Boolean(access.value));

  function persist(payload) {
    access.value = payload.access;
    refresh.value = payload.refresh;
    user.value = payload.user;
    localStorage.setItem("alphapick.access", payload.access);
    localStorage.setItem("alphapick.refresh", payload.refresh);
    localStorage.setItem("alphapick.user", JSON.stringify(payload.user));
  }

  async function login(credentials) {
    const { data } = await api.post("/auth/login/", credentials);
    persist(data);
    return data.user;
  }

  async function register(payload) {
    await api.post("/auth/register/", payload);
    return login({ username: payload.username, password: payload.password });
  }

  async function fetchMe() {
    if (!access.value) return null;
    const { data } = await api.get("/users/me/");
    user.value = data;
    localStorage.setItem("alphapick.user", JSON.stringify(data));
    return data;
  }

  async function updateMe(payload) {
    const { data } = await api.patch("/users/me/", payload);
    user.value = data;
    localStorage.setItem("alphapick.user", JSON.stringify(data));
    return data;
  }

  function clearSession() {
    user.value = null;
    access.value = null;
    refresh.value = null;
    localStorage.removeItem("alphapick.access");
    localStorage.removeItem("alphapick.refresh");
    localStorage.removeItem("alphapick.user");
  }

  function logout() {
    clearSession();
  }

  if (typeof window !== "undefined") {
    window.addEventListener("auth-expired", clearSession);
  }

  return { user, access, refresh, isAuthenticated, login, register, fetchMe, updateMe, logout };
});
