import axios from 'axios';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  timeout: 30000,
});


api.interceptors.request.use(config => {
  const token = window.__authToken;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});


api.interceptors.response.use(r => r, err => {
  if (err.response?.status === 401) {
 const publicPages = ['/login', '/register', '/forgot-password', '/reset-password'];
    const onPublicPage = publicPages.some(p => window.location.pathname.startsWith(p));
    if (!onPublicPage) {
      window.__authToken   = null;
      window.__studentId   = null;
      window.__isTeacher   = null;
      window.__studentName = null;
      window.__profilePic  = null;
      window.location.href = '/login';

      localStorage.removeItem('sa_token');
      localStorage.removeItem('sa_studentId');
      localStorage.removeItem('sa_isTeacher');
      localStorage.removeItem('sa_name');
      localStorage.removeItem('sa_pic');

    window.location.href = '/login';
    }
  }
  return Promise.reject(err);
});

export default api;