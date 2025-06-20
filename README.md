# Study Buddy - Complete Setup & Run Guide

A document-specific RAG (Retrieval-Augmented Generation) chat application with session management and persistent chat history.

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+** (for backend)
- **Node.js 16+** (for frontend)
- **PostgreSQL 12+** (for database)
- **Google AI API Key** (for Gemini model)

### Example Use Case

Imagine you're studying for a Machine Learning course and want to create separate study sessions for different topics. You can:
1. Upload your "Attention Is All You Need" paper and create a session focused only on Transformers
2. Upload your course slides and create another session for general ML concepts
3. Each chat session will only reference its assigned documents - no cross-contamination!

## ✨ Key Features

- **Session-Based Document Isolation**: Each chat session only accesses its assigned documents
- **Persistent Chat History**: All conversations are saved and restored across browser reloads
- **Multi-Format Support**: PDF, TXT, PPTX, IPYNB files
- **Real-time Streaming**: Live AI responses with Google Gemini integration
- **Vector Search**: Semantic search using advanced embeddings

## 🗄️ Database Setup

### Install PostgreSQL

**Windows**: Download from [postgresql.org](https://www.postgresql.org/download/windows/)
**macOS**: `brew install postgresql`
**Linux**: `sudo apt-get install postgresql postgresql-contrib`

### Create Database
```bash
# Start PostgreSQL service
sudo service postgresql start  # Linux
brew services start postgresql  # macOS

# Create database and user
sudo -u postgres psql
CREATE DATABASE study_buddy;
CREATE USER study_buddy_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE study_buddy TO study_buddy_user;
\q
```

## 🔧 Backend Setup

### 1. Navigate to Backend Directory
```bash
cd backend
```

### 2. Create Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Update your `backend/.env` file with these settings:

```env
# Database Configuration
DATABASE_URL=postgresql+asyncpg://study_buddy_user:your_secure_password@localhost:5432/study_buddy

# Google AI settings (REQUIRED)
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_PROJECT_ID=your_project_id
GEMINI_MODEL=gemini-1.5-flash

# Model Provider - IMPORTANT: Set to "gemini"
DEFAULT_MODEL_PROVIDER=gemini

# Other settings
MODEL_TEMPERATURE=0.7
EMBEDDINGS_MODEL=all-mpnet-base-v2
VECTOR_STORE_PATH=../data/vector_store
UPLOAD_DIR=../data/uploads
API_PORT=8000
CORS_ORIGINS=["http://localhost:3000"]
```

**🔑 Get your Google AI API Key**: Go to [Google AI Studio](https://makersuite.google.com/app/apikey)

### 5. Initialize Database
```bash
# Create data directories
mkdir -p ../data/uploads ../data/vector_store

# Initialize database tables
python -c "
import asyncio
from app.database.connection import engine
from app.database.models import Base

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('Database tables created successfully!')

asyncio.run(create_tables())
"
```

### 6. Start Backend Server
```bash
python main.py
```
✅ Backend will be available at `http://localhost:8000`

## 🎨 Frontend Setup

### 1. Navigate to Frontend Directory
```bash
cd ../frontend  # From backend directory
```

### 2. Install Dependencies
```bash
npm install
```

### 3. Configure Environment Variables
Create `frontend/.env`:
```env
REACT_APP_API_BASE_URL=http://localhost:8000/api/v1
```

### 4. Start Frontend Development Server
```bash
npm start
```
✅ Frontend will be available at `http://localhost:3000`

## 📖 How to Use Study Buddy

### 1. Upload Documents
1. Open `http://localhost:3000`
2. Go to document management
3. Upload your PDF, TXT, PPTX, or IPYNB files
4. Wait for processing to complete (status will show "INDEXED")

### 2. Create Chat Sessions
1. Click "New Chat Session"
2. Give it a descriptive title (e.g., "Transformer Architecture Study")
3. Select which documents to include
4. Click "Create Session"

### 3. Start Chatting
1. Select your session from the sidebar
2. Ask questions about your documents
3. The AI will only use information from documents assigned to that session
4. Your chat history is automatically saved!

## 🛠️ Development & Troubleshooting

### Common Issues

**Backend won't start:**
- Check PostgreSQL is running: `sudo service postgresql status`
- Verify database credentials in `.env`
- Ensure virtual environment is activated

**Frontend can't connect:**
- Verify backend is running on port 8000
- Check CORS settings in backend `.env`

**Documents not processing:**
- Check upload directory exists: `mkdir -p data/uploads`
- Verify Google API key is valid

### Useful Commands

```bash
# Backend development
cd backend
source venv/bin/activate
python main.py

# Frontend development
cd frontend
npm start

# Database inspection
psql -h localhost -U study_buddy_user -d study_buddy
\dt  # List tables
SELECT * FROM chat_sessions;  # View sessions
```

## 📁 Project Structure

```
Study-Buddy/
├── backend/
│   ├── app/
│   │   ├── database/     # Database models & services
│   │   ├── routes/       # API endpoints
│   │   ├── services/     # RAG & document processing
│   │   └── models/       # Pydantic schemas
│   ├── main.py          # FastAPI application
│   └── .env             # Configuration
├── frontend/
│   ├── src/
│   │   ├── components/   # React components
│   │   └── api.js       # API client
│   └── .env             # Frontend config
└── data/
    ├── uploads/         # Uploaded documents
    └── vector_store/    # Vector embeddings
```

🎉 **Your Study Buddy is now ready to use!**
