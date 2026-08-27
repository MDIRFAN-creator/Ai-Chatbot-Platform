# SupportBot AI — Production Deployment Guide

This guide describes how to deploy, configure, and maintain the SupportBot AI platform in a production environment.

---

## 1. System Architecture in Production

```text
                                Internet
                                   │
               ┌───────────────────┴───────────────────┐
               ▼                                       ▼
       (Admin Dashboard)                        (Merchant Website)
   https://app.supportbot.ai                 https://urbanthreads.com
               │                                       │
               │ HTTPS                                 │ <script src="embed.js">
               │                                       ▼
               │                            (Customer Chat Widget)
               │                                       │
               │                                       │ HTTP POST /api/chat
               ▼                                       ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                 Reverse Proxy (Nginx / Traefik)             │
    │  - SSL/TLS Termination (Let's Encrypt)                     │
    │  - Rate Limiting & DDoS Mitigation                          │
    │  - CORS Policy Enforcement                                  │
    └──────────────┬───────────────────────────────┬──────────────┘
                   │ :8501                         │ :8000
                   ▼                               ▼
       ┌──────────────────────┐        ┌──────────────────────┐
       │ Streamlit Dashboard  │        │  Starlette ASGI API  │
       │ (Admin & Management) │        │ (High-Throughput)    │
       └───────────┬──────────┘        └──────────┬───────────┘
                   │                              │
                   └──────────────┬───────────────┘
                                  │
                                  ▼
                     ┌──────────────────────────┐
                     │ Core Engine & Persist    │
                     │ - SQLite (Source of Truth)│
                     │ - FAISS (Vector Store)   │
                     │ - Google Gemini API      │
                     └──────────────────────────┘
```

---

## 2. Server Requirements

- **Operating System**: Linux (Ubuntu 22.04 LTS recommended) / Debian
- **Compute**: Minimum 2 vCPUs, 4 GB RAM (8 GB RAM recommended for local embeddings cache)
- **Disk**: 20+ GB SSD (for sentence-transformers cache and SQLite backups)
- **Python**: Python 3.10, 3.11, or 3.12
- **Network**: Port 80 (HTTP), 443 (HTTPS) open to the internet

---

## 3. Installation & Setup

### A. Clone Repository & Setup Virtual Environment
```bash
git clone https://github.com/your-org/ai-chatbot-platform.git /opt/supportbot
cd /opt/supportbot

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### B. Configure Environment Variables
Create `/opt/supportbot/.env`:
```env
# Google Gemini API
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
GEMINI_API_KEY=your_production_gemini_api_key
LLM_TEMPERATURE=0.0

# Local Embeddings
EMBEDDING_PROVIDER=huggingface_local
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
RETRIEVAL_TOP_K=5
RELEVANCE_SCORE_THRESHOLD=1.30

# SQLite Database
DATABASE_URL=sqlite:////opt/supportbot/data/supportbot.db

# HTTP API & CORS
API_HOST=0.0.0.0
API_PORT=8000
CORS_ALLOWED_ORIGINS=https://app.supportbot.ai,https://urbanthreads.com
WIDGET_API_BASE_URL=https://api.supportbot.ai

# Application
APP_ENV=production
DEBUG=false
```

### C. Seed Initial Reference Data (Optional)
```bash
python data/seed/seed_data.py --force
```

---

## 4. Process Management with Systemd

### A. Starlette HTTP Chat API Service
Create `/etc/systemd/system/supportbot-api.service`:
```ini
[Unit]
Description=SupportBot AI HTTP Chat API Service
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/supportbot
EnvironmentFile=/opt/supportbot/.env
ExecStart=/opt/supportbot/.venv/bin/uvicorn api.server:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### B. Streamlit Admin Dashboard Service
Create `/etc/systemd/system/supportbot-ui.service`:
```ini
[Unit]
Description=SupportBot AI Streamlit Admin Dashboard
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/supportbot
EnvironmentFile=/opt/supportbot/.env
ExecStart=/opt/supportbot/.venv/bin/streamlit run app/main.py --server.port 8501 --server.address 127.0.0.1 --server.headless true
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### C. Start & Enable Services
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now supportbot-api
sudo systemctl enable --now supportbot-ui
```

---

## 5. Reverse Proxy Configuration (Nginx)

Create `/etc/nginx/sites-available/supportbot.conf`:
```nginx
# 1. API Server (api.supportbot.ai)
server {
    server_name api.supportbot.ai;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Serve static embed.js with aggressive caching
    location /widget/ {
        alias /opt/supportbot/widget/;
        expires 7d;
        add_header Access-Control-Allow-Origin *;
        add_header Cache-Control "public, no-transform";
    }
}

# 2. Admin Dashboard (app.supportbot.ai)
server {
    server_name app.supportbot.ai;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
```

Enable SSL using Let's Encrypt:
```bash
sudo certbot --nginx -d api.supportbot.ai -d app.supportbot.ai
```

---

## 6. Security Best Practices

1. **Keep Secrets Secure**: Never commit `.env` or API keys to source control.
2. **Restrict CORS in Production**: Set `CORS_ALLOWED_ORIGINS` to the exact merchant storefront domains.
3. **Database Backup**: Schedule daily SQLite backups:
   ```bash
   sqlite3 /opt/supportbot/data/supportbot.db ".backup /opt/backups/supportbot_$(date +%F).db"
   ```
4. **FAISS Index Persistence**: Back up the `/opt/supportbot/vectorstore` directory alongside SQLite backups.
