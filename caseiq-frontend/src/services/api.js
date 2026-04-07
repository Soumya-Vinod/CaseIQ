import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('caseiq_access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Auto-refresh on 401
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      try {
        const refresh = localStorage.getItem('caseiq_refresh_token');
        const { data } = await axios.post(`${API_BASE_URL}/auth/token/refresh/`, { refresh });
        localStorage.setItem('caseiq_access_token', data.access);
        original.headers.Authorization = `Bearer ${data.access}`;
        return api(original);
      } catch {
        localStorage.removeItem('caseiq_access_token');
        localStorage.removeItem('caseiq_refresh_token');
        localStorage.removeItem('caseiq_user');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;

// ─── AUTH ───────────────────────────────────────────
export const authAPI = {
  register: (data) => api.post('/auth/register/', data),
  login: async (email, password) => {
    const res = await api.post('/auth/login/', { email, password });
    localStorage.setItem('caseiq_access_token', res.data.tokens.access);
    localStorage.setItem('caseiq_refresh_token', res.data.tokens.refresh);
    localStorage.setItem('caseiq_user', JSON.stringify(res.data.user));
    return res.data;
  },
  logout: async () => {
    try {
      const refresh = localStorage.getItem('caseiq_refresh_token');
      await api.post('/auth/logout/', { refresh });
    } finally {
      localStorage.removeItem('caseiq_access_token');
      localStorage.removeItem('caseiq_refresh_token');
      localStorage.removeItem('caseiq_user');
    }
  },
  getProfile: () => api.get('/auth/profile/'),
  updateProfile: (data) => api.put('/auth/profile/', data),
  changePassword: (data) => api.post('/auth/change-password/', data),
};

// ─── LEGAL QUERY ────────────────────────────────────

export const legalAPI = {
  submitQuery: (query, language = 'en', sessionId = '') =>
    api.post('/legal/query/', { query, language, session_id: sessionId }),
  getHistory: () => api.get('/legal/query/history/'),
  getSections: (params) => api.get('/legal/sections/', { params }),
};

// ─── KNOWLEDGE BASE ─────────────────────────────────
export const knowledgeAPI = {
  search: (query, top_k = 5) => api.post('/knowledge/search/', { query, top_k }),
  getProvisions: (params) => api.get('/knowledge/provisions/', { params }),
  getCategories: () => api.get('/knowledge/categories/'),
  getRights: () => api.get('/knowledge/rights/'),
};

// ─── COMPLAINTS ─────────────────────────────────────
export const complaintsAPI = {
  generateDraft: (data) => api.post('/complaints/draft/', data),
  getHistory: () => api.get('/complaints/history/'),
  getDetail: (id) => api.get(`/complaints/${id}/`),
  downloadPDF: async (id, complainantName) => {
    const res = await api.get(`/complaints/${id}/download/`, { responseType: 'blob' });
    const url = window.URL.createObjectURL(new Blob([res.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `CaseIQ_FIR_${complainantName || id}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },
};

// ─── AWARENESS ──────────────────────────────────────
export const awarenessAPI = {
  getNews: (params) => api.get('/awareness/news/', { params }),
  getEducation: (params) => api.get('/awareness/education/', { params }),
  getEducationDetail: (id) => api.get(`/awareness/education/${id}/`),
};