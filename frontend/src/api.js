import axios from 'axios';

const API_BASE_URL = import.meta.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// --- Model and System ---

export const switchModel = async (provider) => {
  try {
    const response = await api.post('/model/switch', { provider });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Error switching model provider');
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

// --- Hume EVI and Voice RAG ---

export const fetchHumeToken = async () => {
  try {
    const response = await api.get('/auth/hume-token');
    return response.data;
  } catch (error) {
    console.error('Error fetching Hume token:', error);
    throw new Error(error.response?.data?.detail || 'Failed to fetch Hume authentication token');
  }
};

export const createVoiceRagWebSocket = (sessionUuid = null) => {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
  let wsUrl = `${wsProtocol}${window.location.hostname}:8000/api/v1/ws/voice-rag`;
  if (sessionUuid) {
    wsUrl += `?session_uuid=${encodeURIComponent(sessionUuid)}`;
  }
  return new WebSocket(wsUrl);
};

// --- Document Management ---

export const uploadDocument = async (file, onUploadProgress) => {
  const formData = new FormData();
  formData.append('file', file);
  try {
    const response = await api.post('/documents/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress,
    });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Error uploading document');
  }
};

export const listDocuments = async (limit = 50, offset = 0) => {
  try {
    const response = await api.get('/documents/', { params: { limit, offset } });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Error fetching documents');
  }
};

export const getDocument = async (documentId) => {
  try {
    const response = await api.get(`/documents/${documentId}`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Error fetching document details');
  }
};

export const getDocumentStatus = async (documentId) => {
  try {
    const response = await api.get(`/documents/${documentId}/status`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Error fetching document status');
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

// --- RAG Query ---

export const queryDocuments = async (question, contextWindow = 3, modelProvider = null, sessionUuid = null) => {
  try {
    let url = `${API_BASE_URL}/query/`;
    if (sessionUuid) {
      url += `?session_uuid=${encodeURIComponent(sessionUuid)}`;
    }
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, context_window: contextWindow, model_provider: modelProvider }),
    });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response; // Return the response directly for streaming
  } catch (error) {
    throw new Error(error.message || 'Error querying documents');
  }
};

// --- Chat Session Management ---

export const getChatSessions = async (limit = 20) => {
  try {
    const response = await api.get('/chat/sessions', { params: { limit } });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Error fetching chat sessions');
  }
};

export const createChatSession = async (title = null, documentIds = [], modelProvider = null) => {
  try {
    const response = await api.post('/chat/sessions', {
      title,
      document_ids: documentIds,
      model_provider: modelProvider,
    });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Error creating chat session');
  }
};

export const getChatSession = async (sessionUuid) => {
  try {
    const response = await api.get(`/chat/sessions/${sessionUuid}`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Error fetching chat session');
  }
};

export const updateChatSession = async (sessionUuid, title = null, documentIds = null) => {
  try {
    const updateData = {};
    if (title !== null) updateData.title = title;
    if (documentIds !== null) updateData.document_ids = documentIds;
    const response = await api.put(`/chat/sessions/${sessionUuid}`, updateData);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Error updating chat session');
  }
};

export const deleteChatSession = async (sessionUuid) => {
  try {
    const response = await api.delete(`/chat/sessions/${sessionUuid}`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Error deleting chat session');
  }
};

export const saveChatMessage = async (sessionUuid, messageContent, responseContent = null, modelProvider = null, tokenCount = null, processingTimeMs = null) => {
  try {
    const response = await api.post(`/chat/sessions/${sessionUuid}/messages`, {
      message_content: messageContent,
      response_content: responseContent,
      model_provider: modelProvider,
      token_count: tokenCount,
      processing_time_ms: processingTimeMs,
    });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Error saving chat message');
  }
};

export const getChatMessages = async (sessionUuid, limit = 50, offset = 0) => {
  try {
    const response = await api.get(`/chat/sessions/${sessionUuid}/messages`, {
      params: { limit, offset },
    });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Error fetching chat messages');
  }
};

export const getAvailableDocuments = async () => {
  try {
    const response = await api.get('/chat/available-documents');
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Error fetching available documents');
  }
};