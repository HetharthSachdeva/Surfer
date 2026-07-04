![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Celery](https://img.shields.io/badge/celery-%23a9cc51.svg?style=for-the-badge&logo=celery&logoColor=dd)
![Redis](https://img.shields.io/badge/redis-%23DD0031.svg?style=for-the-badge&logo=redis&logoColor=white)
![Playwright](https://img.shields.io/badge/class-Playwright-45ba4b?style=for-the-badge&logo=playwright)

# Surfer — Autonomous AI Web Operator

Surfer is a full-stack, distributed web automation agent designed to execute complex tasks on the live internet. Powered by large language models (LLMs) and headless browser orchestration, Surfer turns high-level, natural language goals into precise, real-time web actions.

---

## 🌟 The Vision

The vision of Surfer is to build a **fully autonomous personal assistant** that works on your behalf. 

Instead of writing custom scripts for different websites, you provide a single high-level objective:
> *"Book a flight ticket from Delhi to Mumbai for next Tuesday under ₹6,000"* or *"Go to my dashboard, download the latest CSV invoice, and save a screenshot."*

Surfer takes this goal, plans the path, launches a browser, handles login screens, navigates forms, solves errors dynamically, and returns the finished state.

---

## 🚀 Key Features & Systems Architecture

Surfer is engineered for high performance, reliability, and horizontal scaling. It is built using a **decoupled asynchronous architecture**:

### 1. Asynchronous Distributed Task Queue (Celery + Redis)
* **Non-Blocking API**: The FastAPI backend offloads heavy browser operations to a background Celery worker queue instantly (responding in <5ms with a `task_id`).
* **Microservices Design**: The API server remains lightweight and responsive, while Celery workers execute resource-heavy Chromium processes independently.

### 2. Stable Selector Index Mapping
* **Dynamic Tagging**: Surfer injects a lightweight Javascript engine that scans the active page DOM and overlays temporary, sequential `data-surfer-id="[index]"` attributes on visible interactive elements.
* **100% Click Precision**: By forcing the LLM to target element indices (e.g. `click 3`) instead of volatile Tailwind hashes or raw CSS paths, Surfer bypasses class name changes and dynamic UI alterations.

### 3. Optimistic Execution with Reactive Replanning
* **Low Latency**: Instead of calling the LLM before every single click, Surfer generates a full execution plan initially and runs at native browser speed.
* **Fault-Tolerant Feedback Loop**: If an action fails (e.g., due to a popup blocker or timeout), the system isolates the active page state, extracts the visible DOM, and prompts the Gemini LLM for an in-context recovery detour without restarting the browser.

### 4. Pydantic-Enforced Structured JSON Outputs
* **Deterministic Plans**: The planner uses `google-genai`'s structured decoding, enforcing strict Pydantic JSON schemas. This completely eliminates formatting bugs, markdown code blocks, or conversational preambles from the LLM.

---

## 📂 Directory Structure

```
d:\Coding\Surfer\
├── backend/
│   ├── celery_app.py (Celery Broker Setup)
│   ├── tasks.py (Asynchronous Browser Worker)
│   ├── main.py (FastAPI App & Status Pollers)
│   ├── web_agent.py (Playwright Browser Driver)
│   ├── gemini.py (Pydantic LLM Planner)
│   └── .env (API Credentials)
└── frontend/
    ├── index.html (Dashboard Interface)
    ├── style.css (Glassmorphic Dark Theme)
    └── app.js (Real-time Status Polling Event Loop)
```

---

## 🛠️ Setup & Installation

### 1. Prerequisites
Ensure you have the following installed on your machine:
* Python 3.10+
* **[Redis Server](https://github.com/tporadowski/redis/releases)** (For Windows, download the latest `Redis-x64-5.0.14.1.zip` and extract it to `C:\Redis`).

### 2. Clone and Install Dependencies
Install the required packages in your Python environment:
```bash
pip install fastapi uvicorn "redis<5.0.0" celery google-genai python-dotenv playwright
python -m playwright install chromium
```
*(Note: We lock the client `redis` package below v5.0.0 to guarantee backward compatibility with Redis Server 5.x on Windows, bypassing RESP3 handshake issues).*

### 3. Add API Keys
Create a `.env` file inside the `backend/` directory:
```text
# backend/.env
GEMINI_API_KEY=your_google_gemini_api_key_here
```

---

## 🏃 Running the Application

To run the full decoupled system, open three terminal windows:

### Step 1: Start Redis Server
```powershell
cd C:\Redis-x64-5.0.14.1
./redis-server.exe
```

### Step 2: Start Celery Worker
Navigate to the `backend` directory and start the background worker:
```bash
cd backend
celery -A tasks worker --loglevel=info --pool=solo
```
*(Note: We use the `--pool=solo` flag on Windows to bypass the lack of Linux-native process forking).*

### Step 3: Start FastAPI Server
Navigate to the `backend` directory and run the API:
```bash
cd backend
python main.py
```

### Step 4: Open the Frontend
Open `frontend/index.html` directly in your browser. Enter your goal and click **Run Agent**!
