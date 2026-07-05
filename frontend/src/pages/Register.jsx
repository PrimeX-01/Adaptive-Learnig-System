import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { registerUser } from '../services/auth';
import api from '../services/api';   // <-- use configured axios instance
import styles from './Auth.module.css';

const INITIAL_FORM = {
  first_name: '',
  last_name: '',
  email: '',
  password: '',
  confirm_password: '',
};

const ROLES = [
  {
    key: 'student',
    icon: '📚',
    title: 'Student',
    desc: 'Learn at your own pace with AI-powered adaptive tutoring.',
  },
  {
    key: 'teacher',
    icon: '🍎',
    title: 'Teacher',
    desc: 'Manage classes, create content, and guide your students.',
  },
  {
    key: 'lecturer',
    icon: '🎓',
    title: 'Lecturer',
    desc: 'For tertiary institutions — teach courses and track progress.',
  },
];

function Field({ label, children, hint }) {
  return (
    <div className={styles.field}>
      <label className={styles.fieldLabel || styles.label}>{label}</label>
      {children}
      {hint && <p className={styles.fieldHint}>{hint}</p>}
    </div>
  );
}

export default function Register() {
  const navigate = useNavigate();

  const [step, setStep] = useState(1);
  const [role, setRole] = useState(null);
  const [form, setForm] = useState(INITIAL_FORM);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Role‑specific state (students)
  const [educationLevel, setEducationLevel] = useState('school');
  const [grade, setGrade] = useState('');
  const [classId, setClassId] = useState('');
  const [facultyId, setFacultyId] = useState('');
  const [programmeId, setProgrammeId] = useState('');
  const [level, setLevel] = useState('');
  const [learningStyle, setLearningStyle] = useState('reading');
  const [selectedPclIds, setSelectedPclIds] = useState([]);

  // Teacher / lecturer state (unchanged)
  const [teacherSubjects, setTeacherSubjects] = useState([{ name: '', grade_level: '' }]);
  const [selectedLecturerPclIds, setSelectedLecturerPclIds] = useState([]);

  // Fetched data
  const [subjects, setSubjects] = useState([]);
  const [faculties, setFaculties] = useState([]);
  const [classes, setClasses] = useState([]);
  const [programmes, setProgrammes] = useState([]);
  const [programmeCourses, setProgrammeCourses] = useState([]);

  // ── Fetch subjects & faculties on mount ────────────────────────
  useEffect(() => {
    api.get('/api/admin/subjects-public')
      .then(res => setSubjects(Array.isArray(res.data) ? res.data : []))
      .catch(() => setSubjects([]));

    api.get('/api/admin/faculties-public')
      .then(res => setFaculties(Array.isArray(res.data) ? res.data : []))
      .catch(() => setFaculties([]));
  }, []);

  // Fetch classes when grade changes (school)
  useEffect(() => {
    if (educationLevel !== 'school' || !grade) {
      setClasses([]);
      return;
    }
    api.get('/api/admin/classes-public', { params: { grade_id: grade } })
      .then(res => setClasses(Array.isArray(res.data) ? res.data : []))
      .catch(() => setClasses([]));
  }, [grade, educationLevel]);

  // Fetch programmes when faculty changes (tertiary)
  useEffect(() => {
    if (educationLevel !== 'tertiary' || !facultyId) {
      setProgrammes([]);
      return;
    }
    api.get('/api/admin/programmes-public', { params: { faculty_id: facultyId } })
      .then(res => setProgrammes(Array.isArray(res.data) ? res.data : []))
      .catch(() => setProgrammes([]));
  }, [facultyId, educationLevel]);

  // Fetch courses for selected programme + level (tertiary)
  useEffect(() => {
    if (educationLevel !== 'tertiary' || !programmeId || !level) {
      setProgrammeCourses([]);
      return;
    }
    api.get('/api/admin/courses-public', {
      params: { programme_id: programmeId, level: level }
    })
      .then(res => {
        // Backend returns { active_semester, courses: [...] }
        const courses = res.data?.courses || [];
        setProgrammeCourses(courses);
      })
      .catch(() => setProgrammeCourses([]));
  }, [programmeId, level, educationLevel]);

  // ── Field updaters ────────────────────────────────────────────
  const updateForm = (field, value) =>
    setForm(prev => ({ ...prev, [field]: value }));

  const togglePcl = (id) =>
    setSelectedPclIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );

  const updateTeacherSubject = (idx, field, value) =>
    setTeacherSubjects(prev => {
      const copy = [...prev];
      copy[idx] = { ...copy[idx], [field]: value };
      return copy;
    });

  const addTeacherSubject = () =>
    setTeacherSubjects(prev => [...prev, { name: '', grade_level: '' }]);

  const removeTeacherSubject = (idx) =>
    setTeacherSubjects(prev => prev.filter((_, i) => i !== idx));

  // ── Validation ────────────────────────────────────────────────
  const validateBasicInfo = () => {
    if (!form.first_name.trim() || !form.last_name.trim()) {
      return 'Please enter your full name.';
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      return 'Please enter a valid email address.';
    }
    if (form.password.length < 6) {
      return 'Password must be at least 6 characters.';
    }
    if (form.password !== form.confirm_password) {
      return 'Passwords do not match.';
    }
    return null;
  };

  const validateDetails = () => {
    if (role === 'student') {
      if (educationLevel === 'school') {
        if (!grade) return 'Please select your grade.';
        if (!classId) return 'Please select your class.';
      } else {
        if (!facultyId) return 'Please select your faculty.';
        if (!programmeId) return 'Please select your programme.';
        if (!level) return 'Please select your level.';
        if (selectedPclIds.length === 0) return 'Please select at least one course.';
      }
      return null;
    }
    if (role === 'teacher') {
      const valid = teacherSubjects.some(s => s.name.trim() && s.grade_level);
      if (!valid) return 'Please add at least one subject with a grade.';
      return null;
    }
    if (role === 'lecturer') {
      if (!facultyId) return 'Please select your faculty.';
      return null;
    }
    return null;
  };

  const handleSubmit = async () => {
    const payload = {
      first_name: form.first_name,
      last_name: form.last_name,
      email: form.email,
      password: form.password,
      role,
      education_level: educationLevel,
      learning_style: learningStyle,
    };

    if (role === 'student') {
      if (educationLevel === 'school') {
        payload.grade_id = Number(grade);
        payload.class_id = Number(classId);
      } else {
        payload.faculty_id   = Number(facultyId);
        payload.programme_id = Number(programmeId);
        payload.level        = Number(level);
        payload.course_pcl_ids = selectedPclIds;
      }
    } else if (role === 'teacher') {
      payload.class_subject_ids = []; // to be implemented
    } else if (role === 'lecturer') {
      payload.faculty_id = Number(facultyId);
      payload.pcl_ids = selectedLecturerPclIds;
    }

    setError('');
    setLoading(true);
    try {
      const result = await registerUser(payload);
      if (result.status === 'pending') {
        navigate('/waiting-approval', { replace: true });
      } else {
        navigate('/auth?registered=1', { replace: true });
      }
    } catch (err) {
      setError(err.message || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const nextStep = () => {
    if (step === 2) {
      const err = validateBasicInfo();
      if (err) { setError(err); return; }
    }
    if (step === 3) {
      const err = validateDetails();
      if (err) { setError(err); return; }
    }
    setError('');
    setStep(prev => prev + 1);
  };

  const prevStep = () => setStep(prev => prev - 1);

  // ─── Render Steps (all JSX is identical to previous version, using states from above) ──
  // (I'll keep the full JSX for completeness but it's the same UI as before)

  const renderStep1 = () => (
    <>
      <div className={styles.formHeader}>
        <h1 className={styles.formTitle}>Join SiveAdapt</h1>
        <p className={styles.formSub}>Choose your role to get started</p>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {ROLES.map(r => (
          <button
            key={r.key}
            type="button"
            onClick={() => setRole(r.key)}
            className={styles.tabBtn}
            style={{
              textAlign: 'left',
              padding: '1rem',
              border: role === r.key ? '2px solid var(--primary)' : '2px solid transparent',
              background: role === r.key ? 'var(--card-hover)' : 'transparent',
            }}
          >
            <span style={{ fontSize: '1.5rem', marginRight: '0.75rem' }}>{r.icon}</span>
            <div style={{ display: 'inline-block', verticalAlign: 'middle' }}>
              <strong>{r.title}</strong>
              <br />
              <small style={{ color: 'var(--text-secondary)' }}>{r.desc}</small>
            </div>
          </button>
        ))}
      </div>
      <button
        type="button"
        className={styles.submitBtn}
        disabled={!role}
        onClick={() => setStep(2)}
      >
        Continue →
      </button>
    </>
  );

  const renderStep2 = () => (
    <>
      <div className={styles.formHeader}>
        <h1 className={styles.formTitle}>Your details</h1>
        <p className={styles.formSub}>Let us know who you are</p>
      </div>
      <Field label="First Name">
        <input className={styles.input} type="text" value={form.first_name} onChange={e => updateForm('first_name', e.target.value)} required />
      </Field>
      <Field label="Last Name">
        <input className={styles.input} type="text" value={form.last_name} onChange={e => updateForm('last_name', e.target.value)} required />
      </Field>
      <Field label="Email">
        <input className={styles.input} type="email" value={form.email} onChange={e => updateForm('email', e.target.value)} required />
      </Field>
      <Field label="Password" hint="At least 6 characters">
        <input className={styles.input} type="password" value={form.password} onChange={e => updateForm('password', e.target.value)} required />
      </Field>
      <Field label="Confirm Password">
        <input className={styles.input} type="password" value={form.confirm_password} onChange={e => updateForm('confirm_password', e.target.value)} required />
      </Field>
      <div style={{ display: 'flex', gap: '0.75rem' }}>
        <button type="button" className={styles.submitBtn} onClick={prevStep} style={{ flex: 1, background: 'var(--card-hover)' }}>← Back</button>
        <button type="button" className={styles.submitBtn} onClick={nextStep} style={{ flex: 2 }}>Continue →</button>
      </div>
    </>
  );

  const renderStudentDetails = () => (
    <>
      <div className={styles.formHeader}>
        <h1 className={styles.formTitle}>Student details</h1>
        <p className={styles.formSub}>Tell us about your education level</p>
      </div>

      <Field label="Education Level">
        <div style={{ display: 'flex', gap: '1rem' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <input type="radio" value="school" checked={educationLevel === 'school'} onChange={() => setEducationLevel('school')} /> School
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <input type="radio" value="tertiary" checked={educationLevel === 'tertiary'} onChange={() => setEducationLevel('tertiary')} /> Tertiary
          </label>
        </div>
      </Field>

      {educationLevel === 'school' && (
        <>
          <Field label="Grade">
            <select className={styles.input} value={grade} onChange={e => { setGrade(e.target.value); setClassId(''); }}>
              <option value="">-- Select --</option>
              {Array.from({ length: 12 }, (_, i) => (
                <option key={i + 1} value={i + 1}>{i + 1}</option>
              ))}
            </select>
          </Field>
          {grade && (
            <Field label="Class">
              <select className={styles.input} value={classId} onChange={e => setClassId(e.target.value)}>
                <option value="">-- Select --</option>
                {classes.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </Field>
          )}
        </>
      )}

      {educationLevel === 'tertiary' && (
        <>
          <Field label="Faculty">
            <select className={styles.input} value={facultyId} onChange={e => {
              setFacultyId(e.target.value);
              setProgrammeId('');
              setLevel('');
            }}>
              <option value="">-- Select --</option>
              {faculties.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}
            </select>
          </Field>

          {facultyId && (
            <Field label="Programme">
              <select className={styles.input} value={programmeId} onChange={e => {
                setProgrammeId(e.target.value);
                setLevel('');
              }}>
                <option value="">-- Select --</option>
                {programmes.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </Field>
          )}

          {programmeId && (
            <Field label="Level">
              <select className={styles.input} value={level} onChange={e => setLevel(e.target.value)}>
                <option value="">-- Select --</option>
                {[1, 2, 3, 4, 5, 6].map(l => <option key={l} value={l}>{l}</option>)}
              </select>
            </Field>
          )}

          {programmeId && level && (
            <Field label="Courses this semester" hint="Select all you are taking">
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', maxHeight: '200px', overflowY: 'auto' }}>
                {programmeCourses.length === 0 && <p style={{ color: 'var(--text-secondary)' }}>Loading courses…</p>}
                {programmeCourses.map(pcl => (
                  <button
                    key={pcl.pcl_id}
                    type="button"
                    onClick={() => togglePcl(pcl.pcl_id)}
                    style={{
                      padding: '0.4rem 0.8rem',
                      border: '1px solid var(--border)',
                      borderRadius: '20px',
                      background: selectedPclIds.includes(pcl.pcl_id) ? 'var(--primary)' : 'transparent',
                      color: selectedPclIds.includes(pcl.pcl_id) ? '#fff' : 'var(--text)',
                      cursor: 'pointer',
                    }}
                  >
                    {pcl.course_name} ({pcl.course_code})
                  </button>
                ))}
              </div>
            </Field>
          )}
        </>
      )}

      <Field label="Preferred Learning Style (optional)">
        <select className={styles.input} value={learningStyle} onChange={e => setLearningStyle(e.target.value)}>
          <option value="reading">Reading/Writing</option>
          <option value="visual">Visual</option>
          <option value="auditory">Auditory</option>
          <option value="kinesthetic">Kinesthetic</option>
        </select>
      </Field>

      <div style={{ display: 'flex', gap: '0.75rem' }}>
        <button type="button" className={styles.submitBtn} onClick={prevStep} style={{ flex: 1, background: 'var(--card-hover)' }}>← Back</button>
        <button type="button" className={styles.submitBtn} onClick={nextStep} style={{ flex: 2 }}>Continue →</button>
      </div>
    </>
  );

  const renderTeacherDetails = () => (
    // … (keep existing code, unchanged)
    <>
      <div className={styles.formHeader}>
        <h1 className={styles.formTitle}>Teacher details</h1>
        <p className={styles.formSub}>Add the subjects you teach</p>
      </div>
      {teacherSubjects.map((subj, idx) => (
        <div key={idx} style={{ border: '1px solid var(--border)', borderRadius: '8px', padding: '1rem', marginBottom: '1rem', position: 'relative' }}>
          <Field label="Subject Name">
            <input className={styles.input} type="text" placeholder="e.g. Mathematics" value={subj.name} onChange={e => updateTeacherSubject(idx, 'name', e.target.value)} />
          </Field>
          <Field label="Grade Level">
            <select className={styles.input} value={subj.grade_level} onChange={e => updateTeacherSubject(idx, 'grade_level', e.target.value)}>
              <option value="">-- Select --</option>
              {Array.from({ length: 12 }, (_, i) => <option key={i+1} value={i+1}>{i+1}</option>)}
            </select>
          </Field>
          {teacherSubjects.length > 1 && (
            <button type="button" onClick={() => removeTeacherSubject(idx)} style={{ position: 'absolute', top: '0.5rem', right: '0.5rem', background: 'none', border: 'none', color: 'var(--error)', cursor: 'pointer' }}>✕</button>
          )}
        </div>
      ))}
      <button type="button" onClick={addTeacherSubject} style={{ background: 'none', border: '1px dashed var(--border)', padding: '0.5rem', width: '100%', cursor: 'pointer', borderRadius: '6px', marginBottom: '1rem' }}>
        + Add another subject
      </button>
      <div style={{ display: 'flex', gap: '0.75rem' }}>
        <button type="button" className={styles.submitBtn} onClick={prevStep} style={{ flex: 1, background: 'var(--card-hover)' }}>← Back</button>
        <button type="button" className={styles.submitBtn} onClick={nextStep} style={{ flex: 2 }}>Continue →</button>
      </div>
    </>
  );

  const renderLecturerDetails = () => (
    // … (keep existing code, unchanged)
    <>
      <div className={styles.formHeader}>
        <h1 className={styles.formTitle}>Lecturer details</h1>
        <p className={styles.formSub}>Select your faculty</p>
      </div>
      <Field label="Faculty">
        <select className={styles.input} value={facultyId} onChange={e => setFacultyId(e.target.value)}>
          <option value="">-- Select --</option>
          {faculties.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}
        </select>
      </Field>
      <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
        Course assignments will be configured by your administrator after approval.
      </p>
      <div style={{ display: 'flex', gap: '0.75rem' }}>
        <button type="button" className={styles.submitBtn} onClick={prevStep} style={{ flex: 1, background: 'var(--card-hover)' }}>← Back</button>
        <button type="button" className={styles.submitBtn} onClick={nextStep} style={{ flex: 2 }}>Continue →</button>
      </div>
    </>
  );

  const renderReview = () => (
    // … (keep existing code, unchanged)
    <>
      <div className={styles.formHeader}>
        <h1 className={styles.formTitle}>Review your details</h1>
        <p className={styles.formSub}>Make sure everything looks right</p>
      </div>
      <div style={{ background: 'var(--card-hover)', borderRadius: '8px', padding: '1rem', marginBottom: '1rem' }}>
        <p><strong>Role:</strong> {ROLES.find(r => r.key === role)?.title}</p>
        <p><strong>Name:</strong> {form.first_name} {form.last_name}</p>
        <p><strong>Email:</strong> {form.email}</p>
        {role === 'student' && (
          <>
            <p><strong>Education Level:</strong> {educationLevel}</p>
            {educationLevel === 'school' && (
              <>
                <p><strong>Grade:</strong> {grade}</p>
                <p><strong>Class:</strong> {classes.find(c => c.id === Number(classId))?.name || '—'}</p>
              </>
            )}
            {educationLevel === 'tertiary' && (
              <>
                <p><strong>Faculty:</strong> {faculties.find(f => f.id === Number(facultyId))?.name || '—'}</p>
                <p><strong>Programme:</strong> {programmes.find(p => p.id === Number(programmeId))?.name || '—'}</p>
                <p><strong>Level:</strong> {level}</p>
                <p><strong>Courses:</strong> {
                  programmeCourses
                    .filter(pcl => selectedPclIds.includes(pcl.pcl_id))
                    .map(pcl => pcl.course_name)
                    .join(', ') || 'None'
                }</p>
              </>
            )}
            <p><strong>Learning Style:</strong> {learningStyle}</p>
          </>
        )}
        {role === 'teacher' && (
          <div>
            <strong>Subjects:</strong>
            <ul>
              {teacherSubjects.filter(s => s.name && s.grade_level).map((s, i) => (
                <li key={i}>{s.name} (Grade {s.grade_level})</li>
              ))}
            </ul>
          </div>
        )}
        {role === 'lecturer' && (
          <p><strong>Faculty:</strong> {faculties.find(f => f.id === Number(facultyId))?.name || '—'}</p>
        )}
      </div>
      <button type="button" className={styles.submitBtn} onClick={handleSubmit} disabled={loading}>
        {loading && <span className={styles.spinnerInline} />}
        {loading ? 'Creating account…' : 'Create Account'}
      </button>
      <button type="button" className={styles.submitBtn} onClick={prevStep} style={{ marginTop: '0.5rem', background: 'var(--card-hover)' }}>← Back</button>
    </>
  );

  return (
    <div className={styles.page}>
      <div className={styles.orbs} aria-hidden="true">
        <div className={`${styles.orb} ${styles.orb1}`} />
        <div className={`${styles.orb} ${styles.orb2}`} />
      </div>

      <div className={styles.cardWrap}>
        <Link to="/" className={styles.logo}>Sive<em>Adapt</em></Link>

        <div className={styles.card}>
          <div className={styles.tabs}>
            <Link to="/auth" className={styles.tabBtn}>Sign in</Link>
            <button type="button" className={`${styles.tabBtn} ${styles.activeTab}`} disabled>Create account</button>
          </div>

          {error && (
            <div className={styles.errorBox}>
              <span className={styles.errorIcon}>⚠</span> {error}
            </div>
          )}

          <form className={styles.form} noValidate onSubmit={e => e.preventDefault()}>
            {step === 1 && renderStep1()}
            {step === 2 && renderStep2()}
            {step === 3 && role === 'student' && renderStudentDetails()}
            {step === 3 && role === 'teacher' && renderTeacherDetails()}
            {step === 3 && role === 'lecturer' && renderLecturerDetails()}
            {step === 4 && renderReview()}
          </form>

          <div style={{ display: 'flex', justifyContent: 'center', gap: '0.5rem', margin: '1rem 0' }}>
            {[1, 2, 3, 4].map(s => (
              <div
                key={s}
                style={{
                  width: '10px',
                  height: '10px',
                  borderRadius: '50%',
                  backgroundColor: s <= step ? 'var(--primary)' : 'var(--border)',
                }}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}