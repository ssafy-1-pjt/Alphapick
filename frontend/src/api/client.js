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

    // DB 교체나 토큰 만료 뒤에도 공개 API는 익명 요청으로 복구한다.
    // 단, 관심 종목/알림처럼 인증 필수인 API는 익명 재시도하면
    // "자격 인증 데이터가 제공되지 않았습니다."만 다시 돌아오므로 로그인 만료로 처리한다.
    if (error.response?.status === 401 && hasAuthHeader && !config._retriedWithoutAuth) {
      localStorage.removeItem("alphapick.access");
      localStorage.removeItem("alphapick.refresh");
      localStorage.removeItem("alphapick.user");
      window.dispatchEvent(new Event("auth-expired"));

      if (!canRetryWithoutAuth(config)) {
        error.response.data = { ...(error.response.data || {}), detail: "로그인이 만료되었습니다. 다시 로그인해 주세요." };
        return Promise.reject(error);
      }

      config._retriedWithoutAuth = true;
      delete config.headers.Authorization;
      return api(config);
    }

    return Promise.reject(error);
  },
);

function canRetryWithoutAuth(config) {
  const method = (config.method || "get").toLowerCase();
  const url = String(config.url || "");
  if (method !== "get") return false;
  return ![
    "/watchlist",
    "/community/notifications",
    "/users/me",
  ].some((path) => url.startsWith(path));
}

export function unwrapList(payload) {
  if (Array.isArray(payload)) return payload;
  if (payload?.results) return payload.results;
  return [];
}
