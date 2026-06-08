import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { loginUser, registerUser, logoutUser } from '../services/auth';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Rehydrate session from localStorage on mount
  useEffect(() => {
    try {
      const storedToken = localStorage.getItem('sa_token');
      const storedUserId = localStorage.getItem('sa_studentId');
      const storedIsTeacher = localStorage.getItem('sa_isTeacher') === 'true';
      const storedName = localStorage.getItem('sa_name');
      const storedPic = localStorage.getItem('sa_pic');

      if (storedToken && storedUserId) {
        setToken(storedToken);
        setUser({
          id: storedUserId,
          name: storedName,
          first_name: storedName?.split(' ')[0] || '',
          last_name: storedName?.split(' ').slice(1).join(' ') || '',
          role: storedIsTeacher ? 'teacher' : 'student',
          is_teacher: storedIsTeacher,
          profile_pic: storedPic || '',
        });
      }
    } catch (err) {
      console.error('Auth rehydration error', err);
      localStorage.removeItem('sa_token');
      localStorage.removeItem('sa_studentId');
    } finally {
      setLoading(false);
    }
  }, []);

  const persist = (tokenVal, userVal) => {
    localStorage.setItem('sa_token', tokenVal);
    localStorage.setItem('sa_studentId', userVal.id);
    localStorage.setItem('sa_isTeacher', userVal.is_teacher ? 'true' : 'false');
    localStorage.setItem('sa_name', userVal.name);
    if (userVal.profile_pic) localStorage.setItem('sa_pic', userVal.profile_pic);
    setToken(tokenVal);
    setUser(userVal);
  };

  const clearSession = () => {
    localStorage.removeItem('sa_token');
    localStorage.removeItem('sa_studentId');
    localStorage.removeItem('sa_isTeacher');
    localStorage.removeItem('sa_name');
    localStorage.removeItem('sa_pic');
    setToken(null);
    setUser(null);
  };

  const login = useCallback(async (email, password) => {
    setError(null);
    try {
      const data = await loginUser(email, password);
      persist(data.access_token, data.user);
      return data.user;
    } catch (err) {
      const msg = err?.message || 'Login failed. Please check your credentials.';
      setError(msg);
      throw new Error(msg);
    }
  }, []);

  const register = useCallback(async (payload) => {
    setError(null);
    try {
      const data = await registerUser(payload);
      persist(data.access_token, data.user);
      return data.user;
    } catch (err) {
      const msg = err?.message || 'Registration failed. Please try again.';
      setError(msg);
      throw new Error(msg);
    }
  }, []);

  const logout = useCallback(async () => {
    try { await logoutUser(); } catch { /* ignore */ }
    clearSession();
  }, []);

  const updateUser = useCallback((patch) => {
    setUser(prev => {
      const updated = { ...prev, ...patch };
      localStorage.setItem('sa_name', updated.name || '');
      localStorage.setItem('sa_pic', updated.profile_pic || '');
      return updated;
    });
  }, []);

  const isStudent = user?.role === 'student' || user?.is_teacher === false;
  const isTeacher = user?.role === 'teacher' || user?.is_teacher === true;
  const isAdmin   = user?.role === 'admin';

  return (
    <AuthContext.Provider value={{
      user, token, loading, error,
      login, register, logout, updateUser,
      isStudent, isTeacher, isAdmin,
      isAuthenticated: !!token,
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