import { useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';

export default function ForgotPassword() {
  const [email,     setEmail]     = useState('');
  const [loading,   setLoading]   = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [devLink,   setDevLink]   = useState(null);
  const [error,     setError]     = useState('');

  async function handleSubmit(e) {
    e.preventDefault();
    if (!email.trim()) { setError('Please enter your email address.'); return; }
    setError(''); setLoading(true);

    try {
      const { data } = await api.post('/api/auth/forgot-password', { email });
      setSubmitted(true);
      // Show the reset link on screen (dev mode — in production this would be emailed)
      if (data.dev_reset_url) setDevLink(data.dev_reset_url);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Something went wrong. Please try again.');
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
          <h1 className='text-primary text-2xl font-bold'>Reset Password</h1>
          <p className='text-muted text-sm mt-1'>SiveAdapt — AI Adaptive Learning</p>
          <p className='text-muted text-xs mt-0.5'>University of Eswatini</p>
        </div>

        <div className='card p-8'>
          {!submitted ? (
            <>
              <p className='text-muted text-sm mb-6'>
                Enter your registered email address and we'll generate a password reset link for you.
              </p>

              {error && (
                <div className='mb-4 px-3 py-2.5 bg-red-500/10 border border-red-500/30 rounded-lg
                  flex items-center gap-2 text-red-400 text-sm'>
                  <span>⚠</span> {error}
                </div>
              )}

              <form onSubmit={handleSubmit} className='space-y-4'>
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
                    className='w-full bg-input border border-border rounded-lg px-4 py-2.5 text-primary
                      text-sm placeholder-muted focus:outline-none focus:border-teal/60
                      focus:ring-1 focus:ring-teal/30 transition-colors'
                  />
                </div>

                <button
                  type='submit'
                  disabled={loading}
                  className='w-full btn-primary py-2.5 disabled:opacity-50'
                >
                  {loading ? 'Generating link…' : 'Send Reset Link'}
                </button>
              </form>

              <p className='text-center text-muted text-sm mt-5'>
                Remembered it?{' '}
                <Link to='/login' className='text-teal hover:underline'>Back to login</Link>
              </p>
            </>
          ) : (
            /* ── Success state ── */
            <>
              <div className='text-center mb-6'>
                <span className='text-5xl block mb-4'>📬</span>
                <h2 className='text-primary font-semibold text-base mb-2'>Reset link generated</h2>
                <p className='text-muted text-sm'>
                  If <span className='text-primary font-medium'>{email}</span> is registered,
                  a reset link has been created. The link expires in 1 hour.
                </p>
              </div>

              {/* Dev mode — show the link on screen since email isn't configured yet */}
              {devLink && (
                <div className='mb-6 p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl'>
                  <p className='text-amber-400 text-xs font-semibold uppercase tracking-wide mb-2'>
                    🛠 Development Mode — Reset Link
                  </p>
                  <p className='text-amber-300/70 text-xs mb-3'>
                    In production this would be sent to your email. For now, click the link below:
                  </p>
                  <a
                    href={devLink}
                    className='text-teal text-sm break-all hover:underline block'
                  >
                    {devLink}
                  </a>
                </div>
              )}

              <Link
                to='/login'
                className='w-full btn-ghost py-2.5 text-sm text-center block'
              >
                ← Back to login
              </Link>
            </>
          )}
        </div>
      </div>
    </div>
  );
}