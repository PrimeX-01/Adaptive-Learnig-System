import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import PageShell from '../components/PageShell';
import api from '../services/api';

const CHART_TOOLTIP = { contentStyle:{ background:'#0F172A', border:'1px solid #1E293B', borderRadius:'8px', color:'#F1F5F9', fontSize:11 }, labelStyle:{color:'#64748B'} };
const TABS = ['Overview','Students','Messages','Interventions'];

export default function TeacherDashboard() {
  const nav = useNavigate();
  // Double guard
  useEffect(() => { if (!window.__isTeacher) nav('/dashboard', {replace:true}); },[]);
  if (!window.__isTeacher) return null;

  const [tab,          setTab]      = useState('Overview');
  const [dashData,     setDashData] = useState(null);
  const [selSubject,   setSelSubj]  = useState('all');  // selected subject filter
  const [selectedStudent, setSelSt] = useState(null);
  const [studentDetail,   setDetail]= useState(null);
  const [loading,      setLoading]  = useState(true);
  // Interventions state
  const [selIds,   setSelIds]  = useState([]);
  const [tipTopic, setTipTopic]= useState('mathematics_algebra');
  const [tipNote,  setTipNote] = useState('');
  const [tipSending, setTipSend]=useState(false);
  const [tipPreview, setTipPrev]=useState('');
  // Messages state
  const [inbox, setInbox] = useState([]);
  const [thread,setThread]= useState(null);
  const [reply, setReply] = useState('');
  const sid = window.__studentId;

  useEffect(() => {
    Promise.all([
      api.get(`/api/teachers/dashboard/1${selSubject!=='all'?`?subject_code=${selSubject}`:''}`),
      api.get(`/api/messages/inbox/${sid}`),
    ]).then(([d, msgs]) => {
      setDashData(d.data); setInbox(msgs.data);
    }).finally(()=>setLoading(false));
  }, [sid, selSubject]);

  async function openStudentDetail(studentId) {
    setSelSt(studentId);
    const { data } = await api.get(`/api/teachers/student/${studentId}/deep-dive`);
    setDetail(data);
  }

  async function sendReply(receiverId) {
    if (!reply.trim()) return;
    await api.post('/api/messages/send', {
      receiver_id: receiverId, subject: `Re: ${thread?.subject}`,
      body: reply, thread_id: thread?.thread_id || thread?.id,
    });
    setReply(''); setThread(null);
    const { data } = await api.get(`/api/messages/inbox/${sid}`);
    setInbox(data);
  }

  async function sendBulkTip() {
    if (!selIds.length) return;
    setTipSend(true);
    const { data } = await api.post('/api/messages/bulk-tip', {
      student_ids: selIds, topic_id: tipTopic, custom_note: tipNote,
    });
    setTipPrev(data.tip_preview); setTipSend(false); setSelIds([]);
  }

  if (loading) return <div className='min-h-screen bg-app flex items-center justify-center'><div className='w-10 h-10 border-4 border-teal/30 border-t-teal rounded-full animate-spin' /></div>;

  const { students=[], at_risk=[], fcl_distribution=[], teacher_subjects=[], total_students=0 } = dashData||{};
  const unread = inbox.filter(m=>!m.is_read).length;

  return (
    <PageShell title='Teacher Command Centre' subtitle={`${total_students} students across your subjects`} unreadCount={unread}>

      {/* Subject filter bar */}
      <div className='flex items-center gap-3 mb-5'>
        <span className='text-muted text-xs'>Showing:</span>
        <button onClick={()=>setSelSubj('all')} className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${selSubject==='all'?'border-teal bg-teal/10 text-teal':'border-border text-muted hover:text-primary'}`}>All Subjects</button>
        {teacher_subjects.map(s=>(
          <button key={s.code} onClick={()=>setSelSubj(s.code)} className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${selSubject===s.code?'border-teal bg-teal/10 text-teal':'border-border text-muted hover:text-primary'}`}>{s.name}</button>
        ))}
      </div>

      {/* Tab navigation */}
      <div className='flex gap-1 p-1 bg-card border border-border rounded-xl mb-6 w-fit'>
        {TABS.map(t=>(
          <button key={t} onClick={()=>setTab(t)} className={`px-5 py-2 rounded-lg text-sm font-medium transition-all ${tab===t?'bg-teal text-app':'text-muted hover:text-primary'}`}>
            {t}{t==='Messages'&&unread>0&&<span className='ml-1 badge-teal text-xs'>{unread}</span>}
          </button>
        ))}
      </div>

      {/* OVERVIEW TAB */}
      {tab==='Overview' && (
        <div>
          <div className='grid grid-cols-4 gap-4 mb-6'>
            {[['Total Students',total_students,'👥'],['At Risk',at_risk.length,'⚠'],['Avg Accuracy',students.length?Math.round(students.reduce((s,x)=>s+x.accuracy,0)/students.length)+'%':'—','◎'],['Subjects',teacher_subjects.length,'📚']].map(([l,v,i])=>(
              <div key={l} className='card-hover p-5'><div className='flex justify-between items-center mb-3'><span className='text-muted text-xs uppercase tracking-wide'>{l}</span><span className='text-xl'>{i}</span></div><div className='stat-number text-3xl font-bold text-primary'>{v}</div></div>
            ))}
          </div>
          <div className='card p-5'>
            <h3 className='text-primary font-semibold text-sm mb-4'>FCL Distribution</h3>
            <ResponsiveContainer width='100%' height={200}>
              <BarChart data={fcl_distribution}><CartesianGrid strokeDasharray='3 3' stroke='#1E293B' /><XAxis dataKey='fcl_label' tick={{fontSize:11,fill:'#64748B'}} /><YAxis tick={{fontSize:11,fill:'#64748B'}} /><Tooltip {...CHART_TOOLTIP} /><Bar dataKey='count' fill='#00D4C8' radius={[3,3,0,0]} /></BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* STUDENTS TAB */}
      {tab==='Students' && (
        <div className='card overflow-hidden'>
          <div className='px-5 py-4 border-b border-border'><h3 className='text-primary font-semibold text-sm'>All Students ({students.length})</h3></div>
          <div className='overflow-x-auto'>
            <table className='w-full'>
              <thead><tr className='border-b border-border'>{['Name','Grade','Subject','FCL','Accuracy','Hints/Q','Status','Actions'].map(h=><th key={h} className='py-3 px-4 text-left text-muted text-xs uppercase tracking-wide font-medium'>{h}</th>)}</tr></thead>
              <tbody>
                {students.map(s=>(
                  <tr key={`${s.student_id}-${s.subject_code}`} className='border-b border-border/50 hover:bg-border/20 transition-colors'>
                    <td className='py-3 px-4 text-primary text-sm font-medium'>{s.name}</td>
                    <td className='py-3 px-4 stat-number text-muted text-sm'>{s.grade}</td>
                    <td className='py-3 px-4'><span className='badge-teal text-xs'>{s.subject_code}</span></td>
                    <td className='py-3 px-4 stat-number text-teal font-bold'>{s.fcl_level}</td>
                    <td className='py-3 px-4 stat-number text-muted text-sm'>{s.accuracy}%</td>
                    <td className='py-3 px-4 stat-number text-muted text-sm'>{s.hint_density}</td>
                    <td className='py-3 px-4'>{s.is_at_risk?<span className='badge-red'>At Risk</span>:<span className='badge-green'>On Track</span>}</td>
                    <td className='py-3 px-4'><div className='flex gap-2'>
                      <button onClick={()=>openStudentDetail(s.student_id)} className='btn-ghost text-xs py-1 px-2'>View</button>
                      <button onClick={()=>{ setTab('Messages'); }} className='btn-primary text-xs py-1 px-2'>Message</button>
                    </div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {/* Student slide-over */}
          {studentDetail && (
            <>
              <div className='fixed inset-0 bg-black/50 z-40' onClick={()=>{setSelSt(null);setDetail(null);}} />
              <div className='fixed right-0 top-0 h-full w-96 bg-card border-l border-border z-50 overflow-y-auto'>
                <div className='sticky top-0 bg-card border-b border-border px-5 py-4 flex justify-between items-center'>
                  <div><h3 className='text-primary font-semibold'>{studentDetail.name}</h3></div>
                  <button onClick={()=>{setSelSt(null);setDetail(null);}} className='text-muted hover:text-primary text-xl'>✕</button>
                </div>
                <div className='p-5 space-y-4'>
                  <div className='grid grid-cols-2 gap-3'>{[['Accuracy',`${studentDetail.accuracy}%`],['Hint Density',studentDetail.avg_hint_density]].map(([l,v])=><div key={l} className='bg-app rounded-lg p-3 border border-border'><div className='text-muted text-xs mb-1'>{l}</div><div className='stat-number text-primary font-bold'>{v}</div></div>)}</div>
                  <div className='bg-amber-500/5 border border-amber-500/20 rounded-xl p-4'><h4 className='text-amber-400 text-xs font-semibold mb-2'>💡 AI Recommendations</h4><p className='text-primary text-xs leading-relaxed'>{studentDetail.ai_recommendations}</p></div>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* MESSAGES TAB */}
      {tab==='Messages' && (
        <div className='grid grid-cols-3 gap-4 h-96'>
          <div className='card overflow-hidden flex flex-col'>
            <div className='px-4 py-3 border-b border-border'><h3 className='text-primary font-semibold text-sm'>Inbox ({unread} unread)</h3></div>
            <div className='flex-1 overflow-y-auto'>
              {inbox.length===0&&<p className='text-muted text-sm p-4 text-center'>No messages yet</p>}
              {inbox.map(m=>(
                <button key={m.id} onClick={()=>setThread(m)} className={`w-full text-left px-4 py-3 border-b border-border/50 hover:bg-border/20 transition-colors ${!m.is_read?'bg-teal/5':''} ${thread?.id===m.id?'border-l-2 border-l-teal':''}`}>
                  <div className='flex justify-between mb-1'><span className={`text-xs font-semibold ${!m.is_read?'text-primary':'text-muted'}`}>{m.sender_name}</span><span className='text-muted text-xs'>{new Date(m.created_at).toLocaleDateString()}</span></div>
                  <div className={`text-xs truncate ${!m.is_read?'text-primary font-medium':'text-muted'}`}>{m.subject}</div>
                </button>
              ))}
            </div>
          </div>
          <div className='col-span-2 card flex flex-col'>
            {thread ? (<>
              <div className='px-5 py-4 border-b border-border'><h3 className='text-primary font-semibold'>{thread.subject}</h3><p className='text-muted text-xs'>From: {thread.sender_name}</p></div>
              <div className='flex-1 overflow-y-auto p-5'><p className='text-primary text-sm leading-relaxed whitespace-pre-wrap'>{thread.body}</p></div>
              <div className='border-t border-border p-4'>
                <textarea rows={3} value={reply} onChange={e=>setReply(e.target.value)} placeholder='Type your reply...' className='w-full bg-input border border-border rounded-xl px-4 py-3 text-primary text-sm focus:border-teal/60 resize-none mb-3 focus:outline-none' />
                <div className='flex justify-end gap-2'>
                  <button onClick={()=>setThread(null)} className='btn-ghost text-xs'>Clear</button>
                  <button onClick={()=>sendReply(thread.sender_id)} disabled={!reply.trim()} className='btn-primary text-xs disabled:opacity-50'>Send Reply</button>
                </div>
              </div>
            </>) : (
              <div className='flex-1 flex items-center justify-center text-muted'><p className='text-sm'>Select a message to read and reply</p></div>
            )}
          </div>
        </div>
      )}

      {/* INTERVENTIONS TAB */}
      {tab==='Interventions' && (
        <div className='grid grid-cols-3 gap-4'>
          <div className='col-span-2 card'>
            <div className='px-5 py-4 border-b border-border flex justify-between'><h3 className='text-primary font-semibold text-sm'>At-Risk Students ({at_risk.length})</h3><span className='text-muted text-xs'>{selIds.length} selected</span></div>
            {at_risk.map(s=>(
              <div key={s.student_id} className='px-5 py-3 border-b border-border/50 flex items-center gap-4 hover:bg-border/20 transition-colors'>
                <input type='checkbox' checked={selIds.includes(s.student_id)} onChange={e=>setSelIds(ids=>e.target.checked?[...ids,s.student_id]:ids.filter(i=>i!==s.student_id))} className='rounded border-border bg-input accent-teal' />
                <div className='flex-1'><div className='text-primary text-sm font-medium'>{s.name}</div><div className='text-muted text-xs'>{s.risk_reason} · {s.subject_code}</div></div>
                <span className='badge-red'>FCL {s.fcl_level}</span>
              </div>
            ))}
            {at_risk.length===0&&<p className='text-muted text-sm p-5 text-center'>No at-risk students in your subjects</p>}
          </div>
          <div className='card p-5 flex flex-col gap-4'>
            <h3 className='text-primary font-semibold text-sm'>Send Groq AI Tip</h3>
            <p className='text-muted text-xs'>Select students, choose a topic, and an AI-generated improvement tip will be sent to their notifications.</p>
            <div><label className='text-muted text-xs block mb-1.5 uppercase'>Topic</label>
              <select value={tipTopic} onChange={e=>setTipTopic(e.target.value)} className='w-full bg-input border border-border rounded-lg px-3 py-2 text-primary text-sm focus:border-teal/60 focus:outline-none'>
                {['mathematics_algebra','mathematics_geometry','science_biology','science_chemistry','english_comprehension','english_writing','social_studies','computer_science'].map(t=><option key={t} value={t}>{t.replace(/_/g,' ').replace(/\b\w/g,l=>l.toUpperCase())}</option>)}
              </select></div>
            <div><label className='text-muted text-xs block mb-1.5 uppercase'>Custom Note (optional)</label>
              <textarea rows={3} value={tipNote} onChange={e=>setTipNote(e.target.value)} placeholder='Additional context for the AI...' className='w-full bg-input border border-border rounded-lg px-3 py-2 text-primary text-sm focus:border-teal/60 resize-none focus:outline-none' /></div>
            {tipPreview && <div className='bg-teal/5 border border-teal/20 rounded-xl p-3 text-xs text-teal'><div className='font-semibold mb-1'>Sent tip preview:</div>{tipPreview}...</div>}
            <button onClick={sendBulkTip} disabled={!selIds.length||tipSending} className='btn-primary disabled:opacity-50 mt-auto'>{tipSending?'Generating tip...':  `Send to ${selIds.length} student${selIds.length!==1?'s':''}`}</button>
          </div>
        </div>
      )}
    </PageShell>
  );
}
