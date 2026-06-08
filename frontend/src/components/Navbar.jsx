import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import styles from './Navbar.module.css';

export default function Navbar({ onMenuToggle }) {
  const { user, logout, isStudent, isTeacher } = useAuth();
  const navigate = useNavigate();
  const [dropOpen, setDropOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate('/auth');
  };

  const initials = user
    ? `${user.first_name?.[0] ?? ''}${user.last_name?.[0] ?? ''}`.toUpperCase()
    : '?';

  const dashPath = isTeacher ? '/teacher' : '/student';

  return (
    <nav className={styles.navbar}>
      {/* Left: hamburger (mobile) + logo */}
      <div className={styles.left}>
        <button className={styles.menuBtn} onClick={onMenuToggle} aria-label="Toggle sidebar">
          <span /><span /><span />
        </button>
        <Link to={dashPath} className={styles.logo}>
          Sive<span>Adapt</span>
        </Link>
      </div>

      {/* Right: notifications + avatar */}
      <div className={styles.right}>
        <button className={styles.iconBtn} aria-label="Notifications">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
            <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
          </svg>
        </button>

        <div className={styles.avatarWrap}>
          <button
            className={styles.avatar}
            onClick={() => setDropOpen(p => !p)}
            aria-expanded={dropOpen}
          >
            {initials}
          </button>

          {dropOpen && (
            <div className={styles.dropdown} onMouseLeave={() => setDropOpen(false)}>
              <div className={styles.dropHeader}>
                <p className={styles.dropName}>{user?.first_name} {user?.last_name}</p>
                <p className={styles.dropRole}>{user?.role}</p>
              </div>
              <div className={styles.dropDivider} />
              <Link
                to={isTeacher ? '/teacher/profile' : '/student/profile'}
                className={styles.dropItem}
                onClick={() => setDropOpen(false)}
              >
                Profile
              </Link>
              <button className={`${styles.dropItem} ${styles.dropLogout}`} onClick={handleLogout}>
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}
