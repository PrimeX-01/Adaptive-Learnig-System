import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import PageShell from '../components/PageShell';
import api from '../services/api';

const SUBJECT_CODE_SUGGESTIONS = [
  'MATH','SCI','ENG','SOC','CS','PHY','CHEM','BIO',
  'HIST','GEO','ART','MUS','PE','ECO','ACC','BUS',
];

function StatCard({ icon, label, value, sub }) {
  return (
    <div className='card p-5'>
      <div className='flex justify-between items-center mb-2'>
        <span className='text-muted text-xs uppercase tracking-wide'>{label}</span>
        <span className='text-xl'>{icon}</span>
      </div>
      <div className='stat-number text-2xl font-bold text-teal'>{value}</div>
      {sub && <p className='text-muted text-xs mt-1'>{sub}</p>}
    </div>
  );
}

function GradeBadge({ assignment, onRemove }) {
  return (
    <div className='flex items-center gap-2 px-3 py-2 bg-teal/10 border border-teal/30 rounded-lg'>
      <span className='text-teal text-xs font-medium'>{assignment.subject_name}</span>
      <span className='text-border text-xs'>·</span>
      <span className='text-muted text-xs'>Grade {assignment.grade}</span>
      <span className='text-muted text-xs ml-1'>({assignment.subject_code})</span>
      <button onClick={() => onRemove(assignment.id)} className='ml-1 text-muted hover:text-red-400 transition-colors text-xs'>✕</button>
    </div>
  );
}

export default function TeacherProfile() {
  const { user, isAuthenticated, isTeacher } = useAuth();
  const navigate = useNavigate();
  const fileRef = useRef(null);
  const teacherId = user?.id;

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/auth', { replace: true });
    } else if (!isTeacher) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, isTeacher, navigate]);

  const [profile, setProfile] = useState(null);
  const [stats, setStats] = useState(null);
  const [assignments, setAssignments] = useState([]);
  const [existingSubjs, setExistingSubjs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [picSaving, setPicSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [editName, setEditName] = useState('');
  const [editUsername, setEditUsername] = useState('');
  const [editBio, setEditBio] = useState('');
  const [editEmail, setEditEmail] = useState('');

  const [showPwForm, setShowPwForm] = useState(false);
  const [oldPw, setOldPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  const [pwError, setPwError] = useState('');
  const [pwSuccess, setPwSuccess] = useState('');

  const [addingGrade, setAddingGrade] = useState(false);
  const [assignMode, setAssignMode] = useState('create');
  const [newSubjName, setNewSubjName] = useState('');
  const [newSubjCode, setNewSubjCode] = useState('');
  const [newSubjId, setNewSubjId] = useState('');
  const [newGrade, setNewGrade] = useState(8);
  const [assignError, setAssignError] = useState('');
  const [showCodeSugg, setShowCodeSugg] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(null);

  // ---------- Load data ----------
  useEffect(() => {
    if (!teacherId || !isTeacher) return;
    Promise.all([
      api.get(`/api/teachers/profile/${teacherId}`),
      api.get(`/api/teachers/dashboard/${teacherId}`),
      api.get(`/api/teachers/grade-assignments/${teacherId}`),
      api.get('/api/subjects/available'),
    ]).then(([profRes, dashRes, assignRes, subjRes]) => {
      const p = profRes.data;
      setProfile(p);
      setEditName(p.name || '');
      setEditUsername(p.username || '');
      setEditBio(p.bio || '');
      setEditEmail(p.email || '');
      setStats(dashRes.data);
      setAssignments(assignRes.data || []);
      setExistingSubjs(subjRes.data || []);
      if (subjRes.data?.length > 0) setNewSubjId(String(subjRes.data[0].id));
    }).catch(() => setError('Failed to load profile.'))
      .finally(() => setLoading(false));
  }, [teacherId, isTeacher]);

  // ---------- Profile save ----------
  const saveProfile = async () => {
    if (!editName.trim()) { setError('Name is required.'); return; }
    setSaving(true); setError(''); setSuccess('');
    try {
      await api.patch(`/api/teachers/profile/${teacherId}`, {
        name: editName.trim(),
        username: editUsername.trim(),
        bio: editBio.trim(),
        email: editEmail.trim(),
      });
      setProfile(p => ({ ...p, name: editName, username: editUsername, bio: editBio, email: editEmail }));
      setSuccess('Profile saved successfully.');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save.');
    } finally {
      setSaving(false);
    }
  };

  // ---------- Picture upload ----------
  const handlePicChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
      setError('Image must be under 5 MB.');
      return;
    }
    setPicSaving(true);
    const reader = new FileReader();
    reader.onload = async (ev) => {
      const b64 = ev.target.result;
      try {
        await api.patch(`/api/teachers/profile/${teacherId}`, { profile_picture: b64 });
        setProfile(p => ({ ...p, profile_picture: b64 }));
      } catch {
        setError('Failed to upload picture.');
      } finally {
        setPicSaving(false);
      }
    };
    reader.readAsDataURL(file);
  };

  // ---------- Password change ----------
  const changePassword = async () => {
    setPwError(''); setPwSuccess('');
    if (!oldPw || !newPw || !confirmPw) {
      setPwError('All fields required.');
      return;
    }
    if (newPw !== confirmPw) {
      setPwError('Passwords do not match.');
      return;
    }
    if (newPw.length < 6) {
      setPwError('Min 6 characters.');
      return;
    }
    try {
      await api.post(`/api/auth/change-password/${teacherId}`, {
        old_password: oldPw,
        new_password: newPw,
      });
      setPwSuccess('Password changed!');
      setOldPw('');
      setNewPw('');
      setConfirmPw('');
      setTimeout(() => {
        setShowPwForm(false);
        setPwSuccess('');
      }, 2000);
    } catch (err) {
      setPwError(err.response?.data?.detail || 'Failed.');
    }
  };

  // ---------- Remove assignment ----------
  const removeAssignment = async (id) => {
    try {
      await api.delete(`/api/teachers/grade-assignments/${id}`);
      setAssignments(prev => prev.filter(a => a.id !== id));
    } catch {
      setError('Failed to remove assignment.');
    }
    setDeleteConfirm(null);
  };

  // ---------- Add assignment ----------
  const addAssignment = async () => {
    setAssignError('');
    if (assignMode === 'create') {
      if (!newSubjName.trim()) {
        setAssignError('Subject name is required.');
        return;
      }
      if (!newSubjCode.trim()) {
        setAssignError('Subject code is required.');
        return;
      }
      if (newSubjCode.length < 2 || newSubjCode.length > 6) {
        setAssignError('Code must be 2–6 characters.');
        return;
      }
      try {
        const { data } = await api.post('/api/subjects/create', {
          name: newSubjName.trim(),
          code: newSubjCode.trim().toUpperCase(),
          teacher_id: parseInt(teacherId),
          grade: newGrade,
        });
        setAssignments(prev => [...prev, data]);
        setExistingSubjs(prev => [...prev, { id: data.subject_id, name: data.subject_name, code: data.subject_code }]);
        setAddingGrade(false);
        setNewSubjName('');
        setNewSubjCode('');
        setAssignError('');
      } catch (err) {
        setAssignError(err.response?.data?.detail || 'Failed to create subject.');
      }
    } else {
      if (!newSubjId) {
        setAssignError('Please select a subject.');
        return;
      }
      try {
        const { data } = await api.post('/api/teachers/grade-assignments', {
          teacher_id: parseInt(teacherId),
          subject_id: parseInt(newSubjId),
          grade: newGrade,
        });
        setAssignments(prev => [...prev, data]);
        setAddingGrade(false);
        setAssignError('');
      } catch (err) {
        setAssignError(err.response?.data?.detail || 'Failed to add assignment.');
      }
    }
  };

  if (!isAuthenticated || !isTeacher) {
    return (
      <div className='min-h-screen bg-app flex items-center justify-center flex-col gap-4'>
        <div className='w-12 h-12 border-4 border-teal/30 border-t-teal rounded-full animate-spin' />
        <p className='text-muted text-sm'>Loading...</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className='min-h-screen bg-app flex items-center justify-center flex-col gap-4'>
        <div className='w-12 h-12 border-4 border-teal/30 border-t-teal rounded-full animate-spin' />
        <p className='text-muted text-sm'>Loading profile…</p>
      </div>
    );
  }

  const totalStudents = stats?.total_students || 0;
  const subjectCount = assignments.length;
  const atRiskCount = stats?.at_risk?.length || 0;

  return (
    <PageShell title='Teacher Profile' subtitle='Manage your account and teaching assignments'>
      <div className='max-w-4xl mx-auto space-y-6'>
        {error && <div className='px-4 py-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm'>{error}</div>}
        {success && <div className='px-4 py-3 bg-green-500/10 border border-green-500/30 rounded-xl text-green-400 text-sm'>{success}</div>}

        {deleteConfirm && (
          <div className='fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4'>
            <div className='card p-6 w-full max-w-sm text-center'>
              <span className='text-4xl block mb-3'>⚠️</span>
              <h3 className='text-primary font-bold mb-2'>Remove this assignment?</h3>
              <p className='text-muted text-sm mb-5'>Students in this grade will no longer be linked to you for this subject.</p>
              <div className='flex gap-3'>
                <button onClick={() => removeAssignment(deleteConfirm)} className='flex-1 py-2 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm hover:bg-red-500/20 transition-colors'>Remove</button>
                <button onClick={() => setDeleteConfirm(null)} className='btn-ghost flex-1'>Cancel</button>
              </div>
            </div>
          </div>
        )}

        <div className='grid grid-cols-3 gap-4'>
          <StatCard icon='👥' label='Total Students' value={totalStudents} sub='Across all assignments' />
          <StatCard icon='📚' label='Subjects / Grades' value={subjectCount} sub='Active assignments' />
          <StatCard icon='⚠' label='At-Risk Students' value={atRiskCount} sub='Need attention' />
        </div>

        {/* Profile card */}
        <div className='card p-6'>
          <div className='flex items-start gap-6'>
            <div className='flex flex-col items-center gap-3 flex-shrink-0'>
              <div className='w-24 h-24 rounded-2xl bg-teal/20 border-2 border-teal/40 overflow-hidden flex items-center justify-center'>
                {profile?.profile_picture
                  ? <img src={profile.profile_picture} alt='Profile' className='w-full h-full object-cover' />
                  : <span className='text-teal text-3xl font-bold'>{(editName || 'T')[0].toUpperCase()}</span>}
              </div>
              <button onClick={() => fileRef.current?.click()} disabled={picSaving} className='text-xs text-teal hover:underline disabled:opacity-50'>
                {picSaving ? 'Uploading…' : '📷 Change Photo'}
              </button>
              <input ref={fileRef} type='file' accept='image/*' className='hidden' onChange={handlePicChange} />
              <span className='px-2 py-0.5 bg-purple-500/20 border border-purple-500/30 text-purple-400 rounded text-xs font-medium'>Teacher</span>
            </div>

            <div className='flex-1 grid grid-cols-2 gap-4'>
              <div>
                <label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>Full Name</label>
                <input value={editName} onChange={e => setEditName(e.target.value)} className='w-full bg-input border border-border rounded-lg px-4 py-2.5 text-primary text-sm focus:border-teal/60 focus:outline-none' />
              </div>
              <div>
                <label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>Username</label>
                <div className='flex items-center bg-input border border-border rounded-lg px-4 py-2.5 gap-2'>
                  <span className='text-muted text-sm'>@</span>
                  <input value={editUsername} onChange={e => setEditUsername(e.target.value.toLowerCase().replace(/\s/g, ''))} className='flex-1 bg-transparent text-primary text-sm focus:outline-none' />
                </div>
              </div>
              <div>
                <label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>Email</label>
                <input type='email' value={editEmail} onChange={e => setEditEmail(e.target.value)} className='w-full bg-input border border-border rounded-lg px-4 py-2.5 text-primary text-sm focus:border-teal/60 focus:outline-none' />
              </div>
              <div>
                <label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>Member Since</label>
                <div className='bg-input border border-border rounded-lg px-4 py-2.5 text-muted text-sm'>
                  {profile?.created_at ? new Date(profile.created_at).toLocaleDateString() : '—'}
                </div>
              </div>
              <div className='col-span-2'>
                <label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>Bio</label>
                <textarea value={editBio} onChange={e => setEditBio(e.target.value)} rows={2} placeholder='e.g. Mathematics teacher with 5 years experience…' className='w-full bg-input border border-border rounded-lg px-4 py-2.5 text-primary text-sm focus:border-teal/60 focus:outline-none resize-none' />
              </div>
            </div>
          </div>

          <div className='flex justify-end gap-3 mt-5 pt-5 border-t border-border'>
            <button onClick={() => setShowPwForm(!showPwForm)} className='btn-ghost text-sm'>🔒 Change Password</button>
            <button onClick={saveProfile} disabled={saving} className='btn-primary text-sm disabled:opacity-50'>{saving ? 'Saving…' : 'Save Profile'}</button>
          </div>

          {showPwForm && (
            <div className='mt-4 p-4 bg-app border border-border rounded-xl'>
              <h4 className='text-primary font-semibold text-sm mb-3'>Change Password</h4>
              <div className='grid grid-cols-3 gap-3'>
                <div>
                  <label className='text-muted text-xs block mb-1'>Current</label>
                  <input type='password' value={oldPw} onChange={e => setOldPw(e.target.value)} className='w-full bg-input border border-border rounded-lg px-3 py-2 text-primary text-sm focus:outline-none' />
                </div>
                <div>
                  <label className='text-muted text-xs block mb-1'>New Password</label>
                  <input type='password' value={newPw} onChange={e => setNewPw(e.target.value)} className='w-full bg-input border border-border rounded-lg px-3 py-2 text-primary text-sm focus:outline-none' />
                </div>
                <div>
                  <label className='text-muted text-xs block mb-1'>Confirm</label>
                  <input type='password' value={confirmPw} onChange={e => setConfirmPw(e.target.value)} className='w-full bg-input border border-border rounded-lg px-3 py-2 text-primary text-sm focus:outline-none' />
                </div>
              </div>
              {pwError && <p className='text-red-400 text-xs mt-2'>{pwError}</p>}
              {pwSuccess && <p className='text-green-400 text-xs mt-2'>{pwSuccess}</p>}
              <button onClick={changePassword} className='btn-primary text-sm mt-3'>Update Password</button>
            </div>
          )}
        </div>

        {/* Teaching assignments */}
        <div className='card p-6'>
          <div className='flex items-center justify-between mb-4'>
            <div>
              <h3 className='text-primary font-semibold'>Teaching Assignments</h3>
              <p className='text-muted text-xs mt-0.5'>Subjects and grades you are assigned to teach</p>
            </div>
            <button onClick={() => setAddingGrade(!addingGrade)} className='btn-primary text-sm'>
              {addingGrade ? 'Cancel' : '+ Add Assignment'}
            </button>
          </div>
          {assignments.length > 0 ? (
            <div className='flex flex-wrap gap-2 mb-4'>
              {assignments.map(a => <GradeBadge key={a.id} assignment={a} onRemove={id => setDeleteConfirm(id)} />)}
            </div>
          ) : (
            <div className='py-6 text-center border border-dashed border-border rounded-xl text-muted text-sm mb-4'>
              No assignments yet. Add your first subject below.
            </div>
          )}

          {addingGrade && (
            <div className='p-5 bg-app border border-border rounded-xl'>
              <h4 className='text-primary font-semibold text-sm mb-4'>Add Teaching Assignment</h4>
              <div className='flex gap-2 p-1 bg-card border border-border rounded-xl mb-4'>
                <button type='button' onClick={() => setAssignMode('create')} className={`flex-1 py-2 rounded-lg text-xs font-medium transition-all ${assignMode === 'create' ? 'bg-teal text-app' : 'text-muted hover:text-primary'}`}>➕ Create New Subject</button>
                <button type='button' onClick={() => setAssignMode('existing')} className={`flex-1 py-2 rounded-lg text-xs font-medium transition-all ${assignMode === 'existing' ? 'bg-teal text-app' : 'text-muted hover:text-primary'}`}>📚 Use Existing Subject</button>
              </div>

              {assignMode === 'create' && (
                <div className='space-y-3 mb-4'>
                  <div>
                    <label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>Subject Name</label>
                    <input value={newSubjName} onChange={e => setNewSubjName(e.target.value)} placeholder='e.g. Mathematics, Science, English…' className='w-full bg-input border border-border rounded-lg px-4 py-2.5 text-primary text-sm focus:outline-none' />
                  </div>
                  <div className='relative'>
                    <label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>Subject Code</label>
                    <input value={newSubjCode} onChange={e => setNewSubjCode(e.target.value.toUpperCase().replace(/\s/g, '').slice(0, 6))} onFocus={() => setShowCodeSugg(true)} onBlur={() => setTimeout(() => setShowCodeSugg(false), 150)} placeholder='e.g. MATH' maxLength={6} className='w-full bg-input border border-border rounded-lg px-4 py-2.5 text-primary text-sm focus:outline-none' />
                    {showCodeSugg && (
                      <div className='absolute top-full left-0 right-0 mt-1 bg-card border border-border rounded-xl p-3 z-20 shadow-lg'>
                        <div className='flex flex-wrap gap-2'>
                          {SUBJECT_CODE_SUGGESTIONS.filter(c => !newSubjCode || c.startsWith(newSubjCode)).map(c => (
                            <button key={c} type='button' onMouseDown={() => setNewSubjCode(c)} className='text-xs px-2.5 py-1 border border-border rounded-lg text-muted hover:text-teal hover:border-teal/40'>{c}</button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {assignMode === 'existing' && (
                <div className='mb-4'>
                  <label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>Select Subject</label>
                  <select value={newSubjId} onChange={e => setNewSubjId(e.target.value)} className='w-full bg-input border border-border rounded-lg px-4 py-2.5 text-primary text-sm focus:outline-none'>
                    {existingSubjs.map(s => <option key={s.id} value={s.id}>{s.name} ({s.code})</option>)}
                  </select>
                </div>
              )}

              <div>
                <label className='text-muted text-xs uppercase tracking-wide block mb-2'>Grade</label>
                <select value={newGrade} onChange={e => setNewGrade(parseInt(e.target.value))} className='w-full bg-input border border-border rounded-lg px-4 py-2.5 text-primary text-sm focus:outline-none'>
                  {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19].map(g => {
                    let label = g <= 12 ? `Grade ${g}` : (g <= 17 ? `Level ${g - 12}` : (g === 18 ? 'Masters' : 'PhD'));
                    return <option key={g} value={g}>{label}</option>;
                  })}
                </select>
              </div>

              {assignError && <p className='text-red-400 text-xs mt-3'>{assignError}</p>}
              <button onClick={addAssignment} className='btn-primary text-sm w-full mt-4'>Add Assignment</button>
            </div>
          )}
        </div>

        {stats?.teacher_subjects?.length > 0 && (
          <div className='card p-5'>
            <h3 className='text-primary font-semibold mb-4'>My Subjects</h3>
            <div className='grid grid-cols-2 gap-3'>
              {stats.teacher_subjects.map((s, i) => (
                <div key={s.code || i} className='flex items-center gap-3 p-3 bg-app border border-border rounded-xl'>
                  <div className='w-9 h-9 rounded-lg flex items-center justify-center text-sm font-bold' style={{ background: `${['#00D4C8', '#3B82F6', '#8B5CF6', '#F59E0B', '#10B981'][i % 5]}20`, color: ['#00D4C8', '#3B82F6', '#8B5CF6', '#F59E0B', '#10B981'][i % 5] }}>
                    {(s.code || s.name || '?')[0]}
                  </div>
                  <div>
                    <p className='text-primary text-sm font-medium'>{s.name}</p>
                    <p className='text-muted text-xs'>{s.student_count || '—'} students</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className='flex gap-3'>
          <button onClick={() => navigate('/teacher')} className='btn-ghost text-sm'>← Dashboard</button>
        </div>
      </div>
    </PageShell>
  );
}