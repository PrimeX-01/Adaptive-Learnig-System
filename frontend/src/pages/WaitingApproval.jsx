import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

/**
 * WaitingApproval — shown to teachers and lecturers whose accounts
 * exist but have not yet been approved by the administrator.
 *
 * Dark / light mode: uses CSS variables from globals.css so it
 * automatically adapts when the user toggles the theme.
 */
export default function WaitingApproval() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/auth', { replace: true });
  };

  const roleLabel = user?.role === 'lecturer' ? 'Lecturer' : 'Teacher';

  return (
    <div className='min-h-screen bg-app flex items-center justify-center p-4'>

      {/* Subtle background glow */}
      <div className='absolute inset-0 overflow-hidden pointer-events-none'>
        <div className='absolute top-1/3 left-1/2 -translate-x-1/2 w-96 h-96
          bg-amber-500/5 rounded-full blur-3xl' />
      </div>

      <div className='relative w-full max-w-md text-center'>

        {/* Brand */}
        <div className='w-14 h-14 bg-teal/20 border border-teal/40 rounded-2xl
          flex items-center justify-center mx-auto mb-6'>
          <span className='text-teal font-bold text-xl'>S</span>
        </div>

        {/* Card */}
        <div className='card p-8'>

          {/* Animated clock icon */}
          <div className='w-20 h-20 rounded-full bg-amber-500/10 border-2 border-amber-500/30
            flex items-center justify-center mx-auto mb-6'>
            <span className='text-5xl'>⏳</span>
          </div>

          <h1 className='text-primary text-2xl font-bold mb-2'>
            Awaiting Approval
          </h1>

          <p className='text-muted text-sm leading-relaxed mb-4'>
            Your <span className='text-primary font-medium'>{roleLabel}</span> account has been
            submitted successfully. The SiveAdapt administrator will review and approve your
            registration before you can access the dashboard.
          </p>

          {user?.name && (
            <div className='px-4 py-3 bg-app border border-border rounded-xl mb-4 text-left'>
              <p className='text-muted text-xs uppercase tracking-wide mb-1'>Registered as</p>
              <p className='text-primary font-medium'>{user.name}</p>
              <p className='text-muted text-sm'>{user.email || ''}</p>
            </div>
          )}

          {/* What happens next */}
          <div className='px-4 py-4 bg-teal/5 border border-teal/20 rounded-xl mb-6 text-left'>
            <p className='text-teal text-xs font-semibold uppercase tracking-wide mb-3'>
              What happens next
            </p>
            {[
              'The administrator reviews your submitted assignments.',
              'Once approved, you will be able to log in and access your dashboard.',
              'You may return to this page at any time by logging in.',
            ].map((item, i) => (
              <div key={i} className='flex gap-3 mb-2 last:mb-0'>
                <span className='text-teal text-xs mt-0.5 flex-shrink-0'>{i + 1}.</span>
                <p className='text-muted text-xs leading-relaxed'>{item}</p>
              </div>
            ))}
          </div>

          {/* Actions */}
          <div className='flex flex-col gap-3'>
            <button
              onClick={() => window.location.reload()}
              className='w-full btn-ghost py-2.5 text-sm'
            >
              🔄 Check approval status
            </button>
            <button
              onClick={handleLogout}
              className='w-full text-muted text-sm hover:text-primary transition-colors py-2'
            >
              Sign out
            </button>
          </div>

        </div>

        <p className='text-muted text-xs mt-4'>
          SiveAdapt · University of Eswatini · CSC402
        </p>

      </div>
    </div>
  );
}
