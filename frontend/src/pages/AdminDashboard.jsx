import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import AdminSidebar from '../components/AdminSidebar';   // new admin-only sidebar
import Navbar  from '../components/Navbar';
import api from '../services/api';
import styles from './AdminDashboard.module.css';

/* ── Initial form templates ───────────────────────────────────── */
const INIT_GRADE   = { label: '', order_index: 0 };
const INIT_CLASS   = { grade_id: '', name: '' };
const INIT_SUBJECT = { name: '', code: '', description: '' };
const INIT_FACULTY = { name: '', description: '' };
const INIT_PROG    = { faculty_id: '', name: '', duration_levels: 3 };
const INIT_COURSE  = { name: '', code: '', description: '' };

export default function AdminDashboard() {
  const { user } = useAuth();
  const [sideOpen, setSideOpen] = useState(false);

  // ── Active section (driven by sidebar) ────────────────────────
  const [tab, setTab] = useState('overview');   // 'overview' | 'pending' | 'school' | 'tertiary'

  // ── Overview stats ───────────────────────────────────────────
  const [stats, setStats] = useState(null);

  // ── Pending teachers & lecturers ─────────────────────────────
  const [pending, setPending] = useState([]);
  const [loadingPending, setLoadingPending] = useState(false);
  const [busyId, setBusyId] = useState(null);

  // ── School data ──────────────────────────────────────────────
  const [grades, setGrades] = useState([]);
  const [subjects, setSubjects] = useState([]);

  // ── Tertiary data ────────────────────────────────────────────
  const [faculties, setFaculties] = useState([]);
  const [courses, setCourses] = useState([]);   // all courses (for display)

  // ── CRUD modals state ────────────────────────────────────────
  const [modal, setModal] = useState(null);     // 'grade' | 'class' | 'subject' | 'faculty' | 'programme' | 'course'
  const [form, setForm] = useState({});

  // ── Toast & confirm ──────────────────────────────────────────
  const [toast, setToast] = useState(null);
  const [confirmReject, setConfirmReject] = useState(null);

  /* ──── Data loading ──────────────────────────────────────────── */
  const loadStats = async () => {
    try {
      const res = await api.get('/api/admin/stats');
      setStats(res.data);
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  };

  const loadPending = async () => {
    setLoadingPending(true);
    try {
      const res = await api.get('/api/admin/pending');
      setPending(res.data || []);
    } catch (err) {
      setToast({ type: 'error', text: 'Could not load pending approvals.' });
    } finally {
      setLoadingPending(false);
    }
  };

  const loadGrades = async () => {
    try {
      const res = await api.get('/api/admin/grades-public');
      setGrades(res.data || []);
    } catch (err) { console.error(err); }
  };

  const loadSubjects = async () => {
    try {
      const res = await api.get('/api/admin/subjects-public');
      setSubjects(res.data || []);
    } catch (err) { console.error(err); }
  };

  const loadFaculties = async () => {
    try {
      const res = await api.get('/api/admin/faculties-public');
      setFaculties(res.data || []);
    } catch (err) { console.error(err); }
  };

  const loadCourses = async () => {
    try {
      // fetch all courses using a special endpoint? We'll use the public one with 'all'
      const res = await api.get('/api/admin/courses-public', {
        params: { programme_id: 'all', level: 'all' }
      });
      setCourses(res.data?.courses || []);
    } catch (err) { console.error(err); }
  };

  // Load data when tab changes
  useEffect(() => { loadStats(); }, []);
  useEffect(() => {
    if (tab === 'pending') loadPending();
    if (tab === 'school') { loadGrades(); loadSubjects(); }
    if (tab === 'tertiary') { loadFaculties(); loadCourses(); }
  }, [tab]);

  // Toast auto-dismiss
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 4000);
    return () => clearTimeout(t);
  }, [toast]);

  /* ──── Approve / Reject ──────────────────────────────────────── */
  const handleApprove = async (item) => {
    setBusyId(item.id);
    const endpoint = item.role === 'teacher'
      ? `/api/admin/teachers/${item.id}/approve`
      : `/api/admin/lecturers/${item.id}/approve`;
    try {
      await api.post(endpoint, { action: 'approve' });
      setPending(prev => prev.filter(i => i.id !== item.id));
      setToast({ type: 'success', text: `${item.name} approved.` });
      loadStats();
    } catch (err) {
      setToast({ type: 'error', text: err.response?.data?.detail || 'Approval failed.' });
    } finally {
      setBusyId(null);
    }
  };

  const handleReject = async (item) => {
    setBusyId(item.id);
    const endpoint = item.role === 'teacher'
      ? `/api/admin/teachers/${item.id}/approve`
      : `/api/admin/lecturers/${item.id}/approve`;
    try {
      await api.post(endpoint, { action: 'reject' });
      setPending(prev => prev.filter(i => i.id !== item.id));
      setToast({ type: 'success', text: `${item.name} rejected.` });
      loadStats();
    } catch (err) {
      setToast({ type: 'error', text: err.response?.data?.detail || 'Rejection failed.' });
    } finally {
      setBusyId(null);
      setConfirmReject(null);
    }
  };

  /* ──── CRUD handlers ─────────────────────────────────────────── */
  const openModal = (type, data = {}) => {
    setForm(data);
    setModal(type);
  };
  const closeModal = () => setModal(null);

  const handleCreate = async () => {
    let endpoint = '', payload = {};
    switch (modal) {
      case 'grade':
        endpoint = '/api/admin/grades';
        payload = { label: form.label, order_index: form.order_index || 0 };
        break;
      case 'class':
        endpoint = '/api/admin/classes';
        payload = { grade_id: Number(form.grade_id), name: form.name };
        break;
      case 'subject':
        endpoint = '/api/admin/subjects';
        payload = { name: form.name, code: form.code, description: form.description };
        break;
      case 'faculty':
        endpoint = '/api/admin/faculties';
        payload = { name: form.name, description: form.description };
        break;
      case 'programme':
        endpoint = '/api/admin/programmes';
        payload = { faculty_id: Number(form.faculty_id), name: form.name, duration_levels: form.duration_levels };
        break;
      case 'course':
        endpoint = '/api/admin/courses';
        payload = { name: form.name, code: form.code, description: form.description };
        break;
      default: return;
    }
    try {
      await api.post(endpoint, payload);
      setToast({ type: 'success', text: `${modal} created.` });
      closeModal();
      if (modal === 'grade') loadGrades();
      else if (modal === 'subject') loadSubjects();
      else if (modal === 'faculty') loadFaculties();
      else if (modal === 'course') loadCourses();
    } catch (err) {
      setToast({ type: 'error', text: err.response?.data?.detail || 'Creation failed.' });
    }
  };

  /* ──── Helper ───────────────────────────────────────────────── */
  const initials = (name) => (name || '?').split(' ').map(p => p[0]).join('').slice(0, 2).toUpperCase();

  /* ──── Modal renderer ───────────────────────────────────────── */
  const renderModal = () => {
    if (!modal) return null;
    return (
      <div className={styles.modalOverlay} onClick={closeModal}>
        <div className={styles.modal} onClick={e => e.stopPropagation()}>
          <h3>New {modal}</h3>
          {/* dynamic fields */}
          {modal === 'grade' && (
            <>
              <input placeholder="Label" value={form.label} onChange={e => setForm({...form, label: e.target.value})} />
              <input placeholder="Order index" type="number" value={form.order_index} onChange={e => setForm({...form, order_index: e.target.value})} />
            </>
          )}
          {modal === 'class' && (
            <>
              <select value={form.grade_id} onChange={e => setForm({...form, grade_id: e.target.value})}>
                <option value="">-- Grade --</option>
                {grades.map(g => <option key={g.id} value={g.id}>{g.label}</option>)}
              </select>
              <input placeholder="Class name" value={form.name} onChange={e => setForm({...form, name: e.target.value})} />
            </>
          )}
          {modal === 'subject' && (
            <>
              <input placeholder="Name" value={form.name} onChange={e => setForm({...form, name: e.target.value})} />
              <input placeholder="Code" value={form.code} onChange={e => setForm({...form, code: e.target.value})} />
              <textarea placeholder="Description" value={form.description} onChange={e => setForm({...form, description: e.target.value})} />
            </>
          )}
          {modal === 'faculty' && (
            <>
              <input placeholder="Name" value={form.name} onChange={e => setForm({...form, name: e.target.value})} />
              <input placeholder="Description" value={form.description} onChange={e => setForm({...form, description: e.target.value})} />
            </>
          )}
          {modal === 'programme' && (
            <>
              <select value={form.faculty_id} onChange={e => setForm({...form, faculty_id: e.target.value})}>
                <option value="">-- Faculty --</option>
                {faculties.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}
              </select>
              <input placeholder="Name" value={form.name} onChange={e => setForm({...form, name: e.target.value})} />
              <input placeholder="Duration (levels)" type="number" value={form.duration_levels} onChange={e => setForm({...form, duration_levels: e.target.value})} />
            </>
          )}
          {modal === 'course' && (
            <>
              <input placeholder="Name" value={form.name} onChange={e => setForm({...form, name: e.target.value})} />
              <input placeholder="Code" value={form.code} onChange={e => setForm({...form, code: e.target.value})} />
              <textarea placeholder="Description" value={form.description} onChange={e => setForm({...form, description: e.target.value})} />
            </>
          )}
          <div className={styles.modalActions}>
            <button onClick={closeModal}>Cancel</button>
            <button onClick={handleCreate}>Create</button>
          </div>
        </div>
      </div>
    );
  };

  /* ──── Main render ───────────────────────────────────────────── */
  return (
    <div className="dashboard-shell">
      <AdminSidebar
        open={sideOpen}
        onClose={() => setSideOpen(false)}
        activeTab={tab}
        onTabChange={setTab}
      />

      <div className="dashboard-main" style={{ paddingTop: 'var(--navbar-height)' }}>
        <Navbar onMenuToggle={() => setSideOpen(p => !p)} />

        <div className="dashboard-content">
          {/* Header (no top tabs) */}
          <div className={styles.header}>
            <div>
              <h1 className={styles.title}>Admin <span>Console</span></h1>
              <p className={styles.subtitle}>Welcome, {user?.first_name || 'Admin'}</p>
            </div>
          </div>

          {/* Toast */}
          {toast && (
            <div className={`${styles.toast} ${toast.type === 'error' ? styles.toastError : styles.toastSuccess}`}>
              {toast.type === 'error' ? '⚠' : '✓'} {toast.text}
            </div>
          )}

          {/* ── Section: Overview ────────────────────────────── */}
          {tab === 'overview' && stats && (
            <div className={styles.statsGrid}>
              <div className={`card ${styles.statCard}`}><span>👩‍🎓</span><b>{stats.school_students}</b> School Students</div>
              <div className={`card ${styles.statCard}`}><span>🎓</span><b>{stats.tertiary_students}</b> Tertiary Students</div>
              <div className={`card ${styles.statCard}`}><span>🍎</span><b>{stats.teachers}</b> Teachers</div>
              <div className={`card ${styles.statCard}`}><span>👨‍🏫</span><b>{stats.lecturers}</b> Lecturers</div>
              <div className={`card ${styles.statCard}`}><span>⏳</span><b>{stats.pending_count}</b> Pending</div>
              <div className={`card ${styles.statCard}`}><span>🏫</span><b>{stats.grades}</b> Grades</div>
              <div className={`card ${styles.statCard}`}><span>📚</span><b>{stats.classes}</b> Classes</div>
              <div className={`card ${styles.statCard}`}><span>📖</span><b>{stats.subjects}</b> Subjects</div>
              <div className={`card ${styles.statCard}`}><span>🏛️</span><b>{stats.faculties}</b> Faculties</div>
              <div className={`card ${styles.statCard}`}><span>📜</span><b>{stats.programmes}</b> Programmes</div>
              <div className={`card ${styles.statCard}`}><span>📝</span><b>{stats.courses}</b> Courses</div>
            </div>
          )}

          {/* ── Section: Pending ─────────────────────────────── */}
          {tab === 'pending' && (
            <>
              <div className={styles.sectionHead}>
                <h2>Pending Approvals</h2>
                <span className="badge-amber">{pending.length} waiting</span>
              </div>
              {loadingPending ? (
                <div className={styles.loadingBox}>Loading…</div>
              ) : pending.length === 0 ? (
                <p>All caught up!</p>
              ) : (
                <div className={styles.queueList}>
                  {pending.map(item => (
                    <div key={item.id} className={styles.queueRow}>
                      <div className={styles.queueLeft}>
                        <div className={styles.avatar}>{initials(item.name)}</div>
                        <div>
                          <strong>{item.name}</strong> ({item.role})<br />
                          <small>{item.email}</small>
                          {item.assignments?.map((a, i) => <div key={i}><small>{a.label}</small></div>)}
                        </div>
                      </div>
                      <div className={styles.queueActions}>
                        <button className={styles.approveBtn} onClick={() => handleApprove(item)} disabled={busyId === item.id}>
                          {busyId === item.id ? '…' : '✓ Approve'}
                        </button>
                        <button className={styles.rejectBtn} onClick={() => setConfirmReject(item)} disabled={busyId === item.id}>
                          ✕ Reject
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}

          {/* ── Section: School ──────────────────────────────── */}
          {tab === 'school' && (
            <div style={{ display: 'grid', gap: '2rem' }}>
              <section>
                <h3>Grades</h3>
                <ul>{grades.map(g => <li key={g.id}>{g.label} (order: {g.order_index})</li>)}</ul>
                <button onClick={() => openModal('grade')}>+ Add Grade</button>
              </section>
              <section>
                <h3>Subjects</h3>
                <ul>{subjects.map(s => <li key={s.id}>{s.name} ({s.code})</li>)}</ul>
                <button onClick={() => openModal('subject')}>+ Add Subject</button>
              </section>
              <section>
                <h3>Classes</h3>
                <button onClick={() => openModal('class')}>+ Add Class</button>
              </section>
            </div>
          )}

          {/* ── Section: Tertiary ────────────────────────────── */}
          {tab === 'tertiary' && (
            <div style={{ display: 'grid', gap: '2rem' }}>
              <section>
                <h3>Faculties</h3>
                <ul>{faculties.map(f => <li key={f.id}>{f.name}</li>)}</ul>
                <button onClick={() => openModal('faculty')}>+ Add Faculty</button>
              </section>
              <section>
                <h3>Courses</h3>
                <ul>{courses.slice(0, 20).map(c => <li key={c.pcl_id}>{c.course_name} ({c.course_code})</li>)}</ul>
                <button onClick={() => openModal('course')}>+ Add Course</button>
              </section>
              <section>
                <h3>Programmes</h3>
                <button onClick={() => openModal('programme')}>+ Add Programme</button>
              </section>
            </div>
          )}

          {/* ── Modals ────────────────────────────────────────── */}
          {renderModal()}

          {confirmReject && (
            <div className={styles.modalOverlay} onClick={() => setConfirmReject(null)}>
              <div className={styles.modal} onClick={e => e.stopPropagation()}>
                <span>⚠</span>
                <h3>Reject {confirmReject.name}?</h3>
                <div className={styles.modalActions}>
                  <button onClick={() => setConfirmReject(null)}>Cancel</button>
                  <button onClick={() => handleReject(confirmReject)} disabled={busyId === confirmReject.id}>
                    Reject
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}