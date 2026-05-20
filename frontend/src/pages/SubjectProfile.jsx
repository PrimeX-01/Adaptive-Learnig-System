import { useState, useEffect, useCallback } from 'react';
import PageShell from '../components/PageShell';
import api from '../services/api';

// Helper component for points progress bar
function PointsProgress({ subjectId, currentFcl }) {
  const [pointsData, setPointsData] = useState(null);
  const sid = window.__studentId;

  useEffect(() => {
    api.get(`/api/quiz/points/${sid}`)
      .then(res => {
        const found = (res.data || []).find(p => p.subject_id === subjectId);
        setPointsData(found);
      })
      .catch(() => {});
  }, [subjectId, sid]);

  if (!pointsData) return null;
  const { current_points = 0, points_needed = 100, progress_pct = 0 } = pointsData;
  const remaining = points_needed - current_points;

  return (
    <div className="mt-3 pt-2 border-t border-border/50">
      <div className="flex items-center justify-between text-xs text-muted mb-1">
        <span>FCL {currentFcl} → {currentFcl + 1}</span>
        <span className="stat-number">{current_points} / {points_needed} pts</span>
      </div>
      <div className="w-full bg-border rounded-full h-1.5">
        <div className="h-1.5 rounded-full bg-teal transition-all duration-700" style={{ width: `${progress_pct}%` }} />
      </div>
      <p className="text-muted text-xs mt-1">{remaining} points to next FCL</p>
    </div>
  );
}

export default function SubjectProfile() {
  const [enrolled,  setEnrolled]  = useState([]);
  const [available, setAvailable] = useState([]);
  const [overall,   setOverall]   = useState(null);
  const [loading,   setLoading]   = useState(true);
  const [lookupEmail, setLookupEmail] = useState({});
  const [lookupStatus,setLookupStatus]= useState({});
  const [enrolling, setEnrolling] = useState(false);
  const sid = window.__studentId;

  const load = useCallback(() => {
    Promise.all([
      api.get(`/api/subjects/enrolled/${sid}`),
      api.get('/api/subjects/available'),
      api.get(`/api/students/${sid}/subject-performance`),
    ]).then(([e, a, p]) => {
      setEnrolled(e.data); setAvailable(a.data); setOverall(p.data.overall);
    }).finally(()=>setLoading(false));
  }, [sid]);

  useEffect(()=>{ load(); },[load]);

  async function handleTeacherLookup(subjectCode) {
    const email = lookupEmail[subjectCode];
    if (!email?.trim()) return;
    setLookupStatus(s=>({...s,[subjectCode]:'loading'}));
    try {
      const { data } = await api.get(`/api/subjects/teacher-lookup?email=${encodeURIComponent(email)}`);
      await api.patch(`/api/subjects/teacher/${sid}`, { subject_code: subjectCode, teacher_id: data.teacher_id });
      setLookupStatus(s=>({...s,[subjectCode]:'linked'}));
      load(); // Refresh to show teacher name
    } catch {
      setLookupStatus(s=>({...s,[subjectCode]:'error'}));
    }
  }

  async function enrollSubject(code) {
    setEnrolling(true);
    try {
      await api.post(`/api/subjects/enroll/${sid}`, { subject_code: code });
      load();
    } catch {} finally { setEnrolling(false); }
  }

  async function unenrollSubject(code) {
    try {
      await api.delete(`/api/subjects/unenroll/${sid}/${code}`);
      load();
    } catch {}
  }

  const enrolledCodes = enrolled.map(e=>e.subject_code);
  const notEnrolled   = available.filter(s=>!enrolledCodes.includes(s.code));

  return (
    <PageShell title='My Subjects' subtitle='Manage your subject enrollment and teacher links'>
      {loading && <div className='text-muted text-sm'>Loading...</div>}

      {/* Overall performance summary */}
      {overall && (
        <div className='card p-5 mb-6 flex items-center justify-between'>
          <div>
            <p className='text-muted text-xs uppercase tracking-wide mb-1'>Overall Performance</p>
            <p className='text-primary font-bold text-2xl stat-number'>{overall.overall_label}</p>
          </div>
          <div className='flex gap-6'>
            <div className='text-center'><div className='stat-number text-2xl font-bold text-teal'>{overall.avg_fcl||'—'}</div><div className='text-muted text-xs'>Avg FCL</div></div>
            <div className='text-center'><div className='stat-number text-2xl font-bold text-primary'>{overall.avg_accuracy ? `${overall.avg_accuracy}%` : '—'}</div><div className='text-muted text-xs'>Avg Accuracy</div></div>
            <div className='text-center'><div className='stat-number text-2xl font-bold text-primary'>{overall.subjects_count}</div><div className='text-muted text-xs'>Subjects</div></div>
          </div>
        </div>
      )}

      {/* Enrolled subjects */}
      <h2 className='text-primary font-semibold text-sm mb-3'>Enrolled Subjects</h2>
      <div className='grid grid-cols-2 gap-4 mb-8'>
        {enrolled.map(e => (
          <div key={e.subject_code} className='card p-5'>
            <div className='flex items-start justify-between mb-3'>
              <div>
                <h3 className='text-primary font-semibold text-sm'>{e.subject_name}</h3>
                <span className='badge-teal text-xs mt-1 inline-block'>{e.subject_code}</span>
              </div>
              <button onClick={()=>unenrollSubject(e.subject_code)} className='text-muted hover:text-red-400 text-xs transition-colors'>Remove</button>
            </div>
            {/* Per-subject metrics */}
            <div className='grid grid-cols-3 gap-2 mb-4'>
              {[['FCL', e.fcl_level||'—'],['Accuracy', e.accuracy ? `${e.accuracy}%`:'—'],['Mastered', e.mastered_topics ? `${e.mastered_topics}/${e.total_topics}` : '0/0']].map(([label,val])=>(
                <div key={label} className='bg-app rounded-lg p-2 border border-border text-center'>
                  <div className='stat-number text-primary font-bold text-sm'>{val}</div>
                  <div className='text-muted text-xs'>{label}</div>
                </div>
              ))}
            </div>

            {/* ✅ NEW: FCL Points Progress Bar */}
            <PointsProgress subjectId={e.subject_id} currentFcl={e.fcl_level || 1} />

            {/* Teacher link */}
            <div className='border-t border-border pt-3'>
              <p className='text-muted text-xs mb-2'>
                {e.teacher_name ? <span className='text-green-400'>✓ Teacher: {e.teacher_name}</span> : 'No teacher linked yet'}
              </p>
              <div className='flex gap-2'>
                <input type='email' placeholder='Teacher email' value={lookupEmail[e.subject_code]||''}
                  onChange={ev=>setLookupEmail(l=>({...l,[e.subject_code]:ev.target.value}))}
                  className='flex-1 bg-input border border-border rounded-lg px-3 py-1.5 text-primary text-xs focus:border-teal/60 focus:outline-none' />
                <button onClick={()=>handleTeacherLookup(e.subject_code)} className='btn-ghost text-xs py-1.5'>
                  {lookupStatus[e.subject_code]==='loading' ? '...' : e.teacher_name ? 'Update' : 'Link'}
                </button>
              </div>
              {lookupStatus[e.subject_code]==='linked' && <p className='text-green-400 text-xs mt-1'>✓ Teacher linked successfully</p>}
              {lookupStatus[e.subject_code]==='error'  && <p className='text-red-400 text-xs mt-1'>No teacher found with that email</p>}
            </div>
          </div>
        ))}
      </div>

      {/* Add more subjects */}
      {notEnrolled.length > 0 && (
        <div>
          <h2 className='text-primary font-semibold text-sm mb-3'>Add a Subject</h2>
          <div className='grid grid-cols-3 gap-3'>
            {notEnrolled.map(s=>(
              <button key={s.code} onClick={()=>enrollSubject(s.code)} disabled={enrolling} className='card-hover p-4 text-left group disabled:opacity-50'>
                <div className='text-primary text-sm font-medium group-hover:text-teal transition-colors'>{s.name}</div>
                <div className='text-muted text-xs mt-1'>{s.description}</div>
                <div className='text-teal text-xs mt-2 opacity-0 group-hover:opacity-100 transition-opacity'>+ Enrol →</div>
              </button>
            ))}
          </div>
        </div>
      )}
    </PageShell>
  );
}