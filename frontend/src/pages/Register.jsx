import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../services/api';

/* ─── VARK questions ─────────────────────────────────────────────── */
const VARK_QUESTIONS = [
  { q: 'When learning something new I prefer to:', options: [
    { label:'Read about it', type:'R' }, { label:'Watch a diagram or video', type:'V' },
    { label:'Listen to an explanation', type:'A' }, { label:'Try it hands-on', type:'K' }]},
  { q: 'When stuck on a problem I:', options: [
    { label:'Re-read the instructions', type:'R' }, { label:'Look for a chart', type:'V' },
    { label:'Ask someone to explain it', type:'A' }, { label:'Try different approaches', type:'K' }]},
  { q: 'I remember information best when I:', options: [
    { label:'Write it down', type:'R' }, { label:'See a mind map', type:'V' },
    { label:'Hear it aloud', type:'A' }, { label:'Do a practice activity', type:'K' }]},
  { q: 'My ideal study session includes:', options: [
    { label:'Reading notes', type:'R' }, { label:'Reviewing diagrams', type:'V' },
    { label:'Listening to recordings', type:'A' }, { label:'Practising problems', type:'K' }]},
  { q: 'I recall lessons mainly through:', options: [
    { label:'Words and sentences', type:'R' }, { label:'Images and layouts', type:'V' },
    { label:'Sounds and voices', type:'A' }, { label:'What I did or made', type:'K' }]},
];

/* ─── Grade options grouped by education level ───────────────────── */
// Stored as integers in DB: Primary 1-7, High School 8-12,
// Undergraduate 13-17 (Level 1-5), Masters=18, PhD=19
const GRADE_GROUPS = [
  {
    group: 'Primary School',
    options: [1,2,3,4,5,6,7].map(n => ({ value: n, label: `Grade ${n}` })),
  },
  {
    group: 'High School',
    options: [8,9,10,11,12].map(n => ({ value: n, label: `Grade ${n}` })),
  },
  {
    group: 'Tertiary — Undergraduate',
    options: [1,2,3,4,5].map(n => ({ value: n + 12, label: `Level ${n}` })),
  },
  {
    group: 'Tertiary — Postgraduate',
    options: [
      { value: 18, label: 'Masters' },
      { value: 19, label: 'PhD'     },
    ],
  },
];

/* ─── Helper: grade value → readable label ───────────────────────── */
export function gradeLabel(v) {
  if (!v) return '';
  if (v <= 7)  return `Primary — Grade ${v}`;
  if (v <= 12) return `High School — Grade ${v}`;
  if (v <= 17) return `Undergraduate — Level ${v - 12}`;
  if (v === 18) return 'Postgraduate — Masters';
  if (v === 19) return 'Postgraduate — PhD';
  return `Grade ${v}`;
}

/* ═══════════════════════════════════════════════════════════════════
   REGISTER PAGE
═══════════════════════════════════════════════════════════════════ */
export default function Register() {
  const [step,         setStep]   = useState(1);
  const [form,         setForm]   = useState({
    name: '', email: '', password: '', confirm_password: '', grade: '',
    preferred_modality: 'text', feedback_style: 'detailed', session_length_minutes: 30,
  });
  const [varkAnswers,  setVark]   = useState({});
  const [availSubjects,setAvail]  = useState([]);
  const [subjectsLoading, setSubjectsLoading] = useState(false);
  const [enrollments,  setEnroll] = useState([]);
  const [lookupStatus, setLookup] = useState({});
  const [error,        setError]  = useState('');
  const [loading,      setLoading] = useState(false);
  const nav = useNavigate();

  /* ── Load subjects when reaching step 3 ─────────────────────────── */
  useEffect(() => {
    if (step === 3) {
      setSubjectsLoading(true);
      
      api.get('/api/subjects/available')
        .then(r => setAvail(r.data))
        .catch(() => setAvail([]))
        .finally(() => setSubjectsLoading(false));
    }
  }, [step]);

  function setField(k, v) { setForm(f => ({ ...f, [k]: v })); }

  /* ── Step 1 validation ───────────────────────────────────────────── */
  function validateStep1() {
    if (!form.name.trim())    { setError('Full name is required.');          return false; }
    if (!form.email.trim())   { setError('Email address is required.');       return false; }
    if (!form.password)       { setError('Password is required.');            return false; }
    if (form.password.length < 8) { setError('Password must be at least 8 characters.'); return false; }
    if (form.password !== form.confirm_password) { setError('Passwords do not match.'); return false; }
    if (!form.grade)          { setError('Please select your grade / year.');  return false; }
    setError('');
    return true;
  }

  /* ── VARK scoring ────────────────────────────────────────────────── */
  function computeVARK() {
    const scores = { V:0, A:0, R:0, K:0 };
    Object.values(varkAnswers).forEach(t => { if (scores[t] !== undefined) scores[t]++; });
    const top = Object.entries(scores).sort((a,b) => b[1]-a[1])[0][0];
    return { scores, modality: { V:'visual', A:'audio', R:'text', K:'text' }[top] };
  }

  /* ── Subject toggle / teacher lookup ────────────────────────────── */
  function toggleSubject(code) {
    setEnroll(e => e.find(x => x.subject_code === code)
      ? e.filter(x => x.subject_code !== code)
      : [...e, { subject_code: code, teacher_email: '', teacher_id: null }]);
  }

  function updateEnrollField(code, field, value) {
    setEnroll(e => e.map(x => x.subject_code === code ? { ...x, [field]: value } : x));
  }

  async function lookupTeacher(code, email) {
    if (!email.trim()) return;
    setLookup(s => ({ ...s, [code]: 'loading' }));
    try {
      const { data } = await api.get(
        `/api/subjects/teacher-lookup?email=${encodeURIComponent(email)}`
      );
      updateEnrollField(code, 'teacher_id',   data.teacher_id);
      updateEnrollField(code, 'teacher_name', data.teacher_name);
      setLookup(s => ({ ...s, [code]: 'found' }));
    } catch {
      setLookup(s => ({ ...s, [code]: 'error' }));
    }
  }

  /* ── Final submit ────────────────────────────────────────────────── */
  async function handleSubmit() {
    setLoading(true); setError('');
    const { modality } = computeVARK();
    const subject_enrollments = enrollments.map(e => ({
      subject_code: e.subject_code,
      teacher_id:   e.teacher_id || null,
    }));
    try {
      await api.post('/api/auth/register', {
        ...form,
        grade:              parseInt(form.grade),
        preferred_modality: modality,
        subject_enrollments,
      });
      nav('/login');
    } catch (err) {
      setError(err?.response?.data?.detail || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  /* ══════════════════════════════════════════════════════════════════
     RENDER
  ══════════════════════════════════════════════════════════════════ */
  return (
    <div className='min-h-screen bg-app flex items-center justify-center px-4 py-8'>
      <div className='absolute inset-0 overflow-hidden pointer-events-none'>
        <div className='absolute top-1/4 left-1/2 -translate-x-1/2 w-96 h-96 bg-teal/5 rounded-full blur-3xl' />
      </div>

      <div className='relative w-full max-w-lg'>

        {/* Brand */}
        <div className='text-center mb-6'>
          <div className='inline-flex w-12 h-12 rounded-xl bg-teal/10 border border-teal/30 items-center justify-center mb-3'>
            <span className='text-teal font-bold text-lg'>SA</span>
          </div>
          <h1 className='text-primary text-xl font-bold'>SiveAdapt</h1>
          <p className='text-muted text-xs mt-0.5'>University of Eswatini</p>
        </div>

        {/* Step indicator */}
        <div className='flex items-center gap-2 mb-6 justify-center'>
          {['Account', 'Learning Style', 'Subjects'].map((label, i) => {
            const s = i + 1;
            return (
              <div key={s} className='flex items-center gap-2'>
                <div className='flex items-center gap-1.5'>
                  <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all
                    ${step >= s ? 'bg-teal text-app' : 'bg-card border border-border text-muted'}`}>
                    {step > s ? '✓' : s}
                  </div>
                  <span className={`text-xs hidden sm:block ${step === s ? 'text-teal font-medium' : 'text-muted'}`}>
                    {label}
                  </span>
                </div>
                {s < 3 && <div className={`w-8 h-0.5 ${step > s ? 'bg-teal' : 'bg-border'}`} />}
              </div>
            );
          })}
        </div>

        <div className='card p-8'>
          {error && (
            <div className='mb-4 px-3 py-2.5 bg-red-500/10 border border-red-500/30 rounded-lg
              flex items-center gap-2 text-red-400 text-sm'>
              <span>⚠</span> {error}
            </div>
          )}

          {/* ══════════════════════════════════════════════════════════
              STEP 1 — Basic Info
          ══════════════════════════════════════════════════════════ */}
          {step === 1 && (
            <div>
              <h2 className='text-primary font-bold text-xl mb-1'>Create your account</h2>
              <p className='text-muted text-sm mb-6'>Step 1 of 3 — Basic information</p>

              <div className='space-y-4'>
                {/* Full Name */}
                <div>
                  <label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>Full Name</label>
                  <input type='text' value={form.name} onChange={e => setField('name', e.target.value)}
                    placeholder='e.g. Sipho Dlamini'
                    className='w-full bg-input border border-border rounded-lg px-4 py-2.5 text-primary text-sm
                      focus:border-teal/60 focus:ring-1 focus:ring-teal/30 focus:outline-none' />
                </div>

                {/* Email */}
                <div>
                  <label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>Email Address</label>
                  <input type='email' value={form.email} onChange={e => setField('email', e.target.value)}
                    placeholder='you@example.com'
                    className='w-full bg-input border border-border rounded-lg px-4 py-2.5 text-primary text-sm
                      focus:border-teal/60 focus:ring-1 focus:ring-teal/30 focus:outline-none' />
                </div>

                {/* Password */}
                <div>
                  <label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>Password</label>
                  <input type='password' value={form.password} onChange={e => setField('password', e.target.value)}
                    placeholder='Min 8 characters'
                    className='w-full bg-input border border-border rounded-lg px-4 py-2.5 text-primary text-sm
                      focus:border-teal/60 focus:ring-1 focus:ring-teal/30 focus:outline-none' />
                </div>

                {/* Confirm Password */}
                <div>
                  <label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>Confirm Password</label>
                  <input type='password' value={form.confirm_password} onChange={e => setField('confirm_password', e.target.value)}
                    placeholder='Repeat password'
                    className='w-full bg-input border border-border rounded-lg px-4 py-2.5 text-primary text-sm
                      focus:border-teal/60 focus:ring-1 focus:ring-teal/30 focus:outline-none' />
                  {form.confirm_password && (
                    <p className={`text-xs mt-1 flex items-center gap-1 ${form.password === form.confirm_password ? 'text-green-400' : 'text-red-400'}`}>
                      <span>{form.password === form.confirm_password ? '✓' : '✕'}</span>
                      {form.password === form.confirm_password ? 'Passwords match' : 'Passwords do not match'}
                    </p>
                  )}
                </div>

                {/* Grade grouped selector */}
                <div>
                  <label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>
                    Grade / Year Level
                  </label>
                  <select
                    value={form.grade}
                    onChange={e => setField('grade', e.target.value)}
                    className='w-full bg-input border border-border rounded-lg px-4 py-2.5 text-primary text-sm
                      focus:border-teal/60 focus:ring-1 focus:ring-teal/30 focus:outline-none'
                  >
                    <option value=''>— Select your grade / year —</option>
                    {GRADE_GROUPS.map(group => (
                      <optgroup key={group.group} label={group.group}>
                        {group.options.map(opt => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </optgroup>
                    ))}
                  </select>
                  {form.grade && (
                    <p className='text-teal text-xs mt-1'>
                      ✓ {gradeLabel(parseInt(form.grade))}
                    </p>
                  )}
                </div>
              </div>

              <button
                onClick={() => { if (validateStep1()) setStep(2); }}
                className='w-full btn-primary mt-6 py-2.5'
              >
                Next: Learning Style →
              </button>

              <p className='text-center text-muted text-sm mt-5'>
                Already have an account?{' '}
                <Link to='/login' className='text-teal hover:underline'>Sign in</Link>
              </p>
            </div>
          )}

          {/* ══════════════════════════════════════════════════════════
              STEP 2 — VARK
          ══════════════════════════════════════════════════════════ */}
          {step === 2 && (
            <div>
              <h2 className='text-primary font-bold text-xl mb-1'>Learning Style</h2>
              <p className='text-muted text-sm mb-6'>Step 2 of 3 — How do you learn best? (VARK assessment)</p>
              <div className='space-y-6'>
                {VARK_QUESTIONS.map((q, qi) => (
                  <div key={qi}>
                    <p className='text-primary text-sm font-medium mb-3'>{qi+1}. {q.q}</p>
                    <div className='space-y-2'>
                      {q.options.map(opt => (
                        <button key={opt.type} onClick={() => setVark(a => ({ ...a, [qi]: opt.type }))}
                          className={`w-full text-left px-4 py-2.5 rounded-lg border text-sm transition-colors
                            ${varkAnswers[qi] === opt.type
                              ? 'border-teal bg-teal/10 text-teal font-medium'
                              : 'border-border text-muted hover:border-teal/40 hover:text-primary'}`}>
                          {opt.label}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
              <div className='flex gap-3 mt-6'>
                <button onClick={() => setStep(1)} className='btn-ghost flex-1'>← Back</button>
                <button
                  onClick={() => setStep(3)}
                  disabled={Object.keys(varkAnswers).length < 5}
                  className='btn-primary flex-1 disabled:opacity-50'
                >
                  Next: Subjects →
                </button>
              </div>
            </div>
          )}

          {/* ══════════════════════════════════════════════════════════
              STEP 3 — Subject Enrollment
 */}
          {step === 3 && (
            <div>
              <h2 className='text-primary font-bold text-xl mb-1'>Your Subjects</h2>
              <p className='text-muted text-sm mb-6'>Step 3 of 3 — Select your subjects and optionally link your teacher</p>

              {subjectsLoading ? (
                <div className='py-8 text-center'>
                  <div className='w-6 h-6 border-2 border-teal/30 border-t-teal rounded-full animate-spin mx-auto mb-2' />
                  <p className='text-muted text-sm'>Loading subjects…</p>
                </div>
              ) : availSubjects.length === 0 ? (
                <div className='py-8 text-center'>
                  <span className='text-3xl block mb-2'>📚</span>
                  <p className='text-muted text-sm'>No subjects available yet. You can enrol from your profile after registering.</p>
                </div>
              ) : (
                <div className='space-y-3 mb-4 max-h-80 overflow-y-auto pr-1'>
                  {availSubjects.map(subj => {
                    const enrolled = enrollments.find(e => e.subject_code === subj.code);
                    return (
                      <div key={subj.code}
                        className={`rounded-xl border transition-colors ${enrolled ? 'border-teal/40 bg-teal/5' : 'border-border'}`}>
                        <button onClick={() => toggleSubject(subj.code)}
                          className='w-full flex items-center justify-between px-4 py-3'>
                          <div className='text-left'>
                            <div className='text-primary text-sm font-medium'>{subj.name}</div>
                            <div className='text-muted text-xs'>{subj.description}</div>
                          </div>
                          <div className={`w-5 h-5 rounded border flex items-center justify-center flex-shrink-0 ml-3 transition-colors
                            ${enrolled ? 'bg-teal border-teal text-app text-xs' : 'border-border'}`}>
                            {enrolled && '✓'}
                          </div>
                        </button>

                        {enrolled && (
                          <div className='px-4 pb-3 border-t border-border/50'>
                            <p className='text-muted text-xs mb-2 mt-2'>
                              Teacher email <span className='text-muted/60'>(optional — add later from profile)</span>:
                            </p>
                            <div className='flex gap-2'>
                              <input type='email'
                                value={enrolled.teacher_email || ''}
                                placeholder='teacher@school.ac.sz'
                                onChange={e => updateEnrollField(subj.code, 'teacher_email', e.target.value)}
                                className='flex-1 bg-input border border-border rounded-lg px-3 py-1.5 text-primary text-xs
                                  focus:border-teal/60 focus:outline-none' />
                              <button
                                onClick={() => lookupTeacher(subj.code, enrolled.teacher_email || '')}
                                className='btn-ghost text-xs py-1.5 px-3'>
                                {lookupStatus[subj.code] === 'loading' ? '…' : 'Find'}
                              </button>
                            </div>
                            {lookupStatus[subj.code] === 'found' &&
                              <p className='text-green-400 text-xs mt-1'>✓ Teacher linked: {enrolled.teacher_name}</p>}
                            {lookupStatus[subj.code] === 'error' &&
                              <p className='text-red-400 text-xs mt-1'>No teacher found with that email. You can add them later.</p>}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              <p className='text-muted text-xs mb-4'>
                You can enrol in more subjects or update teacher links anytime from My Subjects.
              </p>

              <div className='flex gap-3'>
                <button onClick={() => setStep(2)} className='btn-ghost flex-1'>← Back</button>
                <button
                  onClick={handleSubmit}
                  disabled={loading || enrollments.length === 0}
                  className='btn-primary flex-1 disabled:opacity-50 flex items-center justify-center gap-2'
                >
                  {loading
                    ? <><div className='w-4 h-4 border-2 border-app/30 border-t-app rounded-full animate-spin' />Creating…</>
                    : 'Create Account'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}