import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import PageShell from '../components/PageShell';
import api from '../services/api';

const CHART_TOOLTIP = {
  contentStyle: { backgroundColor: '#0F172A', border: '1px solid #1E293B', borderRadius: 8 },
  labelStyle:   { color: '#F1F5F9', fontSize: 12 },
  itemStyle:    { color: '#00D4C8', fontSize: 12 },
};

function masteryBadge(p) {
  if (p >= 0.8) return <span className="badge-green">Mastered {(p*100).toFixed(0)}%</span>;
  if (p >= 0.5) return <span className="badge-amber">Learning {(p*100).toFixed(0)}%</span>;
  return          <span className="badge-red">Needs Work {(p*100).toFixed(0)}%</span>;
}

export default function ProgressTracker() {
  const navigate    = useNavigate();
  const studentId   = window.__studentId;

  const [fclHistory,  setFclHistory]  = useState([]);
  const [mastery,     setMastery]     = useState([]);
  const [hintDensity, setHintDensity] = useState([]);
  const [reviewItems, setReviewItems] = useState([]);
  const [loading,     setLoading]     = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [perfRes, reviewRes] = await Promise.all([
          api.get(`/api/students/${studentId}/subject-performance`),
          api.get(`/api/review/pending/${studentId}`),
        ]);

        // FCL history — derive from subject performance data
        const perf = perfRes.data?.subjects || [];
        setFclHistory(
          perf.map((s, i) => ({ name: s.subject_code || `S${i+1}`, fcl: s.fcl_level || 5 }))
        );

        // Topic mastery grid
        const allTopics = perf.flatMap(s =>
          (s.topics || []).map(t => ({ topic: t.topic_id, mastery: t.mastery_prob || 0, subject: s.subject_code }))
        );
        setMastery(allTopics);

        // Hint density per subject
        setHintDensity(
          perf.map(s => ({ name: s.subject_code || 'N/A', hints: s.total_hints || 0 }))
        );

        // Spaced repetition items
        setReviewItems(reviewRes.data?.items || []);
      } catch (err) {
        console.error('Progress load failed:', err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [studentId]);

  if (loading) return (
    <PageShell title="Progress Tracker">
      <div className="card p-10 text-center text-muted animate-pulse">Loading your progress…</div>
    </PageShell>
  );

  return (
    <PageShell title="Progress Tracker">

      {/* ── FCL History Line Chart ──────────────────────────────────── */}
      <div className="card p-6 mb-6">
        <h2 className="text-primary font-semibold mb-4">FCL Level by Subject</h2>
        {fclHistory.length ? (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={fclHistory}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
              <XAxis dataKey="name" stroke="#64748B" tick={{ fill: '#64748B', fontSize: 12 }} />
              <YAxis domain={[1, 10]} stroke="#64748B" tick={{ fill: '#64748B', fontSize: 12 }} />
              <Tooltip {...CHART_TOOLTIP} />
              <Line type="monotone" dataKey="fcl" stroke="#00D4C8" strokeWidth={2} dot={{ fill: '#00D4C8', r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-muted text-sm">No FCL data yet — complete some quizzes to see your levels.</p>
        )}
      </div>

      {/* ── Topic Mastery Grid ─────────────────────────────────────── */}
      <div className="card p-6 mb-6">
        <h2 className="text-primary font-semibold mb-4">Topic Mastery</h2>
        {mastery.length ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {mastery.map((t, i) => (
              <div key={i} className="card-hover p-3 flex items-center justify-between">
                <div>
                  <p className="text-sm text-primary">{t.topic.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</p>
                  <p className="text-xs text-muted">{t.subject}</p>
                </div>
                {masteryBadge(t.mastery)}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-muted text-sm">No topic data yet.</p>
        )}
      </div>

      {/* ── Hint Density Bar Chart ─────────────────────────────────── */}
      <div className="card p-6 mb-6">
        <h2 className="text-primary font-semibold mb-4">Hint Usage by Subject</h2>
        {hintDensity.length ? (
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={hintDensity}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
              <XAxis dataKey="name" stroke="#64748B" tick={{ fill: '#64748B', fontSize: 12 }} />
              <YAxis stroke="#64748B" tick={{ fill: '#64748B', fontSize: 12 }} />
              <Tooltip {...CHART_TOOLTIP} />
              <Bar dataKey="hints" fill="#F59E0B" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-muted text-sm">No hint data yet.</p>
        )}
      </div>

      {/* ── Spaced Repetition Schedule ─────────────────────────────── */}
      <div className="card p-6 mb-6">
        <h2 className="text-primary font-semibold mb-4">Due for Review</h2>
        {reviewItems.length ? (
          <div className="divide-y divide-border">
            {reviewItems.map((item, i) => (
              <div key={i} className="py-3 flex items-center justify-between">
                <div>
                  <p className="text-sm text-primary">{item.topic_id?.replace(/_/g, ' ')}</p>
                  <p className="text-xs text-muted">Due: {item.due_date || 'Today'}</p>
                </div>
                <button
                  className="btn-primary text-xs py-1"
                  onClick={() => navigate(`/quiz?topic=${item.topic_id}`)}
                >
                  Review →
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-muted text-sm">Nothing due for review — great work! 🎉</p>
        )}
      </div>

      {/* ── Footer CTA ─────────────────────────────────────────────── */}
      <div className="flex justify-end">
        <button className="btn-ghost" onClick={() => navigate('/messages?compose=true')}>
          Need help? Message your teacher →
        </button>
      </div>

    </PageShell>
  );
}
