/**
 * index.js — 채팅 메인 페이지 로직
 */

let currentUser = null;
let pollingInterval = null;
const LOGIN_UI_PATH = "/login";
const LOGIN_CHAT_API = "/api/login/chat";

document.addEventListener("DOMContentLoaded", () => {
  init();
});

async function init() {
  try {
    currentUser = await apiGet("/api/auth/me");
    document.getElementById("navUser").textContent = currentUser.username;
  } catch {
    // 비로그인 → 로그인 페이지로 (api.js에서 자동 리다이렉트)
    return;
  }

  // 초기 메시지 로드
  await loadMessages();

  // 주기적으로 새 메시지 폴링 (5초)
  pollingInterval = setInterval(loadMessages, 5000);

  // 전송 버튼
  document.getElementById("sendBtn").addEventListener("click", sendMessage);

  // Enter 키로 전송
  document.getElementById("chatInput").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // 로그아웃
  document.getElementById("logoutBtn").addEventListener("click", async () => {
    try {
      await apiPost("/api/auth/logout");
    } catch {
      // 무시
    }
    window.location.href = LOGIN_UI_PATH;
  });
}

/**
 * 채팅 메시지 로드
 */
async function loadMessages() {
  try {
    const messages = await apiGet(`${LOGIN_CHAT_API}?limit=100&offset=0`);
    renderMessages(messages);
  } catch {
    // 에러 시 폴링 중지
    if (pollingInterval) clearInterval(pollingInterval);
  }
}

/**
 * 메시지를 화면에 렌더링
 */
function renderMessages(messages) {
  const container = document.getElementById("chatMessages");
  const wasAtBottom =
    container.scrollHeight - container.scrollTop - container.clientHeight < 50;

  // 최신순으로 받았으므로 역순(오래된 순)으로 표시
  const sorted = [...messages].reverse();

  container.innerHTML = sorted
    .map((msg) => {
      const isMine =
        currentUser && msg.user_id === currentUser.user_id;
      const time = new Date(msg.created_at).toLocaleTimeString("ko-KR", {
        hour: "2-digit",
        minute: "2-digit",
      });
      return `
        <div class="chat-message${isMine ? " mine" : ""}">
          <div class="meta">
            <span class="author">${escapeHtml(msg.username)}</span>
            <span>${time}</span>
          </div>
          <div class="body">${escapeHtml(msg.content)}</div>
        </div>`;
    })
    .join("");

  // 새 메시지가 도착하면 스크롤을 맨 아래로
  if (wasAtBottom) {
    container.scrollTop = container.scrollHeight;
  }
}

/**
 * 메시지 전송
 */
async function sendMessage() {
  const input = document.getElementById("chatInput");
  const content = input.value.trim();
  if (!content) return;

  try {
    input.value = "";
    await apiPost(LOGIN_CHAT_API, { content, message_type: "TEXT" });
    await loadMessages();

    // 전송 후 스크롤 맨 아래로
    const container = document.getElementById("chatMessages");
    container.scrollTop = container.scrollHeight;
  } catch (err) {
    alert("메시지 전송 실패: " + err.message);
  }
}

/**
 * HTML 이스케이프 (XSS 방지)
 */
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
