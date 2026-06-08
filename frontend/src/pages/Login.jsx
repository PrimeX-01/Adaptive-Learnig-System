import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../services/api';

export default function Login() {
  const [email,    setEmail]    = useState('');
  const [password, setPassword] = useState('');
  const [error,    setError]    = useState('');
  const [loading,  setLoading]  = useState(false);
  const nav = useNavigate();

  async function handleLogin() {
    setError(''); setLoading(true);
    try {
      const { data } = await api.post('/api/auth/login', { email, password });

      window.__authToken   = data.access_token;
      window.__studentId   = data.student_id;
      window.__isTeacher   = data.is_teacher;
      window.__isAdmin     = data.is_admin || false;     
      window.__studentName = data.name;
      window.__profilePic  = data.profile_picture || null;

      localStorage.setItem('sa_token',     data.access_token);
      localStorage.setItem('sa_studentId', data.student_id);
      localStorage.setItem('sa_isTeacher', data.is_teacher);
      localStorage.setItem('sa_isAdmin',   data.is_admin || false);
      localStorage.setItem('sa_name',      data.name);
      localStorage.setItem('sa_pic',       data.profile_picture || '');

      if (data.is_admin) {
        nav('/admin');
      } else if (data.is_teacher) {
        nav('/teacher');
      } else {
        nav('/dashboard');
      }
    } catch(err) {
      setError(err?.response?.data?.detail || 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className='min-h-screen bg-app flex items-center justify-center px-4'>
      <div className='absolute inset-0 overflow-hidden pointer-events-none'>
        <div className='absolute top-1/4 left-1/2 -translate-x-1/2 w-96 h-96 bg-teal/5 rounded-full blur-3xl' />
      </div>

      <div className='relative w-full max-w-md'>
        <div className='text-center mb-8'>
          <div className='inline-flex w-12 h-12 rounded-xl bg-teal/10 border border-teal/30 items-center justify-center mb-4'>
            <span className='text-teal font-bold text-lg'>SA</span>
          </div>
          <h1 className='text-primary text-2xl font-bold'>Welcome back</h1>
          <p className='text-muted text-sm mt-1'>SiveAdapt — AI Adaptive Learning</p>
          <p className='text-muted text-xs mt-0.5'>University of Eswatini</p>
        </div>

        <div className='card p-8'>
          {error && (
            <div className='mb-4 px-3 py-2.5 bg-red-500/10 border border-red-500/30 rounded-lg
              flex items-center gap-2 text-red-400 text-sm'>
              <span className='text-base flex-shrink-0'>⚠</span>
              {error}
            </div>
          )}

          <form onSubmit={e => { e.preventDefault(); handleLogin(); }}>
            <div className='space-y-4'>
              <div>
                <label className='text-muted text-xs font-medium block mb-1.5 uppercase tracking-wide'>
                  Email Address
                </label>
                <input
                  type='email'
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder='you@example.com'
                  autoComplete='email'
                  className='w-full bg-input border border-border rounded-lg px-4 py-2.5 text-primary text-sm
                    placeholder-muted focus:outline-none focus:border-teal/60 focus:ring-1
                    focus:ring-teal/30 transition-colors'
                />
              </div>

              <div>
                <label className='text-muted text-xs font-medium uppercase tracking-wide mb-1.5 block'>
                  Password
                </label>
                <input
                  type='password'
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder='••••••••'
                  autoComplete='current-password'
                  className='w-full bg-input border border-border rounded-lg px-4 py-2.5 text-primary text-sm
                    placeholder-muted focus:outline-none focus:border-teal/60 focus:ring-1
                    focus:ring-teal/30 transition-colors'
                />
              </div>
            </div>

            <button
              type='submit'
              disabled={loading}
              className='w-full btn-primary mt-6 py-2.5 disabled:opacity-50'
            >
              {loading ? 'Signing in…' : 'Sign In'}
            </button>
          </form>

          <p className='text-center text-muted text-sm mt-5'>
            No account?{' '}
            <Link to='/register' className='text-teal hover:underline'>
              Register here
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}