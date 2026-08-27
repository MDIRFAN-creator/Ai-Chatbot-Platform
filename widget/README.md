# SupportBot AI Web Widget & API Integration

A lightweight, zero-dependency, embeddable JavaScript chatbot widget for business websites, backed by the SupportBot AI HTTP Chat API.

---

## 1. Quick Start

Add the following `<script>` tag before the closing `</body>` tag on your website:

```html
<!-- Production Embed Snippet -->
<script
    src="https://api.yourdomain.com/widget/embed.js"
    data-business-id="urbanthreads_001"
    data-api-url="https://api.yourdomain.com/api/chat"
    data-title="UrbanThreads Assistant"
    data-welcome-message="Hi there! 👋 How can I help you with UrbanThreads today?"
    data-primary-color="#111827"
    data-position="bottom-right">
</script>
```

For local development and testing:
```html
<!-- Local Development Embed Snippet -->
<script
    src="http://localhost:8000/widget/embed.js"
    data-business-id="urbanthreads_001"
    data-api-url="http://localhost:8000/api/chat"
    data-title="UrbanThreads Assistant"
    data-welcome-message="Hi there! 👋 How can I help you with UrbanThreads today?"
    data-primary-color="#111827"
    data-position="bottom-right">
</script>
```

---

## 2. Configuration Attributes & Aliases

| Attribute | Aliases | Type | Default | Description |
| :--- | :--- | :---: | :---: | :--- |
| `data-business-id` | `data-tenant-id` | `string` | **Required** | The unique identifier of your business tenant in SupportBot AI. |
| `data-api-url` | `data-api-base` | `string` | `/api/chat` | The HTTP endpoint for chat requests (e.g. `http://localhost:8000/api/chat` or base `http://localhost:8000`). |
| `data-title` | `data-name` | `string` | `AI Support Assistant` | Header title displayed in the chat window. |
| `data-welcome-message`| `data-welcome` | `string` | `Hi there! 👋 ...` | Initial greeting message displayed to customers. |
| `data-primary-color` | `data-color` | `string` | `#4F46E5` | Hex or CSS color for launcher button, header, and user bubbles. |
| `data-position` | — | `string` | `bottom-right` | Floating widget placement: `bottom-right` or `bottom-left`. |
| `data-disabled` | `data-enabled="false"` | `string` | `false` | When set to `"true"`, suppresses widget initialization. |

Alternatively, configure global options in JavaScript prior to loading the script:

```html
<script>
  window.SupportBotConfig = {
    businessId: "urbanthreads_001",
    apiUrl: "http://localhost:8000/api/chat",
    title: "UrbanThreads Assistant",
    welcomeMessage: "Welcome to UrbanThreads! Ask us anything.",
    primaryColor: "#111827",
    position: "bottom-right"
  };
</script>
<script src="http://localhost:8000/widget/embed.js"></script>
```

---

## 3. Running the Servers Locally

### A. Start the HTTP Chat API Server
```powershell
.venv\Scripts\python.exe -m uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
```
- Health Check: `GET http://localhost:8000/health`
- Chat Endpoint: `POST http://localhost:8000/api/chat`
- Static Widget JS: `GET http://localhost:8000/widget/embed.js`

### B. Start the Streamlit Dashboard
```powershell
.venv\Scripts\python.exe -m streamlit run app/main.py
```
- Dashboard URL: `http://localhost:8501`

### C. Test the Standalone Storefront Page
Open [widget/test_page.html](file:///c:/Users/IRFAN/OneDrive/Desktop/Ai%20Chatbot%20Platform/widget/test_page.html) in your web browser with the API server running on port 8000.

---

## 4. HTTP API Payload Contract

### Request: `POST /api/chat`
```http
POST /api/chat HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "business_id": "urbanthreads_001",
  "session_id": "visitor-session-123",
  "message": "Do you accept returns?"
}
```

### Response: `200 OK`
```json
{
  "answer": "Returns are accepted within 7 days of delivery for eligible unworn items in original condition.",
  "business_id": "urbanthreads_001",
  "session_id": "visitor-session-123",
  "fallback_triggered": false
}
```

---

## 5. Security Guarantees

1. **Zero Secret Leakage**: Client JavaScript contains zero API keys (`GEMINI_API_KEY`), database connection strings, or system prompts.
2. **XSS Protection**: All incoming messages and user inputs pass through native `.textContent` escaping before DOM insertion.
3. **Session Continuity**: Conversation sessions are isolated per business in browser `sessionStorage`.
4. **Tenant Isolation**: The HTTP API strictly routes retrieval, memory, and generation to the verified `business_id`.
5. **CORS Defense**: Allowed origins are configurable via `CORS_ALLOWED_ORIGINS` environment variable.
