/**
 * SupportBot AI — Embeddable Chatbot Widget
 * Version: 1.1.0
 * 
 * Self-contained, zero-dependency client-side integration for e-commerce storefronts.
 * 
 * Usage:
 * <script
 *   src="https://your-platform.example/widget/embed.js"
 *   data-business-id="your_business_id"
 *   data-api-url="https://your-platform.example/api/chat"
 *   data-title="Store Assistant"
 *   data-primary-color="#111827"
 *   data-position="bottom-right">
 * </script>
 */

(function () {
  "use strict";

  // Prevent multiple initializations on the same host page
  if (window.__SupportBotWidgetInitialized) {
    return;
  }
  window.__SupportBotWidgetInitialized = true;

  // Find current script tag and read configuration attributes
  var currentScript =
    document.currentScript ||
    (function () {
      var scripts = document.getElementsByTagName("script");
      return scripts[scripts.length - 1];
    })();

  function getAttr(name) {
    return currentScript ? currentScript.getAttribute(name) : null;
  }

  var config = window.SupportBotConfig || {};

  // Check if widget is explicitly disabled
  var isDisabled =
    config.disabled === true ||
    getAttr("data-disabled") === "true" ||
    getAttr("data-enabled") === "false";

  if (isDisabled) {
    console.info("[SupportBot AI] Widget is disabled by configuration.");
    return;
  }

  // Parse configuration with support for attribute aliases
  var businessId =
    config.businessId ||
    getAttr("data-business-id") ||
    getAttr("data-tenant-id") ||
    "";

  var apiBase = config.apiBase || getAttr("data-api-base") || "";
  var apiUrl =
    config.apiUrl ||
    getAttr("data-api-url") ||
    (apiBase ? apiBase.replace(/\/+$/, "") + "/api/chat" : "/api/chat");

  var title =
    config.title ||
    getAttr("data-title") ||
    getAttr("data-name") ||
    "AI Support Assistant";

  var welcomeMessage =
    config.welcomeMessage ||
    getAttr("data-welcome-message") ||
    getAttr("data-welcome") ||
    "Hi there! 👋 How can I help you today?";

  var primaryColor =
    config.primaryColor ||
    getAttr("data-primary-color") ||
    getAttr("data-color") ||
    "#4F46E5";

  var position =
    config.position ||
    getAttr("data-position") ||
    "bottom-right";

  if (!businessId) {
    console.warn(
      "[SupportBot AI] data-business-id attribute is required to initialize the widget."
    );
  }

  // Session ID management for multi-turn conversation continuity
  var storageKey = "supportbot_sess_" + (businessId || "default");
  var sessionId = "";
  try {
    sessionId = sessionStorage.getItem(storageKey) || "";
    if (!sessionId) {
      sessionId =
        "wgt_sess_" +
        Math.random().toString(36).substring(2, 10) +
        "_" +
        Date.now();
      sessionStorage.setItem(storageKey, sessionId);
    }
  } catch (e) {
    sessionId = "wgt_sess_" + Date.now();
  }

  // HTML sanitization helper for configuration rendering
  function escapeHTML(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Inject Isolated CSS Styles
  var style = document.createElement("style");
  style.id = "supportbot-widget-styles";
  var isLeft = position === "bottom-left";

  style.textContent = `
    .sb-widget-container {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      position: fixed;
      ${isLeft ? "left: 20px;" : "right: 20px;"}
      bottom: 20px;
      z-index: 999999;
    }
    .sb-launcher-btn {
      width: 60px;
      height: 60px;
      border-radius: 30px;
      background: ${primaryColor};
      color: #ffffff;
      border: none;
      box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: transform 0.2s ease, box-shadow 0.2s ease;
      outline: none;
    }
    .sb-launcher-btn:hover {
      transform: scale(1.05);
      box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
    }
    .sb-launcher-btn svg {
      width: 28px;
      height: 28px;
      fill: currentColor;
    }
    .sb-chat-window {
      position: absolute;
      ${isLeft ? "left: 0;" : "right: 0;"}
      bottom: 75px;
      width: 360px;
      max-width: calc(100vw - 40px);
      height: 520px;
      max-height: calc(100vh - 120px);
      background: #ffffff;
      border-radius: 16px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      transition: opacity 0.25s ease, transform 0.25s ease;
      border: 1px solid rgba(0, 0, 0, 0.08);
    }
    .sb-chat-window.sb-hidden {
      opacity: 0;
      pointer-events: none;
      transform: translateY(15px) scale(0.95);
      display: none;
    }
    .sb-chat-header {
      background: ${primaryColor};
      color: #ffffff;
      padding: 14px 18px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .sb-header-title {
      font-size: 15px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .sb-online-dot {
      width: 8px;
      height: 8px;
      border-radius: 4px;
      background: #10B981;
    }
    .sb-close-btn {
      background: transparent;
      border: none;
      color: #ffffff;
      cursor: pointer;
      font-size: 18px;
      padding: 4px;
      line-height: 1;
      opacity: 0.85;
    }
    .sb-close-btn:hover {
      opacity: 1;
    }
    .sb-message-list {
      flex: 1;
      padding: 16px;
      overflow-y: auto;
      background: #F9FAFB;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .sb-message {
      max-width: 80%;
      padding: 10px 14px;
      border-radius: 14px;
      font-size: 13.5px;
      line-height: 1.45;
      word-break: break-word;
    }
    .sb-msg-user {
      align-self: flex-end;
      background: ${primaryColor};
      color: #ffffff;
      border-bottom-right-radius: 4px;
    }
    .sb-msg-assistant {
      align-self: flex-start;
      background: #FFFFFF;
      color: #1F2937;
      border: 1px solid #E5E7EB;
      border-bottom-left-radius: 4px;
    }
    .sb-typing-indicator {
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 8px 12px;
      background: #FFFFFF;
      border: 1px solid #E5E7EB;
      border-radius: 12px;
      align-self: flex-start;
      width: fit-content;
    }
    .sb-typing-dot {
      width: 6px;
      height: 6px;
      background: #9CA3AF;
      border-radius: 3px;
      animation: sb-bounce 1.4s infinite ease-in-out both;
    }
    .sb-typing-dot:nth-child(1) { animation-delay: -0.32s; }
    .sb-typing-dot:nth-child(2) { animation-delay: -0.16s; }
    @keyframes sb-bounce {
      0%, 80%, 100% { transform: scale(0); }
      40% { transform: scale(1); }
    }
    .sb-input-area {
      padding: 12px;
      background: #FFFFFF;
      border-top: 1px solid #E5E7EB;
      display: flex;
      gap: 8px;
      align-items: center;
    }
    .sb-input {
      flex: 1;
      padding: 10px 14px;
      border: 1px solid #D1D5DB;
      border-radius: 20px;
      font-size: 13.5px;
      outline: none;
    }
    .sb-input:focus {
      border-color: ${primaryColor};
    }
    .sb-send-btn {
      width: 36px;
      height: 36px;
      border-radius: 18px;
      background: ${primaryColor};
      color: #ffffff;
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      transition: background 0.15s ease;
    }
    .sb-send-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
    .sb-send-btn svg {
      width: 16px;
      height: 16px;
      fill: currentColor;
    }
    .sb-footer-brand {
      text-align: center;
      font-size: 10.5px;
      color: #9CA3AF;
      padding: 4px 0 6px 0;
      background: #FFFFFF;
    }
  `;
  document.head.appendChild(style);

  // Build Scoped DOM Elements
  var container = document.createElement("div");
  container.className = "sb-widget-container";

  container.innerHTML = `
    <div class="sb-chat-window sb-hidden" id="sbChatWindow">
      <div class="sb-chat-header">
        <div class="sb-header-title">
          <span class="sb-online-dot"></span>
          <span>${escapeHTML(title)}</span>
        </div>
        <button class="sb-close-btn" id="sbCloseBtn" aria-label="Close chat">✕</button>
      </div>
      <div class="sb-message-list" id="sbMessageList">
        <div class="sb-message sb-msg-assistant">${escapeHTML(welcomeMessage)}</div>
      </div>
      <div class="sb-input-area">
        <input type="text" class="sb-input" id="sbInput" placeholder="Type a message..." autocomplete="off" />
        <button class="sb-send-btn" id="sbSendBtn" aria-label="Send message">
          <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
        </button>
      </div>
      <div class="sb-footer-brand">Powered by SupportBot AI</div>
    </div>
    <button class="sb-launcher-btn" id="sbLauncherBtn" aria-label="Open support chat">
      <svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/></svg>
    </button>
  `;

  document.body.appendChild(container);

  var launcherBtn = container.querySelector("#sbLauncherBtn");
  var chatWindow = container.querySelector("#sbChatWindow");
  var closeBtn = container.querySelector("#sbCloseBtn");
  var messageList = container.querySelector("#sbMessageList");
  var inputEl = container.querySelector("#sbInput");
  var sendBtn = container.querySelector("#sbSendBtn");

  var isOpen = false;
  var isSending = false;

  function toggleChat() {
    isOpen = !isOpen;
    if (isOpen) {
      chatWindow.classList.remove("sb-hidden");
      inputEl.focus();
    } else {
      chatWindow.classList.add("sb-hidden");
    }
  }

  launcherBtn.addEventListener("click", toggleChat);
  closeBtn.addEventListener("click", toggleChat);

  function appendMessage(text, role) {
    var msgEl = document.createElement("div");
    msgEl.className =
      "sb-message " + (role === "user" ? "sb-msg-user" : "sb-msg-assistant");
    msgEl.textContent = text;
    messageList.appendChild(msgEl);
    messageList.scrollTop = messageList.scrollHeight;
  }

  function showTyping() {
    var typingEl = document.createElement("div");
    typingEl.className = "sb-typing-indicator";
    typingEl.id = "sbTypingIndicator";
    typingEl.innerHTML = `
      <div class="sb-typing-dot"></div>
      <div class="sb-typing-dot"></div>
      <div class="sb-typing-dot"></div>
    `;
    messageList.appendChild(typingEl);
    messageList.scrollTop = messageList.scrollHeight;
  }

  function hideTyping() {
    var typingEl = document.getElementById("sbTypingIndicator");
    if (typingEl) {
      typingEl.remove();
    }
  }

  async function handleSend() {
    var text = inputEl.value.trim();
    if (!text || isSending) return;

    if (!businessId) {
      appendMessage("Error: Business ID is not configured.", "assistant");
      return;
    }

    appendMessage(text, "user");
    inputEl.value = "";
    isSending = true;
    sendBtn.disabled = true;
    showTyping();

    try {
      var response = await fetch(apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          business_id: businessId,
          session_id: sessionId,
          message: text,
        }),
      });

      hideTyping();

      if (response.status === 404) {
        appendMessage(
          "This support assistant is currently unavailable for this store.",
          "assistant"
        );
        return;
      }

      if (response.status === 400) {
        appendMessage(
          "Sorry, your message could not be processed. Please check your query.",
          "assistant"
        );
        return;
      }

      if (!response.ok) {
        throw new Error("HTTP error " + response.status);
      }

      var data = await response.json();
      var answer = data.answer || "I received your message.";
      if (data.session_id) {
        sessionId = data.session_id;
        try {
          sessionStorage.setItem(storageKey, sessionId);
        } catch (e) {}
      }
      appendMessage(answer, "assistant");
    } catch (err) {
      hideTyping();
      appendMessage(
        "Sorry, I am unable to connect to the assistant right now. Please try again later.",
        "assistant"
      );
      console.error("[SupportBot AI] Chat error:", err);
    } finally {
      hideTyping();
      isSending = false;
      sendBtn.disabled = false;
      inputEl.focus();
    }
  }

  sendBtn.addEventListener("click", handleSend);
  inputEl.addEventListener("keypress", function (e) {
    if (e.key === "Enter") {
      handleSend();
    }
  });
})();
