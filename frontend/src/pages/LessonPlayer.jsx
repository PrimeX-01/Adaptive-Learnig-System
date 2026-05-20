import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import { InlineMath, BlockMath } from 'react-katex';
import 'katex/dist/katex.min.css';
import mermaid from 'mermaid';
import PageShell from '../components/PageShell';
import api from '../services/api';

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

// ── TTS helper ──────────────────────────────────────────────────────────────
function useTTS() {
  const [speaking, setSpeaking] = useState(false);
  const [rate,     setRate]     = useState(1.0);

  function speak(text) {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utt = new SpeechSynthesisUtterance(text);
    utt.rate = rate;
    utt.onstart = () => setSpeaking(true);
    utt.onend   = () => setSpeaking(false);
    utt.onerror = () => setSpeaking(false);
    window.speechSynthesis.speak(utt);
  }

  function stop() {
    window.speechSynthesis?.cancel();
    setSpeaking(false);
  }

  return { speak, stop, speaking, rate, setRate };
}

// ── Mermaid renderer ─────────────────────────────────────────────────────────
function MermaidBlock({ code }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!ref.current || !code) return;
    mermaid.render('mermaid-' + Date.now(), code).then(({ svg }) => {
      if (ref.current) ref.current.innerHTML = svg;
    }).catch(() => {
      if (ref.current) ref.current.innerHTML =
        '<p class="text-red-400 text-sm">Diagram could not be rendered.</p>';
    });
  }, [code]);
  return <div ref={ref} className="my-6 overflow-x-auto flex justify-center" />;
}

// ── Markdown components ──────────────────────────────────────────────────────
const mdComponents = {
  code({ className, children }) {
    if (className === 'language-math')   return <InlineMath math={String(children)} />;
    if (className === 'language-Math')   return <BlockMath  math={String(children)} />;
    if (className === 'language-mermaid') return <MermaidBlock code={String(children)} />;
    return (
      <code className={`${className || ''} bg-app px-1.5 py-0.5 rounded text-teal font-mono text-sm`}>
        {children}
      </code>
    );
  },
  h1: ({ children }) => <h1 className="text-primary text-2xl font-bold mt-6 mb-3">{children}</h1>,
  h2: ({ children }) => <h2 className="text-primary text-xl font-semibold mt-5 mb-2">{children}</h2>,
  h3: ({ children }) => <h3 className="text-primary text-lg font-medium mt-4 mb-2">{children}</h3>,
  p:  ({ children }) => <p  className="text-primary text-sm leading-relaxed mb-3">{children}</p>,
  ul: ({ children }) => <ul className="list-disc list-inside text-primary text-sm space-y-1 mb-3 pl-2">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal list-inside text-primary text-sm space-y-1 mb-3 pl-2">{children}</ol>,
  li: ({ children }) => <li className="text-primary text-sm leading-relaxed">{children}</li>,
  blockquote: ({ children }) => (
    <blockquote className="border-l-4 border-teal pl-4 py-1 bg-teal/5 rounded-r-lg my-4 text-muted italic text-sm">
      {children}
    </blockquote>
  ),
  pre: ({ children }) => (
    <pre className="bg-app border border-border rounded-xl p-4 overflow-x-auto text-sm my-4 font-mono">
      {children}
    </pre>
  ),
  strong: ({ children }) => <strong className="text-primary font-semibold">{children}</strong>,
  em:     ({ children }) => <em     className="text-muted italic">{children}</em>,
};

// ── Audio player for TTS mode ─────────────────────────────────────────────
function AudioPlayer({ text, speak, stop, speaking, rate, setRate }) {
  return (
    <div className="card p-6 flex flex-col items-center gap-6">
      <div className="w-20 h-20 rounded-full bg-teal/10 border-2 border-teal/30 flex items-center justify-center">
        <span className="text-4xl">{speaking ? '🔊' : '🎧'}</span>
      </div>
      <p className="text-muted text-sm text-center max-w-md">
        This lesson is optimised for audio. Press play to listen.
      </p>
      <div className="flex items-center gap-4">
        <button
          onClick={() => speaking ? stop() : speak(text)}
          className={`px-8 py-3 rounded-xl font-semibold text-sm transition-all ${
            speaking
              ? 'bg-red-500/10 border border-red-500/40 text-red-400 hover:bg-red-500/20'
              : 'btn-primary'
          }`}
        >
          {speaking ? '⏹ Stop' : '▶ Play Lesson'}
        </button>
      </div>
      <div className="flex items-center gap-3 text-xs text-muted">
        <span>Speed:</span>
        {[0.75, 1.0, 1.25, 1.5].map(r => (
          <button
            key={r}
            onClick={() => setRate(r)}
            className={`px-2 py-1 rounded border transition-colors ${
              rate === r
                ? 'border-teal bg-teal/10 text-teal'
                : 'border-border text-muted hover:text-primary'
            }`}
          >
            {r}x
          </button>
        ))}
      </div>
      {/* Show transcript */}
      <details className="w-full">
        <summary className="text-muted text-xs cursor-pointer hover:text-primary transition-colors">
          Show transcript
        </summary>
        <div className="mt-3 p-4 bg-app border border-border rounded-xl text-primary text-sm leading-relaxed whitespace-pre-wrap max-h-64 overflow-y-auto">
          {text}
        </div>
      </details>
    </div>
  );
}

// ── Main LessonPlayer component ───────────────────────────────────────────
export default function LessonPlayer() {
  const { id }   = useParams();
  const nav      = useNavigate();
  const [lesson,  setLesson]  = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState('');
  const [progress,setProgress]= useState(0); // read progress 0–100
  const contentRef = useRef(null);
  const { speak, stop, speaking, rate, setRate } = useTTS();
  const sid = window.__studentId;

  useEffect(() => {
    api.get(`/api/content/${id}`)
      .then(r => setLesson(r.data))
      .catch(() => setError('Lesson not found or could not be loaded.'))
      .finally(() => setLoading(false));
  }, [id]);

  // Track read progress via scroll
  useEffect(() => {
    const el = contentRef.current;
    if (!el) return;
    function onScroll() {
      const { scrollTop, scrollHeight, clientHeight } = el;
      const pct = scrollHeight <= clientHeight
        ? 100
        : Math.round((scrollTop / (scrollHeight - clientHeight)) * 100);
      setProgress(pct);
    }
    el.addEventListener('scroll', onScroll);
    return () => el.removeEventListener('scroll', onScroll);
  }, [lesson]);

  // Mark complete when progress reaches 90%
  useEffect(() => {
    if (progress >= 90 && lesson && sid) {
      api.post(`/api/content/${id}/complete`, { student_id: sid }).catch(() => {});
    }
  }, [progress, lesson, id, sid]);

  const modalityLabel = {
    text:   'Reading',
    visual: 'Visual',
    audio:  'Audio',
  };

  const modalityIcon = {
    text:   '📖',
    visual: '🗺',
    audio:  '🎧',
  };

  if (loading) return (
    <div className="min-h-screen bg-app flex items-center justify-center">
      <div className="w-10 h-10 border-4 border-teal/30 border-t-teal rounded-full animate-spin" />
    </div>
  );

  if (error) return (
    <PageShell title="Lesson" subtitle="Content Library">
      <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 max-w-lg">
        <p className="text-red-400 text-sm">{error}</p>
        <button onClick={() => nav('/library')} className="btn-ghost text-xs mt-4">
          ← Back to Library
        </button>
      </div>
    </PageShell>
  );

  const actions = (
    <div className="flex items-center gap-3">
      {/* Progress pill */}
      <div className="flex items-center gap-2 text-xs text-muted">
        <div className="w-24 h-1.5 bg-border rounded-full overflow-hidden">
          <div
            className="h-full bg-teal rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
        <span className="stat-number">{progress}%</span>
      </div>
      {lesson?.modality === 'text' && (
        <>
          {speaking
            ? <button onClick={stop} className="btn-ghost text-xs">⏹ Stop</button>
            : <button onClick={() => speak(lesson.content || lesson.body || '')} className="btn-ghost text-xs">🔊 Read aloud</button>
          }
        </>
      )}
      <button onClick={() => nav('/library')} className="btn-ghost text-xs">← Library</button>
    </div>
  );

  return (
    <PageShell
      title={lesson?.title || 'Lesson'}
      subtitle={`${modalityIcon[lesson?.modality] || '📖'} ${modalityLabel[lesson?.modality] || 'Reading'} · FCL ${lesson?.difficulty_level || '—'} · ${lesson?.topic?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) || ''}`}
      actions={actions}
    >
      <div className="max-w-3xl mx-auto">

        {/* Lesson header card */}
        <div className="card p-6 mb-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="badge-teal text-xs">{lesson?.subject_name || lesson?.topic || 'General'}</span>
                <span className="badge-blue text-xs capitalize">{lesson?.modality || 'text'}</span>
                <span className="text-muted text-xs">FCL {lesson?.difficulty_level}</span>
              </div>
              <h1 className="text-primary font-bold text-xl mb-1">{lesson?.title}</h1>
              {lesson?.description && (
                <p className="text-muted text-sm">{lesson.description}</p>
              )}
            </div>
            <div className="text-4xl flex-shrink-0">
              {modalityIcon[lesson?.modality] || '📖'}
            </div>
          </div>
        </div>

        {/* ── TEXT modality ── */}
        {(!lesson?.modality || lesson?.modality === 'text') && (
          <div
            ref={contentRef}
            className="card p-8 max-h-[60vh] overflow-y-auto prose-invert"
          >
            {lesson?.content || lesson?.body ? (
              <ReactMarkdown
                rehypePlugins={[rehypeHighlight]}
                components={mdComponents}
              >
                {lesson.content || lesson.body}
              </ReactMarkdown>
            ) : (
              <p className="text-muted text-sm">No content available for this lesson.</p>
            )}
          </div>
        )}

        {/* ── VISUAL modality ── */}
        {lesson?.modality === 'visual' && (
          <div className="card p-8">
            {lesson?.diagram_code ? (
              <MermaidBlock code={lesson.diagram_code} />
            ) : lesson?.content || lesson?.body ? (
              <ReactMarkdown
                rehypePlugins={[rehypeHighlight]}
                components={mdComponents}
              >
                {lesson.content || lesson.body}
              </ReactMarkdown>
            ) : (
              <p className="text-muted text-sm">No visual content available.</p>
            )}
          </div>
        )}

        {/* ── AUDIO modality ── */}
        {lesson?.modality === 'audio' && (
          <AudioPlayer
            text={lesson?.content || lesson?.body || lesson?.transcript || ''}
            speak={speak}
            stop={stop}
            speaking={speaking}
            rate={rate}
            setRate={setRate}
          />
        )}

        {/* ── Navigation footer ── */}
        <div className="mt-6 flex items-center justify-between">
          <button
            onClick={() => nav('/library')}
            className="btn-ghost text-sm"
          >
            ← Back to Library
          </button>
          <div className="flex gap-3">
            <button
              onClick={() => nav('/quiz?topic=' + (lesson?.topic || ''))}
              className="btn-ghost text-sm"
            >
              ◎ Take Quiz on this Topic
            </button>
            <button
              onClick={() => nav('/chat?topic=' + (lesson?.topic || ''))}
              className="btn-primary text-sm"
            >
              ◈ Ask AI Tutor
            </button>
          </div>
        </div>

        {/* ── Help link ── */}
        <div className="mt-4 text-center">
          <button
            onClick={() => nav('/messages?compose=true')}
            className="text-muted text-xs hover:text-teal transition-colors"
          >
            Need help? Message your teacher →
          </button>
        </div>

      </div>
    </PageShell>
  );
}
