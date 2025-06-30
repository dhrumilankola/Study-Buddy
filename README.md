# Study Buddy 🧑‍🎓🤖

_A full-stack AI study assistant with document-aware chat, voice conversation, and persistent history_

---

![Study Buddy – Hero Demo](docs/hero.gif)

> **"Ask questions about your notes, talk through complex topics, or quiz yourself – Study Buddy is your personal study partner."**

---

## ✨ Features

- **Document-Specific RAG:** Each chat session references only the documents you assign – no cross-contamination.
- **Multi-Modal Voice Chat 🎙️:** Speak naturally with your Study Buddy powered by [ElevenLabs Conversational AI](https://elevenlabs.io/).
- **Persistent History 💾:** Chats and sessions survive browser refreshes & restarts.
- **Multi-Format Uploads:** PDF, TXT, PPTX, and IPYNB out-of-the-box (extendable).
- **Real-Time Streaming ⚡:** Enjoy token-streamed answers with Google Gemini or local Ollama models.
- **Session Isolation 🛡️:** Keep a "Linear Algebra" session completely separate from "Transformers Paper" session.
- **Embeddings & Vector Search 🔍:** Super-charged by Sentence-Transformers and a local vector store.

---

## 📸 Live Demo

1. **Chat/Voice Mode** – Ask follow-up questions hands-free
   
   ![Chat](docs/chat_interface.png)
   ![Voice Chat](docs/voice_chat.png)
2. **Document Manager** – Upload & monitor indexing status
   
   ![Uploads Screenshot](docs/manage_documents.png)

---

## 🗺️ Table of Contents

1. 🚀 [Quick Start](#-quick-start)
2. 🔧 [Configuration](#-configuration)
3. 🛠️ [Backend Setup](#-backend-setup)
4. 🎨 [Frontend Setup](#-frontend-setup)
5. 🎙️ [Enable Voice Chat](#-enable-voice-chat-optional)
6. 📖 [Usage Guide](#-how-to-use-study-buddy)
7. 👩‍💻 [Development & Troubleshooting](#-development--troubleshooting)
8. 🤝 [Contributing](#-contributing)
9. 📝 [License](#-license)

---

## 🚀 Quick Start

```bash
# 1. Clone repo
$ git clone https://github.com/your-org/study-buddy.git && cd study-buddy

# 2. Start PostgreSQL (macOS example)
$ brew services start postgresql

# 3. Bootstrap database
$ psql -U postgres -c "CREATE DATABASE study_buddy;"
$ psql -U postgres -c "CREATE USER study_buddy_user WITH PASSWORD 'change_me';"
$ psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE study_buddy TO study_buddy_user;"

# 4. Run backend & frontend (separate terminals)
$ cd backend && make run   # or `python main.py`
$ cd ../frontend && npm start
```

_Need Docker?_ A containerised setup is tracked in `docker-compose.yml` (coming soon).

---

## 🔧 Configuration

Create **two** `.env` files:

```shell
# backend/.env
API_PORT=8000
CORS_ORIGINS=["http://localhost:3000"]

# ─── Database ─────────────────────────
DATABASE_URL=postgresql+asyncpg://study_buddy_user:change_me@localhost:5432/study_buddy

# ─── Model Provider ───────────────────
DEFAULT_MODEL_PROVIDER=gemini   # or "ollama"

#   Gemini (if provider == gemini)
GOOGLE_API_KEY=your_google_api_key
GOOGLE_PROJECT_ID=your_project_id
GEMINI_MODEL=gemini-1.5-flash

#   Ollama (if provider == ollama)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3:8b

# ─── Embeddings & RAG ────────────────
EMBEDDINGS_MODEL=all-mpnet-base-v2
MODEL_TEMPERATURE=0.7

# ─── ElevenLabs Voice Chat ───────────
ELEVENLABS_API_KEY=sk_your_elevenlabs_key
AGENT_ID=agent_XXXXXXXXXXXX
```

```shell
# frontend/.env
REACT_APP_API_BASE_URL=http://localhost:8000/api/v1
```

> 🔑 **Tip:** Missing an ENV? The backend will tell you exactly which one.

---

## 🛠️ Backend Setup

```bash
# In /backend
python -m venv venv           # Create virtual env
source venv/bin/activate       # Windows: venv\Scripts\activate

pip install -r requirements.txt

# Create required directories
mkdir -p ../data/uploads ../data/vector_store

# Initialise DB tables – copy the inline snippet below into a REPL **or** save it as `init_db.py` and run `python init_db.py`.
```

Inline init script (copy–paste directly):

```python
import asyncio
from app.database.connection import engine
from app.database.models import Base

async def create():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅  Tables created")

asyncio.run(create())
```

Run the API server:

```bash
uvicorn main:app --reload --port 8000  # hot-reload during dev
```

---

## 🎨 Frontend Setup

```bash
# In /frontend
npm install                 # Install React + deps
npm start                   # Dev server on http://localhost:3000
```

> The app uses **Vite + React 18** and Tailwind CSS. Hot-reload is enabled by default.

---

## 🎙️ Enable Voice Chat (Optional)

1. **Create an ElevenLabs account** → grab your **API key**.
2. **Create a Conversational AI Agent** in the ElevenLabs dashboard → copy the **Agent ID**.
3. Add both values to `backend/.env` as shown above.
4. Restart the backend.
5. In the UI, create a **Voice Chat Session** and start talking!

Permissions: The browser will ask for microphone access the first time you enter voice mode. You can mute / end the call using the floating controls.

---

## 📖 How to Use Study Buddy

1. **Upload Documents** via _Documents → Upload_.
   - Supported: PDF, TXT, PPTX, IPYNB
   - Processing status goes from **PENDING → PROCESSING → INDEXED** (or ⚠️ ERROR).
2. **Create Chat Sessions**.
   - Give it a name, pick documents, choose _Text_ or _Voice_.
3. **Start Chatting**.
   - Text: type & hit **Enter**.
   - Voice (if enabled): click **Start Voice Chat**, speak naturally.
4. **Switch Models** on the fly (_Settings → Model_).
5. **Export History** or **Delete Sessions** when you're done.

---

## 🛠️ Development & Troubleshooting

| Issue | Fix |
|-------|-----|
| **Backend fails to start** | Ensure PostgreSQL is running & `.env` is correct |
| **Voice Chat unavailable** | Check `ELEVENLABS_` envs & that your account has voice credits |
| **Documents stuck in PROCESSING** | Look at backend logs; large PDFs may exceed `MAX_FILE_SIZE` |
| **Frontend 404s** | Verify `REACT_APP_API_BASE_URL` |

Run tests:

```bash
pytest -q   # backend unit & integration tests
```

Lint & format:

```bash
ruff check . && black .
```

---

## 🤝 Contributing

PRs and issues are welcome! Please:

1. Fork the repo and create a branch (`feat/your-feature`).
2. Commit using conventional commits (`fix:`, `feat:`…).
3. Ensure `pytest` & `eslint` pass.
4. Open a PR with a clear description.

---

## 📝 License

MIT © 2024 Your Name or Organisation
