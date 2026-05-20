import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import PageShell from '../components/PageShell';
import api from '../services/api';

export default function MessagesPage() {
  const [params] = useSearchParams();
  const [view,   setView]  = useState(params.get('compose')?'compose':'inbox');
  const [inbox,  setInbox] = useState([]);
  const [sent,   setSent]  = useState([]);
  const [thread, setThread]= useState(null);
  const [contacts,setContacts]=useState([]);  // teachers for students; students for teachers
  const [toId,   setToId]  = useState('');
  const [subj,   setSubj]  = useState('');
  const [body,   setBody]  = useState('');
  const [reply,  setReply] = useState('');
  const [sending,setSending]=useState(false);
  const [success,setSuccess]=useState(false);
  const sid = window.__studentId;
  const isTeacher = window.__isTeacher;

  const loadMessages = async () => {
    const [ib, st] = await Promise.all([api.get(`/api/messages/inbox/${sid}`), api.get(`/api/messages/sent/${sid}`)]);
    setInbox(ib.data); setSent(st.data);
  };

  useEffect(() => {
    loadMessages();
    // Load contacts: students load their enrolled teachers; teachers load all students
    if (isTeacher) {
      api.get('/api/students/all').then(r=>setContacts(r.data.filter(s=>!s.is_teacher)));
    } else {
      api.get(`/api/subjects/enrolled/${sid}`).then(r=>{
        const teachers = r.data.filter(e=>e.teacher_id).map(e=>({id:e.teacher_id,name:e.teacher_name,subject:e.subject_name}));
        setContacts(teachers);
      });
    }
  }, [sid]);

  async function sendMessage() {
    if (!toId||!subj.trim()||!body.trim()) return;
    setSending(true);
    await api.post('/api/messages/send', { receiver_id:parseInt(toId), subject:subj, body, thread_id:thread?.thread_id||thread?.id||null });
    setSuccess(true); setSubj(''); setBody(''); setToId('');
    await loadMessages();
    setSending(false); setTimeout(()=>setSuccess(false),3000);
  }

  async function sendReply() {
    if (!reply.trim()) return;
    setSending(true);
    const replyTo = thread.sender_id === sid ? thread.receiver_id : thread.sender_id;
    await api.post('/api/messages/send', { receiver_id:replyTo, subject:`Re: ${thread.subject}`, body:reply, thread_id:thread.thread_id||thread.id });
    setReply('');
    await loadMessages();
    setSending(false);
  }

  const unread = inbox.filter(m=>!m.is_read).length;

  return (
    <PageShell title='Messages' subtitle={`${unread} unread`} unreadCount={unread}>
      <div className='flex gap-4 h-[calc(100vh-8rem)]'>
        {/* Left: thread list */}
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
        {/* Right: content */}
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
                <div><label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>To</label>
                  <select value={toId} onChange={e=>setToId(e.target.value)} className='w-full bg-input border border-border rounded-lg px-3 py-2.5 text-primary text-sm focus:border-teal/60 focus:outline-none'>
                    <option value=''>Select recipient...</option>
                    {contacts.map(c=><option key={c.id} value={c.id}>{c.name}{c.subject?` (${c.subject})`:c.grade?` (Grade ${c.grade})`:''}</option>)}
                  </select></div>
                <div><label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>Subject</label><input value={subj} onChange={e=>setSubj(e.target.value)} placeholder='What is this about?' className='w-full bg-input border border-border rounded-lg px-3 py-2.5 text-primary text-sm focus:border-teal/60 focus:outline-none' /></div>
                <div className='flex-1'><label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>Message</label><textarea rows={8} value={body} onChange={e=>setBody(e.target.value)} placeholder='Write your message here...' className='w-full bg-input border border-border rounded-xl px-4 py-3 text-primary text-sm focus:border-teal/60 resize-none focus:outline-none' /></div>
              </div>
              <div className='flex justify-between items-center mt-4 pt-4 border-t border-border'><p className='text-muted text-xs'>{isTeacher?'Student will be notified immediately':'Your teacher will be notified immediately'}</p><div className='flex gap-2'><button onClick={()=>{setSubj('');setBody('');setToId('');}} className='btn-ghost'>Clear</button><button onClick={sendMessage} disabled={!toId||!subj.trim()||!body.trim()||sending} className='btn-primary disabled:opacity-50'>{sending?'Sending...':'✉ Send Message'}</button></div></div>
            </div>
          )}
          {(view==='inbox'||view==='sent')&&!thread&&(<div className='flex-1 flex flex-col items-center justify-center text-muted gap-3'><span className='text-4xl'>✉</span><p className='text-sm'>Select a message to read it</p><button onClick={()=>setView('compose')} className='btn-primary text-xs'>Compose New Message</button></div>)}
        </div>
      </div>
    </PageShell>
  );
}
