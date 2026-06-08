import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';

/* Public */
import Landing       from './pages/Landing';
import Auth          from './pages/Auth';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword  from './pages/ResetPassword';

/* Student */
import StudentDashboard from './pages/StudentDashboard';
import TutorChat        from './pages/TutorChat';
import QuizPage         from './pages/QuizPage';
import ProgressPage     from './pages/ProgressPage';
import LibraryPage      from './pages/LibraryPage';
import MessagesPage     from './pages/MessagesPage';
import StudentProfile   from './pages/StudentProfile';
import LessonPlayer     from './pages/LessonPlayer';
import ReviewPage       from './pages/ReviewPage';

/* Teacher */
import TeacherDashboard      from './pages/TeacherDashboard';
import TeacherLibraryUpload  from './pages/TeacherLibraryUpload';
import TeacherProfile        from './pages/TeacherProfile';
import TeacherTopics from './pages/TeacherTopics';

function getDashboardPath() {
  const isTeacher = localStorage.getItem('sa_isTeacher') === 'true';
  return isTeacher ? '/teacher' : '/student';
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public */}
          <Route path="/"             element={<Landing />} />
          <Route path="/auth"         element={<Auth />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password"  element={<ResetPassword />} />

          {/* Redirect /dashboard */}
          <Route path="/dashboard" element={<Navigate to={getDashboardPath()} replace />} />

          {/* Student routes */}
          <Route element={<ProtectedRoute roles={['student']} />}>
            <Route path="/student"           element={<StudentDashboard />} />
            <Route path="/student/tutor"     element={<TutorChat />} />
            <Route path="/student/quizzes"   element={<QuizPage />} />
            <Route path="/student/progress"  element={<ProgressPage />} />
            <Route path="/student/review"    element={<ReviewPage />} />   {/* NEW */}
            <Route path="/student/library"   element={<LibraryPage />} />
            <Route path="/student/messages"  element={<MessagesPage />} />
            <Route path="/student/profile"   element={<StudentProfile />} />
            <Route path="/student/lesson/:id" element={<LessonPlayer />} />
          </Route>

          {/* Teacher routes */}
          <Route element={<ProtectedRoute roles={['teacher']} />}>
            <Route path="/teacher"            element={<TeacherDashboard />} />
            <Route path="/teacher/students"   element={<TeacherDashboard tab="students" />} />
            <Route path="/teacher/directives" element={<TeacherDashboard tab="directives" />} />
            <Route path="/teacher/library"    element={<TeacherLibraryUpload />} />
            <Route path="/teacher/messages"   element={<MessagesPage />} />
            <Route path="/teacher/profile"    element={<TeacherProfile />} />
            <Route path="/teacher/topics" element={<TeacherTopics />} />
          </Route>

          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}