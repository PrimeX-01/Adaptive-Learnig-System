import axios from 'axios';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  timeout: 30000, // Increase from 15000 to 30000 ms
});

api.interceptors.request.use(config => {
  const token = localStorage.getItem('sa_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(r => r, async err => {
  const originalRequest = err.config;
  if (err.response?.status === 401 && !originalRequest._retry) {
    originalRequest._retry = true;
    // optional: refresh token logic if you have it
    localStorage.removeItem('sa_token');
    window.location.href = '/auth';
    return Promise.reject(err);
  }
  return Promise.reject(err);
});

export default api;