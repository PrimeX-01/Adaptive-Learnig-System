import { api } from './client';

/* All api.get/post/patch/delete already return the JSON data directly.
   No need to unwrap response.data. */

export const getTeacherDashboard = () =>
  api.get('/teachers/dashboard');

export const getTeacherProfile = () =>
  api.get('/teachers/profile');

export const updateTeacherProfile = (b) =>
  api.patch('/teachers/profile', b);

export const getMyStudents = (subjectId) =>
  api.get(`/teachers/students${subjectId ? `?subject_id=${subjectId}` : ''}`);

export const getStudentDetail = (id) =>
  api.get(`/teachers/students/${id}`);

export const getStrugglingStudents = () =>
  api.get('/teachers/students/struggling');

export const getMySubjects = () =>
  getTeacherDashboard().then(dash => dash.teacher_subjects || []);

export const createSubject = (b) =>
  api.post('/subjects', b);

export const updateSubject = (id, b) =>
  api.put(`/subjects/${id}`, b);

export const getDirectives = () =>
  api.get('/teachers/directives');

export const upsertDirective = (b) =>
  api.post('/teachers/directive', b);

export const deleteDirective = (id) =>
  api.delete(`/teachers/directive/${id}`);

export const getTeacherLibrary = () =>
  api.get('/library');

export const uploadContent = (formData) =>
  fetch(
    `${(import.meta.env.VITE_API_URL || 'http://localhost:8000')}/api/library`,
    {
      method: 'POST',
      headers: { Authorization: `Bearer ${localStorage.getItem('sa_token')}` },
      body: formData,
    }
  ).then(r => r.json());

export const deleteContent = (id) =>
  api.delete(`/library/${id}`);

export const getClassAnalytics = (subjectId) =>
  api.get(`/teachers/analytics${subjectId ? `?subject_id=${subjectId}` : ''}`);

export const getTeacherConversations = () =>
  api.get('/messages/conversations');

export const getTeacherMessages = (convId) =>
  api.get(`/messages/${convId}`);

export const sendTeacherMessage = (convId, b) =>
  api.post(`/messages/${convId}`, b);