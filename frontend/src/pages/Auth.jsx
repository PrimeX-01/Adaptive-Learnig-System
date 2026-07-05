import { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import styles from './Auth.module.css';


export default function Auth() {
  const { login, isAuthenticated, user } = useAuth();
  const navigate  = useNavigate();
  const location  = useLocation();

  const [email,    setEmail]    = useState('');
  const [password, setPassword] = useState('');
  const [showPw,   setShowPw]   = useState(false);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState('');

  // ── Redirect already-authenticated users to their dashboard ─────
  useEffect(() => {
    if (!isAuthenticated || !user) return;
    const dest = _dashboardFor(user.role);
    if (location.pathname !== dest) {
      navigate(dest, { replace: true });
    }
  }, [isAuthenticated, user, location.pathname, navigate]);

  // ── Login handler ────────────────────────────────────────────────
  const handleLogin = async (e) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setError('Please enter your email and password.');
      return;
    }
    setError('');
    setLoading(true);

    try {
      const result = await login(email.trim(), password);

      // Teacher or lecturer registered but not yet approved by admin
      if (result?.status === 'pending') {
        navigate('/waiting-approval', { replace: true });
        return;
      }

      // Normal login — result is the user object from AuthContext
      navigate(_dashboardFor(result?.role), { replace: true });

    } catch (err) {
      setError(err.message || 'Invalid email or password. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // ── Render ───────────────────────────────────────────────────────
  return (
    <div className={styles.page}>


      {/* ── Form panel (right) ── */}
      <div className={styles.formPanel}>
        <div className={styles.formInner}>

          {/* Tab bar — Sign in is active; Create account links to /register */}
          <div className={styles.tabs}>
            <button
              className={`${styles.tabBtn} ${styles.activeTab}`}
              type='button'
            >
              Sign in
            </button>

            {/*
              "Create account" navigates to /register where the four
              role-specific registration flows live (Register.jsx).
              It is a Link, not a button, so no inline registration
              form is toggled here.
            */}
            <Link
              to='/register'
              className={styles.tabBtn}
              style={{ textAlign: 'center', textDecoration: 'none' }}
            >
              Create account
            </Link>
          </div>

          {/* ── Login form ── */}
          <form onSubmit={handleLogin} className={styles.form} noValidate>

            <h1 className={styles.formTitle}>Welcome back</h1>

            {error && (
              <div className={styles.error} role='alert'>
                {error}
              </div>
            )}

            <div className={styles.field}>
              <label className={styles.label} htmlFor='auth-email'>
                Email address
              </label>
              <input
                id='auth-email'
                className='input'
                type='email'
                required
                autoComplete='email'
                placeholder='you@example.com'
                value={email}
                onChange={e => setEmail(e.target.value)}
              />
            </div>

            <div className={styles.field}>
              <label className={styles.label} htmlFor='auth-password'>
                Password
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  id='auth-password'
                  className='input'
                  type={showPw ? 'text' : 'password'}
                  required
                  autoComplete='current-password'
                  placeholder='••••••••'
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  style={{ paddingRight: '3rem' }}
                />
                <button
                  type='button'
                  onClick={() => setShowPw(p => !p)}
                  aria-label={showPw ? 'Hide password' : 'Show password'}
                  style={{
                    position:  'absolute',
                    right:     '0.75rem',
                    top:       '50%',
                    transform: 'translateY(-50%)',
                    background:'none',
                    border:    'none',
                    cursor:    'pointer',
                    color:     'var(--text-secondary, #8899aa)',
                    fontSize:  '12px',
                    padding:   0,
                  }}
                >
                  {showPw ? 'Hide' : 'Show'}
                </button>
              </div>
            </div>

            <div style={{
              display:        'flex',
              justifyContent: 'flex-end',
              marginTop:      '-4px',
              marginBottom:   '8px',
            }}>
              <Link
                to='/forgot-password'
                style={{
                  fontSize:        '13px',
                  color:           'var(--accent-primary, #6ee7f7)',
                  textDecoration:  'none',
                }}
              >
                Forgot password?
              </Link>
            </div>

            <button
              type='submit'
              className={`btn btn-primary ${styles.submitBtn}`}
              disabled={loading}
            >
              {loading ? 'Signing in…' : 'Sign in →'}
            </button>

            <p style={{
              textAlign:  'center',
              fontSize:   '13px',
              color:      'var(--text-secondary, #8899aa)',
              marginTop:  '12px',
            }}>
              Don't have an account?{' '}
              <Link
                to='/register'
                style={{
                  color:          'var(--accent-primary, #6ee7f7)',
                  fontWeight:     600,
                  textDecoration: 'none',
                }}
              >
                Register here
              </Link>
            </p>

          </form>
        </div>
      </div>
    </div>
  );
}

// ── Helper — resolve dashboard path from role ────────────────────
function _dashboardFor(role) {
  switch (role) {
    case 'admin':    return '/admin';
    case 'teacher':  return '/teacher';
    case 'lecturer': return '/lecturer';
    default:         return '/student';
  }
}