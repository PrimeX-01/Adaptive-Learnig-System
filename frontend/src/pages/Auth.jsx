import { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';
import styles from './Auth.module.css';

// Full grade options (same as Register.jsx)
const GRADE_OPTIONS = [
  { value: 1,  label: 'Grade 1',   group: 'Primary' },
  { value: 2,  label: 'Grade 2',   group: 'Primary' },
  { value: 3,  label: 'Grade 3',   group: 'Primary' },
  { value: 4,  label: 'Grade 4',   group: 'Primary' },
  { value: 5,  label: 'Grade 5',   group: 'Primary' },
  { value: 6,  label: 'Grade 6',   group: 'Primary' },
  { value: 7,  label: 'Grade 7',   group: 'Primary' },
  { value: 8,  label: 'Grade 8',   group: 'High School' },
  { value: 9,  label: 'Grade 9',   group: 'High School' },
  { value: 10, label: 'Grade 10',  group: 'High School' },
  { value: 11, label: 'Grade 11',  group: 'High School' },
  { value: 12, label: 'Grade 12',  group: 'High School' },
  { value: 13, label: 'Level 1',   group: 'Tertiary' },
  { value: 14, label: 'Level 2',   group: 'Tertiary' },
  { value: 15, label: 'Level 3',   group: 'Tertiary' },
  { value: 16, label: 'Level 4',   group: 'Tertiary' },
  { value: 17, label: 'Level 5',   group: 'Tertiary' },
  { value: 18, label: 'Masters',   group: 'Postgraduate' },
  { value: 19, label: 'PhD',       group: 'Postgraduate' },
];

export default function Auth() {
  const { login, register, isAuthenticated, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [tab, setTab] = useState('login');
  const [role, setRole] = useState('student');
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Student registration fields
  const [form, setForm] = useState({
    first_name: '', last_name: '', email: '',
    password: '', confirm: '',
    education_level: 'secondary',
    grade_level: '',
    subjectSearch: '',
    availableSubjects: [],
    selectedSubjects: [],
    loadingSubjects: false,
  });

  // Teacher fields
  const [teacherSubjects, setTeacherSubjects] = useState([]);
  const [teacherSubjectName, setTeacherSubjectName] = useState('');
  const [teacherSubjectGrade, setTeacherSubjectGrade] = useState('8');

  // ✅ Fix: redirect only once, and only if not already on a dashboard page
  useEffect(() => {
    if (isAuthenticated) {
      const currentPath = location.pathname;
      // If already on a dashboard, do nothing
      if (currentPath === '/student' || currentPath === '/teacher') return;
      const dest = user?.role === 'teacher' ? '/teacher' : '/student';
      navigate(dest, { replace: true });
    }
  }, [isAuthenticated, user, location.pathname, navigate]);

  const set = (k, v) => setForm(p => ({ ...p, [k]: v }));

  // Load subjects for tertiary
  useEffect(() => {
    if (tab === 'register' && role === 'student' && form.education_level === 'tertiary' && step === 2) {
      set('loadingSubjects', true);
      api.get('/api/subjects/available')
        .then(r => set('availableSubjects', r.data || []))
        .catch(() => set('availableSubjects', []))
        .finally(() => set('loadingSubjects', false));
    }
  }, [tab, role, form.education_level, step]);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const u = await login(form.email, form.password);
      // After login, navigate to the appropriate dashboard
      navigate(u.role === 'teacher' ? '/teacher' : '/student', { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    if (form.password !== form.confirm) {
      setError('Passwords do not match');
      return;
    }
    setError('');
    setLoading(true);

    const payload = {
      first_name: form.first_name,
      last_name:  form.last_name,
      email:      form.email,
      password:   form.password,
      role,
    };

    if (role === 'student') {
      const grade = form.education_level === 'tertiary' ? null : Number(form.grade_level);
      payload.grade_level = grade;
      payload.education_level = form.education_level;
      if (form.education_level === 'tertiary') {
        payload.subject_ids = form.selectedSubjects;
      }
    } else {
      payload.subjects = teacherSubjects;
    }

    try {
      const u = await register(payload);
      navigate(u.role === 'teacher' ? '/teacher' : '/student', { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const addTeacherSubject = () => {
    if (!teacherSubjectName.trim()) return;
    setTeacherSubjects(prev => [...prev, { name: teacherSubjectName, grade_level: Number(teacherSubjectGrade) }]);
    setTeacherSubjectName('');
  };
  const removeTeacherSubject = (i) => setTeacherSubjects(prev => prev.filter((_, idx) => idx !== i));

  const isTertiary = form.education_level === 'tertiary';
  const filteredSubjects = form.availableSubjects.filter(s =>
    s.name.toLowerCase().includes(form.subjectSearch.toLowerCase()) ||
    s.code.toLowerCase().includes(form.subjectSearch.toLowerCase())
  );

  return (
    <div className={styles.page}>
      <div className={styles.brand}>
        <Link to="/" className={styles.logo}>Sive<span>Adapt</span></Link>
        <div className={styles.brandContent}>
          <h2 className={styles.brandHeadline}>
            Learning that adapts<br />to <em>you.</em>
          </h2>
          <p className={styles.brandSub}>
            Personalised AI tutoring, FCL tracking, and VARK-optimised content —
            built for South African learners.
          </p>
          <div className={styles.brandFeatures}>
            {['FCL Level Tracking', 'VARK-Aware AI Tutor', 'Teacher Directives', 'Smart Quizzes'].map(f => (
              <div key={f} className={styles.brandFeature}>
                <span className={styles.brandCheck}>✓</span>
                <span>{f}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className={styles.formPanel}>
        <div className={styles.formInner}>
          <div className={styles.tabs}>
            <button className={`${styles.tabBtn} ${tab === 'login' ? styles.activeTab : ''}`} onClick={() => { setTab('login'); setError(''); }}>
              Sign in
            </button>
            <button className={`${styles.tabBtn} ${tab === 'register' ? styles.activeTab : ''}`} onClick={() => { setTab('register'); setError(''); setStep(1); }}>
              Create account
            </button>
          </div>

          {/* LOGIN FORM */}
          {tab === 'login' && (
            <form onSubmit={handleLogin} className={styles.form}>
              <h1 className={styles.formTitle}>Welcome back</h1>
              {error && <div className={styles.error}>{error}</div>}
              <div className={styles.field}>
                <label className={styles.label}>Email</label>
                <input className="input" type="email" required value={form.email} onChange={e => set('email', e.target.value)} placeholder="you@example.com" />
              </div>
              <div className={styles.field}>
                <label className={styles.label}>Password</label>
                <input className="input" type="password" required value={form.password} onChange={e => set('password', e.target.value)} placeholder="••••••••" />
              </div>
              <button type="submit" className={`btn btn-primary ${styles.submitBtn}`} disabled={loading}>
                {loading ? 'Signing in…' : 'Sign in'}
              </button>
            </form>
          )}

          {/* REGISTER - Step 1 */}
          {tab === 'register' && step === 1 && (
            <form onSubmit={e => { e.preventDefault(); setStep(2); }} className={styles.form}>
              <h1 className={styles.formTitle}>Create account</h1>
              {error && <div className={styles.error}>{error}</div>}
              <div className={styles.roleToggle}>
                <button type="button" className={`${styles.roleBtn} ${role === 'student' ? styles.activeRole : ''}`} onClick={() => setRole('student')}>
                  🎓 Student
                </button>
                <button type="button" className={`${styles.roleBtn} ${role === 'teacher' ? styles.activeRole : ''}`} onClick={() => setRole('teacher')}>
                  📖 Teacher
                </button>
              </div>
              <div className={styles.fieldRow}>
                <div className={styles.field}>
                  <label className={styles.label}>First name</label>
                  <input className="input" required value={form.first_name} onChange={e => set('first_name', e.target.value)} placeholder="First name" />
                </div>
                <div className={styles.field}>
                  <label className={styles.label}>Last name</label>
                  <input className="input" required value={form.last_name} onChange={e => set('last_name', e.target.value)} placeholder="Last name" />
                </div>
              </div>
              <div className={styles.field}>
                <label className={styles.label}>Email</label>
                <input className="input" type="email" required value={form.email} onChange={e => set('email', e.target.value)} placeholder="you@example.com" />
              </div>
              <div className={styles.field}>
                <label className={styles.label}>Password</label>
                <input className="input" type="password" required minLength={8} value={form.password} onChange={e => set('password', e.target.value)} placeholder="At least 8 characters" />
              </div>
              <div className={styles.field}>
                <label className={styles.label}>Confirm password</label>
                <input className="input" type="password" required value={form.confirm} onChange={e => set('confirm', e.target.value)} placeholder="Repeat password" />
              </div>
              <button type="submit" className={`btn btn-primary ${styles.submitBtn}`}>
                Continue →
              </button>
            </form>
          )}

          {/* REGISTER - Step 2: Student details */}
          {tab === 'register' && step === 2 && role === 'student' && (
            <form onSubmit={handleRegister} className={styles.form}>
              <button type="button" className={styles.backBtn} onClick={() => setStep(1)}>← Back</button>
              <h1 className={styles.formTitle}>Your details</h1>
              {error && <div className={styles.error}>{error}</div>}

              <div className={styles.field}>
                <label className={styles.label}>Education level</label>
                <select className="input" value={form.education_level} onChange={e => set('education_level', e.target.value)}>
                  <option value="secondary">Primary / Secondary (Grade 1–12)</option>
                  <option value="tertiary">Tertiary / University (Level 1–5)</option>
                </select>
              </div>

              {form.education_level === 'secondary' && (
                <div className={styles.field}>
                  <label className={styles.label}>Grade</label>
                  <div className="max-h-60 overflow-y-auto pr-1 space-y-3">
                    {['Primary', 'High School'].map(group => (
                      <div key={group}>
                        <p className="text-muted text-xs uppercase tracking-wide mb-2">{group}</p>
                        <div className="flex flex-wrap gap-2">
                          {GRADE_OPTIONS.filter(g => g.group === group).map(g => (
                            <button
                              key={g.value}
                              type="button"
                              onClick={() => set('grade_level', String(g.value))}
                              className={`px-3 py-1.5 rounded-lg border text-sm transition-all ${
                                form.grade_level === String(g.value)
                                  ? 'border-teal bg-teal/10 text-teal font-medium'
                                  : 'border-border text-muted hover:text-primary'
                              }`}
                            >
                              {g.label}
                            </button>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {isTertiary && (
                <div>
                  <div className={styles.field}>
                    <label className={styles.label}>Search for your subjects</label>
                    <input
                      type="text"
                      placeholder="By code or name (e.g. CSC411, Mathematics)"
                      value={form.subjectSearch}
                      onChange={e => set('subjectSearch', e.target.value)}
                      className="input"
                    />
                  </div>
                  {form.loadingSubjects ? (
                    <div className="py-4 text-center"><div className="w-6 h-6 border-2 border-teal/30 border-t-teal rounded-full animate-spin mx-auto" /></div>
                  ) : form.availableSubjects.length === 0 ? (
                    <p className="text-muted text-sm py-4 text-center">No subjects available yet.</p>
                  ) : (
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {filteredSubjects.map(s => {
                        const checked = form.selectedSubjects.includes(s.id);
                        return (
                          <button
                            key={s.id}
                            type="button"
                            onClick={() => {
                              if (checked) set('selectedSubjects', form.selectedSubjects.filter(id => id !== s.id));
                              else set('selectedSubjects', [...form.selectedSubjects, s.id]);
                            }}
                            className={`w-full text-left p-3 rounded-xl border transition-all ${checked ? 'border-teal bg-teal/5' : 'border-border hover:border-teal/30'}`}
                          >
                            <div className="flex justify-between">
                              <div>
                                <p className="text-primary text-sm font-medium">{s.name}</p>
                                <p className="text-muted text-xs">{s.code}</p>
                              </div>
                              <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${checked ? 'bg-teal border-teal' : 'border-border'}`}>
                                {checked && <span className="text-app text-xs font-bold">✓</span>}
                              </div>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  )}
                  {form.selectedSubjects.length > 0 && (
                    <div className="mt-3 p-3 bg-teal/5 border border-teal/20 rounded-xl">
                      <p className="text-teal text-xs font-semibold mb-2">Selected ({form.selectedSubjects.length}):</p>
                      <div className="flex flex-wrap gap-2">
                        {form.selectedSubjects.map(id => {
                          const subj = form.availableSubjects.find(s => s.id === id);
                          return subj ? (
                            <span key={id} className="text-xs px-2 py-1 bg-teal/10 border border-teal/30 text-teal rounded-lg">
                              {subj.code} – {subj.name}
                            </span>
                          ) : null;
                        })}
                      </div>
                    </div>
                  )}
                </div>
              )}

              <button type="submit" className={`btn btn-primary ${styles.submitBtn}`} disabled={loading}>
                {loading ? 'Creating account…' : 'Create Account'}
              </button>
            </form>
          )}

          {/* REGISTER - Step 2: Teacher subjects */}
          {tab === 'register' && step === 2 && role === 'teacher' && (
            <form onSubmit={handleRegister} className={styles.form}>
              <button type="button" className={styles.backBtn} onClick={() => setStep(1)}>← Back</button>
              <h1 className={styles.formTitle}>Your subjects</h1>
              {error && <div className={styles.error}>{error}</div>}
              <p className={styles.helpText}>Add the subjects you teach. You can add more later.</p>
              <div className={styles.subjectAdder}>
                <input
                  className="input"
                  placeholder="Subject name (e.g. Mathematics)"
                  value={teacherSubjectName}
                  onChange={e => setTeacherSubjectName(e.target.value)}
                />
                <select className="input" style={{ width: 140 }} value={teacherSubjectGrade} onChange={e => setTeacherSubjectGrade(e.target.value)}>
                  {[8,9,10,11,12].map(g => <option key={g} value={g}>Grade {g}</option>)}
                </select>
                <button type="button" className="btn btn-ghost" onClick={addTeacherSubject}>Add</button>
              </div>
              <div className={styles.subjectTags}>
                {teacherSubjects.map((s, i) => (
                  <div key={i} className={styles.subjectTag}>
                    {s.name} <span className={styles.tagGrade}>G{s.grade_level}</span>
                    <button type="button" onClick={() => removeTeacherSubject(i)}>✕</button>
                  </div>
                ))}
              </div>
              <button type="submit" className={`btn btn-primary ${styles.submitBtn}`} disabled={loading}>
                {loading ? 'Creating account…' : 'Create Account'}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}