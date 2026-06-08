import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import Sidebar from '../components/Sidebar';
import Navbar  from '../components/Navbar';
import { sendTutorMessage, getChatHistory } from '../services/tutor';
import { getSubjects } from '../services/student';
import api from '../services/api';
import styles from './TutorChat.module.css';

// Rich content rendering imports
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css';
import mermaid from 'mermaid';
import 'katex/dist/katex.min.css';
import { InlineMath, BlockMath } from 'react-katex';
import AudioPlayer from '../components/AudioPlayer';

mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  themeVariables: {
    primaryColor: '#00D4C8',
    background: '#0F172A',
    mainBkg: '#0F172A',
    nodeBorder: '#1E293B',
    labelBackground: '#0F172A',
    edgeLabelBackground: '#0F172A',
  },
});

// Helper: split content into segments (mermaid, math, text)
function splitContent(content) {
  const segments = [];
  let remaining = content;
  const mermaidRegex = /```mermaid\n([\s\S]*?)\n```/g;
  const blockMathRegex = /\$\$([\s\S]*?)\$\$/g;
  const inlineMathRegex = /(?<!\$)\$(?!\$)([^\$]+?)\$(?!\$)/g;
  const matches = [];
  let match;
  while ((match = mermaidRegex.exec(remaining)) !== null) {
    matches.push({ type: 'mermaid', content: match[1], index: match.index, end: match.index + match[0].length });
  }
  while ((match = blockMathRegex.exec(remaining)) !== null) {
    matches.push({ type: 'math_block', content: match[1], index: match.index, end: match.index + match[0].length });
  }
  while ((match = inlineMathRegex.exec(remaining)) !== null) {
    matches.push({ type: 'math_inline', content: match[1], index: match.index, end: match.index + match[0].length });
  }
  matches.sort((a,b) => a.index - b.index);
  let pos = 0;
  for (const m of matches) {
    if (m.index > pos) {
      const text = remaining.slice(pos, m.index);
      if (text.trim()) segments.push({ type: 'text', content: text });
    }
    segments.push({ type: m.type, content: m.content });
    pos = m.end;
  }
  if (pos < remaining.length) {
    const text = remaining.slice(pos);
    if (text.trim()) segments.push({ type: 'text', content: text });
  }
  return segments;
}

function MermaidDiagram({ code }) {
  const ref = useRef(null);
  useEffect(() => {
    if (ref.current && code) {
      try {
        mermaid.render('mermaid_' + Date.now() + Math.random(), code).then(({ svg }) => {
          if (ref.current) ref.current.innerHTML = svg;
        }).catch(err => {
          console.error('Mermaid error:', err);
          if (ref.current) ref.current.innerHTML = '<p class="text-red-400 text-sm">Diagram could not be rendered.</p>';
        });
      } catch (err) { console.error(err); }
    }
  }, [code]);
  return <div ref={ref} className="my-4 overflow-x-auto flex justify-center" />;
}

function MessageContent({ content }) {
  if (!content) return null;
  if (content.includes('```mermaid') || content.includes('$$')) {
    const segments = splitContent(content);
    return (
      <div className="space-y-3">
        {segments.map((seg, idx) => {
          if (seg.type === 'mermaid') {
            return <MermaidDiagram key={idx} code={seg.content} />;
          } else if (seg.type === 'math_block') {
            return <BlockMath key={idx} math={seg.content} />;
          } else if (seg.type === 'math_inline') {
            return <InlineMath key={idx} math={seg.content} />;
          } else {
            return (
              <ReactMarkdown key={idx} remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
                {seg.content}
              </ReactMarkdown>
            );
          }
        })}
      </div>
    );
  }
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
      {content}
    </ReactMarkdown>
  );
}

function MessageBubble({ msg }) {
  const isUser = msg.role === 'user';
  return (
    <div className={`${styles.bubble} ${isUser ? styles.userBubble : styles.aiBubble}`}>
      {!isUser && <div className={styles.bubbleAvatar}>🤖</div>}
      <div className={`${styles.bubbleContent} ${msg.error ? styles.errorBubble : ''}`}>
        <div className={styles.bubbleText}>
          {msg.streaming ? (
            msg.content || <span className={styles.cursor} />
          ) : (
            <MessageContent content={msg.content} />
          )}
        </div>
        {msg.streaming && <span className={styles.cursor} />}
        {!isUser && !msg.streaming && msg.content && (
          <div className="mt-3 pt-2 border-t border-border/40">
            <AudioPlayer text={msg.content} label="🔊 Read aloud" />
          </div>
        )}
      </div>
    </div>
  );
}

function SendIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <line x1="22" y1="2" x2="11" y2="13"/>
      <polygon points="22 2 15 22 11 13 2 9 22 2"/>
    </svg>
  );
}

function SpinnerIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={styles.spinner}>
      <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
    </svg>
  );
}

export default function TutorChat() {
  const { user } = useAuth();
  const [messages, setMessages]   = useState([]);
  const [input, setInput]         = useState('');
  const [streaming, setStreaming] = useState(false);
  const [sideOpen, setSideOpen]   = useState(false);
  const [subjects, setSubjects]   = useState([]);
  const [subjectId, setSubjectId] = useState('');
  const [aiStatus, setAiStatus]   = useState('checking');
  const [socraticMode, setSocraticMode] = useState(() => {
    const saved = localStorage.getItem('socratic_mode');
    return saved === 'true';
  });
  const [historySessions, setHistorySessions] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const bottomRef = useRef(null);
  const inputRef  = useRef(null);

  useEffect(() => {
    localStorage.setItem('socratic_mode', socraticMode);
  }, [socraticMode]);

  const loadHistory = async () => {
    try {
      const res = await api.get('/api/chat/history');
      setHistorySessions(res.data || []);
    } catch (err) {
      console.error('Failed to load chat history:', err);
    }
  };

  useEffect(() => {
    getSubjects().then(s => setSubjects(s ?? [])).catch(() => {});
    loadHistory();
  }, []);

  const loadSessionMessages = (session) => {
    const msgs = session.messages || [];
    setMessages(msgs);
    setCurrentSessionId(session.session_id);
    setShowHistory(false);
  };

  const startNewSession = async () => {
    setMessages([]);
    setCurrentSessionId(null);
  };

  useEffect(() => {
    const checkAI = async () => {
      try {
        const res = await api.get('/api/health/ai');
        if (res.data.status === 'connected') setAiStatus('connected');
        else setAiStatus('disconnected');
      } catch {
        setAiStatus('disconnected');
      }
    };
    checkAI();
    const interval = setInterval(checkAI, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    let text = input.trim();
    if (!text || streaming || aiStatus !== 'connected') return;
    setInput('');

    if (socraticMode) {
      text += "\n\n[Instruction: Please respond in Socratic mode. Do NOT give me the answer directly. Instead, ask me guiding questions that help me discover the answer myself. Break down the problem step by step through questions.]";
    }

    const userMsg = { role: 'user', content: text, ts: Date.now() };
    setMessages(prev => [...prev, userMsg]);

    const assistantMsg = { role: 'assistant', content: '', ts: Date.now(), streaming: true };
    setMessages(prev => [...prev, assistantMsg]);
    setStreaming(true);

    let accumulated = '';
    let hasReceivedChunk = false;

    sendTutorMessage(
      { message: text, subject_id: subjectId || undefined },
      (chunk) => {
        hasReceivedChunk = true;
        accumulated += chunk;
        setMessages(prev => {
          const copy = [...prev];
          const last = copy[copy.length - 1];
          if (last.role === 'assistant') copy[copy.length - 1] = { ...last, content: accumulated };
          return copy;
        });
      },
      () => {
        if (!hasReceivedChunk) {
          setMessages(prev => {
            const copy = [...prev];
            const last = copy[copy.length - 1];
            if (last.role === 'assistant') {
              copy[copy.length - 1] = { ...last, content: 'Sorry, I could not generate a response. Please try again.', streaming: false, error: true };
            }
            return copy;
          });
        } else {
          setMessages(prev => {
            const copy = [...prev];
            const last = copy[copy.length - 1];
            if (last.role === 'assistant') copy[copy.length - 1] = { ...last, streaming: false };
            return copy;
          });
        }
        setStreaming(false);
        inputRef.current?.focus();
        loadHistory();
      },
      (err) => {
        setStreaming(false);
        setMessages(prev => {
          const copy = [...prev];
          const last = copy[copy.length - 1];
          if (last.role === 'assistant') {
            copy[copy.length - 1] = { ...last, content: 'Sorry, I ran into an error. Please try again.', streaming: false, error: true };
          }
          return copy;
        });
      }
    );
  };

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const toggleSocraticMode = () => {
    setSocraticMode(prev => !prev);
  };

  const statusColor = {
    checking: 'text-amber-400',
    connected: 'text-green-400',
    disconnected: 'text-red-400',
  }[aiStatus];
  const statusText = {
    checking: 'Connecting...',
    connected: 'Connected',
    disconnected: 'Disconnected – check API key',
  }[aiStatus];

  return (
    <div className="dashboard-shell">
      <Sidebar open={sideOpen} onClose={() => setSideOpen(false)} />

      <div className="dashboard-main" style={{ paddingTop: 'var(--navbar-height)', height: '100vh', display: 'flex', flexDirection: 'column' }}>
        <Navbar onMenuToggle={() => setSideOpen(p => !p)} />

        {/* No extra padding wrapper – direct chat */}
        <div className={styles.chatWrapper} style={{ flex: 1, overflow: 'hidden' }}>
          <div className={styles.chatHeader}>
            <div className={styles.chatHeaderLeft}>
              <div className={styles.botAvatar}>🤖</div>
              <div>
                <h2 className={styles.chatTitle}>AI Tutor</h2>
                <p className={styles.chatSub}>Personalised for your {user?.dominant_vark ?? 'VARK'} learning style</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowHistory(!showHistory)}
                className="px-3 py-1.5 rounded-lg text-xs font-medium bg-border text-muted hover:text-primary transition-all"
                title="View chat history"
              >
                📜 History
              </button>
              <button
                onClick={startNewSession}
                className="px-3 py-1.5 rounded-lg text-xs font-medium bg-border text-muted hover:text-primary transition-all"
                title="Start new chat"
              >
                ✨ New Chat
              </button>
              <button
                onClick={toggleSocraticMode}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  socraticMode
                    ? 'bg-teal text-app'
                    : 'bg-border text-muted hover:text-primary'
                }`}
                title={socraticMode ? 'Socratic mode: I will ask guiding questions' : 'Tutoring mode: I will explain directly'}
              >
                {socraticMode ? '🧠 Socratic' : '💬 Tutoring'}
              </button>
              <div className={`flex items-center gap-1 text-xs ${statusColor}`}>
                <span className="inline-block w-2 h-2 rounded-full currentColor animate-pulse" />
                <span>{statusText}</span>
              </div>
              <select
                className={`input ${styles.subjectSelect}`}
                value={subjectId}
                onChange={e => setSubjectId(e.target.value)}
              >
                <option value="">No subject filter</option>
                {subjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
          </div>

          {/* Chat history sidebar */}
          {showHistory && (
            <div className="absolute left-0 top-20 bottom-0 w-80 bg-sidebar border-r border-border z-20 overflow-y-auto p-4">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-primary font-semibold">Past Conversations</h3>
                <button onClick={() => setShowHistory(false)} className="text-muted hover:text-primary">✕</button>
              </div>
              {historySessions.length === 0 ? (
                <p className="text-muted text-sm">No past conversations yet.</p>
              ) : (
                <div className="space-y-2">
                  {historySessions.map(session => (
                    <button
                      key={session.session_id}
                      onClick={() => loadSessionMessages(session)}
                      className="w-full text-left p-3 rounded-xl border border-border hover:border-teal/30 transition-colors"
                    >
                      <div className="flex justify-between text-xs text-muted mb-1">
                        <span>{new Date(session.started_at).toLocaleString()}</span>
                        <span>{session.messages?.length || 0} messages</span>
                      </div>
                      <p className="text-primary text-sm truncate">
                        {session.messages?.[0]?.content?.substring(0, 60) || 'New conversation'}
                      </p>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className={styles.messages}>
            {messages.length === 0 && (
              <div className={styles.emptyState}>
                <div className={styles.emptyIcon}>💬</div>
                <h3>Ask me anything</h3>
                <p>I'll explain concepts tailored to how you learn best.</p>
                <div className={styles.suggestions}>
                  {['Explain photosynthesis', 'Help me with quadratic equations', 'What is osmosis?'].map(s => (
                    <button key={s} className={styles.suggestion} onClick={() => { setInput(s); inputRef.current?.focus(); }}>
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg, i) => (
              <MessageBubble key={i} msg={msg} />
            ))}
            <div ref={bottomRef} />
          </div>

          <div className={styles.inputArea}>
            <div className={styles.inputWrap}>
              <textarea
                ref={inputRef}
                className={styles.textInput}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Ask a question… (Enter to send, Shift+Enter for newline)"
                rows={1}
                disabled={streaming || aiStatus !== 'connected'}
              />
              <button
                className={styles.sendBtn}
                onClick={sendMessage}
                disabled={!input.trim() || streaming || aiStatus !== 'connected'}
                aria-label="Send message"
              >
                {streaming ? <SpinnerIcon /> : <SendIcon />}
              </button>
            </div>
            <p className={styles.inputHint}>AI responses are for learning support. Always verify with your teacher.</p>
          </div>
        </div>
      </div>
    </div>
  );
}