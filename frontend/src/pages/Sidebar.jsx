import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import styles from './Sidebar.module.css';

/* ── Nav items by role ── */
const STUDENT_NAV = [
  { path: '/student',           label: 'Overview',   icon: GridIcon },
  { path: '/student/tutor',     label: 'AI Tutor',   icon: BotIcon },
  { path: '/student/quizzes',   label: 'Quizzes',    icon: QuizIcon },
  { path: '/student/progress',  label: 'Progress',   icon: ChartIcon },
  { path: '/student/review',    label: 'Review',     icon: ReviewIcon },   // NEW
  { path: '/student/library',   label: 'Library',    icon: BookIcon },
  { path: '/student/messages',  label: 'Messages',   icon: MsgIcon },
];

const TEACHER_NAV = [
  { path: '/teacher',              label: 'Overview',    icon: GridIcon },
  { path: '/teacher/students',     label: 'Students',    icon: UsersIcon },
  { path: '/teacher/directives',   label: 'AI Directives', icon: BotIcon },
  { path: '/teacher/library',      label: 'Library',     icon: BookIcon },
  { path: '/teacher/messages',     label: 'Messages',    icon: MsgIcon },
  { path: '/teacher/topics', label: 'Topics', icon: BookIcon },
];

const ADMIN_NAV = [
  { path: '/admin', label: 'Verifications', icon: ShieldIcon },
];

export default function Sidebar({ open, onClose }) {
  const { user, logout, isTeacher, isAdmin } = useAuth();
  const navigate = useNavigate();
  const navItems = isAdmin ? ADMIN_NAV : isTeacher ? TEACHER_NAV : STUDENT_NAV;

  const handleLogout = async () => {
    await logout();
    navigate('/auth');
  };

  return (
    <>
      {open && <div className={styles.overlay} onClick={onClose} />}
      <aside className={`${styles.sidebar} ${open ? styles.open : ''}`}>
        <div className={styles.brand}>
          <span className={styles.brandText}>Sive<em>Adapt</em></span>
          <button className={styles.closeBtn} onClick={onClose} aria-label="Close menu">✕</button>
        </div>
        <div className={styles.userPill}>
          <div className={styles.avatar}>{user?.first_name?.[0]}{user?.last_name?.[0]}</div>
          <div className={styles.userInfo}>
            <p className={styles.userName}>{user?.first_name}</p>
            <p className={styles.userRole}>{user?.role}</p>
          </div>
        </div>
        <nav className={styles.nav}>
          {navItems.map(({ path, label, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              end={path === '/student' || path === '/teacher' || path === '/admin'}
              className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
              onClick={onClose}
            >
              <span className={styles.navIcon}><Icon /></span>
              <span className={styles.navLabel}>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className={styles.bottom}>
          <button className={styles.logoutBtn} onClick={handleLogout}>
            <LogoutIcon />
            <span>Sign out</span>
          </button>
        </div>
      </aside>
    </>
  );
}

/* ── Inline SVG icons ── */
function GridIcon()   { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>; }
function BotIcon()    { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><line x1="8" y1="16" x2="8" y2="16"/><line x1="16" y1="16" x2="16" y2="16"/></svg>; }
function QuizIcon()   { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>; }
function ChartIcon()  { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6"  y1="20" x2="6"  y2="14"/></svg>; }
function ReviewIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>; }  // NEW
function BookIcon()   { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>; }
function MsgIcon()    { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>; }
function UsersIcon()  { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>; }
function ShieldIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2l8 4v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V6l8-4z"/><path d="M9.5 12l2 2 3.5-4"/></svg>; }
function LogoutIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>; }