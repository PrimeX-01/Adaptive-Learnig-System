import { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import PageShell from '../components/PageShell';
import api from '../services/api';

const VARK_QUESTIONS = [
  { q:'When learning something new, you prefer to:', options:[{label:'Watch a video or look at diagrams',style:'visual'},{label:'Listen to someone explain it',style:'auditory'},{label:'Read through notes or a textbook',style:'reading'},{label:'Try it yourself hands-on',style:'kinesthetic'}] },
  { q:'When you need directions to a new place, you prefer:', options:[{label:'A map or visual guide',style:'visual'},{label:'Someone to tell you verbally',style:'auditory'},{label:'Written step-by-step instructions',style:'reading'},{label:'Just start walking and figure it out',style:'kinesthetic'}] },
  { q:'When you remember something, you usually remember it by:', options:[{label:'A picture or image in your mind',style:'visual'},{label:'Hearing it said out loud',style:'auditory'},{label:'Reading it again',style:'reading'},{label:'Doing or experiencing it',style:'kinesthetic'}] },
  { q:'When studying for a test, you find it most helpful to:', options:[{label:'Draw diagrams and colour-code notes',style:'visual'},{label:'Read notes aloud or record yourself',style:'auditory'},{label:'Re-read and rewrite your notes',style:'reading'},{label:'Practice with exercises and examples',style:'kinesthetic'}] },
  { q:'You understand a concept best when:', options:[{label:'You can see it shown visually',style:'visual'},{label:'It is explained in conversation',style:'auditory'},{label:'You read a detailed explanation',style:'reading'},{label:'You can apply it to a real situation',style:'kinesthetic'}] },
];

const STYLE_INFO = {
  visual:      { icon:'👁️', label:'Visual',         color:'text-blue-400',   badge:'bg-blue-400/20 text-blue-400',   desc:'You learn best through diagrams, charts and visual aids.' },
  auditory:    { icon:'🎧', label:'Auditory',        color:'text-purple-400', badge:'bg-purple-400/20 text-purple-400',desc:'You learn best through listening and verbal explanations.' },
  reading:     { icon:'📖', label:'Reading/Writing', color:'text-green-400',  badge:'bg-green-400/20 text-green-400', desc:'You learn best through written notes and text content.' },
  kinesthetic: { icon:'🧪', label:'Kinesthetic',     color:'text-amber-400',  badge:'bg-amber-400/20 text-amber-400', desc:'You learn best through hands-on practice and examples.' },
};

export default function StudentProfile() {
  const nav      = useNavigate();
  const location = useLocation();
  const { user, isAuthenticated } = useAuth();
  const fileRef  = useRef(null);

  // ✅ Use authenticated user ID, fallback to localStorage
  const sid = user?.id || localStorage.getItem('sa_studentId');

  const [profile,       setProfile]       = useState(null);
  const [subjectStyles, setSubjectStyles] = useState([]);
  const [pointsSummary, setPointsSummary] = useState([]);
  const [loading,       setLoading]       = useState(true);
  const [saving,        setSaving]        = useState(false);
  const [picSaving,     setPicSaving]     = useState(false);
  const [error,         setError]         = useState('');
  const [success,       setSuccess]       = useState('');

  const [editName,     setEditName]     = useState('');
  const [editUsername, setEditUsername] = useState('');
  const [editBio,      setEditBio]      = useState('');

  const [showPwForm, setShowPwForm] = useState(false);
  const [oldPw,      setOldPw]      = useState('');
  const [newPw,      setNewPw]      = useState('');
  const [confirmPw,  setConfirmPw]  = useState('');
  const [pwError,    setPwError]    = useState('');
  const [pwSuccess,  setPwSuccess]  = useState('');

  const [showVark,    setShowVark]    = useState(false);
  const [varkAnswers, setVarkAnswers] = useState({});
  const [varkSaving,  setVarkSaving]  = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (params.get('retake') === 'true') setShowVark(true);
  }, [location.search]);

  useEffect(() => {
    if (!sid) {
      setLoading(false);
      setError('No student ID found. Please log in again.');
      return;
    }

    Promise.all([
      api.get(`/api/students/${sid}/profile`),
      api.get(`/api/style/${sid}`).catch(()=>({data:[]})),
      api.get(`/api/quiz/points/${sid}`).catch(()=>({data:[]})),
    ]).then(([profRes, styleRes, pointsRes]) => {
      const p = profRes.data;
      setProfile(p);
      setEditName(p.name || '');
      setEditUsername(p.username || '');
      setEditBio(p.bio || '');
      setSubjectStyles(styleRes.data || []);
      setPointsSummary(pointsRes.data || []);
    }).catch((err) => {
      console.error('Failed to load profile:', err);
      setError('Failed to load profile. Please try again.');
    }).finally(() => setLoading(false));
  }, [sid]);

  const saveProfile = async () => {
    if (!editName.trim()) { setError('Name is required.'); return; }
    setSaving(true); setError(''); setSuccess('');
    try {
      await api.patch(`/api/students/${sid}/profile`, { name:editName.trim(), username:editUsername.trim(), bio:editBio.trim() });
      setProfile(prev=>({...prev, name:editName, username:editUsername, bio:editBio}));
      if (user) user.name = editName.trim(); // update context if possible
      localStorage.setItem('sa_name', editName.trim());
      setSuccess('Profile saved.'); setTimeout(()=>setSuccess(''),3000);
    } catch(err){ setError(err.response?.data?.detail||'Failed to save.'); }
    finally { setSaving(false); }
  };

  const handlePicChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 5*1024*1024) { setError('Image must be under 5 MB.'); return; }
    setPicSaving(true);
    const reader = new FileReader();
    reader.onload = async (ev) => {
      const b64 = ev.target.result;
      try {
        await api.patch(`/api/students/${sid}/profile`, { profile_picture: b64 });
        setProfile(prev=>({...prev, profile_picture:b64}));
        localStorage.setItem('sa_pic', b64);
      } catch { setError('Failed to upload picture.'); }
      finally { setPicSaving(false); }
    };
    reader.readAsDataURL(file);
  };

  const changePassword = async () => {
    setPwError(''); setPwSuccess('');
    if (!oldPw||!newPw||!confirmPw) { setPwError('All fields required.'); return; }
    if (newPw!==confirmPw) { setPwError('Passwords do not match.'); return; }
    if (newPw.length<6)   { setPwError('Min 6 characters.'); return; }
    try {
      await api.post(`/api/auth/change-password/${sid}`, { old_password:oldPw, new_password:newPw });
      setPwSuccess('Password changed!'); setOldPw(''); setNewPw(''); setConfirmPw('');
      setTimeout(()=>{ setShowPwForm(false); setPwSuccess(''); },2000);
    } catch(err){ setPwError(err.response?.data?.detail||'Failed.'); }
  };

  const submitVark = async () => {
    if (Object.keys(varkAnswers).length<VARK_QUESTIONS.length) { setError('Please answer all questions.'); return; }
    setVarkSaving(true);
    const counts={visual:0,auditory:0,reading:0,kinesthetic:0};
    Object.values(varkAnswers).forEach(s=>{if(counts[s]!==undefined)counts[s]++;});
    const dominant=Object.entries(counts).sort((a,b)=>b[1]-a[1])[0][0];
    try {
      await api.post(`/api/style/${sid}/update`, { style:dominant });
      setProfile(prev=>({...prev, preferred_learning_style:dominant}));
      setShowVark(false); setVarkAnswers({});
      setSuccess(`Learning style updated to ${STYLE_INFO[dominant]?.label||dominant}!`);
      setTimeout(()=>setSuccess(''),4000);
    } catch { setError('Failed to update learning style.'); }
    finally { setVarkSaving(false); }
  };

  if (loading) return (
    <div className='min-h-screen bg-app flex items-center justify-center flex-col gap-4'>
      <div className='w-12 h-12 border-4 border-teal/30 border-t-teal rounded-full animate-spin'/>
      <p className='text-muted text-sm'>Loading profile…</p>
    </div>
  );

  if (error && !profile) {
    return (
      <PageShell title='My Profile' subtitle=''>
        <div className='bg-red-500/10 border border-red-500/30 rounded-xl p-6 text-red-400 text-sm'>
          {error}
          <button onClick={() => nav('/auth')} className='mt-4 btn-ghost text-sm'>Go to Login</button>
        </div>
      </PageShell>
    );
  }

  const learningStyle = profile?.preferred_learning_style || 'reading';
  const styleInfo     = STYLE_INFO[learningStyle] || STYLE_INFO.reading;
  const overallFcl    = pointsSummary.length > 0
    ? (Math.round(pointsSummary.reduce((s,p)=>s+(p.subject_fcl||1),0)/pointsSummary.length*10)/10)
    : 1;

  return (
    <PageShell title='My Profile' subtitle='Manage your account and learning preferences'>
      <div className='max-w-3xl mx-auto space-y-6'>

        {error   && <div className='px-4 py-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm'>{error}</div>}
        {success && <div className='px-4 py-3 bg-green-500/10 border border-green-500/30 rounded-xl text-green-400 text-sm'>{success}</div>}

        {/* VARK retake modal */}
        {showVark && (
          <div className='fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4 overflow-y-auto'>
            <div className='card p-6 w-full max-w-lg my-4'>
              <div className='flex justify-between items-center mb-4'>
                <h2 className='text-primary font-bold text-lg'>Update Learning Style</h2>
                <button onClick={()=>setShowVark(false)} className='text-muted hover:text-primary text-xl'>✕</button>
              </div>
              <p className='text-muted text-sm mb-5'>Answer these 5 questions to recalibrate your personalisation.</p>
              <div className='space-y-5'>
                {VARK_QUESTIONS.map((vq,qi)=>(
                  <div key={qi}>
                    <p className='text-primary text-sm font-medium mb-2'>{qi+1}. {vq.q}</p>
                    <div className='space-y-2'>
                      {vq.options.map((opt,oi)=>{
                        const sel=varkAnswers[qi]===opt.style;
                        return <button key={oi} type='button' onClick={()=>setVarkAnswers(p=>({...p,[qi]:opt.style}))}
                          className={`w-full text-left px-4 py-2.5 rounded-lg border text-sm transition-all ${sel?'border-teal bg-teal/10 text-teal':'border-border text-muted hover:text-primary hover:border-teal/30'}`}>{opt.label}</button>;
                      })}
                    </div>
                  </div>
                ))}
              </div>
              <div className='flex gap-3 mt-5'>
                <button onClick={submitVark} disabled={varkSaving||Object.keys(varkAnswers).length<VARK_QUESTIONS.length} className='btn-primary flex-1 disabled:opacity-50'>{varkSaving?'Saving…':'Update My Style'}</button>
                <button onClick={()=>setShowVark(false)} className='btn-ghost flex-1'>Cancel</button>
              </div>
            </div>
          </div>
        )}

        {/* Profile card */}
        <div className='card p-6'>
          <div className='flex items-start gap-6'>
            <div className='flex flex-col items-center gap-3 flex-shrink-0'>
              <div className='w-24 h-24 rounded-2xl bg-teal/20 border-2 border-teal/40 overflow-hidden flex items-center justify-center'>
                {profile?.profile_picture
                  ? <img src={profile.profile_picture} alt='Profile' className='w-full h-full object-cover'/>
                  : <span className='text-teal text-3xl font-bold'>{(editName||'S')[0].toUpperCase()}</span>}
              </div>
              <button onClick={()=>fileRef.current?.click()} disabled={picSaving} className='text-xs text-teal hover:underline disabled:opacity-50'>{picSaving?'Uploading…':'📷 Change'}</button>
              <input ref={fileRef} type='file' accept='image/*' className='hidden' onChange={handlePicChange}/>
              <span className='text-muted text-xs'>Grade {profile?.grade||'—'}</span>
            </div>

            <div className='flex-1 grid grid-cols-2 gap-4'>
              <div><label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>Full Name</label><input value={editName} onChange={e=>setEditName(e.target.value)} className='w-full bg-input border border-border rounded-lg px-4 py-2.5 text-primary text-sm focus:border-teal/60 focus:outline-none'/></div>
              <div><label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>Username</label><div className='flex items-center bg-input border border-border rounded-lg px-4 py-2.5 gap-2'><span className='text-muted text-sm'>@</span><input value={editUsername} onChange={e=>setEditUsername(e.target.value.toLowerCase().replace(/\s/g,''))} className='flex-1 bg-transparent text-primary text-sm focus:outline-none'/></div></div>
              <div><label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>Email</label><div className='bg-input border border-border rounded-lg px-4 py-2.5 text-muted text-sm'>{profile?.email||'—'}</div></div>
              <div><label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>Overall FCL</label><div className='bg-input border border-border rounded-lg px-4 py-2.5 text-teal text-sm stat-number font-bold'>FCL {overallFcl}</div></div>
              <div className='col-span-2'><label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>Bio</label><textarea value={editBio} onChange={e=>setEditBio(e.target.value)} rows={2} placeholder='Tell us about yourself…' className='w-full bg-input border border-border rounded-lg px-4 py-2.5 text-primary text-sm focus:border-teal/60 focus:outline-none resize-none'/></div>
            </div>
          </div>

          <div className='flex justify-end gap-3 mt-5 pt-5 border-t border-border'>
            <button onClick={()=>setShowPwForm(!showPwForm)} className='btn-ghost text-sm'>🔒 Change Password</button>
            <button onClick={saveProfile} disabled={saving} className='btn-primary text-sm disabled:opacity-50'>{saving?'Saving…':'Save Changes'}</button>
          </div>

          {showPwForm && (
            <div className='mt-4 p-4 bg-app border border-border rounded-xl'>
              <h4 className='text-primary font-semibold text-sm mb-3'>Change Password</h4>
              <div className='grid grid-cols-3 gap-3'>
                {[['Current Password',oldPw,setOldPw],['New Password',newPw,setNewPw],['Confirm New',confirmPw,setConfirmPw]].map(([l,v,set])=>(
                  <div key={l}><label className='text-muted text-xs block mb-1'>{l}</label><input type='password' value={v} onChange={e=>set(e.target.value)} className='w-full bg-input border border-border rounded-lg px-3 py-2 text-primary text-sm focus:outline-none'/></div>
                ))}
              </div>
              {pwError   && <p className='text-red-400 text-xs mt-2'>{pwError}</p>}
              {pwSuccess && <p className='text-green-400 text-xs mt-2'>{pwSuccess}</p>}
              <button onClick={changePassword} className='btn-primary text-sm mt-3'>Update Password</button>
            </div>
          )}
        </div>

        {/* Learning style */}
        <div className='card p-5'>
          <div className='flex items-center justify-between mb-4'>
            <div><h3 className='text-primary font-semibold'>Learning Style</h3><p className='text-muted text-xs mt-0.5'>How SiveAdapt personalises your content</p></div>
            <button onClick={()=>setShowVark(true)} className='btn-ghost text-xs'>🔄 Retake Assessment</button>
          </div>
          <div className='flex items-start gap-4 p-4 bg-app border border-border rounded-xl mb-4'>
            <span className='text-3xl'>{styleInfo.icon}</span>
            <div><div className='flex items-center gap-2 mb-1'><span className={`font-semibold text-sm ${styleInfo.color}`}>{styleInfo.label} Learner</span><span className='badge-teal text-xs'>Overall</span></div><p className='text-muted text-xs leading-relaxed'>{styleInfo.desc}</p></div>
          </div>
          {subjectStyles.length > 0 && (
            <div className='space-y-2'>
              <p className='text-muted text-xs uppercase tracking-wide mb-2'>Per-subject</p>
              {subjectStyles.map(s=>{
                const si=STYLE_INFO[s.learning_style]||STYLE_INFO.reading;
                return (
                  <div key={s.subject_id} className='flex items-center justify-between px-3 py-2 bg-app border border-border rounded-lg'>
                    <span className='text-primary text-xs font-medium'>{s.subject_name}</span>
                    <div className='flex items-center gap-2'><span className='text-sm'>{si.icon}</span><span className={`text-xs ${si.color}`}>{si.label}</span>{s.auto_detected&&<span className='text-muted text-xs'>(auto)</span>}</div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Subject FCL progress */}
        {pointsSummary.length > 0 && (
          <div className='card p-5'>
            <h3 className='text-primary font-semibold mb-4'>Subject Progress</h3>
            <div className='space-y-4'>
              {pointsSummary.map(s=>{
                const pct=Math.min(100,Math.round((s.total_points%1000)/1000*100));
                return (
                  <div key={s.subject_id}>
                    <div className='flex items-center justify-between mb-1.5'>
                      <div className='flex items-center gap-2'><span className='text-primary text-xs font-medium'>{s.subject_name}</span><span className='badge-teal text-xs stat-number'>FCL {s.subject_fcl}</span></div>
                      <button onClick={()=>nav(`/subjects/${s.subject_id}`)} className='text-teal text-xs hover:underline'>Details →</button>
                    </div>
                    <div className='w-full bg-border rounded-full h-2'><div className='h-2 rounded-full bg-teal transition-all duration-700' style={{width:`${pct}%`}}/></div>
                    <p className='text-muted text-xs mt-1'>{s.total_points%1000}/1000 pts to next FCL · {s.total_points} total earned</p>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        <div className='flex gap-3'>
          <button onClick={()=>nav('/dashboard')} className='btn-ghost text-sm'>← Dashboard</button>
          <button onClick={()=>nav('/library')}   className='btn-ghost text-sm'>📚 Library</button>
          <button onClick={()=>nav('/progress')}  className='btn-ghost text-sm'>📊 Progress</button>
        </div>
      </div>
    </PageShell>
  );
}