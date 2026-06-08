import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../services/api';

/* ─── VARK Questions (only for students) ───────────────────────── */
const VARK_QUESTIONS = [
  { q:'When learning something new, you prefer to:',
    options:[{label:'Watch a video or look at diagrams',style:'visual'},{label:'Listen to someone explain it',style:'auditory'},{label:'Read through notes or a textbook',style:'reading'},{label:'Try it yourself hands-on',style:'kinesthetic'}] },
  { q:'When you need directions to a new place, you prefer:',
    options:[{label:'A map or visual guide',style:'visual'},{label:'Someone to tell you verbally',style:'auditory'},{label:'Written step-by-step instructions',style:'reading'},{label:'Just start walking and figure it out',style:'kinesthetic'}] },
  { q:'When you remember something, you usually remember it by:',
    options:[{label:'A picture or image in your mind',style:'visual'},{label:'Hearing it said out loud',style:'auditory'},{label:'Reading it again',style:'reading'},{label:'Doing or experiencing it',style:'kinesthetic'}] },
  { q:'When studying for a test, you find it most helpful to:',
    options:[{label:'Draw diagrams and colour-code notes',style:'visual'},{label:'Read notes aloud or record yourself',style:'auditory'},{label:'Re-read and rewrite your notes',style:'reading'},{label:'Practice with exercises and examples',style:'kinesthetic'}] },
  { q:'You understand a concept best when:',
    options:[{label:'You can see it shown visually',style:'visual'},{label:'It is explained in conversation',style:'auditory'},{label:'You read a detailed explanation',style:'reading'},{label:'You can apply it to a real situation',style:'kinesthetic'}] },
];

/* ─── Grade options for teacher selection (by education level) ─── */
const TEACHER_LEVELS = [
  { level: 'Primary',     grades: [1,2,3,4,5,6,7], label: 'Primary School (Grades 1–7)' },
  { level: 'High School', grades: [8,9,10,11,12],   label: 'High School (Grades 8–12)' },
  { level: 'Undergraduate', grades: [13,14,15,16,17], label: 'Undergraduate (Levels 1–5)' },
  { level: 'Postgraduate', grades: [18,19],         label: 'Postgraduate (Masters, PhD)' },
];

/* ─── Student grade options (full range) ───────────────────────── */
const GRADE_OPTIONS = [
  // Primary 1–7
  { value: 1,  label: 'Grade 1',   group: 'Primary' },
  { value: 2,  label: 'Grade 2',   group: 'Primary' },
  { value: 3,  label: 'Grade 3',   group: 'Primary' },
  { value: 4,  label: 'Grade 4',   group: 'Primary' },
  { value: 5,  label: 'Grade 5',   group: 'Primary' },
  { value: 6,  label: 'Grade 6',   group: 'Primary' },
  { value: 7,  label: 'Grade 7',   group: 'Primary' },
  // High School 8–12
  { value: 8,  label: 'Grade 8',   group: 'High School' },
  { value: 9,  label: 'Grade 9',   group: 'High School' },
  { value: 10, label: 'Grade 10',  group: 'High School' },
  { value: 11, label: 'Grade 11',  group: 'High School' },
  { value: 12, label: 'Grade 12',  group: 'High School' },
  // Tertiary Level 1–5 (13–17)
  { value: 13, label: 'Level 1',   group: 'Tertiary' },
  { value: 14, label: 'Level 2',   group: 'Tertiary' },
  { value: 15, label: 'Level 3',   group: 'Tertiary' },
  { value: 16, label: 'Level 4',   group: 'Tertiary' },
  { value: 17, label: 'Level 5',   group: 'Tertiary' },
  // Masters & PhD
  { value: 18, label: 'Masters',   group: 'Postgraduate' },
  { value: 19, label: 'PhD',       group: 'Postgraduate' },
];

const SUBJECT_CODE_SUGGESTIONS = [
  'MATH','SCI','ENG','SOC','CS','PHY','CHEM','BIO',
  'HIST','GEO','ART','MUS','PE','ECO','ACC','BUS',
];

/* ─── Stepper ────────────────────────────────────────────────── */
function Stepper({ steps, current }) {
  return (
    <div className='flex items-center justify-center gap-2 mb-8'>
      {steps.map((label, i) => (
        <div key={i} className='flex items-center gap-2'>
          <div className={`flex items-center gap-2 ${i<=current?'text-teal':'text-muted'}`}>
            <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-all ${i<current?'bg-teal border-teal text-app':i===current?'border-teal text-teal':'border-border text-muted'}`}>
              {i<current?'✓':i+1}
            </div>
            <span className='text-xs hidden sm:inline'>{label}</span>
          </div>
          {i<steps.length-1&&<div className={`w-8 h-px ${i<current?'bg-teal':'bg-border'}`}/>}
        </div>
      ))}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   REGISTER PAGE
═══════════════════════════════════════════════════════════════ */
export default function Register() {
  const nav = useNavigate();
  const [step, setStep] = useState(0);

  /* ── Account ─────────────────────────────────────────────────── */
  const [name,      setName]      = useState('');
  const [email,     setEmail]     = useState('');
  const [password,  setPassword]  = useState('');
  const [confirm,   setConfirm]   = useState('');
  const [isTeacher, setIsTeacher] = useState(false);

  /* ── Student ─────────────────────────────────────────────────── */
  const [grade,            setGrade]            = useState('');
  const [availableSubjects,setAvailableSubjects] = useState([]);
  const [selectedSubjects, setSelectedSubjects]  = useState([]);
  const [subjectSearch,    setSubjectSearch]    = useState(''); // NEW: search filter
  const [autoEnrolled,     setAutoEnrolled]     = useState([]);
  const [loadingSubjects,  setLoadingSubjects]  = useState(false);

  /* ── Teacher — creates a subject, selects specific grades ────── */
  const [teachSubjectName, setTeachSubjectName] = useState('');
  const [teachSubjectCode, setTeachSubjectCode] = useState('');
  const [teacherLevel, setTeacherLevel] = useState('Primary');
  const [selectedGrades, setSelectedGrades] = useState([]);
  const [showCodeSuggestions, setShowCodeSuggestions] = useState(false);

  /* ── VARK (students only) ───────────────────────────────────── */
  const [varkAnswers, setVarkAnswers] = useState({});

  /* ── UI ──────────────────────────────────────────────────────── */
  const [error,      setError]      = useState('');
  const [submitting, setSubmitting] = useState(false);

  const isTertiary = parseInt(grade) >= 13;

  const studentSteps = isTertiary
    ? ['Account','Grade','Subjects','Learning Style']
    : ['Account','Grade','Learning Style'];
  const teacherSteps = ['Account','Your Subject & Grades'];
  const steps = isTeacher ? teacherSteps : studentSteps;

  useEffect(() => {
    if (!grade) return;
    if (isTertiary && step === 2) {
      setLoadingSubjects(true);
      api.get(`/api/subjects/available`)
        .then(r => setAvailableSubjects(r.data || []))
        .catch(() => setAvailableSubjects([]))
        .finally(() => setLoadingSubjects(false));
    } else if (!isTertiary && step === 1) {
      api.get(`/api/subjects/for-grade/${grade}`)
        .then(r => setAutoEnrolled(r.data || []))
        .catch(() => setAutoEnrolled([]));
    }
  }, [grade, step, isTertiary]);

  const currentLevelGrades = TEACHER_LEVELS.find(l => l.level === teacherLevel)?.grades || [];
  useEffect(() => {
    setSelectedGrades(prev => prev.filter(g => currentLevelGrades.includes(g)));
  }, [teacherLevel, currentLevelGrades]);

  function validate() {
    setError('');
    if (step === 0) {
      if (!name.trim())        { setError('Please enter your full name.'); return false; }
      if (!email.trim())       { setError('Please enter your email.'); return false; }
      if (password.length < 6) { setError('Password must be at least 6 characters.'); return false; }
      if (password !== confirm) { setError('Passwords do not match.'); return false; }
    }
    if (step === 1) {
      if (!isTeacher) {
        if (!grade) { setError('Please select your grade.'); return false; }
      } else {
        if (!teachSubjectName.trim()) { setError('Please enter the subject name.'); return false; }
        if (!teachSubjectCode.trim()) { setError('Please enter the subject code.'); return false; }
        if (teachSubjectCode.length < 2 || teachSubjectCode.length > 6) {
          setError('Subject code must be 2–6 characters.'); return false;
        }
        if (selectedGrades.length === 0) {
          setError('Please select at least one grade you teach.'); return false;
        }
      }
    }
    if (step === 2 && isTertiary && !isTeacher) {
      if (selectedSubjects.length === 0) {
        setError('Please select at least one subject.'); return false;
      }
    }
    return true;
  }

  function nextStep() {
    if (!validate()) return;
    if (!isTeacher && step === 1 && !isTertiary) {
      setStep(3);
      return;
    }
    setStep(s => s + 1);
  }

  const isLastStep = isTeacher ? step === 1 : (isTertiary ? step === 3 : step === 2);

  function computeStyle() {
    const c = {visual:0,auditory:0,reading:0,kinesthetic:0};
    Object.values(varkAnswers).forEach(s => { if(c[s]!==undefined) c[s]++; });
    return Object.entries(c).sort((a,b)=>b[1]-a[1])[0][0];
  }

  async function handleSubmit() {
    if (!isTeacher && Object.keys(varkAnswers).length < VARK_QUESTIONS.length) {
      setError('Please answer all 5 learning style questions.');
      return;
    }
    setSubmitting(true);
    setError('');
    const learningStyle = isTeacher ? null : computeStyle();
    const payload = {
      name:               name.trim(),
      email:              email.trim(),
      password,
      is_teacher:         isTeacher,
      learning_style:     learningStyle,
      grade:              isTeacher ? null : parseInt(grade),
      subject_ids:        (isTertiary && !isTeacher) ? selectedSubjects : [],
      teach_grades:       isTeacher ? selectedGrades : null,
      teach_subject_name: isTeacher ? teachSubjectName.trim() : null,
      teach_subject_code: isTeacher ? teachSubjectCode.trim().toUpperCase() : null,
    };
    try {
      const { data } = await api.post('/api/auth/register', payload);
      window.__authToken   = data.access_token;
      window.__studentId   = data.student_id;
      window.__studentName = name.trim();
      window.__isTeacher   = isTeacher;
      window.__profilePic  = '';
      localStorage.setItem('sa_token',     data.access_token);
      localStorage.setItem('sa_studentId', data.student_id);
      localStorage.setItem('sa_name',      name.trim());
      localStorage.setItem('sa_isTeacher', isTeacher.toString());
      nav(isTeacher ? '/teacher' : '/dashboard', {replace:true});
    } catch (err) {
      let errorMsg = 'Registration failed. Please try again.';
      if (err.response?.data?.detail) {
        const detail = err.response.data.detail;
        if (typeof detail === 'string') {
          errorMsg = detail;
        } else if (Array.isArray(detail)) {
          errorMsg = detail.map(e => e.msg).join(', ');
        } else if (typeof detail === 'object') {
          errorMsg = JSON.stringify(detail);
        }
      } else if (err.message) {
        errorMsg = err.message;
      }
      setError(errorMsg);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className='min-h-screen bg-app flex items-center justify-center p-4'>
      <div className='w-full max-w-lg'>

        <div className='text-center mb-8'>
          <div className='w-12 h-12 bg-teal/20 border border-teal/40 rounded-2xl flex items-center justify-center mx-auto mb-4'>
            <span className='text-teal font-bold text-lg'>S</span>
          </div>
          <h1 className='text-primary text-2xl font-bold'>Create Account</h1>
          <p className='text-muted text-sm mt-1'>SiveAdapt · University of Eswatini</p>
        </div>

        <Stepper steps={steps} current={step > steps.length-1 ? steps.length-1 : step}/>

        {error && (
          <div className='mb-4 px-4 py-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm'>{error}</div>
        )}

        <div className='card p-6'>

          {/* STEP 0 — Account */}
          {step === 0 && (
            <div className='space-y-4'>
              <h2 className='text-primary font-semibold mb-2'>Account Information</h2>
              <div className='flex gap-2 p-1 bg-app border border-border rounded-xl'>
                {['Student','Teacher'].map(type=>(
                  <button key={type} type='button' onClick={()=>setIsTeacher(type==='Teacher')}
                    className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-all ${(type==='Teacher')===isTeacher?'bg-teal text-app':'text-muted hover:text-primary'}`}>
                    {type}
                  </button>
                ))}
              </div>
              {[
                ['Full Name',   name,     setName,     'Your full name',    'text'],
                ['Email',       email,    setEmail,    'your@email.com',    'email'],
                ['Password',    password, setPassword, 'Min. 6 characters', 'password'],
                ['Confirm Password', confirm, setConfirm, 'Repeat password', 'password'],
              ].map(([label, val, set, placeholder, type])=>(
                <div key={label}>
                  <label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>{label}</label>
                  <input type={type} value={val} onChange={e=>set(e.target.value)} placeholder={placeholder}
                    className='w-full bg-input border border-border rounded-lg px-4 py-3 text-primary text-sm focus:border-teal/60 focus:outline-none'/>
                </div>
              ))}
            </div>
          )}

          {/* STEP 1 — Grade (student) */}
          {step === 1 && !isTeacher && (
            <div>
              <h2 className='text-primary font-semibold mb-2'>Select Your Grade</h2>
              <p className='text-muted text-sm mb-4'>
                {isTertiary
                  ? 'Tertiary students will choose subjects in the next step.'
                  : 'You will be automatically enrolled in all subjects available for your grade.'}
              </p>
              <div className='max-h-80 overflow-y-auto pr-1 space-y-3'>
                {['Primary','High School','Tertiary','Postgraduate'].map(group=>(
                  <div key={group}>
                    <p className='text-muted text-xs uppercase tracking-wide mb-2'>{group}</p>
                    <div className='flex flex-wrap gap-2'>
                      {GRADE_OPTIONS.filter(g=>g.group===group).map(g=>(
                        <button key={g.value} type='button' onClick={()=>setGrade(String(g.value))}
                          className={`px-3 py-1.5 rounded-lg border text-sm transition-all ${grade===String(g.value)?'border-teal bg-teal/10 text-teal font-medium':'border-border text-muted hover:text-primary'}`}>
                          {g.label}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
              {grade && !isTertiary && (
                <div className='mt-4 p-4 bg-teal/5 border border-teal/20 rounded-xl'>
                  {autoEnrolled.length > 0 ? (
                    <>
                      <p className='text-teal text-xs font-semibold mb-2'>
                        ✓ You will be auto-enrolled in {autoEnrolled.length} subject{autoEnrolled.length!==1?'s':''}:
                      </p>
                      <div className='flex flex-wrap gap-2'>
                        {autoEnrolled.map(s=>(
                          <span key={s.id} className='text-xs px-2.5 py-1 bg-teal/10 border border-teal/30 text-teal rounded-lg font-medium'>
                            {s.name}
                          </span>
                        ))}
                      </div>
                    </>
                  ) : (
                    <div className='flex items-start gap-2'>
                      <span className='text-amber-400 text-sm flex-shrink-0'>ℹ</span>
                      <div>
                        <p className='text-amber-300 text-xs font-medium'>No subjects available for Grade {grade} yet</p>
                        <p className='text-muted text-xs mt-0.5'>
                          Your account will be created and you will be automatically enrolled when a teacher registers for your grade.
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* STEP 1 — Teacher: Subject + Grade selection */}
          {step === 1 && isTeacher && (
            <div className='space-y-5'>
              <h2 className='text-primary font-semibold mb-1'>Your Subject & Grades</h2>
              <p className='text-muted text-sm mb-2'>
                Register the subject you teach and choose exactly which grades you teach.
              </p>
              <div>
                <label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>Subject Name</label>
                <input
                  value={teachSubjectName}
                  onChange={e => setTeachSubjectName(e.target.value)}
                  placeholder='e.g. Mathematics, Science, English Literature…'
                  className='w-full bg-input border border-border rounded-lg px-4 py-3 text-primary text-sm focus:border-teal/60 focus:outline-none'
                />
              </div>
              <div className='relative'>
                <label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>
                  Subject Code
                  <span className='text-muted font-normal ml-1 normal-case'>(2–6 chars, no spaces)</span>
                </label>
                <input
                  value={teachSubjectCode}
                  onChange={e => setTeachSubjectCode(e.target.value.toUpperCase().replace(/\s/g,'').slice(0,6))}
                  onFocus={()=>setShowCodeSuggestions(true)}
                  onBlur={()=>setTimeout(()=>setShowCodeSuggestions(false),150)}
                  placeholder='e.g. MATH, SCI, ENG'
                  maxLength={6}
                  className='w-full bg-input border border-border rounded-lg px-4 py-3 text-primary text-sm focus:border-teal/60 focus:outline-none'
                />
                {showCodeSuggestions && (
                  <div className='absolute top-full left-0 right-0 mt-1 bg-card border border-border rounded-xl p-3 z-20 shadow-lg'>
                    <p className='text-muted text-xs mb-2'>Suggestions:</p>
                    <div className='flex flex-wrap gap-2'>
                      {SUBJECT_CODE_SUGGESTIONS.filter(c=>!teachSubjectCode||c.startsWith(teachSubjectCode)).map(c=>(
                        <button key={c} type='button'
                          onMouseDown={()=>setTeachSubjectCode(c)}
                          className='text-xs px-2.5 py-1 border border-border rounded-lg text-muted hover:text-teal hover:border-teal/40 transition-colors'>
                          {c}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              <div>
                <label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>Education Level</label>
                <div className='flex flex-wrap gap-2'>
                  {TEACHER_LEVELS.map(level => (
                    <button
                      key={level.level}
                      type='button'
                      onClick={() => setTeacherLevel(level.level)}
                      className={`px-3 py-1.5 rounded-lg border text-sm transition-all ${
                        teacherLevel === level.level
                          ? 'border-teal bg-teal/10 text-teal font-medium'
                          : 'border-border text-muted hover:text-primary'
                      }`}
                    >
                      {level.label}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>
                  Grades You Teach
                  <span className='text-muted font-normal ml-1 normal-case'>(select all that apply)</span>
                </label>
                <div className='flex flex-wrap gap-2'>
                  {currentLevelGrades.map(g => {
                    const gradeLabel = g <= 12 ? `Grade ${g}` : (g <= 17 ? `Level ${g-12}` : (g===18 ? 'Masters' : 'PhD'));
                    const isSelected = selectedGrades.includes(g);
                    return (
                      <button
                        key={g}
                        type='button'
                        onClick={() => {
                          if (isSelected) {
                            setSelectedGrades(prev => prev.filter(gr => gr !== g));
                          } else {
                            setSelectedGrades(prev => [...prev, g]);
                          }
                        }}
                        className={`px-3 py-1.5 rounded-lg border text-sm transition-all ${
                          isSelected
                            ? 'border-teal bg-teal/10 text-teal font-medium'
                            : 'border-border text-muted hover:text-primary'
                        }`}
                      >
                        {gradeLabel}
                      </button>
                    );
                  })}
                </div>
                {selectedGrades.length === 0 && (
                  <p className='text-amber-400 text-xs mt-2'>Select at least one grade.</p>
                )}
              </div>
              {teachSubjectName && teachSubjectCode && selectedGrades.length > 0 && (
                <div className='p-3 bg-teal/5 border border-teal/20 rounded-xl'>
                  <p className='text-teal text-xs font-semibold mb-1'>Subject preview:</p>
                  <p className='text-primary text-sm'>
                    <span className='font-medium'>{teachSubjectName}</span>
                    <span className='text-muted mx-2'>·</span>
                    <span className='badge-teal text-xs'>{teachSubjectCode || '—'}</span>
                    <span className='text-muted mx-2'>·</span>
                    <span className='text-muted text-xs'>Grades {selectedGrades.sort((a,b)=>a-b).join(', ')}</span>
                  </p>
                </div>
              )}
            </div>
          )}

          {/* STEP 2 — Tertiary subject selection (students only) with SEARCH */}
          {step === 2 && isTertiary && !isTeacher && (
            <div>
              <h2 className='text-primary font-semibold mb-2'>Choose Your Subjects</h2>
              <p className='text-muted text-sm mb-4'>
                Search for your courses by code or name (e.g. CSC411, Mathematics) and add them to your list.
              </p>

              {/* Search input */}
              <div className='mb-4'>
                <input
                  type='text'
                  placeholder='Search by code or name...'
                  value={subjectSearch}
                  onChange={e => setSubjectSearch(e.target.value)}
                  className='w-full bg-input border border-border rounded-lg px-4 py-2.5 text-primary text-sm focus:border-teal/60 focus:outline-none'
                />
              </div>

              {loadingSubjects ? (
                <div className='py-10 text-center'><div className='w-6 h-6 border-2 border-teal/30 border-t-teal rounded-full animate-spin mx-auto'/></div>
              ) : availableSubjects.length === 0 ? (
                <div className='py-10 text-center'>
                  <span className='text-4xl block mb-3'>📚</span>
                  <p className='text-primary font-medium mb-1'>No subjects available yet</p>
                  <p className='text-muted text-sm'>
                    No lecturers have registered subjects yet. Your account will be created
                    and you can enrol in subjects from your profile once they are available.
                  </p>
                </div>
              ) : (
                <>
                  {/* Filtered list of subjects */}
                  <div className='space-y-2 max-h-72 overflow-y-auto pr-1 mb-4'>
                    {availableSubjects
                      .filter(s =>
                        s.name.toLowerCase().includes(subjectSearch.toLowerCase()) ||
                        s.code.toLowerCase().includes(subjectSearch.toLowerCase())
                      )
                      .map(s => {
                        const checked = selectedSubjects.includes(s.id);
                        return (
                          <button
                            key={s.id}
                            type='button'
                            onClick={() => setSelectedSubjects(prev =>
                              checked ? prev.filter(id => id !== s.id) : [...prev, s.id]
                            )}
                            className={`w-full text-left p-4 rounded-xl border transition-all ${
                              checked ? 'border-teal bg-teal/5' : 'border-border hover:border-teal/30'
                            }`}
                          >
                            <div className='flex items-center justify-between'>
                              <div>
                                <p className='text-primary font-medium text-sm'>{s.name}</p>
                                <p className='text-muted text-xs'>{s.code}</p>
                              </div>
                              <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                                checked ? 'bg-teal border-teal' : 'border-border'
                              }`}>
                                {checked && <span className='text-app text-xs font-bold'>✓</span>}
                              </div>
                            </div>
                          </button>
                        );
                      })}
                  </div>

                  {/* Selected subjects summary */}
                  {selectedSubjects.length > 0 && (
                    <div className='mt-4 p-3 bg-teal/5 border border-teal/20 rounded-xl'>
                      <p className='text-teal text-xs font-semibold mb-2'>
                        Selected ({selectedSubjects.length}):
                      </p>
                      <div className='flex flex-wrap gap-2'>
                        {selectedSubjects.map(id => {
                          const subj = availableSubjects.find(s => s.id === id);
                          return subj ? (
                            <span key={id} className='text-xs px-2 py-1 bg-teal/10 border border-teal/30 text-teal rounded-lg'>
                              {subj.code} – {subj.name}
                            </span>
                          ) : null;
                        })}
                      </div>
                    </div>
                  )}
                </>
              )}
              <p className='text-muted text-xs mt-3'>
                {selectedSubjects.length} subject{selectedSubjects.length !== 1 ? 's' : ''} selected
              </p>
            </div>
          )}

          {/* VARK step (students only) */}
          {!isTeacher && step === (isTertiary ? 3 : 2) && (
            <div>
              <h2 className='text-primary font-semibold mb-1'>Learning Style Assessment</h2>
              <p className='text-muted text-sm mb-4'>5 quick questions to personalise your experience. No right or wrong answers.</p>
              <div className='space-y-5 max-h-96 overflow-y-auto pr-1'>
                {VARK_QUESTIONS.map((vq, qi) => (
                  <div key={qi}>
                    <p className='text-primary text-sm font-medium mb-2'>{qi+1}. {vq.q}</p>
                    <div className='space-y-2'>
                      {vq.options.map((opt, oi) => {
                        const sel = varkAnswers[qi]===opt.style;
                        return (
                          <button key={oi} type='button'
                            onClick={()=>setVarkAnswers(p=>({...p,[qi]:opt.style}))}
                            className={`w-full text-left px-4 py-2.5 rounded-lg border text-sm transition-all ${sel?'border-teal bg-teal/10 text-teal':'border-border text-muted hover:text-primary hover:border-teal/30'}`}>
                            {opt.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className={`flex gap-3 mt-6 ${step>0?'justify-between':'justify-end'}`}>
            {step > 0 && (
              <button type='button' onClick={()=>setStep(s=>s-1)} className='btn-ghost text-sm'>← Back</button>
            )}
            {isLastStep ? (
              <button type='button' onClick={handleSubmit} disabled={submitting}
                className='btn-primary text-sm disabled:opacity-50'>
                {submitting ? 'Creating account…' : 'Create Account →'}
              </button>
            ) : (
              <button type='button' onClick={nextStep} className='btn-primary text-sm'>
                Continue →
              </button>
            )}
          </div>
        </div>

        <p className='text-center text-muted text-sm mt-4'>
          Already have an account? <Link to='/login' className='text-teal hover:underline'>Sign in</Link>
        </p>
      </div>
    </div>
  );
}