import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { loginUser, logoutUser } from '../services/auth';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user,    setUser]    = useState(null);
  const [token,   setToken]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);

  // ── Rehydrate from localStorage on mount ──────────────────────
  useEffect(() => {
    try {
      const storedToken = localStorage.getItem('sa_token');
      const storedUser  = localStorage.getItem('sa_user');

      if (storedToken && storedUser) {
        const parsedUser = JSON.parse(storedUser);
        setToken(storedToken);
        setUser(parsedUser);
        _syncLegacyGlobals(storedToken, parsedUser);
      }
    } catch {
     
      _clearStorage();
    } finally {
      setLoading(false);
    }
  }, []);

  // ── Persist helpers ───────────────────────────────────────────

  const _persist = (tokenVal, userVal) => {
    // Primary storage — single JSON object
    localStorage.setItem('sa_token', tokenVal);
    localStorage.setItem('sa_user',  JSON.stringify(userVal));

    
    localStorage.setItem('sa_studentId', userVal.id);
    localStorage.setItem('sa_isTeacher', userVal.role === 'teacher' ? 'true' : 'false');
    localStorage.setItem('sa_name',      userVal.name || '');
    localStorage.setItem('sa_pic',       userVal.profile_pic || '');

    _syncLegacyGlobals(tokenVal, userVal);
    setToken(tokenVal);
    setUser(userVal);
  };

  const _clearStorage = () => {
    [
      'sa_token', 'sa_user', 'sa_studentId',
      'sa_isTeacher', 'sa_name', 'sa_pic',
    ].forEach(k => localStorage.removeItem(k));
    _syncLegacyGlobals(null, null);
    setToken(null);
    setUser(null);
  };


  function _syncLegacyGlobals(tokenVal, userVal) {
    window.__authToken   = tokenVal  || null;
    window.__studentId   = userVal?.id   || null;
    window.__studentName = userVal?.name || null;
    window.__isTeacher   = userVal?.role === 'teacher';
    window.__profilePic  = userVal?.profile_pic || '';
  }

  // ── Login ─────────────────────────────────────────────────────
  const login = useCallback(async (email, password) => {
    setError(null);
    try {
      const data = await loginUser(email, password);

      // Pending teacher / lecturer — backend sends no token
      if (data.status === 'pending') {
        return { status: 'pending', role: data.role, message: data.message };
      }

      _persist(data.access_token, data.user);
      return data.user;
    } catch (err) {
      const msg = err?.message || 'Login failed. Please check your credentials.';
      setError(msg);
      throw new Error(msg);
    }
  }, []);

  
  const logout = useCallback(async () => {
    try { await logoutUser(); } catch { /* ignore */ }
    _clearStorage();
  }, []);


  const updateUser = useCallback((patch) => {
    setUser(prev => {
      if (!prev) return prev;
      const updated = { ...prev, ...patch };
      localStorage.setItem('sa_user', JSON.stringify(updated));
      localStorage.setItem('sa_name', updated.name || '');
      localStorage.setItem('sa_pic',  updated.profile_pic || '');
      window.__studentName = updated.name;
      window.__profilePic  = updated.profile_pic || '';
      return updated;
    });
  }, []);

 
  const isStudent         = user?.role === 'student';
  const isTeacher         = user?.role === 'teacher';
  const isLecturer        = user?.role === 'lecturer';
  const isAdmin           = user?.role === 'admin';
  const isSchoolStudent   = user?.role === 'student' && user?.student_type === 'school';
  const isTertiaryStudent = user?.role === 'student' && user?.student_type === 'tertiary';

  return (
    <AuthContext.Provider value={{
      user,
      token,
      loading,
      error,
      login,
      logout,
      updateUser,
      isAuthenticated:  !!token,
      isStudent,
      isTeacher,
      isLecturer,
      isAdmin,
      isSchoolStudent,
      isTertiaryStudent,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}