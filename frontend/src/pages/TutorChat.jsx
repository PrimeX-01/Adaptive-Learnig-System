import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import { InlineMath, BlockMath } from 'react-katex';
import 'katex/dist/katex.min.css';
import mermaid from 'mermaid';
import Sidebar from '../components/Sidebar';
import NotificationsPanel from '../components/NotificationsPanel';
import { useTTS } from '../hooks/useTTS';
import { useSpeechInput } from '../hooks/useSpeechInput';
import api from '../services/api';
import { useNavigate } from 'react-router-dom';

mermaid.initialize({
  startOnLoad: false, theme: 'dark',
  themeVariables: {
    primaryColor: '#00D4C8', background: '#0F172A', mainBkg: '#0F172A',
    nodeBorder: '#1E293B', labelBackground: '#0F172A', edgeLabelBackground: '#0F172A',
  },
});

const SUBJECT_TOPICS = {
  MATH: { name: 'Mathematics',      topics: ['mathematics_algebra','mathematics_geometry','mathematics_calculus','mathematics_statistics'] },
  SCI:  { name: 'Science',          topics: ['science_biology','science_chemistry','science_physics'] },
  ENG:  { name: 'English',          topics: ['english_comprehension','english_writing','english_literature'] },
  SOC:  { name: 'Social Studies',   topics: ['social_studies','civics'] },
  CS:   { name: 'Computer Science', topics: ['computer_science','programming'] },
};

function gradeToFCL(grade) {
  if (!grade || grade <= 0) return 6;
  if (grade <= 4)  return 2;
  if (grade <= 7)  return 4;
  if (grade <= 9)  return 6;
  if (grade <= 12) return 8;
  if (grade <= 15) return 9;
  if (grade <= 17) return 11;
  return 13;
}

function MsgBubble({ msg, onSpeak, imageUrl, youtubeLink }) {
  const ref = useRef(null);

  useEffect(() => {
    if (!ref.current) return;
    ref.current.querySelectorAll('code.language-mermaid').forEach(async block => {
      try {
        const { svg } = await mermaid.render('d' + Date.now(), block.textContent);
        const w = document.createElement('div');
        w.innerHTML = svg;
        w.className = 'my-4 overflow-x-auto';
        block.parentElement.replaceWith(w);
      } catch {}
    });
  }, [msg.content]);

  const comps = {
    code({ className, children }) {
      if (className === 'language-math') return <InlineMath math={String(children)} />;
      if (className === 'language-Math') return <BlockMath  math={String(children)} />;
      return <code className={className}>{children}</code>;
    },
  };

  const isAI = msg.role === 'assistant';
  return (
    <div className={`flex gap-3 mb-4 ${isAI ? 'justify-start' : 'justify-end'}`}>
      {isAI && (
        <div className='w-8 h-8 rounded-lg bg-teal/15 border border-teal/30 flex items-center justify-center text-teal text-xs font-bold flex-shrink-0 mt-1'>
          AI
        </div>
      )}
      <div
        ref={ref}
        className={`max-w-2xl rounded-2xl px-4 py-3 text-sm leading-relaxed
          ${isAI ? 'bg-card border border-border' : 'bg-teal/10 border border-teal/30'}`}
      >
        <ReactMarkdown rehypePlugins={[rehypeHighlight]} components={comps}>
          {msg.content}
        </ReactMarkdown>
        
        {imageUrl && (
          <div className="mt-3">
            <img src={imageUrl} alt="AI generated illustration" className="rounded-lg max-w-full border border-teal/30" />
          </div>
        )}
        
        {youtubeLink && (
          <div className="mt-3">
            <a href={youtubeLink} target="_blank" rel="noopener noreferrer"
               className="text-teal text-sm hover:underline flex items-center gap-1">
              🎥 Watch related video on YouTube
            </a>
          </div>
        )}
        
        {isAI && (
          <button
            onClick={() => onSpeak(msg.content)}
            className='mt-2 text-xs text-muted hover:text-teal flex items-center gap-1 transition-colors'
          >
            🔊 Read aloud
          </button>
        )}
      </div>
    </div>
  );
}

export default function TutorChat() {
  const navigate = useNavigate();
  const sid      = window.__studentId;

  const [enrolled,    setEnrolled]    = useState([]);
  const [subjectCode, setSubjectCode] = useState('MATH');
  const [topic,       setTopic]       = useState('mathematics_algebra');
  const [subjectId,   setSubjectId]   = useState(null);
  const [messages,    setMessages]    = useState([{
    role: 'assistant',
    content: 'Hello! I am your AI tutor. Select a subject and topic above, then ask me anything.',
  }]);
  const [input,        setInput]        = useState('');
  const [sessionId,    setSessionId]    = useState(null);
  const [sending,      setSending]      = useState(false);
  const [autoRead,     setAutoRead]     = useState(false);
  const [fcl,          setFCL]          = useState(6);
  const [unread,       setUnread]       = useState(0);
  const [learningStyle, setLearningStyle] = useState('reading');

  const bottomRef = useRef(null);
  const { speak, stop, speaking, rate, setRate } = useTTS();
  const { startListening, stopListening, listening } = useSpeechInput(t => setInput(t));

  const isStudyModeRef = useRef(false);

  // Load enrolled subjects + profile + learning style
  useEffect(() => {
    Promise.all([
      api.get(`/api/subjects/enrolled/${sid}`),
      api.get(`/api/students/${sid}/profile`),
      api.get(`/api/messages/inbox/${sid}`),
    ]).then(([enrollRes, profRes, inboxRes]) => {
      const enrollments  = enrollRes.data || [];
      const studentGrade = profRes.data?.grade || null;
      const style = profRes.data?.preferred_learning_style || 'reading';

      setEnrolled(enrollments);
      setUnread(inboxRes.data.filter(m => !m.is_read).length);
      setLearningStyle(style);

      if (enrollments.length > 0) {
        const first = enrollments[0];
        setSubjectCode(first.subject_code);
        setSubjectId(first.subject_id);
        setFCL(first.fcl_level || gradeToFCL(studentGrade));
        const firstTopic = SUBJECT_TOPICS[first.subject_code]?.topics[0] || 'mathematics_algebra';
        setTopic(firstTopic);
      }
    }).catch(() => {});
  }, [sid]);

  // Restore library study session (runs once on mount)
  useEffect(() => {
    const studyData = localStorage.getItem('ai_study_session');
    if (studyData) {
      try {
        const { sessionId: storedSessionId, contentTitle, initialResponse } = JSON.parse(studyData);
        setSessionId(storedSessionId);
        setMessages([{ role: 'assistant', content: initialResponse }]);
        isStudyModeRef.current = true;
        localStorage.removeItem('ai_study_session');
      } catch (e) {
        console.error('Failed to parse study session data:', e);
      }
    }
  }, []);

  // Start a new chat session when subject changes (unless we are in study mode)
  useEffect(() => {
    if (!subjectId) return;
    if (isStudyModeRef.current) {
      isStudyModeRef.current = false;
      return;
    }
    api.post('/api/chat/new-session', { student_id: sid, subject_id: subjectId })
       .then(r => setSessionId(r.data.session_id))
       .catch(() => {});
  }, [subjectId, sid]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  function handleSubjectChange(code) {
    setSubjectCode(code);
    const e = enrolled.find(x => x.subject_code === code);
    if (e) {
      setSubjectId(e.subject_id);
      setFCL(e.fcl_level || 6);
    }
    const firstTopic = SUBJECT_TOPICS[code]?.topics[0] || 'mathematics_algebra';
    setTopic(firstTopic);
    setMessages([{
      role: 'assistant',
      content: `Switched to ${e?.subject_name || code}. What would you like to learn?`,
    }]);
  }

  async function sendMessage() {
    if (!input.trim() || sending) return;

    if (!sessionId) {
      setMessages(m => [...m, {
        role: 'assistant',
        content: 'Session not ready yet. Please wait a moment and try again.',
      }]);
      return;
    }

    const userMsg = { role: 'user', content: input };
    setMessages(m => [...m, userMsg]);
    setInput('');
    setSending(true);

    try {
      const { data } = await api.post('/api/chat/message', {
        session_id: sessionId,
        student_id: sid,
        message:    input,
        topic,
        fcl_level:  fcl,
        learning_style: learningStyle,
      });
      
      const aiMsg = {
        role: 'assistant',
        content: data.response,
        image_url: data.image_url,
        youtube_link: data.youtube_link
      };
      setMessages(m => [...m, aiMsg]);
      if (autoRead) speak(data.response);
    } catch {
      setMessages(m => [...m, {
        role: 'assistant',
        content: 'Sorry, I could not reach the server. Please try again.',
      }]);
    } finally {
      setSending(false);
    }
  }

  const currentTopics = SUBJECT_TOPICS[subjectCode]?.topics || [];

  const headerActions = (
    <div className='flex items-center gap-3'>
      <select
        value={subjectCode}
        onChange={e => handleSubjectChange(e.target.value)}
        className='bg-input border border-border rounded-lg px-3 py-1.5 text-primary text-sm
          focus:border-teal/60 focus:outline-none'
      >
        {enrolled.length > 0
          ? enrolled.map(e => (
              <option key={e.subject_code} value={e.subject_code}>{e.subject_name}</option>
            ))
          : Object.entries(SUBJECT_TOPICS).map(([code, s]) => (
              <option key={code} value={code}>{s.name}</option>
            ))
        }
      </select>

      <select
        value={topic}
        onChange={e => setTopic(e.target.value)}
        className='bg-input border border-border rounded-lg px-3 py-1.5 text-primary text-sm
          focus:border-teal/60 focus:outline-none'
      >
        {currentTopics.map(t => (
          <option key={t} value={t}>
            {t.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
          </option>
        ))}
      </select>

      <span className='badge-blue text-xs'>
        {learningStyle === 'visual' ? '🎨 Visual' : learningStyle === 'auditory' ? '🎧 Auditory' : learningStyle === 'kinesthetic' ? '🧪 Kinesthetic' : '📖 Reading'}
      </span>

      <span className='badge-teal stat-number'>FCL {fcl}</span>

      {speaking && (
        <button onClick={stop} className='text-red-400 text-xs hover:underline'>
          ⏹ Stop
        </button>
      )}
    </div>
  );

  return (
    <div className='flex h-screen bg-app overflow-hidden'>
      <Sidebar unreadCount={unread} />

      <div className='flex flex-col flex-1 min-w-0 ml-60'>
        <div className='sticky top-0 z-30 bg-app/80 backdrop-blur border-b border-border
          px-6 py-3 flex items-center justify-between'>
          <div>
            <h1 className='text-primary font-semibold text-base'>AI Tutor</h1>
            <p className='text-muted text-xs'>Powered by Gemini + Hugging Face</p>
          </div>
          <div className='flex items-center gap-4'>
            {headerActions}
            <NotificationsPanel />
            <button
              onClick={() => navigate('/profile')}
              className='w-8 h-8 rounded-full bg-teal/20 border border-teal/40 flex items-center
                justify-center text-teal text-xs font-bold hover:bg-teal/30 transition-colors overflow-hidden'
            >
              {window.__profilePic
                ? <img src={window.__profilePic} alt='avatar' className='w-full h-full object-cover rounded-full' />
                : (window.__studentName || 'U')[0].toUpperCase()
              }
            </button>
          </div>
        </div>

        <div className='bg-card border-b border-border px-6 py-2 flex items-center gap-6 text-xs text-muted'>
          <label className='flex items-center gap-2 cursor-pointer'>
            <input
              type='checkbox' checked={autoRead}
              onChange={e => setAutoRead(e.target.checked)}
              className='accent-teal'
            />
            Auto-read responses
          </label>
          <label className='flex items-center gap-2'>
            Speed:
            <select
              value={rate} onChange={e => setRate(+e.target.value)}
              className='bg-input border border-border rounded px-1 text-xs focus:outline-none'
            >
              {[0.75, 1.0, 1.25, 1.5].map(r => (
                <option key={r} value={r}>{r}x</option>
              ))}
            </select>
          </label>
          <span className={`ml-auto flex items-center gap-1 ${sessionId ? 'text-green-400' : 'text-amber-400'}`}>
            <span className={`w-1.5 h-1.5 rounded-full inline-block ${sessionId ? 'bg-green-400' : 'bg-amber-400 animate-pulse'}`} />
            {sessionId ? 'Session active' : 'Connecting…'}
          </span>
        </div>

        <div className='flex-1 overflow-y-auto px-6 py-4'>
          {messages.map((m, i) => (
            <MsgBubble 
              key={i} 
              msg={m} 
              onSpeak={speak} 
              imageUrl={m.image_url} 
              youtubeLink={m.youtube_link} 
            />
          ))}

          {sending && (
            <div className='flex gap-3 mb-4'>
              <div className='w-8 h-8 rounded-lg bg-teal/15 border border-teal/30 flex items-center justify-center text-teal text-xs'>
                AI
              </div>
              <div className='bg-card border border-border rounded-2xl px-4 py-3 flex gap-1 items-center'>
                {[0, 1, 2].map(i => (
                  <div key={i} className='w-2 h-2 rounded-full bg-teal animate-bounce'
                    style={{ animationDelay: `${i * 150}ms` }} />
                ))}
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className='bg-card border-t border-border px-6 py-4 flex gap-3'>
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendMessage()}
            placeholder='Ask your tutor anything…'
            className='flex-1 bg-input border border-border rounded-xl px-4 py-3 text-primary text-sm
              focus:outline-none focus:border-teal/60 focus:ring-1 focus:ring-teal/30'
          />
          <button
            onClick={listening ? stopListening : startListening}
            className={`px-4 py-3 rounded-xl text-sm font-medium transition-colors ${
              listening
                ? 'bg-red-500/10 border border-red-500/40 text-red-400'
                : 'bg-card border border-border text-muted hover:border-teal/40'
            }`}
          >
            {listening ? '⏹' : '🎤'}
          </button>
          <button
            onClick={sendMessage}
            disabled={sending || !input.trim()}
            className='btn-primary px-6 py-3 rounded-xl disabled:opacity-50'
          >
            {sending ? '…' : 'Send'}
          </button>
        </div>

      </div>
    </div>
  );
}