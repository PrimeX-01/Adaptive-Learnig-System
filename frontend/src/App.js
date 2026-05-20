import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login            from './pages/Login';
import Register         from './pages/Register';
import StudentDashboard from './pages/StudentDashboard';
import SubjectProfile   from './pages/SubjectProfile';
import TutorChat        from './pages/TutorChat';
import QuizPage         from './pages/QuizPage';
import ProgressTracker  from './pages/ProgressTracker';
import ContentLibrary   from './pages/ContentLibrary';
import LessonPlayer     from './pages/LessonPlayer';
import MessagesPage     from './pages/MessagesPage';
import TeacherDashboard from './pages/TeacherDashboard';
import StudentProfile   from './pages/StudentProfile';   
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword  from './pages/ResetPassword';
import TeacherUpload from './pages/TeacherUpload';


// ... inside Routes
<Route path="/teacher/upload" element={<Private teacherOnly><TeacherUpload /></Private>} />

function Private({ children, teacherOnly = false }) {
  if (!window.__authToken) {
    const token = localStorage.getItem('sa_token');
    if (token) {
      window.__authToken   = token;
      window.__studentId   = localStorage.getItem('sa_studentId');
      window.__isTeacher   = localStorage.getItem('sa_isTeacher') === 'true';
      window.__studentName = localStorage.getItem('sa_name');
      window.__profilePic  = localStorage.getItem('sa_pic') || null;
    }
  }

  if (!window.__authToken) return <Navigate to='/login' replace />;
  if (teacherOnly && !window.__isTeacher) return <Navigate to='/dashboard' replace />;
  return children;
}

export default function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path='/login'      element={<Login />} />
        <Route path='/register'   element={<Register />} />
        <Route path='/forgot-password' element={<ForgotPassword />} />
        <Route path='/reset-password'  element={<ResetPassword />} />
        <Route path='/dashboard'  element={<Private><StudentDashboard /></Private>} />
        <Route path='/subjects'   element={<Private><SubjectProfile /></Private>} />
        <Route path='/chat'       element={<Private><TutorChat /></Private>} />
        <Route path='/quiz'       element={<Private><QuizPage /></Private>} />
        <Route path='/progress'   element={<Private><ProgressTracker /></Private>} />
        <Route path='/library'    element={<Private><ContentLibrary /></Private>} />
        <Route path='/lesson/:id' element={<Private><LessonPlayer /></Private>} />
        <Route path='/messages'   element={<Private><MessagesPage /></Private>} />
        <Route path='/teacher'    element={<Private teacherOnly><TeacherDashboard /></Private>} />
        <Route path='/profile'    element={<Private><StudentProfile /></Private>} />  {/* ← NEW */}
        <Route path='*'           element={<Navigate to='/login' replace />} />
      </Routes>
    </BrowserRouter>
  );
}