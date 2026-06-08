import { useState, useEffect, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import Sidebar from '../components/Sidebar';
import Navbar  from '../components/Navbar';
import api from '../services/api';
import styles from './StudentDashboard.module.css';

const FCL_LABELS = ['', 'Beginner', 'Basic', 'Developing', 'Proficient', 'Advanced'];
const FCL_COLOR  = ['', 'var(--fcl-1)', 'var(--fcl-2)', 'var(--fcl-3)', 'var(--fcl-4)', 'var(--fcl-5)'];
const VARK_COLOR = { V: 'var(--vark-v)', A: 'var(--vark-a)', R: 'var(--vark-r)', K: 'var(--vark-k)' };
const VARK_LABEL = { V: 'Visual', A: 'Auditory', R: 'Reading', K: 'Kinesthetic' };

function timeGreeting() {
  const h = new Date().getHours();
  if (h < 12) return 'morning';
  if (h < 17) return 'afternoon';
  return 'evening';
}

function getLearningStyleInfo(styleKey) {
  const map = {
    visual:      { icon: '👁️', label: 'Visual',       desc: 'You learn best through diagrams, charts and visual aids.' },
    auditory:    { icon: '🎧', label: 'Auditory',      desc: 'You learn best through listening and verbal explanations.' },
    reading:     { icon: '📖', label: 'Reading/Writing', desc: 'You learn best through written notes and text content.' },
    kinesthetic: { icon: '🧪', label: 'Kinesthetic',   desc: 'You learn best through hands-on practice and examples.' },
  };
  return map[styleKey] || map.reading;
}

function getWeekNumber() {
  const d = new Date();
  const yearStart = new Date(d.getFullYear(), 0, 1);
  const week = Math.ceil(((d - yearStart) / 86400000 + yearStart.getDay() + 1) / 7);
  return `${d.getFullYear()}-W${week}`;
}

function DashboardSkeleton() {
  return (
    <div className="dashboard-shell">
      <div className="dashboard-main" style={{ paddingTop: 'var(--navbar-height)', padding: 'var(--space-8)' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: '16px', marginTop: '80px' }}>
          {[...Array(4)].map((_, i) => (
            <div key={i} className="skeleton" style={{ height: '100px', borderRadius: '12px' }} />
          ))}
        </div>
      </div>
    </div>
  );
}

function LearningStyleCard({ styleKey }) {
  const info = getLearningStyleInfo(styleKey);
  return (
    <div className="card p-5 mb-6 bg-gradient-to-r from-teal/5 to-transparent border-teal/20">
      <div className="flex items-center gap-4 flex-wrap">
        <div className="w-16 h-16 rounded-full bg-teal/20 flex items-center justify-center text-4xl">
          {info.icon}
        </div>
        <div className="flex-1">
          <p className="text-muted text-xs uppercase tracking-wide">Your Learning Style</p>
          <h2 className="text-primary text-xl font-bold">{info.label} Learner</h2>
          <p className="text-muted text-sm mt-1">{info.desc}</p>
        </div>
        <Link to="/student/profile?retake=true" className="btn-ghost text-sm">
          Update Assessment
        </Link>
      </div>
    </div>
  );
}

function WeeklySummary({ data, onDismiss }) {
  const [visible, setVisible] = useState(true);
  const lastSeen = localStorage.getItem('weekly_summary_last_seen');
  const thisWeek = getWeekNumber();
  if (lastSeen === thisWeek && !visible) return null;
  if (!data) return null;

  const handleDismiss = () => {
    setVisible(false);
    localStorage.setItem('weekly_summary_last_seen', thisWeek);
    if (onDismiss) onDismiss();
  };

  return (
    <div className="card p-5 mb-6 bg-blue-500/5 border-blue-500/30">
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xl">📊</span>
            <h3 className="text-primary font-semibold">Your Weekly Summary</h3>
          </div>
          <p className="text-muted text-sm">
            Last week you completed <strong>{data.quizzes_completed || 0}</strong> quizzes,
            with an average accuracy of <strong>{data.avg_accuracy || 0}%</strong>.
            {data.fcl_increased && ` Your FCL increased in ${data.fcl_increased}!`}
            {data.streak && ` You maintained a ${data.streak}-day study streak.`}
          </p>
        </div>
        <button onClick={handleDismiss} className="text-muted hover:text-primary">✕</button>
      </div>
    </div>
  );
}

function RecommendationCard({ recommendation, onStudy }) {
  if (!recommendation) return null;
  return (
    <div className="card p-5 mb-6 bg-amber-500/5 border-amber-500/30">
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-2xl">💡</span>
        <div className="flex-1">
          <p className="text-muted text-xs uppercase tracking-wide">Recommended for you</p>
          <p className="text-primary text-sm font-medium">{recommendation.message}</p>
        </div>
        <button onClick={onStudy} className="btn-primary text-sm py-1.5">
          Study Now →
        </button>
      </div>
    </div>
  );
}

function MoodTracker({ onComplete }) {
  const [show, setShow] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const lastAsked = localStorage.getItem('mood_last_asked');
  const today = new Date().toDateString();
  const shouldAsk = lastAsked !== today;

  useEffect(() => {
    if (shouldAsk) setShow(true);
  }, [shouldAsk]);

  const handleSelect = async (mood) => {
    setSubmitting(true);
    localStorage.setItem('mood_last_asked', today);
    localStorage.setItem('last_mood', mood);
    try {
      await api.post('/api/students/mood', { mood });
    } catch (e) { console.warn('Mood tracking endpoint not yet implemented'); }
    setSubmitting(false);
    setShow(false);
    if (onComplete) onComplete(mood);
  };

  if (!show) return null;

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
      <div className="card p-6 w-full max-w-md">
        <h3 className="text-primary font-bold text-lg mb-2">How are you feeling today?</h3>
        <p className="text-muted text-sm mb-5">This helps us personalise your learning experience.</p>
        <div className="flex justify-around gap-3">
          {[
            { emoji: '😊', mood: 'happy', label: 'Happy' },
            { emoji: '😐', mood: 'neutral', label: 'Neutral' },
            { emoji: '😔', mood: 'sad', label: 'Sad' },
            { emoji: '🤯', mood: 'stressed', label: 'Stressed' },
            { emoji: '⚡', mood: 'energetic', label: 'Energetic' },
          ].map(item => (
            <button
              key={item.mood}
              onClick={() => handleSelect(item.mood)}
              disabled={submitting}
              className="flex flex-col items-center gap-1 p-3 rounded-xl hover:bg-teal/10 transition-colors"
            >
              <span className="text-3xl">{item.emoji}</span>
              <span className="text-xs text-muted">{item.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function AdaptationNotifications({ events, onEventSeen }) {
  const [active, setActive] = useState(null);
  const [queue, setQueue] = useState([]);
  const seenIds = useRef(new Set());

  useEffect(() => {
    if (!events || events.length === 0) return;
    const newEvents = events.filter(e => !seenIds.current.has(e.id));
    if (newEvents.length > 0) {
      setQueue(prev => [...prev, ...newEvents]);
      newEvents.forEach(e => seenIds.current.add(e.id));
    }
  }, [events]);

  useEffect(() => {
    if (!active && queue.length > 0) {
      const next = queue[0];
      setActive(next);
      setQueue(prev => prev.slice(1));
      const timer = setTimeout(() => {
        setActive(null);
        if (onEventSeen) onEventSeen(next.id);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [active, queue, onEventSeen]);

  if (!active) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50 animate-slide-up">
      <div className="bg-teal/90 text-app rounded-xl shadow-lg p-4 max-w-sm border border-teal-200">
        <div className="flex items-start gap-3">
          <span className="text-xl">{active.event_type === 'FCL_ADVANCE' ? '🎉' : '⚠️'}</span>
          <div className="flex-1">
            <p className="font-semibold text-sm">{active.title}</p>
            <p className="text-xs opacity-90">{active.message}</p>
          </div>
          <button onClick={() => setActive(null)} className="text-app/70 hover:text-app">✕</button>
        </div>
      </div>
    </div>
  );
}

export default function StudentDashboard() {
  const { user, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sideOpen, setSideOpen] = useState(false);
  const [adaptationEvents, setAdaptationEvents] = useState([]);
  const [weeklyData, setWeeklyData] = useState(null);
  const [recommendation, setRecommendation] = useState(null);
  const [quizzesCompleted, setQuizzesCompleted] = useState(0);
  const [totalPoints, setTotalPoints] = useState(0);
  const pollingInterval = useRef(null);
  const isRefreshing = useRef(false);
  const lastRefresh = useRef(0);

  const studentId = user?.id || localStorage.getItem('sa_studentId');

  const fetchAdaptationEvents = async () => {
    if (!studentId) return;
    try {
      const res = await api.get(`/api/students/${studentId}/adaptation-events`, { timeout: 10000 });
      setAdaptationEvents(res.data || []);
    } catch (err) {
      console.error('Failed to fetch adaptation events:', err.message);
    }
  };

  const fetchStats = async () => {
    if (!studentId) return { quizzes: 0, points: 0 };
    try {
      const [quizzesRes, pointsRes] = await Promise.all([
        api.get(`/api/students/${studentId}/assessments-count`, { timeout: 5000 }).catch(() => ({ data: 0 })),
        api.get(`/api/students/${studentId}/total-points`, { timeout: 5000 }).catch(() => ({ data: 0 })),
      ]);
      return { quizzes: quizzesRes.data || 0, points: pointsRes.data || 0 };
    } catch {
      return { quizzes: 0, points: 0 };
    }
  };

  const refreshDashboard = async (silent = false) => {
    if (!studentId) return;
    // Prevent concurrent refreshes
    if (isRefreshing.current) return;
    // Throttle: max once every 10 seconds
    const now = Date.now();
    if (now - lastRefresh.current < 10000 && !silent) return;
    lastRefresh.current = now;
    isRefreshing.current = true;

    if (!silent) setLoading(true);
    try {
      const [profileRes, perfRes, historyRes, stats] = await Promise.all([
        api.get(`/api/students/${studentId}/profile`, { timeout: 15000 }),
        api.get(`/api/students/${studentId}/subject-performance`, { timeout: 15000 }),
        api.get('/api/quiz/history', { timeout: 10000 }).catch(() => ({ data: [] })),
        fetchStats(),
      ]);

      setQuizzesCompleted(stats.quizzes);
      setTotalPoints(stats.points);

      const performance = perfRes.data;
      const subjects = (performance.subjects || []).map(sub => ({
        id: sub.subject_id,
        name: sub.subject_name,
        code: sub.subject_code,
        fcl_level: sub.fcl_level,
        accuracy: sub.accuracy,
      }));

      const profile = profileRes.data;
      const learningStyle = profile.preferred_learning_style || 'reading';

      const history = historyRes.data || [];
      const lastWeek = history.filter(q => {
        const date = new Date(q.completedAt);
        const oneWeekAgo = new Date();
        oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
        return date >= oneWeekAgo;
      });
      const weekly = {
        quizzes_completed: lastWeek.length,
        avg_accuracy: lastWeek.length ? Math.round(lastWeek.reduce((s,q) => s + (q.score || 0), 0) / lastWeek.length) : 0,
        fcl_increased: null,
        streak: 0,
      };
      setWeeklyData(weekly);

      const styleMap = {
        visual:      { v: 60, a: 15, r: 15, k: 10 },
        auditory:    { v: 10, a: 60, r: 20, k: 10 },
        reading:     { v: 15, a: 10, r: 60, k: 15 },
        kinesthetic: { v: 10, a: 15, r: 15, k: 60 },
      };
      const dominant = profile.preferred_learning_style || 'reading';
      const vark_profile = styleMap[dominant] || styleMap.reading;

      const lowestAcc = subjects.reduce((min, sub) => (sub.accuracy !== null && sub.accuracy < (min?.accuracy ?? 100) ? sub : min), null);
      if (lowestAcc && lowestAcc.accuracy < 70) {
        setRecommendation({
          message: `You're scoring ${lowestAcc.accuracy}% in ${lowestAcc.name}. Focus on this topic to improve.`,
          subjectId: lowestAcc.id,
          subjectName: lowestAcc.name,
        });
      } else if (subjects.length > 0) {
        setRecommendation({
          message: `Ready for a challenge? Try the next topic in ${subjects[0].name}.`,
          subjectId: subjects[0].id,
          subjectName: subjects[0].name,
        });
      }

      setData({
        stats: {
          subjects_count: performance.overall?.subjects_count || subjects.length,
          avg_fcl: performance.overall?.avg_fcl,
        },
        subjects,
        vark_profile,
        learningStyle,
      });
    } catch (err) {
      console.error('Dashboard fetch error:', err.message);
      if (err.response?.status === 401) navigate('/auth');
    } finally {
      if (!silent) setLoading(false);
      isRefreshing.current = false;
    }
  };

  // Initial load
  useEffect(() => {
    if (!isAuthenticated || !studentId) {
      navigate('/auth', { replace: true });
      return;
    }
    refreshDashboard(false);
    fetchAdaptationEvents();

    // Poll adaptation events every 30 seconds (lightweight)
    pollingInterval.current = setInterval(() => {
      fetchAdaptationEvents();
    }, 30000);

    // Refresh dashboard when page becomes visible (user returns from quiz)
    const handleVisibility = () => {
      if (document.visibilityState === 'visible') {
        refreshDashboard(true); // silent refresh
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => {
      if (pollingInterval.current) clearInterval(pollingInterval.current);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [isAuthenticated, studentId, navigate]);

  const handleStudyRecommendation = () => {
    if (recommendation?.subjectId) {
      navigate(`/quiz?subject=${recommendation.subjectId}`);
    } else {
      navigate('/student/quizzes');
    }
  };

  const handleMoodComplete = (mood) => {
    console.log('Mood recorded:', mood);
  };

  const handleEventSeen = (eventId) => {
    console.log('Event dismissed:', eventId);
  };

  if (!isAuthenticated || !studentId) {
    return (
      <div className="dashboard-shell">
        <div className="dashboard-main" style={{ textAlign: 'center', padding: '2rem' }}>
          <p>Not logged in. Please <Link to="/auth">login again</Link>.</p>
        </div>
      </div>
    );
  }

  if (loading) return <DashboardSkeleton />;
  if (!data) return <div className="dashboard-shell"><div className="dashboard-main">Error loading dashboard</div></div>;

  const { subjects, learningStyle, vark_profile } = data;

  return (
    <div className="dashboard-shell">
      <Sidebar open={sideOpen} onClose={() => setSideOpen(false)} />

      <div className="dashboard-main" style={{ paddingTop: 'var(--navbar-height)' }}>
        <Navbar onMenuToggle={() => setSideOpen(p => !p)} />

        <div className="dashboard-content">
          <div className={styles.header}>
            <div>
              <h1 className={styles.greeting}>
                Good {timeGreeting()}, <span>{user?.first_name || 'Student'}</span> 👋
              </h1>
              <p className={styles.subtitle}>Here's your learning progress today</p>
            </div>
            <Link to="/student/tutor" className="btn btn-primary">
              Ask AI Tutor
            </Link>
          </div>

          <LearningStyleCard styleKey={learningStyle} />
          <WeeklySummary data={weeklyData} />
          <RecommendationCard recommendation={recommendation} onStudy={handleStudyRecommendation} />

          <div className={styles.statsGrid}>
            <StatCard label="Subjects Enrolled" value={data.stats.subjects_count ?? subjects.length} icon="📚" />
            <StatCard label="Quizzes Completed" value={quizzesCompleted} icon="✅" />
            <StatCard label="Avg FCL Level"      value={data.stats.avg_fcl ? `L${data.stats.avg_fcl}` : '—'} icon="🎯" />
            <StatCard label="Points Earned"      value={totalPoints} icon="⭐" />
          </div>

          <div className={styles.mainGrid}>
            <section className={styles.section}>
              <div className={styles.sectionHead}>
                <h2 className={styles.sectionTitle}>FCL Progress</h2>
                <Link to="/student/progress" className={styles.sectionLink}>View all →</Link>
              </div>
              <div className={styles.subjectList}>
                {subjects.length === 0 && (
                  <p className={styles.empty}>No subjects yet. <Link to="/student/library">Browse library</Link></p>
                )}
                {subjects.map(sub => (
                  <SubjectRow key={sub.id} subject={sub} />
                ))}
              </div>
            </section>

            <div className={styles.rightCol}>
              <section className={styles.section}>
                <div className={styles.sectionHead}>
                  <h2 className={styles.sectionTitle}>VARK Profile</h2>
                  <Link to="/student/progress" className={styles.sectionLink}>Details →</Link>
                </div>
                <div className={styles.varkGrid}>
                  {Object.entries(VARK_LABEL).map(([k, label]) => {
                    const pct = vark_profile[k.toLowerCase()] ?? 0;
                    return (
                      <div key={k} className={styles.varkItem}>
                        <div className={styles.varkBar}>
                          <div className={styles.varkFill} style={{ height: `${pct}%`, background: VARK_COLOR[k] }} />
                        </div>
                        <span className={styles.varkPct} style={{ color: VARK_COLOR[k] }}>{pct}%</span>
                        <span className={styles.varkLabel}>{label[0]}</span>
                      </div>
                    );
                  })}
                </div>
                <p className="text-muted text-xs text-center mt-2">Based on your chosen learning style. Complete more activities to refine the profile.</p>
              </section>
            </div>
          </div>

          <MoodTracker onComplete={handleMoodComplete} />
          <AdaptationNotifications events={adaptationEvents} onEventSeen={handleEventSeen} />
        </div>
      </div>
    </div>
  );
}

function SubjectRow({ subject }) {
  const fcl = subject.fcl_level ?? 1;
  const pct = ((fcl - 1) / 4) * 100;
  return (
    <div className={styles.subjectRow}>
      <div className={styles.subjectMeta}>
        <span className={styles.subjectName}>{subject.name}</span>
        <span className={`fcl-badge fcl-${fcl}`}>L{fcl} — {FCL_LABELS[fcl]}</span>
      </div>
      <div className="progress-track" style={{ flex: 1 }}>
        <div className="progress-fill" style={{ width: `${pct}%`, background: FCL_COLOR[fcl] }} />
      </div>
    </div>
  );
}

function StatCard({ label, value, icon }) {
  return (
    <div className={`card ${styles.statCard}`}>
      <span className={styles.statIcon}>{icon}</span>
      <p className={styles.statValue}>{value}</p>
      <p className={styles.statLabel}>{label}</p>
    </div>
  );
}