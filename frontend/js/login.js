/**
 * login.js — 로그인/회원가입 페이지 로직
 */

document.addEventListener("DOMContentLoaded", () => {
  const TTS_HOME_PATH = "/tts";
  const msgEl = document.getElementById("msg");
  const tabs = document.querySelectorAll(".tab");
  const tabContents = document.querySelectorAll(".tab-content");

  // --- 이미 로그인 상태인지 확인 ---
  apiGet("/api/auth/me")
    .then(() => {
      // 이미 로그인되어 있으면 TTS 페이지로 이동
      window.location.href = TTS_HOME_PATH;
    })
    .catch(() => {
      // 비로그인 상태 → 정상적으로 로그인 폼 표시
    });

  // --- 탭 전환 ---
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.tab;

      tabs.forEach((t) => t.classList.remove("active"));
      tabContents.forEach((tc) => tc.classList.remove("active"));

      tab.classList.add("active");
      document.getElementById(`tab-${target}`).classList.add("active");

      // 메시지 초기화
      msgEl.style.display = "none";
    });
  });

  // --- 로그인 폼 제출 ---
  document.getElementById("loginForm").addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = document.getElementById("loginEmail").value.trim();
    const password = document.getElementById("loginPassword").value;

    try {
      await apiPost("/api/auth/login", { email, password });
      window.location.href = TTS_HOME_PATH;
    } catch (err) {
      showMessage(msgEl, err.message, "error");
    }
  });

  // --- 회원가입 폼 제출 ---
  document.getElementById("registerForm").addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = document.getElementById("regEmail").value.trim();
    const password = document.getElementById("regPassword").value;
    const username = document.getElementById("regUsername").value.trim();
    const phone_number = document.getElementById("regPhone").value.trim() || null;

    try {
      await apiPost("/api/auth/register", { email, password, username, phone_number });
      showMessage(msgEl, "가입이 완료되었습니다! 로그인해주세요.", "success");

      // 로그인 탭으로 전환
      tabs[0].click();
    } catch (err) {
      showMessage(msgEl, err.message, "error");
    }
  });
});
