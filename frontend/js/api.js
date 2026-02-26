/**
 * api.js — 공통 fetch 래퍼
 * 모든 요청에 credentials: 'include'를 설정하여 쿠키를 자동 포함합니다.
 */

const LOGIN_UI_PATH = "/login";
const API_BASE = "";

/**
 * 공통 API 호출 함수
 * @param {string} endpoint - API 경로 (예: /api/auth/login)
 * @param {object} options - fetch 옵션 (method, body 등)
 * @returns {Promise<object>} 응답 JSON
 */
async function api(endpoint, options = {}) {
  const config = {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  };

  // headers가 options에도 있으면 병합
  if (options.headers) {
    config.headers = { ...config.headers, ...options.headers };
  }

  const response = await fetch(`${API_BASE}${endpoint}`, config);

  if (response.status === 401) {
    // 이미 로그인 페이지라면 리다이렉트하지 않음 (무한 루프 방지)
    const path = window.location.pathname;
    const isLoginPage =
      path === "/" || path === LOGIN_UI_PATH || path === `${LOGIN_UI_PATH}/`;
    if (!isLoginPage) {
      window.location.href = LOGIN_UI_PATH;
    }
    throw new Error("인증이 필요합니다.");
  }

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "요청에 실패했습니다.");
  }

  return data;
}

/**
 * GET 요청
 */
async function apiGet(endpoint) {
  return api(endpoint, { method: "GET" });
}

/**
 * POST 요청
 */
async function apiPost(endpoint, body) {
  return api(endpoint, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/**
 * PUT 요청
 */
async function apiPut(endpoint, body) {
  return api(endpoint, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

/**
 * 알림 메시지 표시
 */
function showMessage(container, text, type = "error") {
  if (!container) return;
  container.textContent = text;
  container.className = `message ${type}`;
  container.style.display = "block";
  if (type === "success") {
    setTimeout(() => {
      container.style.display = "none";
    }, 3000);
  }
}
