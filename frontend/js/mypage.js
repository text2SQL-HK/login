/**
 * mypage.js — 마이페이지 로직
 */

document.addEventListener("DOMContentLoaded", () => {
  const LOGIN_UI_PATH = "/login";
  const msgEl = document.getElementById("msg");

  // --- 현재 사용자 정보 로드 ---
  loadUserInfo();

  async function loadUserInfo() {
    try {
      const user = await apiGet("/api/auth/me");
      document.getElementById("myEmail").value = user.email;
      document.getElementById("myLevel").value =
        user.access_level === 9 ? "관리자" : "일반 사용자";
      document.getElementById("myCreated").value = new Date(
        user.created_at
      ).toLocaleDateString("ko-KR", {
        year: "numeric",
        month: "long",
        day: "numeric",
      });
      document.getElementById("myUsername").value = user.username;
      document.getElementById("myPhone").value = user.phone_number || "";
    } catch {
      // 비로그인 → 리다이렉트 (api.js에서 자동 처리)
    }
  }

  // --- 정보 수정 폼 제출 ---
  document.getElementById("updateForm").addEventListener("submit", async (e) => {
    e.preventDefault();

    const username = document.getElementById("myUsername").value.trim();
    const phone_number = document.getElementById("myPhone").value.trim() || null;

    if (!username) {
      showMessage(msgEl, "사용자 이름은 필수입니다.", "error");
      return;
    }

    try {
      await apiPut("/api/users/me", { username, phone_number });
      showMessage(msgEl, "정보가 성공적으로 수정되었습니다.", "success");
    } catch (err) {
      showMessage(msgEl, err.message, "error");
    }
  });

  // --- 로그아웃 ---
  document.getElementById("logoutBtn").addEventListener("click", async () => {
    try {
      await apiPost("/api/auth/logout");
    } catch {
      // 무시
    }
    window.location.href = LOGIN_UI_PATH;
  });
});
