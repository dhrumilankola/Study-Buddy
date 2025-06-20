import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const switchModel = async (provider) => {
  try {
    const response = await api.post('/model/switch', {
      provider: provider,
      temperature: 0.7,
    });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Error switching model provider');
  }
};

export const fetchHumeToken = async () => {
  try {
    // Updated to use the correct endpoint from the backend
    const response = await api.get('/auth/hume-token');
    return response.data; // Returns { access_token, token_type, expires_in, config_id, hostname }
  } catch (error) {
    console.error('Error fetching Hume token:', error);
    throw new Error(error.response?.data?.detail || 'Failed to fetch Hume authentication token');
  }
};

export const uploadDocument = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  
  try {
    const response = await api.post('/documents/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        console.log(`Upload Progress: ${percentCompleted}%`);
      },
    });
    return response.data;
  } catch (error) {
    if (error.response?.status === 400) {
      throw new Error(error.response.data.detail || 'Invalid file type or size');
    } else {
      throw new Error(error.response?.data?.detail || 'Error uploading document');
    }
  }
};

export const listDocuments = async () => {
  try {
    const response = await api.get('/documents/');
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Error fetching documents');
  }
};

export const queryDocuments = async (question, contextWindow = 3, modelProvider = null) => {
  try {
    const response = await fetch(`${API_BASE_URL}/query/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question: question,
        context_window: contextWindow,
        model_provider: modelProvider
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response; // Return response for streaming
  } catch (error) {
    throw new Error(error.message || 'Error querying documents');
  }
};

export const deleteDocument = async (documentId) => {
  try {
    const response = await api.delete(`/documents/${documentId}`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Error deleting document');
  }
};

export const getStatus = async () => {
  try {
    const response = await api.get('/status');
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Error fetching status');
  }
};

// Voice RAG API
export const voiceRagQuery = async (transcription) => {
  try {
    const response = await api.post('/voice/query', {
      transcription: transcription
    });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Error processing voice query');
  }
};

// WebSocket connection for real-time voice RAG
export const createVoiceRagWebSocket = () => {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
  const wsUrl = `${wsProtocol}${window.location.hostname}:8000/api/v1/ws/voice-rag`;
  return new WebSocket(wsUrl);
};