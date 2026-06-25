import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("alphapick.access");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config;
    const hasAuthHeader = Boolean(config?.headers?.Authorization);

    // DB 교체나 토큰 만료 뒤에도 공개 API가 막히지 않도록 익명 요청으로 한 번 복구한다.
    if (error.response?.status === 401 && hasAuthHeader && !config._retriedWithoutAuth) {
      localStorage.removeItem("alphapick.access");
      localStorage.removeItem("alphapick.refresh");
      localStorage.removeItem("alphapick.user");
      config._retriedWithoutAuth = true;
      delete config.headers.Authorization;
      return api(config);
    }

    return Promise.reject(error);
  },
);

export function unwrapList(payload) {
  if (Array.isArray(payload)) return payload;
  if (payload?.results) return payload.results;
  return [];
}
