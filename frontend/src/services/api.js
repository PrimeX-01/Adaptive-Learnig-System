import axios from 'axios';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  timeout: 30000,
});

// ✅ Use localStorage to get token (reliable across page refreshes)
api.interceptors.request.use(config => {
  const token = localStorage.getItem('sa_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(r => r, err => {
  if (err.response?.status === 401) {
    const publicPages = ['/login', '/register', '/forgot-password', '/reset-password'];
    const onPublicPage = publicPages.some(p => window.location.pathname.startsWith(p));
    if (!onPublicPage) {
      // Clear session
      localStorage.removeItem('sa_token');
      localStorage.removeItem('sa_studentId');
      localStorage.removeItem('sa_isTeacher');
      localStorage.removeItem('sa_name');
      localStorage.removeItem('sa_pic');
      window.location.href = '/auth';
    }
  }
  return Promise.reject(err);
});

export default api;