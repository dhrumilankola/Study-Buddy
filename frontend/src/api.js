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

export const listDocuments = async (limit = 50, offset = 0) => {
  try {
    const response = await api.get('/documents/', {
      params: { limit, offset }
    });
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
    throw new Error(error.response?.data?.detail || 'Error fetching document');
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

export const queryDocuments = async (question, contextWindow = 3, modelProvider = null, sessionUuid = null) => {
    try {
      let url = `${API_BASE_URL}/query/`;
      if (sessionUuid) {
        url += `?session_uuid=${encodeURIComponent(sessionUuid)}`;
      }

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: question,
          context_window: contextWindow,
          model_provider: modelProvider
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return response;
    } catch (error) {
      throw new Error(error.message || 'Error querying documents');
    }
};

export const checkStatus = async () => {
  try {
    const response = await api.get('/status');
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Error checking status');
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

export const deleteDocumentByFilename = async (filename) => {
    try {
      const response = await fetch(`${API_BASE_URL}/documents/by-filename/${encodeURIComponent(filename)}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Error deleting document');
      }

      return await response.json();
    } catch (error) {
      throw new Error(error.message || 'Error deleting document');
    }
  };

export const getChatSessions = async (limit = 20) => {
  try {
    const response = await api.get('/chat/sessions', {
      params: { limit }
    });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Error fetching chat sessions');
  }
};

export const createChatSession = async (title = null, documentIds = [], modelProvider = null, sessionType = 'text') => {
  try {
    const response = await api.post('/chat/sessions', {
      title,
      document_ids: documentIds,
      model_provider: modelProvider,
      session_type: sessionType
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

export const getChatMessages = async (sessionUuid) => {
  try {
    const response = await api.get(`/chat/sessions/${sessionUuid}/messages`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Error fetching chat messages');
  }
};

export const saveChatMessage = async (sessionUuid, messageContent, responseContent, modelProvider, tokenCount, processingTime) => {
  try {
    const response = await api.post(`/chat/sessions/${sessionUuid}/messages`, {
      message_content: messageContent,
      response_content: responseContent,
      model_provider: modelProvider,
      token_count: tokenCount,
      processing_time_ms: processingTime
    });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Error saving chat message');
  }
};

export const startVoiceChat = async (title, documentIds) => {
  try {
    const response = await api.post('/voice-chat/start-session', {
      title,
      document_ids: documentIds,
      session_type: 'voice'
    });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Error starting voice chat');
  }
};

export const endVoiceChat = async (sessionUuid) => {
  try {
    const response = await api.post(`/voice-chat/end-session/${sessionUuid}`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Error ending voice chat');
  }
};

export const getVoiceChatConfig = async () => {
    try {
        const response = await api.get('/voice-chat/config');
        return response.data;
    } catch (error) {
        throw new Error(error.response?.data?.detail || 'Error getting voice chat config');
    }
};