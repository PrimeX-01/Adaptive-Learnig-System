import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import ReactMarkdown from 'react-markdown';
import PageShell from '../components/PageShell';
import api from '../services/api';
import AudioPlayer from '../components/AudioPlayer';

const CONTENT_ICONS = { text:'📝', link:'🔗', image:'🖼', pdf:'📄', audio:'🎧' };
const CONTENT_LABELS = { text:'Note', link:'Link', image:'Image', pdf:'PDF', audio:'Audio' };

function useStudyTimer(active) {
  const [seconds, setSeconds] = useState(0);
  const ref = useRef(null);
  useEffect(() => {
    if (active) { ref.current = setInterval(() => setSeconds(s => s + 1), 1000); }
    else { clearInterval(ref.current); }
    return () => clearInterval(ref.current);
  }, [active]);
  const minutes = Math.floor(seconds / 60);
  const display = `${String(minutes).padStart(2,'0')}:${String(seconds%60).padStart(2,'0')}`;
  return { seconds, minutes, display };
}

function LibraryTutorPanel({ content, sid, fcl, learningStyle, onClose }) {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [initialized, setInitialized] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior:'smooth' }); }, [messages]);

  useEffect(() => {
    if (initialized) return;
    setInitialized(true);
    (async () => {
      try {
        const { data } = await api.post('/api/chat/new-session', { student_id: parseInt(sid), subject_id: content.subject_id });
        setSessionId(data.session_id);
        setSending(true);
        const initMsg = `I am studying a document titled "${content.title}". Here is the content:\n\n${content.file_data?.slice(0, 3000)}\n\nPlease summarise the key points for me and ask what I would like to explore first.`;
        const res = await api.post('/api/chat/message', {
          session_id: data.session_id, student_id: parseInt(sid),
          message: initMsg, topic: content.subject_code || 'general',
          fcl_level: fcl, learning_style: learningStyle,
        }, { timeout: 90000 });
        setMessages([{ role:'assistant', content: res.data.response }]);
      } catch { setMessages([{ role:'assistant', content:'Ready to help you study this document. What would you like to know?' }]); }
      finally { setSending(false); }
    })();
  }, []);

  const send = async () => {
    if (!input.trim() || sending || !sessionId) return;
    const msg = input.trim(); setInput('');
    setMessages(m => [...m, { role:'user', content: msg }]); setSending(true);
    try {
      const res = await api.post('/api/chat/message', {
        session_id: sessionId, student_id: parseInt(sid), message: msg,
        topic: content.subject_code || 'general', fcl_level: fcl, learning_style: learningStyle,
      }, { timeout: 90000 });
      setMessages(m => [...m, { role:'assistant', content: res.data.response }]);
    } catch { setMessages(m => [...m, { role:'assistant', content:'Connection error. Try again.' }]); }
    finally { setSending(false); }
  };

  return (
    <div className='flex flex-col h-full border-l border-border'>
      <div className='px-4 py-3 border-b border-border flex items-center justify-between flex-shrink-0'>
        <div><p className='text-primary font-semibold text-sm'>AI Tutor</p><p className='text-muted text-xs'>Studying: {content.title}</p></div>
        <button onClick={onClose} className='text-muted hover:text-primary'>✕</button>
      </div>
      <div className='flex-1 overflow-y-auto px-4 py-3 space-y-3'>
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role==='user'?'justify-end':'justify-start'}`}>
            {m.role==='assistant' && <div className='w-6 h-6 rounded-md bg-teal/15 border border-teal/30 flex items-center justify-center text-teal text-xs mr-2 mt-0.5 flex-shrink-0'>AI</div>}
            <div className={`max-w-[280px] rounded-xl px-3 py-2 text-xs leading-relaxed ${m.role==='user'?'bg-teal/10 border border-teal/30':'bg-card border border-border'} text-primary`}>
              <ReactMarkdown>{m.content}</ReactMarkdown>
            </div>
          </div>
        ))}
        {sending && <div className='flex gap-2'><div className='w-6 h-6 rounded-md bg-teal/15 border border-teal/30 flex items-center justify-center text-teal text-xs'>AI</div><div className='bg-card border border-border rounded-xl px-3 py-2 flex gap-1'>{[0,1,2].map(i=><div key={i} className='w-1.5 h-1.5 rounded-full bg-teal animate-bounce' style={{animationDelay:`${i*150}ms`}}/>)}</div></div>}
        <div ref={bottomRef}/>
      </div>
      <div className='px-4 py-3 border-t border-border flex gap-2 flex-shrink-0'>
        <input value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>e.key==='Enter'&&send()} placeholder='Ask about this content…' className='flex-1 bg-input border border-border rounded-lg px-3 py-2 text-primary text-xs focus:outline-none focus:border-teal/60'/>
        <button onClick={send} disabled={sending||!input.trim()} className='btn-primary px-3 py-2 text-xs disabled:opacity-50'>Send</button>
      </div>
    </div>
  );
}

function ContentViewer({ content, sid, fcl, learningStyle, onClose, onSessionEnd }) {
  const [showTutor, setShowTutor] = useState(false);
  const timer = useStudyTimer(true);
  const sessionStartedRef = useRef(null);

  useEffect(() => {
    api.post('/api/library/session/start', null, { params: { student_id: sid, content_id: content.id } })
      .then(r => { sessionStartedRef.current = r.data.session_id; })
      .catch(() => {});
    return () => {
      if (timer.minutes >= 1) {
        api.post('/api/library/session/end', {
          student_id: parseInt(sid),
          content_id: content.id,
          duration_minutes: timer.minutes,
          ai_tutor_used: showTutor,
        }).then(r => onSessionEnd && onSessionEnd(r.data)).catch(() => {});
      }
    };
  }, []);

  const renderBody = () => {
    switch (content.content_type) {
      case 'text':
        return <div className='prose prose-invert max-w-none'><ReactMarkdown>{content.file_data}</ReactMarkdown></div>;
      case 'link':
        return (
          <div className='text-center py-16'>
            <span className='text-5xl block mb-4'>🔗</span>
            <p className='text-primary font-semibold mb-2'>{content.title}</p>
            {content.description && <p className='text-muted text-sm mb-6'>{content.description}</p>}
            <a href={content.file_data} target='_blank' rel='noreferrer' className='btn-primary text-sm inline-flex items-center gap-2'>Open Resource ↗</a>
            <p className='text-muted text-xs mt-4 break-all'>{content.file_data}</p>
          </div>
        );
      case 'image':
        return <div className='text-center'><img src={content.file_data} alt={content.title} className='max-w-full rounded-xl border border-border mx-auto' /></div>;
      case 'pdf':
        return (
          <div className='text-center py-16'>
            <span className='text-5xl block mb-4'>📄</span>
            <p className='text-primary font-semibold mb-2'>{content.title}</p>
            {content.description && <p className='text-muted text-sm mb-6'>{content.description}</p>}
            <a href={content.file_data} target='_blank' rel='noreferrer' className='btn-primary text-sm inline-flex items-center gap-2'>Open PDF ↗</a>
          </div>
        );
      case 'audio':
        return (
          <div className='text-center py-8'>
            <div className='flex flex-col items-center gap-4'>
              <span className='text-6xl'>🎧</span>
              <p className='text-primary font-semibold'>{content.title}</p>
              {content.description && <p className='text-muted text-sm'>{content.description}</p>}
              <AudioPlayer text={content.file_data || ''} label="Play Audio" />
            </div>
          </div>
        );
      default:
        return <p className='text-muted text-sm'>Unsupported content type.</p>;
    }
  };

  return (
    <div className='fixed inset-0 bg-black/60 z-50 flex'>
      <div className={`bg-app flex flex-col ${showTutor ? 'flex-1' : 'w-full max-w-4xl mx-auto'}`}>
        <div className='flex items-center justify-between px-6 py-4 border-b border-border flex-shrink-0'>
          <div className='flex items-center gap-3'>
            <span className='text-2xl'>{CONTENT_ICONS[content.content_type]}</span>
            <div><h2 className='text-primary font-semibold'>{content.title}</h2><p className='text-muted text-xs'>{content.subject_name} · {CONTENT_LABELS[content.content_type]}</p></div>
          </div>
          <div className='flex items-center gap-3'>
            <div className='flex items-center gap-2 px-3 py-1.5 bg-teal/10 border border-teal/30 rounded-lg'>
              <span className='w-2 h-2 rounded-full bg-green-400 animate-pulse'/>
              <span className='text-teal text-xs stat-number'>{timer.display}</span>
            </div>
            <button onClick={() => setShowTutor(!showTutor)} className={`btn-ghost text-xs flex items-center gap-2 ${showTutor ? 'border-teal/40 text-teal' : ''}`}>
              ◈ {showTutor ? 'Hide Tutor' : 'Study with AI Tutor'}
            </button>
            <button onClick={onClose} className='text-muted hover:text-primary text-xl'>✕</button>
          </div>
        </div>
        <div className='flex-1 overflow-y-auto p-6'>{renderBody()}</div>
      </div>
      {showTutor && (
        <div className='w-96 bg-sidebar flex flex-col flex-shrink-0'>
          <LibraryTutorPanel content={content} sid={sid} fcl={fcl} learningStyle={learningStyle} onClose={() => setShowTutor(false)}/>
        </div>
      )}
    </div>
  );
}

function LibrarySkeleton() {
  return (
    <div className='flex gap-6 animate-pulse'>
      <div className='w-64 flex-shrink-0 space-y-2'>
        <div className='h-10 bg-border rounded w-full' />
        <div className='h-10 bg-border rounded w-full' />
        <div className='h-10 bg-border rounded w-full' />
      </div>
      <div className='flex-1'><div className='h-8 bg-border rounded w-1/3 mb-6' /><div className='grid grid-cols-2 gap-4'><div className='h-32 bg-border rounded' /><div className='h-32 bg-border rounded' /></div></div>
    </div>
  );
}

export default function LibraryPage() {
  const { user, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const sid = user?.id || localStorage.getItem('sa_studentId');

  const [subjects, setSubjects] = useState([]);
  const [activeSubject, setActiveSubject] = useState(null);
  const [subjectContent, setSubjectContent] = useState([]);
  const [contentLoading, setContentLoading] = useState(false);
  const [openContent, setOpenContent] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [pointsToast, setPointsToast] = useState(null);
  const [filterType, setFilterType] = useState('all');
  const [search, setSearch] = useState('');

  useEffect(() => {
    if (!sid) {
      if (!isAuthenticated) navigate('/auth');
      else setLoading(false);
      return;
    }
    Promise.all([
      api.get(`/api/library/student/${sid}`),
      api.get(`/api/students/${sid}/profile`),
    ]).then(([libRes, profRes]) => {
      setSubjects(libRes.data || []);
      setProfile(profRes.data);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [sid, isAuthenticated, navigate]);

  const openSubject = async (subject) => {
    setActiveSubject(subject);
    setContentLoading(true);
    try {
      const { data } = await api.get(`/api/library/subject/${subject.subject_id}/student/${sid}`);
      setSubjectContent(data || []);
    } catch { setSubjectContent([]); }
    finally { setContentLoading(false); }
  };

  const fcl = profile?.fcl_level || 5;
  const learningStyle = profile?.preferred_learning_style || 'reading';

  const filteredContent = subjectContent.filter(item => {
    const typeOk = filterType === 'all' || item.content_type === filterType;
    const searchOk = !search || item.title.toLowerCase().includes(search.toLowerCase()) || item.description?.toLowerCase().includes(search.toLowerCase());
    return typeOk && searchOk;
  });

  const handleSessionEnd = (result) => {
    if (result?.points_earned > 0) {
      setPointsToast(`+${result.points_earned} pts earned for studying!${result.fcl_changed ? ` FCL advanced!` : ''}`);
      setTimeout(() => setPointsToast(null), 4000);
    }
  };

  if (!sid) return <div className='min-h-screen bg-app flex items-center justify-center'><p>Please log in. <Link to="/auth">Login</Link></p></div>;
  if (loading) return <LibrarySkeleton />;

  return (
    <PageShell title='Library' subtitle='Your learning resources by subject'>
      {pointsToast && <div className='fixed top-4 right-4 z-50 px-5 py-3 bg-teal text-app rounded-xl font-medium text-sm shadow-lg animate-bounce'>🎯 {pointsToast}</div>}
      {openContent && <ContentViewer content={openContent} sid={sid} fcl={fcl} learningStyle={learningStyle} onClose={() => setOpenContent(null)} onSessionEnd={handleSessionEnd}/>}
      <div className='flex gap-6 flex-wrap md:flex-nowrap'>
        <div className='w-full md:w-64 flex-shrink-0'>
          <h3 className='text-muted text-xs uppercase tracking-wide mb-3'>Your Subjects</h3>
          <div className='space-y-2'>
            {subjects.length === 0 ? <div className='card p-4 text-center'><p className='text-muted text-xs'>No library content yet for your subjects.</p></div>
            : subjects.map(s => (
              <button key={s.subject_id} onClick={() => openSubject(s)} className={`w-full text-left p-4 rounded-xl border transition-all ${activeSubject?.subject_id===s.subject_id?'border-teal bg-teal/5':'card-hover border-border hover:border-teal/30'}`}>
                <div className='flex items-center justify-between mb-1'><span className='text-primary font-medium text-sm'>{s.subject_name}</span><span className='badge-teal text-xs'>{s.items?.length || 0}</span></div>
                <span className='text-muted text-xs'>{s.subject_code}</span>
              </button>
            ))}
          </div>
        </div>
        <div className='flex-1 min-w-0'>
          {!activeSubject ? (
            <div className='py-20 text-center'><span className='text-6xl block mb-4'>📚</span><h2 className='text-primary font-semibold text-lg mb-2'>Welcome to Your Library</h2><p className='text-muted text-sm mb-1'>Select a subject on the left to browse your learning resources.</p></div>
          ) : (
            <>
              <div className='flex items-center justify-between mb-5'><div><h2 className='text-primary font-semibold text-lg'>{activeSubject.subject_name}</h2><p className='text-muted text-xs'>{filteredContent.length} resource{filteredContent.length!==1?'s':''} available</p></div></div>
              <div className='flex flex-wrap items-center gap-3 mb-5'>
                <input value={search} onChange={e=>setSearch(e.target.value)} placeholder='Search resources…' className='bg-input border border-border rounded-lg px-3 py-1.5 text-primary text-sm focus:border-teal/60 focus:outline-none w-48'/>
                {['all','text','link','image','pdf','audio'].map(type => (
                  <button key={type} onClick={()=>setFilterType(type)} className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${filterType===type?'border-teal bg-teal/10 text-teal':'border-border text-muted hover:text-primary'}`}>
                    {type==='all'?'All':CONTENT_LABELS[type]}
                  </button>
                ))}
              </div>
              {contentLoading ? <div className='py-16 text-center'><div className='w-8 h-8 border-4 border-teal/30 border-t-teal rounded-full animate-spin mx-auto'/></div>
              : filteredContent.length === 0 ? <div className='py-16 text-center'><span className='text-4xl block mb-3'>🔍</span><p className='text-muted text-sm'>No resources found for your filters.</p></div>
              : <div className='grid grid-cols-1 sm:grid-cols-2 gap-4'>
                  {filteredContent.map(item => (
                    <div key={item.id} className='card-hover p-5 flex flex-col gap-3 cursor-pointer' onClick={() => setOpenContent({...item, subject_name:activeSubject.subject_name, subject_code:activeSubject.subject_code})}>
                      <div className='flex items-start gap-3'><span className='text-2xl flex-shrink-0'>{CONTENT_ICONS[item.content_type]}</span><div className='flex-1 min-w-0'><h4 className='text-primary font-semibold text-sm mb-0.5 truncate'>{item.title}</h4>{item.description && <p className='text-muted text-xs line-clamp-2'>{item.description}</p>}</div></div>
                      {item.content_type === 'text' && <p className='text-muted text-xs line-clamp-3 bg-app rounded-lg p-3 border border-border'>{item.file_data}</p>}
                      {item.content_type === 'link' && <p className='text-teal text-xs truncate'>{item.file_data}</p>}
                      <div className='flex flex-wrap items-center gap-2 mt-auto pt-2 border-t border-border/50'>
                        <span className='text-xs px-2 py-0.5 bg-teal/10 border border-teal/30 text-teal rounded'>{CONTENT_LABELS[item.content_type]}</span>
                        {(item.topic_tags||[]).slice(0,2).map(tag=><span key={tag} className='text-xs px-2 py-0.5 bg-border/50 text-muted rounded'>{tag}</span>)}
                        <span className='ml-auto text-muted text-xs'>{new Date(item.uploaded_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  ))}
                </div>
              }
            </>
          )}
        </div>
      </div>
    </PageShell>
  );
}