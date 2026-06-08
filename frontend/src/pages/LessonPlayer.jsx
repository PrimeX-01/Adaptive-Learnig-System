import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import { InlineMath, BlockMath } from 'react-katex';
import 'katex/dist/katex.min.css';
import mermaid from 'mermaid';
import PageShell from '../components/PageShell';
import api from '../services/api';
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

// ── Mermaid renderer ───────────────────────────────────────────
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

// ── Markdown components (enhanced) ─────────────────────────────
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
  img: ({ src, alt }) => (
    <img src={src} alt={alt || 'Lesson image'} className="max-w-full rounded-lg my-4 border border-border" />
  ),
};

// ── Visual content (images, diagrams) ─────────────────────────
function VisualContent({ lesson }) {
  return (
    <div className="card p-8 space-y-6">
      {lesson?.image_url && (
        <img src={lesson.image_url} alt={lesson.title} className="max-w-full rounded-xl border border-border mx-auto" />
      )}
      {lesson?.diagram_code ? (
        <MermaidBlock code={lesson.diagram_code} />
      ) : lesson?.content || lesson?.body ? (
        <ReactMarkdown rehypePlugins={[rehypeHighlight]} components={mdComponents}>
          {lesson.content || lesson.body}
        </ReactMarkdown>
      ) : (
        <p className="text-muted text-sm">No visual content available.</p>
      )}
    </div>
  );
}

// ── Audio content (transcript + player) ────────────────────────
function AudioContent({ text }) {
  const [showTranscript, setShowTranscript] = useState(false);
  return (
    <div className="card p-6 space-y-6">
      <div className="flex flex-col items-center gap-4">
        <div className="w-20 h-20 rounded-full bg-teal/10 border-2 border-teal/30 flex items-center justify-center">
          <span className="text-4xl">🎧</span>
        </div>
        <p className="text-muted text-sm text-center max-w-md">
          This lesson is optimised for audio. Click the button below to listen.
        </p>
        <AudioPlayer text={text} label="▶ Play Lesson" />
        <button
          onClick={() => setShowTranscript(!showTranscript)}
          className="btn-ghost text-xs"
        >
          {showTranscript ? 'Hide transcript' : 'Show transcript'}
        </button>
        {showTranscript && (
          <div className="mt-4 p-4 bg-app border border-border rounded-xl text-primary text-sm leading-relaxed whitespace-pre-wrap max-h-64 overflow-y-auto w-full">
            {text}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Loading skeleton ───────────────────────────────────────────
function LessonSkeleton() {
  return (
    <div className="max-w-3xl mx-auto animate-pulse">
      <div className="card p-6 mb-6">
        <div className="h-6 bg-border rounded w-1/3 mb-2" />
        <div className="h-4 bg-border rounded w-1/2" />
      </div>
      <div className="card p-8">
        <div className="space-y-3">
          <div className="h-4 bg-border rounded w-full" />
          <div className="h-4 bg-border rounded w-5/6" />
          <div className="h-4 bg-border rounded w-4/6" />
        </div>
      </div>
    </div>
  );
}

// ── Main LessonPlayer ──────────────────────────────────────────
export default function LessonPlayer() {
  const { id } = useParams();
  const nav = useNavigate();
  const [lesson, setLesson] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [progress, setProgress] = useState(0);
  const contentRef = useRef(null);
  const sid = window.__studentId;

  useEffect(() => {
    api.get(`/api/content/${id}`)
      .then(r => setLesson(r.data))
      .catch(() => setError('Lesson not found or could not be loaded.'))
      .finally(() => setLoading(false));
  }, [id]);

  // Track read progress (only for text/visual)
  useEffect(() => {
    const el = contentRef.current;
    if (!el || lesson?.modality === 'audio') return;
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

  useEffect(() => {
    if (progress >= 90 && lesson && sid) {
      api.post(`/api/content/${id}/complete`, { student_id: sid }).catch(() => {});
    }
  }, [progress, lesson, id, sid]);

  const modalityLabel = {
    text: 'Reading',
    visual: 'Visual',
    audio: 'Audio',
  };
  const modalityIcon = {
    text: '📖',
    visual: '🗺',
    audio: '🎧',
  };

  if (loading) return <LessonSkeleton />;
  if (error) {
    return (
      <PageShell title="Lesson" subtitle="Content Library">
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 max-w-lg">
          <p className="text-red-400 text-sm">{error}</p>
          <button onClick={() => nav('/library')} className="btn-ghost text-xs mt-4">
            ← Back to Library
          </button>
        </div>
      </PageShell>
    );
  }

  const actions = (
    <div className="flex items-center gap-3">
      {lesson?.modality !== 'audio' && (
        <div className="flex items-center gap-2 text-xs text-muted">
          <div className="w-24 h-1.5 bg-border rounded-full overflow-hidden">
            <div className="h-full bg-teal rounded-full transition-all duration-300" style={{ width: `${progress}%` }} />
          </div>
          <span className="stat-number">{progress}%</span>
        </div>
      )}
      <button onClick={() => nav('/library')} className="btn-ghost text-xs">← Library</button>
    </div>
  );

  const renderContent = () => {
    switch (lesson?.modality) {
      case 'visual':
        return <VisualContent lesson={lesson} />;
      case 'audio':
        return <AudioContent text={lesson?.content || lesson?.body || lesson?.transcript || ''} />;
      default:
        return (
          <div ref={contentRef} className="card p-8 max-h-[60vh] overflow-y-auto prose-invert">
            {lesson?.content || lesson?.body ? (
              <ReactMarkdown rehypePlugins={[rehypeHighlight]} components={mdComponents}>
                {lesson.content || lesson.body}
              </ReactMarkdown>
            ) : (
              <p className="text-muted text-sm">No content available for this lesson.</p>
            )}
          </div>
        );
    }
  };

  return (
    <PageShell
      title={lesson?.title || 'Lesson'}
      subtitle={`${modalityIcon[lesson?.modality] || '📖'} ${modalityLabel[lesson?.modality] || 'Reading'} · FCL ${lesson?.difficulty_level || '—'} · ${lesson?.topic?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) || ''}`}
      actions={actions}
    >
      <div className="max-w-3xl mx-auto">
        {/* Header card */}
        <div className="card p-6 mb-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="badge-teal text-xs">{lesson?.subject_name || lesson?.topic || 'General'}</span>
                <span className="badge-blue text-xs capitalize">{lesson?.modality || 'text'}</span>
                <span className="text-muted text-xs">FCL {lesson?.difficulty_level}</span>
              </div>
              <h1 className="text-primary font-bold text-xl mb-1">{lesson?.title}</h1>
              {lesson?.description && <p className="text-muted text-sm">{lesson.description}</p>}
            </div>
            <div className="text-4xl flex-shrink-0">{modalityIcon[lesson?.modality] || '📖'}</div>
          </div>
        </div>

        {renderContent()}

        {/* Navigation footer */}
        <div className="mt-6 flex items-center justify-between">
          <button onClick={() => nav('/library')} className="btn-ghost text-sm">← Back to Library</button>
          <div className="flex gap-3">
            <button onClick={() => nav(`/quiz?topic=${lesson?.topic || ''}`)} className="btn-ghost text-sm">
              ◎ Take Quiz on this Topic
            </button>
            <button onClick={() => nav(`/chat?topic=${lesson?.topic || ''}`)} className="btn-primary text-sm">
              ◈ Ask AI Tutor
            </button>
          </div>
        </div>
      </div>
    </PageShell>
  );
}