import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

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

export const queryDocuments = async (question, contextWindow = 3) => {
    try {
      const response = await fetch(`${API_BASE_URL}/query/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: question,
          context_window: contextWindow
        })
      });
  
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
  
      // Create a readable stream from the response
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
  
      return {
        async *[Symbol.asyncIterator]() {
          try {
            while (true) {
              const { done, value } = await reader.read();
              if (done) break;
              
              const chunk = decoder.decode(value);
              const lines = chunk.split('\n');
              
              for (const line of lines) {
                if (line.startsWith('data: ')) {
                  try {
                    const data = JSON.parse(line.slice(6));
                    yield data;
                  } catch (e) {
                    console.error('Error parsing SSE data:', e);
                  }
                }
              }
            }
          } finally {
            reader.releaseLock();
          }
        }
      };
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