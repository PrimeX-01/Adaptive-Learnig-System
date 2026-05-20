import { NavLink, useNavigate } from 'react-router-dom';

const STUDENT_LINKS = [
  { to: '/dashboard', icon: '⬡',  label: 'Dashboard'  },
  { to: '/subjects',  icon: '📚', label: 'My Subjects' },
  { to: '/chat',      icon: '◈',  label: 'AI Tutor'   },
  { to: '/quiz',      icon: '◎',  label: 'Quiz'       },
  { to: '/progress',  icon: '◐',  label: 'Progress'   },
  { to: '/library',   icon: '◫',  label: 'Library'    },
  { to: '/messages',  icon: '✉',  label: 'Messages',  badge: true },
  { to: '/profile',   icon: '👤', label: 'My Profile' },
];

const TEACHER_LINKS = [
  { to: '/teacher',  icon: '⬡', label: 'Command Centre' },
  { to: '/messages', icon: '✉', label: 'Messages', badge: true },
];

export default function Sidebar({ unreadCount = 0 }) {
  const nav = useNavigate();
  const isTeacher = window.__isTeacher;
  const links     = isTeacher ? TEACHER_LINKS : STUDENT_LINKS;

  function handleLogout() {
    // Clear window variables
    ['__authToken', '__studentId', '__isTeacher', '__studentName', '__profilePic']
      .forEach(k => { window[k] = null; });

    
    localStorage.removeItem('sa_token');
    localStorage.removeItem('sa_studentId');
    localStorage.removeItem('sa_isTeacher');
    localStorage.removeItem('sa_name');
    localStorage.removeItem('sa_pic');

    nav('/login');
  }

  return (
    <aside className='w-60 min-h-screen bg-sidebar border-r border-border flex flex-col fixed left-0 top-0 z-40'>

      {/* ── Brand header ─────────────────────────────────────────── */}
      <div className='px-6 py-5 border-b border-border'>
        <div className='flex items-center gap-2'>
          <div className='w-8 h-8 rounded-lg bg-teal/20 border border-teal/40 flex items-center justify-center text-teal font-black text-sm'>
            SA
          </div>
          <div>
            <div className='font-bold text-primary text-sm leading-none'>SiveAdapt</div>
            <div className='text-muted text-xs mt-0.5'>Univ. of Eswatini</div>
          </div>
        </div>
      </div>

      {/* ── Navigation links ─────────────────────────────────────── */}
      <nav className='flex-1 px-3 py-4 flex flex-col gap-1'>
        {links.map(link => (
          <NavLink
            key={link.to}
            to={link.to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all relative
               ${isActive
                 ? 'bg-teal/10 text-teal border border-teal/30 shadow-teal-glow'
                 : 'text-muted hover:text-primary hover:bg-card'
               }`
            }
          >
            <span className='text-base w-5 text-center'>{link.icon}</span>
            <span className='font-medium'>{link.label}</span>
            {link.badge && unreadCount > 0 && (
              <span className='ml-auto badge-blue'>{unreadCount}</span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* ── Bottom user card + logout ─────────────────────────────── */}
      <div className='px-4 py-4 border-t border-border'>

        {/* Clickable user card → goes to /profile */}
        <button
          onClick={() => nav('/profile')}
          className='flex items-center gap-3 mb-3 w-full hover:opacity-80 transition-opacity text-left'
        >
          <div className='w-8 h-8 rounded-full bg-teal/20 border border-teal/40 flex items-center justify-center text-teal text-xs font-bold overflow-hidden flex-shrink-0'>
            {window.__profilePic
              ? <img src={window.__profilePic} alt='avatar' className='w-full h-full object-cover rounded-full' />
              : (window.__studentName || 'U')[0].toUpperCase()
            }
          </div>
          <div className='min-w-0'>
            <div className='text-primary text-xs font-medium truncate'>{window.__studentName || 'User'}</div>
            <div className='text-muted text-xs'>{isTeacher ? 'Teacher' : 'Student'}</div>
          </div>
        </button>

        <button
          onClick={handleLogout}
          className='text-muted hover:text-red-400 text-xs flex items-center gap-2 transition-colors'
        >
          <span>⏻</span> Logout
        </button>
      </div>

    </aside>
  );
}