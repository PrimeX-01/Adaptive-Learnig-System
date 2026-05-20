import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

const ICONS = { teacher_tip:'💡', review_due:'📅', level_up:'🎯', new_message:'✉', student_level_change:'📈', default:'🔔' };
const COLS  = { teacher_tip:'text-amber-400', review_due:'text-blue-400', level_up:'text-teal', new_message:'text-teal', student_level_change:'text-green-400', default:'text-muted' };

export default function NotificationsPanel() {
  const [open,   setOpen]   = useState(false);
  const [notifs, setNotifs] = useState([]);
  const ref = useRef(null);
  const nav = useNavigate();
  const sid = window.__studentId;

  const load = () => sid && api.get(`/api/messages/notifications/${sid}`).then(r => setNotifs(r.data)).catch(()=>{});
  useEffect(() => { load(); const t = setInterval(load, 60000); return () => clearInterval(t); }, [sid]);
  useEffect(() => {
    const fn = e => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', fn);
    return () => document.removeEventListener('mousedown', fn);
  }, []);

  const unread = notifs.filter(n => !n.is_read).length;
  return (
    <div className='relative' ref={ref}>
      <button onClick={() => setOpen(o=>!o)} className='relative w-9 h-9 rounded-lg bg-card border border-border flex items-center justify-center hover:border-teal/50 transition-colors'>
        <span className='text-lg'>🔔</span>
        {unread > 0 && <span className='absolute -top-1 -right-1 w-4 h-4 bg-teal text-app text-xs font-bold rounded-full flex items-center justify-center'>{unread}</span>}
      </button>
      {open && (
        <div className='absolute right-0 top-11 w-80 bg-card border border-border rounded-xl shadow-card overflow-hidden z-50'>
          <div className='px-4 py-3 border-b border-border flex justify-between items-center'>
            <span className='font-semibold text-primary text-sm'>Notifications</span>
            {unread > 0 && <span className='badge-teal'>{unread} new</span>}
          </div>
          <div className='max-h-80 overflow-y-auto'>
            {notifs.length === 0 && <p className='text-muted text-sm p-4 text-center'>No notifications yet</p>}
            {notifs.map(n => (
              <button key={n.id} onClick={() => { if(n.action_url) nav(n.action_url); setOpen(false); }}
                className={`w-full text-left px-4 py-3 border-b border-border/50 hover:bg-border/30 transition-colors ${!n.is_read?'bg-teal/5':''}`}>
                <div className='flex items-start gap-3'>
                  <span className={`text-lg mt-0.5 ${COLS[n.type]||COLS.default}`}>{ICONS[n.type]||ICONS.default}</span>
                  <div className='flex-1 min-w-0'>
                    <p className='text-primary text-xs font-medium leading-snug'>{n.title}</p>
                    {n.body && <p className='text-muted text-xs mt-0.5 truncate'>{n.body}</p>}
                  </div>
                  {!n.is_read && <div className='w-2 h-2 rounded-full bg-teal flex-shrink-0 mt-1' />}
                </div>
              </button>
            ))}
          </div>
          <button onClick={() => { nav('/messages'); setOpen(false); }} className='w-full py-2.5 text-teal text-xs font-medium hover:bg-teal/5 transition-colors border-t border-border'>
            View all messages →
          </button>
        </div>
      )}
    </div>
  );
}
