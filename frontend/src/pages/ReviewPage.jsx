import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import PageShell from '../components/PageShell';
import api from '../services/api';

export default function ReviewPage() {
  const navigate = useNavigate();
  const studentId = window.__studentId;
  const [dueReviews, setDueReviews] = useState([]);
  const [upcomingReviews, setUpcomingReviews] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!studentId) return;
    Promise.all([
      api.get(`/api/review/pending/${studentId}`),
      api.get(`/api/review/upcoming/${studentId}`).catch(() => ({ data: [] })),
    ]).then(([dueRes, upcomingRes]) => {
      setDueReviews(dueRes.data?.items || []);
      setUpcomingReviews(upcomingRes.data || []);
    }).catch(console.error)
      .finally(() => setLoading(false));
  }, [studentId]);

  const startReview = (topicId, subjectId) => {
    navigate(`/quiz?topic=${topicId}&mode=review&subject=${subjectId}`);
  };

  if (loading) {
    return (
      <PageShell title="Review Schedule" subtitle="Spaced repetition">
        <div className="flex items-center justify-center py-20">
          <div className="w-10 h-10 border-4 border-teal/30 border-t-teal rounded-full animate-spin" />
        </div>
      </PageShell>
    );
  }

  return (
    <PageShell title="Review Schedule" subtitle="Strengthen your long‑term memory">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Due today */}
        <section className="card p-6">
          <div className="flex items-center gap-2 mb-4">
            <span className="text-2xl">⏰</span>
            <h2 className="text-primary font-semibold text-lg">Due for Review</h2>
            {dueReviews.length > 0 && (
              <span className="badge-teal ml-2">{dueReviews.length}</span>
            )}
          </div>
          {dueReviews.length === 0 ? (
            <p className="text-muted text-sm">No reviews due today. Great job! 🎉</p>
          ) : (
            <div className="space-y-3">
              {dueReviews.map(item => (
                <div
                  key={item.id}
                  className="flex items-center justify-between p-4 bg-app border border-border rounded-xl"
                >
                  <div>
                    <p className="text-primary font-medium">
                      {item.topic_id.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </p>
                    <p className="text-muted text-xs">Repetition #{item.repetition_count + 1}</p>
                  </div>
                  <button
                    onClick={() => startReview(item.topic_id, item.subject_id)}
                    className="btn-primary text-sm py-1.5 px-4"
                  >
                    Review Now →
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Upcoming reviews */}
        {upcomingReviews.length > 0 && (
          <section className="card p-6">
            <div className="flex items-center gap-2 mb-4">
              <span className="text-2xl">📅</span>
              <h2 className="text-primary font-semibold text-lg">Upcoming Reviews</h2>
            </div>
            <div className="space-y-2">
              {upcomingReviews.map(item => (
                <div
                  key={item.id}
                  className="flex items-center justify-between p-3 bg-app border border-border rounded-lg"
                >
                  <div>
                    <p className="text-primary text-sm font-medium">
                      {item.topic_name}
                    </p>
                    <p className="text-muted text-xs">
                      Due: {new Date(item.next_review_date).toLocaleDateString()}
                    </p>
                  </div>
                  <span className="text-muted text-xs">
                    in {item.interval_days} days
                  </span>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </PageShell>
  );
}