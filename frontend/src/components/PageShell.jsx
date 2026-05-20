import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Sidebar from './Sidebar';
import NotificationsPanel from './NotificationsPanel';

/*  Search bar component  */
function SearchBar() {
  const [query, setQuery] = useState('');
  const navigate = useNavigate();

  const handleSearch = (e) => {
    e.preventDefault();
    if (query.trim()) {
      navigate(`/library?q=${encodeURIComponent(query.trim())}`);
      setQuery('');
    }
  };

  return (
    <form onSubmit={handleSearch} className='relative w-full max-w-sm'>
      <span className='absolute left-3 top-1/2 -translate-y-1/2 text-muted text-sm pointer-events-none'>
        🔍
      </span>
      <input
        value={query}
        onChange={e => setQuery(e.target.value)}
        placeholder='Search topics, subjects, content…'
        className='w-full bg-app border border-border rounded-lg pl-9 pr-4 py-2 text-primary text-sm
          placeholder-muted/50 focus:outline-none focus:border-teal transition-colors'
      />
    </form>
  );
}

/* PAGE SHELL */
export default function PageShell({ children, title, subtitle, actions, unreadCount = 0 }) {
  const navigate = useNavigate();

  return (
    <div className='flex min-h-screen bg-app'>
      <Sidebar unreadCount={unreadCount} />

      <div className='ml-60 flex-1 flex flex-col min-h-screen'>

        <header className='sticky top-0 z-30 bg-app/80 backdrop-blur border-b border-border px-6 py-3 flex items-center gap-4'>

          {/* Left — page title + welcome subtitle */}
          <div className='flex-shrink-0 min-w-0'>
            {title    && <h1 className='text-primary font-semibold text-base leading-none'>{title}</h1>}
            {subtitle && <p className='text-muted text-xs mt-0.5'>{subtitle}</p>}
          </div>

          {/* Centre — search bar (fills available space) */}
          <div className='flex-1 flex justify-center'>
            <SearchBar />
          </div>

          {/* Right — action buttons + icons */}
          <div className='flex items-center gap-3 flex-shrink-0'>
            {actions}

            {/* Messages icon with unread badge */}
            <button
              onClick={() => navigate('/messages')}
              title='Messages'
              className='relative w-9 h-9 rounded-full bg-border/40 hover:bg-border flex items-center justify-center transition-colors'
            >
              <span className='text-muted text-base'>✉</span>
              {unreadCount > 0 && (
                <span className='absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full bg-teal text-app
                  text-[9px] font-bold flex items-center justify-center leading-none'>
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </button>

            {/* Notifications */}
            <NotificationsPanel />

            {/* Profile avatar — click navigates to /profile */}
            <button
              onClick={() => navigate('/profile')}
              title='My Profile'
              className='w-9 h-9 rounded-full bg-teal/20 border border-teal/40 flex items-center justify-center
                text-teal text-xs font-bold hover:bg-teal/30 transition-colors overflow-hidden flex-shrink-0'
            >
              {window.__profilePic
                ? <img
                    src={window.__profilePic}
                    alt='avatar'
                    className='w-full h-full object-cover rounded-full'
                  />
                : (window.__studentName || 'U')[0].toUpperCase()
              }
            </button>
          </div>

        </header>

        <main className='flex-1 p-6'>{children}</main>
      </div>
    </div>
  );
}