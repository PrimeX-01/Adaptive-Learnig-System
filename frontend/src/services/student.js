import { api } from './client';


export const getProfile      = ()    => api.get('/students/profile');
export const updateProfile   = (b)   => api.patch('/students/profile', b);

/* ── Subjects & FCL ── */
export const getSubjects     = ()    => api.get('/subjects');
export const getSubjectDetail = (id) => api.get(`/subjects/${id}`);

/* ── Performance data for dashboard ── */
export const getSubjectPerformance = (studentId) =>
  api.get(`/students/${studentId}/subject-performance`);

/* ── Quiz ── */
export const getQuizzes      = (subjectId) =>
  api.get(`/quiz${subjectId ? `?subject_id=${subjectId}` : ''}`);
export const getQuiz         = (id)  => api.get(`/quiz/${id}`);
export const startQuiz       = (id)  => api.post(`/quiz/${id}/start`);
export const submitQuiz      = (id, answers) =>
  api.post(`/quiz/${id}/submit`, { answers });
export const getQuizHistory  = ()    => api.get('/quiz/history');

/* ── VARK / Style ── */
export const getVARKProfile  = ()    => api.get('/style/profile');
export const updateStyle     = (b)   => api.post('/style/update', b);

/* ── Progress ── */
export const getProgress     = ()    => api.get('/students/progress');
export const getProgressBySubject = (id) => api.get(`/students/progress/${id}`);

/* ── Content / Library ── */
export const getLibrary      = (params) => {
  const q = new URLSearchParams(params || {}).toString();
  return api.get(`/library${q ? `?${q}` : ''}`);
};
export const getLibraryItem  = (id) => api.get(`/library/${id}`);

/* ── Messages ── */
export const getConversations = ()        => api.get('/messages/conversations');
export const getMessages      = (convId)  => api.get(`/messages/${convId}`);
export const sendMessage      = (convId, body) => api.post(`/messages/${convId}`, body);