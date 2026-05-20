import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import api from '../services/api';

export default function ResetPassword() {
  const [searchParams]                  = useSearchParams();
  const token                            = searchParams.get('token') || '';
  const [newPassword,     setNewPassword]     = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading,         setLoading]         = useState(false);
  const [error,           setError]           = useState('');
  const [success,         setSuccess]         = useState(false);
  const nav = useNavigate();

  async function handleReset(e) {
    e.preventDefault();
    setError('');

    if (!token) {
      setError('Invalid reset link. Please request a new one.');
      return;
    }
    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);
    try {
      await api.post('/api/auth/reset-password', {
        token,
        new_password: newPassword,
      });
      setSuccess(true);
      // Redirect to login after 3 seconds
      setTimeout(() => nav('/login'), 3000);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Reset failed. Please request a new link.');
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

        {/* Brand header */}
        <div className='text-center mb-8'>
          <div className='inline-flex w-12 h-12 rounded-xl bg-teal/10 border border-teal/30 items-center justify-center mb-4'>
            <span className='text-teal font-bold text-lg'>SA</span>
          </div>
          <h1 className='text-primary text-2xl font-bold'>Create New Password</h1>
          <p className='text-muted text-sm mt-1'>SiveAdapt — AI Adaptive Learning</p>
          <p className='text-muted text-xs mt-0.5'>University of Eswatini</p>
        </div>

        <div className='card p-8'>

          {!token && !success && (
            <div className='text-center'>
              <span className='text-4xl block mb-4'>🔗</span>
              <p className='text-red-400 text-sm mb-4'>
                Invalid or missing reset token. Please request a new reset link.
              </p>
              <Link to='/forgot-password' className='btn-primary text-sm px-6 py-2'>
                Request New Link
              </Link>
            </div>
          )}

          {token && !success && (
            <>
              <p className='text-muted text-sm mb-6'>
                Enter your new password below. It must be at least 8 characters.
              </p>

              {error && (
                <div className='mb-4 px-3 py-2.5 bg-red-500/10 border border-red-500/30 rounded-lg
                  flex items-center gap-2 text-red-400 text-sm'>
                  <span>⚠</span> {error}
                </div>
              )}

              <form onSubmit={handleReset} className='space-y-4'>
                <div>
                  <label className='text-muted text-xs font-medium block mb-1.5 uppercase tracking-wide'>
                    New Password
                  </label>
                  <input
                    type='password'
                    value={newPassword}
                    onChange={e => setNewPassword(e.target.value)}
                    placeholder='Min 8 characters'
                    autoComplete='new-password'
                    className='w-full bg-input border border-border rounded-lg px-4 py-2.5 text-primary
                      text-sm placeholder-muted focus:outline-none focus:border-teal/60
                      focus:ring-1 focus:ring-teal/30 transition-colors'
                  />
                </div>

                <div>
                  <label className='text-muted text-xs font-medium block mb-1.5 uppercase tracking-wide'>
                    Confirm New Password
                  </label>
                  <input
                    type='password'
                    value={confirmPassword}
                    onChange={e => setConfirmPassword(e.target.value)}
                    placeholder='Repeat new password'
                    autoComplete='new-password'
                    className='w-full bg-input border border-border rounded-lg px-4 py-2.5 text-primary
                      text-sm placeholder-muted focus:outline-none focus:border-teal/60
                      focus:ring-1 focus:ring-teal/30 transition-colors'
                  />
                </div>

                {/* Password match indicator */}
                {confirmPassword && (
                  <p className={`text-xs flex items-center gap-1 ${
                    newPassword === confirmPassword ? 'text-green-400' : 'text-red-400'
                  }`}>
                    <span>{newPassword === confirmPassword ? '✓' : '✕'}</span>
                    {newPassword === confirmPassword ? 'Passwords match' : 'Passwords do not match'}
                  </p>
                )}

                <button
                  type='submit'
                  disabled={loading || newPassword !== confirmPassword || newPassword.length < 8}
                  className='w-full btn-primary py-2.5 disabled:opacity-50'
                >
                  {loading ? 'Updating password…' : 'Set New Password'}
                </button>
              </form>

              <p className='text-center text-muted text-sm mt-5'>
                <Link to='/login' className='text-teal hover:underline'>← Back to login</Link>
              </p>
            </>
          )}

          {/* ── Success state ── */}
          {success && (
            <div className='text-center'>
              <span className='text-5xl block mb-4'>✅</span>
              <h2 className='text-primary font-semibold text-base mb-2'>Password updated!</h2>
              <p className='text-muted text-sm mb-6'>
                Your password has been changed successfully. Redirecting you to login in 3 seconds…
              </p>
              <Link to='/login' className='text-teal text-sm hover:underline'>
                Go to login now →
              </Link>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}