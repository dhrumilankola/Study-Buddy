# Study Buddy - AI Study Partner

## Introduction

Study Buddy is a comprehensive application designed to assist users in managing and processing documents, enabling efficient study and collaboration. It combines a robust backend for document processing and retrieval with an intuitive frontend for user interaction. The application allows users to select a local open-source model running on OLLAMA or utilize Gemini's API for advanced AI capabilities. Study Buddy leverages an advanced Retrieval-Augmented Generation (RAG) architecture, utilizing semantic search to achieve up to 90% accuracy in providing relevant and precise information.

### Example Use Case

Imagine you are enrolled in a Machine Learning course this semester and want to study only from the resources provided by your professor. You can upload all the course materials (PDFs, PowerPoint presentations, Jupyter Notebooks) to Study Buddy. The application will help you learn with proper and accurate context, even pointing out specific details within the documents to enhance your understanding.

## Features

- **Document Upload and Management**: Upload and manage documents seamlessly.
- **Chat Interface**: Interact with an AI-powered chat interface for document-related queries.
- **Document Processing**: Extract embeddings, process files, and store vectors for efficient retrieval.
- **Responsive Frontend**: A user-friendly interface built with modern web technologies.

## Project Structure

### Backend

The backend is responsible for processing documents, managing configurations, and providing APIs for the frontend. It is structured as follows:

#### Key Modules

- **`app/config.py`**: Contains configuration settings for the application.
- **`app/models/schemas.py`**: Defines data schemas used across the application.
- **`app/routes/api.py`**: Implements API endpoints for document processing and retrieval.
- **`app/services/`**:
  - **`document_processor.py`**: Handles document processing logic.
  - **`rag_service.py`**: Implements retrieval-augmented generation (RAG) services.
  - **`vector_store.py`**: Manages vector storage for efficient document retrieval.
- **`app/utils/`**:
  - **`embedding_generator.py`**: Generates embeddings for documents.
  - **`file_handlers.py`**: Handles file operations.
  - **`file_processor.py`**: Processes uploaded files.

### Frontend

The frontend provides an interactive interface for users to upload documents, view their status, and interact with the AI chat interface. It is built using React and Tailwind CSS.

#### Key Components

- **`components/`**:
  - **`ChatInterface.jsx`**: AI-powered chat interface for user queries.
  - **`DocumentList.jsx`**: Displays a list of uploaded documents.
  - **`FileUpload.jsx`**: Handles file upload functionality.
  - **`Header.jsx`**: Displays the application header.
  - **`Layout.jsx`**: Manages the overall layout of the application.
  - **`StatusIndicator.jsx`**: Shows the status of document processing.
- **`src/api.js`**: Manages API calls to the backend.
- **`src/index.jsx`**: Entry point for the React application.

### Additional Files

- **`check_documents.py`**: A script for verifying document integrity.
- **`test.py`**: Contains test cases for the application.
- **`requirements.txt`**: Lists Python dependencies for the backend.
- **`package.json`**: Lists JavaScript dependencies for the frontend.

## Installation

### Backend

1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```
2. Create a virtual environment and activate it:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the backend server:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

### Frontend

1. Navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```

## Usage

1. Start the backend server.
2. Start the frontend development server.
3. Open the application in your browser at `http://localhost:3000` (or the port specified by Vite).
4. Upload documents, interact with the chat interface, and manage your study materials.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
