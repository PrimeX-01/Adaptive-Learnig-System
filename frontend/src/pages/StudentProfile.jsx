import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import PageShell from '../components/PageShell';
import api from '../services/api';

/* ─── VARK learning styles ───────────────────────────────────────── */
const LEARNING_STYLES = [
  { value:'visual',      label:'Visual',           icon:'👁️', desc:'Charts, diagrams, images and colour-coded notes' },
  { value:'auditory',    label:'Auditory',          icon:'🎧', desc:'Explanations, discussions and verbal repetition' },
  { value:'reading',     label:'Reading / Writing', icon:'📖', desc:'Text-based content, lists and written notes' },
  { value:'kinesthetic', label:'Kinesthetic',       icon:'🧪', desc:'Practice questions, examples and hands-on exercises' },
];

/* ─── Grade groups (same as Register.jsx) ────────────────────────── */
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

/* ─── Grade value → readable label ──────────────────────────────── */
function gradeLabel(v) {
  if (!v) return 'Not set';
  if (v <= 7)  return `Primary School — Grade ${v}`;
  if (v <= 12) return `High School — Grade ${v}`;
  if (v <= 17) return `Undergraduate — Level ${v - 12}`;
  if (v === 18) return 'Postgraduate — Masters';
  if (v === 19) return 'Postgraduate — PhD';
  return `Grade ${v}`;
}

/* ─── FCL level label ─────────────────────────────────────────────── */
const FCL_LABEL = (n) => {
  if (!n) return 'Not assessed yet';
  if (n <= 4)  return `Level ${n} — Foundation`;
  if (n <= 7)  return `Level ${n} — Developing`;
  if (n <= 10) return `Level ${n} — Proficient`;
  return `Level ${n} — Advanced`;
};

/* ─── Section wrapper ────────────────────────────────────────────── */
function Section({ title, children }) {
  return (
    <div className='card'>
      <div className='px-6 py-4 border-b border-border'>
        <h2 className='text-primary font-semibold text-sm'>{title}</h2>
      </div>
      <div className='px-6 py-5'>{children}</div>
    </div>
  );
}

/* ─── Input field ────────────────────────────────────────────────── */
function Field({ label, type='text', value, onChange, placeholder, disabled, hint }) {
  return (
    <div>
      <label className='block text-muted text-xs font-medium uppercase tracking-wide mb-1.5'>
        {label}
      </label>
      <input
        type={type} value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder} disabled={disabled}
        className={`w-full bg-app border border-border rounded-lg px-4 py-2.5 text-primary text-sm
          placeholder-muted/50 focus:outline-none focus:border-teal transition-colors
          ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      />
      {hint && <p className='text-muted text-xs mt-1'>{hint}</p>}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   STUDENT PROFILE PAGE
═══════════════════════════════════════════════════════════════════ */
export default function StudentProfile() {
  const nav = useNavigate();
  const sid = window.__studentId;

  /* ── Remote data ─────────────────────────────────────────────────── */
  const [profile,  setProfile]  = useState(null);
  const [subPerf,  setSubPerf]  = useState(null);
  const [loading,  setLoading]  = useState(true);
  const [saving,   setSaving]   = useState(false);
  const [saveMsg,  setSaveMsg]  = useState(null);

  /* ── Editable fields ─────────────────────────────────────────────── */
  const [fullName,      setFullName]      = useState('');
  const [username,      setUsername]      = useState('');
  const [email,         setEmail]         = useState('');
  const [age,           setAge]           = useState('');
  const [grade,         setGrade]         = useState('');   // ← NEW
  const [bio,           setBio]           = useState('');
  const [learningStyle, setLearningStyle] = useState('visual');
  const [profilePic,    setProfilePic]    = useState(null);

  /* ── Password fields ─────────────────────────────────────────────── */
  const [oldPw,     setOldPw]     = useState('');
  const [newPw,     setNewPw]     = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  const [pwMsg,     setPwMsg]     = useState(null);

  const fileInputRef = useRef(null);

  /* ── Load profile ────────────────────────────────────────────────── */
  useEffect(() => {
    if (!sid) return;
    Promise.all([
      api.get(`/api/students/${sid}/profile`),
      api.get(`/api/students/${sid}/subject-performance`),
    ]).then(([profRes, subRes]) => {
      const p = profRes.data;
      setProfile(p);
      setSubPerf(subRes.data);
      setFullName(p.name        || '');
      setUsername(p.username    || '');
      setEmail(p.email          || '');
      setAge(p.age              || '');
      setGrade(p.grade          || '');   // ← NEW
      setBio(p.bio              || '');
      setLearningStyle(p.preferred_learning_style || 'visual');
      setProfilePic(p.profile_picture || null);
    }).finally(() => setLoading(false));
  }, [sid]);

  /* ── Profile picture selection + compression ─────────────────────── */
  const handlePicSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) {
      setSaveMsg({ ok: false, text: 'Image must be under 2 MB.' });
      return;
    }
    const reader = new FileReader();
    reader.onload = (ev) => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        const MAX    = 200;
        const ratio  = Math.min(MAX / img.width, MAX / img.height);
        canvas.width  = Math.round(img.width  * ratio);
        canvas.height = Math.round(img.height * ratio);
        canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
        setProfilePic(canvas.toDataURL('image/jpeg', 0.8));
      };
      img.src = ev.target.result;
    };
    reader.readAsDataURL(file);
  };

  /* ── Save profile ────────────────────────────────────────────────── */
  const handleSave = async () => {
    setSaving(true); setSaveMsg(null);
    try {
      await api.patch(`/api/students/${sid}/profile`, {
  name:                    fullName.trim()  || null,
  username:                username.trim()  || null,  
  email:                   email.trim()     || null,
  age:                     age   ? parseInt(age)   : null,
  grade:                   grade ? parseInt(grade) : null,
  bio:                     bio.trim()       || null,  
  preferred_learning_style: learningStyle,
  profile_picture:         profilePic,
});
      if (window.__studentName !== undefined) window.__studentName = fullName;
      if (profilePic) window.__profilePic = profilePic;
      setSaveMsg({ ok: true, text: 'Profile saved successfully!' });
    } catch (err) {
      setSaveMsg({ ok: false, text: err?.response?.data?.detail || 'Save failed. Please try again.' });
    } finally {
      setSaving(false);
      setTimeout(() => setSaveMsg(null), 4000);
    }
  };

  /* ── Change password ─────────────────────────────────────────────── */
  const handlePasswordChange = async () => {
    if (newPw !== confirmPw) { setPwMsg({ ok:false, text:'Passwords do not match.' }); return; }
    if (newPw.length < 8)    { setPwMsg({ ok:false, text:'Password must be at least 8 characters.' }); return; }
    setPwMsg(null);
    try {
      await api.post('/api/auth/change-password', {
        student_id: sid, old_password: oldPw, new_password: newPw,
      });
      setPwMsg({ ok:true, text:'Password updated successfully!' });
      setOldPw(''); setNewPw(''); setConfirmPw('');
    } catch (err) {
      setPwMsg({ ok:false, text: err?.response?.data?.detail || 'Password change failed.' });
    } finally { setTimeout(() => setPwMsg(null), 4000); }
  };

  if (loading) return (
    <div className='min-h-screen bg-app flex items-center justify-center flex-col gap-4'>
      <div className='w-12 h-12 border-4 border-teal/30 border-t-teal rounded-full animate-spin' />
      <p className='text-muted text-sm'>Loading your profile…</p>
    </div>
  );

  const initials = fullName
    ? fullName.split(' ').map(n=>n[0]).join('').slice(0,2).toUpperCase()
    : '??';

  /* ══════════════════════════════════════════════════════════════════
     RENDER
  ══════════════════════════════════════════════════════════════════ */
  return (
    <PageShell title='My Profile' subtitle='Manage your personal information and preferences'>
      <div className='max-w-4xl mx-auto space-y-6'>

        {/* Save toast */}
        {saveMsg && (
          <div className={`px-4 py-3 rounded-xl border text-sm font-medium flex items-center gap-2
            ${saveMsg.ok
              ? 'bg-green-500/10 border-green-500/30 text-green-400'
              : 'bg-red-500/10  border-red-500/30  text-red-400'}`}>
            <span>{saveMsg.ok ? '✓' : '✕'}</span> {saveMsg.text}
          </div>
        )}

        {/* ════════════════════════════════════════════════════════════
            AVATAR + IDENTITY HEADER
        ════════════════════════════════════════════════════════════ */}
        <div className='card p-6'>
          <div className='flex items-start gap-6 flex-wrap'>

            {/* Profile picture */}
            <div className='flex flex-col items-center gap-3'>
              <div className='relative w-24 h-24'>
                {profilePic ? (
                  <img src={profilePic} alt='Profile'
                    className='w-24 h-24 rounded-full object-cover border-2 border-teal/40' />
                ) : (
                  <div className='w-24 h-24 rounded-full bg-teal/20 border-2 border-teal/40 flex items-center justify-center'>
                    <span className='text-teal text-2xl font-bold stat-number'>{initials}</span>
                  </div>
                )}
                <button onClick={() => fileInputRef.current?.click()}
                  className='absolute bottom-0 right-0 w-8 h-8 rounded-full bg-teal text-app flex items-center justify-center shadow-lg hover:bg-teal/80 transition-colors'
                  title='Change photo'>
                  <span className='text-sm'>📷</span>
                </button>
              </div>
              <button onClick={() => fileInputRef.current?.click()} className='text-teal text-xs hover:underline'>
                Change photo
              </button>
              {profilePic && (
                <button onClick={() => setProfilePic(null)} className='text-red-400 text-xs hover:underline'>
                  Remove photo
                </button>
              )}
              <input ref={fileInputRef} type='file' accept='image/png,image/jpeg,image/webp'
                className='hidden' onChange={handlePicSelect} />
              <p className='text-muted text-xs text-center'>PNG, JPG or WebP · max 2 MB</p>
            </div>

            {/* Name + stats summary */}
            <div className='flex-1 min-w-0'>
              <h1 className='text-primary text-2xl font-bold mb-0.5'>{fullName || 'Your Name'}</h1>
              <p className='text-muted text-sm mb-1'>@{username || 'username'} · {email || 'email@example.com'}</p>

              {/* ✅ NEW — Grade shown here */}
              {grade && (
                <p className='text-teal text-xs mb-4 flex items-center gap-1'>
                  <span>🎓</span> {gradeLabel(parseInt(grade))}
                </p>
              )}

              <div className='grid grid-cols-3 gap-4 mt-3'>
                <div className='bg-app border border-border rounded-lg p-3 text-center'>
                  <p className='stat-number text-teal text-xl font-bold'>
                    {subPerf?.overall?.avg_fcl || '—'}
                  </p>
                  <p className='text-muted text-xs mt-0.5'>Current FCL</p>
                  <p className='text-muted text-xs'>{FCL_LABEL(subPerf?.overall?.avg_fcl)}</p>
                </div>
                <div className='bg-app border border-border rounded-lg p-3 text-center'>
                  <p className='stat-number text-green-400 text-xl font-bold'>
                    {subPerf?.subjects?.length || 0}
                  </p>
                  <p className='text-muted text-xs mt-0.5'>Enrolled Subjects</p>
                  <button onClick={() => nav('/subjects')} className='text-teal text-xs hover:underline mt-0.5 block'>
                    Manage →
                  </button>
                </div>
                <div className='bg-app border border-border rounded-lg p-3 text-center'>
                  <p className='stat-number text-blue-400 text-xl font-bold'>
                    {subPerf?.overall?.avg_accuracy ? `${subPerf.overall.avg_accuracy}%` : '—'}
                  </p>
                  <p className='text-muted text-xs mt-0.5'>Overall Accuracy</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ════════════════════════════════════════════════════════════
            PERSONAL INFORMATION
        ════════════════════════════════════════════════════════════ */}
        <Section title='Personal Information'>
          <div className='grid grid-cols-2 gap-4 mb-4'>
            <Field label='Full Name'     value={fullName} onChange={setFullName} placeholder='Enter your full name' />
            <Field label='Username'      value={username} onChange={setUsername} placeholder='Your login username'
              hint='Used to log in to SiveAdapt' />
            <Field label='Email Address' type='email' value={email} onChange={setEmail} placeholder='student@example.com' />
            <Field label='Age'           type='number' value={age} onChange={setAge} placeholder='e.g. 20' />

            {/* ✅ NEW — Grade selector (full width, same grouped style as Register) */}
            <div className='col-span-2'>
              <label className='block text-muted text-xs font-medium uppercase tracking-wide mb-1.5'>
                Grade / Year Level
              </label>
              <select
                value={grade}
                onChange={e => setGrade(e.target.value)}
                className='w-full bg-app border border-border rounded-lg px-4 py-2.5 text-primary text-sm
                  focus:outline-none focus:border-teal transition-colors'
              >
                <option value=''>— Select your grade / year —</option>
                {GRADE_GROUPS.map(group => (
                  <optgroup key={group.group} label={group.group}>
                    {group.options.map(opt => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </optgroup>
                ))}
              </select>
              {grade && (
                <p className='text-teal text-xs mt-1 flex items-center gap-1'>
                  <span>🎓</span> {gradeLabel(parseInt(grade))}
                </p>
              )}
            </div>
          </div>

          {/* Bio */}
          <div>
            <label className='block text-muted text-xs font-medium uppercase tracking-wide mb-1.5'>
              Bio / About Me
            </label>
            <textarea
              value={bio} onChange={e => setBio(e.target.value)}
              placeholder='A short description about yourself, your goals, or interests…'
              rows={3}
              className='w-full bg-app border border-border rounded-lg px-4 py-2.5 text-primary text-sm
                placeholder-muted/50 focus:outline-none focus:border-teal transition-colors resize-none'
            />
          </div>
        </Section>

        {/* ════════════════════════════════════════════════════════════
            PREFERRED LEARNING STYLE (VARK)
        ════════════════════════════════════════════════════════════ */}
        <Section title='Preferred Learning Style'>
          <p className='text-muted text-xs mb-4'>
            This tells the AI Tutor how to present content to match the way you learn best.
            You can change this any time.
          </p>
          <div className='grid grid-cols-2 gap-3'>
            {LEARNING_STYLES.map(style => (
              <button key={style.value} onClick={() => setLearningStyle(style.value)}
                className={`p-4 rounded-xl border text-left transition-all ${
                  learningStyle === style.value
                    ? 'border-teal bg-teal/10'
                    : 'border-border hover:border-border/80 hover:bg-border/20'
                }`}>
                <div className='flex items-center gap-3 mb-1'>
                  <span className='text-xl'>{style.icon}</span>
                  <span className={`text-sm font-semibold ${learningStyle === style.value ? 'text-teal' : 'text-primary'}`}>
                    {style.label}
                  </span>
                  {learningStyle === style.value && <span className='ml-auto text-teal text-sm'>✓</span>}
                </div>
                <p className='text-muted text-xs leading-relaxed'>{style.desc}</p>
              </button>
            ))}
          </div>
        </Section>

        {/* ════════════════════════════════════════════════════════════
            MY SUBJECTS
        ════════════════════════════════════════════════════════════ */}
        <Section title='My Subjects'>
          {(subPerf?.subjects || []).length > 0 ? (
            <div className='space-y-2 mb-4'>
              {subPerf.subjects.map((s, i) => (
                <div key={s.subject_code}
                  className='flex items-center justify-between py-2 border-b border-border/50 last:border-0'>
                  <div className='flex items-center gap-3'>
                    <span className='w-2.5 h-2.5 rounded-full flex-shrink-0'
                      style={{ background: ['#00D4C8','#3B82F6','#8B5CF6','#F59E0B','#10B981'][i%5] }} />
                    <div>
                      <p className='text-primary text-sm font-medium'>{s.subject_name}</p>
                      <p className='text-muted text-xs'>{s.subject_code}</p>
                    </div>
                  </div>
                  <div className='flex items-center gap-3 text-xs'>
                    {s.fcl_level && <span className='stat-number text-teal'>FCL {s.fcl_level}</span>}
                    <span className={`font-medium ${
                      s.performance_label === 'Excellent' ? 'text-green-400' :
                      s.performance_label === 'Good'      ? 'text-amber-400' : 'text-red-400'
                    }`}>{s.performance_label}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className='text-muted text-sm mb-4'>You are not enrolled in any subjects yet.</p>
          )}
          <button onClick={() => nav('/subjects')} className='btn-ghost text-xs'>
            Manage subjects →
          </button>
        </Section>

        {/* ════════════════════════════════════════════════════════════
            ACCOUNT SETTINGS
        ════════════════════════════════════════════════════════════ */}
        <Section title='Account Settings'>
          <div className='space-y-3 mb-4'>
            <Field label='Email (login / contact)' type='email' value={email} onChange={setEmail}
              placeholder='student@example.com'
              hint='Your email is used to contact you and recover your account' />
            <Field label='Username (used to log in)' value={username} onChange={setUsername}
              placeholder='e.g. sipho_dlamini' />
          </div>
        </Section>

        {/* ════════════════════════════════════════════════════════════
            CHANGE PASSWORD
        ════════════════════════════════════════════════════════════ */}
        <Section title='Change Password'>
          {pwMsg && (
            <div className={`mb-4 px-4 py-2.5 rounded-lg border text-sm flex items-center gap-2
              ${pwMsg.ok
                ? 'bg-green-500/10 border-green-500/30 text-green-400'
                : 'bg-red-500/10  border-red-500/30  text-red-400'}`}>
              <span>{pwMsg.ok ? '✓' : '✕'}</span> {pwMsg.text}
            </div>
          )}
          <div className='space-y-3 mb-4'>
            <Field label='Current Password'    type='password' value={oldPw}     onChange={setOldPw}     placeholder='Enter current password' />
            <Field label='New Password'         type='password' value={newPw}     onChange={setNewPw}     placeholder='Min 8 characters' />
            <Field label='Confirm New Password' type='password' value={confirmPw} onChange={setConfirmPw} placeholder='Repeat new password' />
          </div>
          {confirmPw && (
            <p className={`text-xs mb-3 flex items-center gap-1 ${newPw === confirmPw ? 'text-green-400' : 'text-red-400'}`}>
              <span>{newPw === confirmPw ? '✓' : '✕'}</span>
              {newPw === confirmPw ? 'Passwords match' : 'Passwords do not match'}
            </p>
          )}
          <button onClick={handlePasswordChange} className='btn-ghost text-sm'>
            Update Password
          </button>
        </Section>

        {/* ── Sticky save bar ───────────────────────────────────────── */}
        <div className='flex items-center justify-between py-4 sticky bottom-0 bg-app/90 backdrop-blur border-t border-border px-1'>
          <p className='text-muted text-xs'>Changes are saved to your SiveAdapt account</p>
          <button onClick={handleSave} disabled={saving}
            className='btn-primary text-sm px-8 flex items-center gap-2'>
            {saving ? (
              <><div className='w-4 h-4 border-2 border-app/30 border-t-app rounded-full animate-spin' />Saving…</>
            ) : 'Save Profile'}
          </button>
        </div>

      </div>
    </PageShell>
  );
}