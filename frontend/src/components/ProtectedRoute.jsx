import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';


export default function ProtectedRoute({ roles }) {
  const { isAuthenticated, user, loading } = useAuth();
  const location = useLocation();

  // Wait for session rehydration from localStorage before deciding
  if (loading) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--bg, #080E1C)',
      }}>
        <div style={{
          width: 40, height: 40,
          border: '3px solid rgba(0,212,200,0.2)',
          borderTopColor: '#00D4C8',
          borderRadius: '50%',
          animation: 'spin 0.8s linear infinite',
        }} />
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (!isAuthenticated) {
    // Save where the user was trying to go so we can redirect back after login
    return <Navigate to="/auth" state={{ from: location }} replace />;
  }

  if (roles && roles.length > 0 && !roles.includes(user?.role)) {
    // Role mismatch — send to the correct dashboard
    const dest = user?.role === 'teacher' ? '/teacher' : '/student';
    return <Navigate to={dest} replace />;
  }


  return <Outlet />;
}