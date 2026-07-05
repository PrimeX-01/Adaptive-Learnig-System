import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider }   from './contexts/AuthContext';
import { ThemeProvider }  from './contexts/ThemeContext';
import ProtectedRoute     from './components/ProtectedRoute';

/* ── Public pages ─────────────────────────────────────────────── */
import Landing         from './pages/Landing';
import Auth            from './pages/Auth';
import Register        from './pages/Register';
import ForgotPassword  from './pages/ForgotPassword';
import ResetPassword   from './pages/ResetPassword';
import WaitingApproval from './pages/WaitingApproval';

/* ── Student pages ────────────────────────────────────────────── */
import StudentDashboard from './pages/StudentDashboard';
import TutorChat        from './pages/TutorChat';
import QuizPage         from './pages/QuizPage';
import ProgressPage     from './pages/ProgressPage';
import LibraryPage      from './pages/LibraryPage';
import MessagesPage     from './pages/MessagesPage';
import StudentProfile   from './pages/StudentProfile';
import LessonPlayer     from './pages/LessonPlayer';
import ReviewPage       from './pages/ReviewPage';

/* ── Teacher pages ────────────────────────────────────────────── */
import TeacherDashboard     from './pages/TeacherDashboard';
import TeacherLibraryUpload from './pages/TeacherLibraryUpload';
import TeacherProfile       from './pages/TeacherProfile';
import TeacherTopics        from './pages/TeacherTopics';

/* ── Admin pages ──────────────────────────────────────────────── */
import AdminDashboard from './pages/AdminDashboard';

/*
  Lecturer uses TeacherDashboard as a placeholder until a dedicated
  LecturerDashboard page is built. Swap this import when ready.
*/

/* ── Dashboard path resolver (reads JWT role field) ───────────── */
function getDashboardPath() {
  try {
    const token = localStorage.getItem('sa_token');
    if (!token) return '/auth';
    const payload = JSON.parse(atob(token.split('.')[1]));
    switch (payload.role) {
      case 'admin':    return '/admin';
      case 'teacher':  return '/teacher';
      case 'lecturer': return '/lecturer';
      case 'student':  return '/student';
      default:         return '/auth';
    }
  } catch {
    return '/auth';
  }
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>

            {/* ── Public routes ──────────────────────────────── */}
            <Route path='/'                 element={<Landing />} />
            <Route path='/auth'             element={<Auth />} />
            <Route path='/register'         element={<Register />} />
            <Route path='/forgot-password'  element={<ForgotPassword />} />
            <Route path='/reset-password'   element={<ResetPassword />} />
            <Route path='/waiting-approval' element={<WaitingApproval />} />

            {/* ── Smart dashboard redirect ────────────────────── */}
            <Route
              path='/dashboard'
              element={<Navigate to={getDashboardPath()} replace />}
            />

            {/* ── Student routes ──────────────────────────────── */}
            <Route element={<ProtectedRoute roles={['student']} />}>
              <Route path='/student'             element={<StudentDashboard />} />
              <Route path='/student/tutor'       element={<TutorChat />} />
              <Route path='/student/quizzes'     element={<QuizPage />} />
              <Route path='/student/progress'    element={<ProgressPage />} />
              <Route path='/student/review'      element={<ReviewPage />} />
              <Route path='/student/library'     element={<LibraryPage />} />
              <Route path='/student/messages'    element={<MessagesPage />} />
              <Route path='/student/profile'     element={<StudentProfile />} />
              <Route path='/student/lesson/:id'  element={<LessonPlayer />} />
            </Route>

            {/* ── Teacher routes ──────────────────────────────── */}
            <Route element={<ProtectedRoute roles={['teacher']} />}>
              <Route path='/teacher'               element={<TeacherDashboard />} />
              <Route path='/teacher/students'      element={<TeacherDashboard tab='students' />} />
              <Route path='/teacher/directives'    element={<TeacherDashboard tab='directives' />} />
              <Route path='/teacher/heatmap'       element={<TeacherDashboard tab='heatmap' />} />
              <Route path='/teacher/engagement'    element={<TeacherDashboard tab='engagement' />} />
              <Route path='/teacher/library'       element={<TeacherLibraryUpload />} />
              <Route path='/teacher/topics'        element={<TeacherTopics />} />
              <Route path='/teacher/messages'      element={<MessagesPage />} />
              <Route path='/teacher/profile'       element={<TeacherProfile />} />
            </Route>

            {/* ── Lecturer routes (placeholder dashboard) ─────── */}
            <Route element={<ProtectedRoute roles={['lecturer']} />}>
              <Route path='/lecturer'              element={<TeacherDashboard />} />
              <Route path='/lecturer/students'     element={<TeacherDashboard tab='students' />} />
              <Route path='/lecturer/directives'   element={<TeacherDashboard tab='directives' />} />
              <Route path='/lecturer/library'      element={<TeacherLibraryUpload />} />
              <Route path='/lecturer/messages'     element={<MessagesPage />} />
              <Route path='/lecturer/profile'      element={<TeacherProfile />} />
            </Route>

            {/* ── Admin routes ────────────────────────────────── */}
            <Route element={<ProtectedRoute roles={['admin']} />}>
              <Route path='/admin'             element={<AdminDashboard />} />
              <Route path='/admin/approvals'   element={<AdminDashboard initialTab='approvals' />} />
              <Route path='/admin/school'      element={<AdminDashboard initialTab='school' />} />
              <Route path='/admin/tertiary'    element={<AdminDashboard initialTab='tertiary' />} />
              <Route path='/admin/subjects'    element={<AdminDashboard initialTab='subjects' />} />
              <Route path='/admin/semesters'   element={<AdminDashboard initialTab='semesters' />} />
              <Route path='/admin/users'       element={<AdminDashboard initialTab='users' />} />
            </Route>

            {/* ── Catch-all ───────────────────────────────────── */}
            <Route path='*' element={<Navigate to='/' replace />} />

          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}