import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach JWT token to every request if present
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const authAPI = {
  getCurrentUser: async () => {
    const response = await api.get('/api/v1/auth/user');
    return response.data;
  },
  logout: async () => {
    localStorage.removeItem('token');
    const response = await api.post('/api/v1/auth/logout');
    return response.data;
  },
  getGitHubLoginUrl: () => {
    return `${API_URL}/api/v1/auth/github`;
  },
};

export const analysisAPI = {
  submitAnalysis: async (repoUrl, options = {}) => {
    const response = await api.post('/api/v1/analysis', {
      repoUrl,
      language: options.language || 'auto',
      analyzeSecurity: options.analyzeSecurity !== false,
      analyzePerformance: options.analyzePerformance !== false,
    });
    return response.data;
  },

  getAnalysis: async (id) => {
    const response = await api.get(`/api/v1/analysis/${id}`);
    return response.data;
  },

  getAllAnalyses: async () => {
    const response = await api.get('/api/v1/analysis');
    return response.data;
  },

  healthCheck: async () => {
    const response = await api.get('/health');
    return response.data;
  },
};

export default api;