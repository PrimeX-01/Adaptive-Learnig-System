import { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import PageShell from '../components/PageShell';
import api from '../services/api';

export default function MessagesPage() {
  const { user, isAuthenticated } = useAuth();
  const [params] = useSearchParams();
  const [view, setView] = useState(params.get('compose')?'compose':'inbox');
  const [inbox, setInbox] = useState([]);
  const [sent, setSent] = useState([]);
  const [thread, setThread] = useState(null);
  const [recipientFilter, setRecipientFilter] = useState('all'); // 'all', 'teachers', 'classmates'
  const [recipients, setRecipients] = useState([]); // filtered list
  const [allTeachers, setAllTeachers] = useState([]);
  const [allClassmates, setAllClassmates] = useState([]);
  const [toId, setToId] = useState('');
  const [subj, setSubj] = useState('');
  const [body, setBody] = useState('');
  const [reply, setReply] = useState('');
  const [sending, setSending] = useState(false);
  const [success, setSuccess] = useState(false);
  
  const sid = user?.id || localStorage.getItem('sa_studentId');
  const isTeacher = user?.role === 'teacher' || localStorage.getItem('sa_isTeacher') === 'true';

  // Load messages and recipient lists
  useEffect(() => {
    if (!sid) return;
    async function loadData() {
      const [ib, st] = await Promise.all([
        api.get(`/api/messages/inbox/${sid}`),
        api.get(`/api/messages/sent/${sid}`)
      ]);
      setInbox(ib.data);
      setSent(st.data);

      // Load teachers and classmates
      if (!isTeacher) {
        // Get enrolled subjects to find teachers and classmates
        const subjectsRes = await api.get(`/api/subjects/enrolled/${sid}`);
        const subjects = subjectsRes.data || [];
        const teacherIds = [...new Set(subjects.map(s => s.teacher_id).filter(Boolean))];
        const teacherPromises = teacherIds.map(id => api.get(`/api/students/${id}/profile`).catch(() => null));
        const teacherProfiles = (await Promise.all(teacherPromises)).filter(p => p && p.data);
        const teachers = teacherProfiles.map(p => ({ id: p.data.id, name: p.data.name, type: 'teacher' }));

        // Get classmates: students enrolled in same subjects
        const subjectIds = subjects.map(s => s.subject_id);
        const classmatesSet = new Set();
        for (const subjId of subjectIds) {
          const studentsRes = await api.get(`/api/subjects/enrolled-students/${subjId}`).catch(() => ({ data: [] }));
          for (const stu of studentsRes.data) {
            if (stu.id != sid) classmatesSet.add({ id: stu.id, name: stu.name, type: 'classmate' });
          }
        }
        const classmates = Array.from(classmatesSet.values());
        setAllTeachers(teachers);
        setAllClassmates(classmates);
      } else {
        // For teachers: load all students
        const studentsRes = await api.get('/api/students/all');
        const students = studentsRes.data.filter(s => !s.is_teacher).map(s => ({ id: s.id, name: s.name, type: 'student' }));
        setAllTeachers([]);
        setAllClassmates(students);
      }
    }
    loadData();
  }, [sid, isTeacher]);

  useEffect(() => {
    // Apply filter
    if (recipientFilter === 'teachers') {
      setRecipients(allTeachers);
    } else if (recipientFilter === 'classmates') {
      setRecipients(allClassmates);
    } else {
      // Combine teachers + classmates for 'all'
      setRecipients([...allTeachers, ...allClassmates]);
    }
  }, [recipientFilter, allTeachers, allClassmates]);

  async function sendMessage() {
    if (!toId || !subj.trim() || !body.trim()) return;
    setSending(true);
    await api.post('/api/messages/send', { 
      receiver_id: parseInt(toId), 
      subject: subj, 
      body, 
      thread_id: thread?.thread_id || thread?.id || null 
    });
    setSuccess(true); setSubj(''); setBody(''); setToId('');
    await Promise.all([
      api.get(`/api/messages/inbox/${sid}`).then(r => setInbox(r.data)),
      api.get(`/api/messages/sent/${sid}`).then(r => setSent(r.data))
    ]);
    setSending(false); setTimeout(()=>setSuccess(false),3000);
  }

  async function sendReply() {
    if (!reply.trim()) return;
    setSending(true);
    const replyTo = thread.sender_id === sid ? thread.receiver_id : thread.sender_id;
    await api.post('/api/messages/send', { 
      receiver_id: replyTo, 
      subject: `Re: ${thread.subject}`, 
      body: reply, 
      thread_id: thread.thread_id || thread.id 
    });
    setReply('');
    await Promise.all([
      api.get(`/api/messages/inbox/${sid}`).then(r => setInbox(r.data)),
      api.get(`/api/messages/sent/${sid}`).then(r => setSent(r.data))
    ]);
    setSending(false);
  }

  if (!sid) return <div className='min-h-screen bg-app flex items-center justify-center'><Link to="/auth">Please log in</Link></div>;

  const unread = inbox.filter(m=>!m.is_read).length;
  const uniqueRecipients = recipients.filter((v,i,a)=>a.findIndex(t=>t.id===v.id)===i);

  return (
    <PageShell title='Messages' subtitle={`${unread} unread`} unreadCount={unread}>
      <div className='flex gap-4 h-[calc(100vh-8rem)]'>
        <div className='w-72 flex-shrink-0 card flex flex-col overflow-hidden'>
          <div className='flex border-b border-border'>
            {['inbox','sent','compose'].map(t=>(
              <button key={t} onClick={()=>{setView(t);setThread(null);}} className={`flex-1 py-3 text-xs font-medium capitalize transition-colors ${view===t||view==='thread'&&t==='inbox'?'text-teal border-b-2 border-teal':'text-muted hover:text-primary'}`}>
                {t}{t==='inbox'&&unread>0&&<span className='ml-1 badge-teal'>{unread}</span>}
              </button>
            ))}
          </div>
          <div className='flex-1 overflow-y-auto'>
            {(view==='inbox'||view==='thread')&&inbox.map(m=>(
              <button key={m.id} onClick={()=>{setThread(m);setView('thread');api.patch(`/api/messages/read/${m.id}`).catch(()=>{});}} className={`w-full text-left px-4 py-3 border-b border-border/50 hover:bg-border/20 transition-colors ${thread?.id===m.id?'bg-teal/5 border-l-2 border-l-teal':''} ${!m.is_read?'bg-teal/3':''}`}>
                <div className='flex justify-between mb-1'><span className={`text-xs font-semibold ${!m.is_read?'text-primary':'text-muted'}`}>{m.sender_name}</span><span className='text-muted text-xs'>{new Date(m.created_at).toLocaleDateString()}</span></div>
                <div className={`text-xs truncate ${!m.is_read?'text-primary font-medium':'text-muted'}`}>{m.subject}</div>
                {!m.is_read&&<div className='mt-1 w-1.5 h-1.5 rounded-full bg-teal' />}
              </button>
            ))}
            {view==='sent'&&sent.map(m=>(
              <button key={m.id} onClick={()=>{setThread(m);setView('thread');}} className='w-full text-left px-4 py-3 border-b border-border/50 hover:bg-border/20 transition-colors'>
                <div className='flex justify-between mb-1'><span className='text-muted text-xs'>To: {m.receiver_name}</span><span className='text-muted text-xs'>{new Date(m.created_at).toLocaleDateString()}</span></div>
                <div className='text-primary text-xs font-medium truncate'>{m.subject}</div>
              </button>
            ))}
          </div>
        </div>
        <div className='flex-1 card flex flex-col overflow-hidden'>
          {view==='thread'&&thread&&(
            <>
              <div className='px-5 py-4 border-b border-border'><h3 className='text-primary font-semibold'>{thread.subject}</h3><p className='text-muted text-xs'>{thread.sender_name?`From: ${thread.sender_name}`:`To: ${thread.receiver_name}`}</p></div>
              <div className='flex-1 overflow-y-auto p-5'><p className='text-primary text-sm leading-relaxed whitespace-pre-wrap'>{thread.body}</p></div>
              <div className='border-t border-border p-4'>
                <textarea rows={3} value={reply} onChange={e=>setReply(e.target.value)} placeholder='Write your reply...' className='w-full bg-input border border-border rounded-xl px-4 py-3 text-primary text-sm focus:border-teal/60 resize-none mb-3 focus:outline-none' />
                <div className='flex justify-end gap-2'><button onClick={()=>setReply('')} className='btn-ghost text-xs'>Clear</button><button onClick={sendReply} disabled={!reply.trim()||sending} className='btn-primary text-xs disabled:opacity-50'>{sending?'Sending...':'Send Reply'}</button></div>
              </div>
            </>
          )}
          {view==='compose'&&(
            <div className='flex-1 flex flex-col p-6'>
              <h3 className='text-primary font-semibold mb-5'>New Message</h3>
              {success&&<div className='mb-4 px-4 py-3 bg-teal/10 border border-teal/30 rounded-xl text-teal text-sm'>Message sent successfully!</div>}
              <div className='space-y-4 flex-1'>
                <div>
                  <label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>Filter recipients</label>
                  <select value={recipientFilter} onChange={e=>setRecipientFilter(e.target.value)} className='w-full bg-input border border-border rounded-lg px-3 py-2.5 text-primary text-sm focus:border-teal/60 focus:outline-none'>
                    <option value="all">All (Teachers + Classmates)</option>
                    <option value="teachers">Teachers Only</option>
                    <option value="classmates">Classmates Only</option>
                  </select>
                </div>
                <div>
                  <label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>To</label>
                  <select value={toId} onChange={e=>setToId(e.target.value)} className='w-full bg-input border border-border rounded-lg px-3 py-2.5 text-primary text-sm focus:border-teal/60 focus:outline-none'>
                    <option value=''>Select recipient...</option>
                    {uniqueRecipients.map(c=><option key={c.id} value={c.id}>{c.name} ({c.type})</option>)}
                  </select>
                </div>
                <div><label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>Subject</label><input value={subj} onChange={e=>setSubj(e.target.value)} placeholder='What is this about?' className='w-full bg-input border border-border rounded-lg px-3 py-2.5 text-primary text-sm focus:outline-none' /></div>
                <div className='flex-1'><label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>Message</label><textarea rows={8} value={body} onChange={e=>setBody(e.target.value)} placeholder='Write your message here...' className='w-full bg-input border border-border rounded-xl px-4 py-3 text-primary text-sm focus:border-teal/60 resize-none focus:outline-none' /></div>
              </div>
              <div className='flex justify-between items-center mt-4 pt-4 border-t border-border'>
                <p className='text-muted text-xs'>{isTeacher?'Student will be notified immediately':'Your teacher will be notified immediately'}</p>
                <div className='flex gap-2'><button onClick={()=>{setSubj('');setBody('');setToId('');}} className='btn-ghost'>Clear</button><button onClick={sendMessage} disabled={!toId||!subj.trim()||!body.trim()||sending} className='btn-primary disabled:opacity-50'>{sending?'Sending...':'✉ Send Message'}</button></div>
              </div>
            </div>
          )}
          {(view==='inbox'||view==='sent')&&!thread&&(<div className='flex-1 flex flex-col items-center justify-center text-muted gap-3'><span className='text-4xl'>✉</span><p className='text-sm'>Select a message to read it</p><button onClick={()=>setView('compose')} className='btn-primary text-xs'>Compose New Message</button></div>)}
        </div>
      </div>
    </PageShell>
  );
}