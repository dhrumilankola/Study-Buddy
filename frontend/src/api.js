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
        temperature: 0.7, // Using default temperature
      });
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Error switching model provider');
    }
  };

export const fetchHumeToken = async () => {
  try {
    // The endpoint /api/generate-hume-token is not under /api/v1, so construct URL accordingly
    // Assuming the backend API is running on localhost:8000
    const response = await fetch('http://localhost:8000/api/generate-hume-token');
    if (!response.ok) {
      const errorData = await response.text();
      console.error('Failed to fetch Hume token:', response.status, errorData);
      throw new Error(`Failed to fetch Hume token: ${response.status} ${errorData}`);
    }
    const data = await response.json();
    return data; // Should be { access_token: '...' }
  } catch (error) {
    console.error('Error in fetchHumeToken:', error);
    throw error; // Re-throw the error for the caller to handle
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
      // Add progress tracking
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
  
      return response; // Return the response directly for streaming
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

export const deleteDocument = async (filename) => {
    try {
      const response = await fetch(`${API_BASE_URL}/documents/${encodeURIComponent(filename)}`, {
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