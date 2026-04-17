const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const messages = document.getElementById("messages");
const statusStrip = document.getElementById("status-strip");
const statusBadge = document.getElementById("status-badge");
const statusText = document.getElementById("status-text");
const agentBaseUrl = "http://localhost:8000";
const sessionKey = "iwoa-user-id";
const userId = (() => {
  const existing = window.sessionStorage.getItem(sessionKey);
  if (existing) return existing;
  const next = `web-${crypto.randomUUID()}`;
  window.sessionStorage.setItem(sessionKey, next);
  return next;
})();

function setStatusState(type, badge, text) {
  statusStrip.classList.remove("status-pending", "status-ok", "status-warn", "status-error");
  statusStrip.classList.add(type);
  statusBadge.textContent = badge;
  statusText.innerHTML = text;
}

function appendMessage(role, text) {
  const article = document.createElement("article");
  article.className = `message ${role}`;
  article.textContent = text;
  messages.appendChild(article);
  messages.scrollTop = messages.scrollHeight;
  return article;
}

function updateMessage(article, text) {
  article.textContent = text;
  messages.scrollTop = messages.scrollHeight;
}

async function refreshStatus() {
  try {
    const response = await fetch(`${agentBaseUrl}/health`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();

    if (!data.model_configured) {
      setStatusState("status-warn", "Config", `Agent 已启动，但模型密钥未配置，当前默认模型为 <strong>${data.model}</strong>。`);
      return;
    }

    if (!data.backend_reachable) {
      setStatusState("status-warn", "Backend", `当前由 <strong>${data.model}</strong> 驱动，但 Java 后端暂时不可达。请先启动 <code>8080</code> 服务。`);
      return;
    }

    setStatusState("status-ok", "Online", `当前由 <strong>${data.model}</strong> 驱动，Agent 与后端服务都已就绪。`);
  } catch (error) {
    setStatusState("status-error", "Offline", "Agent 服务不可用，请先启动 <code>http://localhost:8000</code>。");
  }
}

refreshStatus();

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message) return;

  appendMessage("user", message);
  input.value = "";

  try {
    const response = await fetch(`${agentBaseUrl}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, user_id: userId }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const assistantMessage = appendMessage("assistant", "");
    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error("Stream not supported");
    }

    const decoder = new TextDecoder();
    let buffer = "";
    let assistantText = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (!line.trim()) continue;
        const eventData = JSON.parse(line);

        if (eventData.type === "delta") {
          assistantText += eventData.delta;
          updateMessage(assistantMessage, assistantText);
        }

        if (eventData.type === "done") {
          if (eventData.tool_calls?.length) {
            assistantText += `\n工具调用：${JSON.stringify(eventData.tool_calls)}`;
          }
          updateMessage(assistantMessage, assistantText || eventData.answer || "");
        }
      }
    }

    refreshStatus();
  } catch (error) {
    appendMessage("assistant", "调用 Agent 服务失败，请确认 Python 服务已经启动。");
    refreshStatus();
  }
});
