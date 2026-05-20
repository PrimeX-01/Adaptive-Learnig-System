import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import PageShell from '../components/PageShell';
import api from '../services/api';

const SUBJECTS = [
  { code: '', label: 'All Subjects' },
  { code: 'MATH', label: 'Mathematics' },
  { code: 'SCI',  label: 'Science' },
  { code: 'ENG',  label: 'English' },
  { code: 'SOC',  label: 'Social Studies' },
  { code: 'CS',   label: 'Computer Science' },
];

// Map content_type to display label and icon
const CONTENT_TYPE_MAP = {
  text:       { label: 'Text',   icon: '📄', badge: 'badge-blue' },
  pdf:        { label: 'PDF',    icon: '📑', badge: 'badge-blue' },
  video_link: { label: 'Video',  icon: '🎬', badge: 'badge-amber' },
  image:      { label: 'Image',  icon: '🖼️', badge: 'badge-teal' },
};

function contentTypeBadge(type) {
  const t = CONTENT_TYPE_MAP[type] || { label: type, icon: '📄', badge: 'badge-blue' };
  return <span className={t.badge}>{t.icon} {t.label}</span>;
}

export default function ContentLibrary() {
  const navigate   = useNavigate();
  const studentId  = window.__studentId;

  const [content,   setContent]   = useState([]);
  const [filtered,  setFiltered]  = useState([]);
  const [loading,   setLoading]   = useState(true);
  const [error,     setError]     = useState('');

  const [subject,   setSubject]   = useState('');
  const [contentType, setContentType] = useState('');
  const [search,    setSearch]    = useState('');

  // ── fetch library content from new endpoint 
  useEffect(() => {
    async function load() {
      setLoading(true);
      setError('');
      try {
        // New endpoint: get content filtered by student's enrolled subjects + grade
        const { data } = await api.get(`/api/library/student/${studentId}`);
        setContent(data || []);
      } catch (err) {
        console.error('Library load failed:', err);
        setError('Could not load library content. Please try again later.');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [studentId]);

  // ── client-side filtering (subject + content_type + search) 
  useEffect(() => {
    let result = [...content];

    if (subject)  result = result.filter(c => c.subject_code === subject);
    if (contentType) result = result.filter(c => c.content_type === contentType);
    if (search)   result = result.filter(c =>
      c.title?.toLowerCase().includes(search.toLowerCase()) ||
      c.description?.toLowerCase().includes(search.toLowerCase())
    );

    setFiltered(result);
  }, [content, subject, contentType, search]);

  // ── Study with AI Tutor 
  const startAITutor = async (contentId, title) => {
    try {
      const res = await api.post('/api/library/study', {
        content_id: contentId,
        student_id: studentId,
        initial_question: null
      });
      // Store session data to be picked up by TutorChat
      localStorage.setItem('ai_study_session', JSON.stringify({
        sessionId: res.data.session_id,
        contentTitle: title,
        initialResponse: res.data.response
      }));
      navigate('/chat?study=true');
    } catch (err) {
      console.error('Failed to start AI study:', err);
      alert('Could not start AI tutor session. Please try again.');
    }
  };

  const selectEl = 'bg-input border border-border text-primary rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-teal/60 w-full';

  // Content type filter options
  const contentTypes = [
    { value: '',        label: 'All Types' },
    { value: 'text',    label: 'Text / Notes' },
    { value: 'pdf',     label: 'PDF Documents' },
    { value: 'video_link', label: 'Videos' },
    { value: 'image',   label: 'Images' },
  ];

  return (
    <PageShell title="Content Library" subtitle="Teacher‑uploaded learning materials">

      {/* ── Filters  */}
      <div className="card p-4 mb-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <input
          className={selectEl}
          placeholder="Search content…"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <select className={selectEl} value={subject} onChange={e => setSubject(e.target.value)}>
          {SUBJECTS.map(s => <option key={s.code} value={s.code}>{s.label}</option>)}
        </select>
        <select className={selectEl} value={contentType} onChange={e => setContentType(e.target.value)}>
          {contentTypes.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
        </select>
        {/* Grade / FCL filter removed – content is already filtered by student's grade on backend */}
      </div>

      {/* ── Results count  */}
      <p className="text-xs text-muted mb-4">
        {loading ? 'Loading…' : `${filtered.length} item${filtered.length !== 1 ? 's' : ''} found`}
      </p>

      {/* ── Error state  */}
      {error && (
        <div className="card p-10 text-center text-red-400">
          ⚠️ {error}
        </div>
      )}

      {/* ── Content Grid  */}
      {loading ? (
        <div className="card p-10 text-center text-muted animate-pulse">Loading content…</div>
      ) : !error && filtered.length === 0 ? (
        <div className="card p-10 text-center text-muted">
          No content matches your filters. Try adjusting them above.
        </div>
      ) : !error && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
          {filtered.map((item) => (
            <div key={item.id} className="card-hover p-5 flex flex-col gap-3">
              {/* header */}
              <div className="flex items-start justify-between gap-2">
                <h3 className="text-primary font-medium text-sm leading-snug">{item.title}</h3>
                {contentTypeBadge(item.content_type)}
              </div>

              {/* description */}
              {item.description && (
                <p className="text-xs text-muted leading-relaxed line-clamp-3">{item.description}</p>
              )}

              {/* meta row */}
              <div className="flex items-center gap-3 text-xs text-muted">
                <span>{item.subject_code}</span>
                <span>Grades {item.grade_min}–{item.grade_max}</span>
                {item.topic_tags?.length > 0 && (
                  <span className="truncate">#{item.topic_tags[0]}</span>
                )}
              </div>

              {/* action buttons */}
              <div className="flex gap-2 mt-auto">
                <button
                  className="btn-primary flex-1"
                  onClick={() => navigate(`/lesson/${item.id}`)}
                >
                  Open Lesson →
                </button>
                <button
                  className="btn-ghost text-sm px-3"
                  onClick={() => startAITutor(item.id, item.title)}
                  title="Study with AI Tutor"
                >
                  🧠 AI
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Footer CTA  */}
      <div className="flex justify-end">
        <button className="btn-ghost" onClick={() => navigate('/messages?compose=true')}>
          Need help? Message your teacher →
        </button>
      </div>

    </PageShell>
  );
}