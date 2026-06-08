import { Link, Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import styles from './Landing.module.css';

const MARQUEE_ITEMS = [
  'FCL Progression', 'VARK Profiling', 'AI Tutor', 'Syllabus Awareness',
  'Smart Library', 'Teacher Directives', 'Quiz Engine', 'Groq LLaMA 70B',
  'Struggling Detection', 'Supabase · FastAPI',
];

const FEATURES = [
  { icon: '🧠', color: 'g', title: 'FCL Progression',
    desc: 'Fused Cognitive Level tracks mastery across 20 levels — Topic → Subject → Overall FCL, powered by quizzes, study time, and teacher awards.',
    chip: 'Levels 1–20' },
  { icon: '🎯', color: 'v', title: 'VARK Adaptation',
    desc: 'Detects your learning style after 20 interactions per subject and reshapes content delivery. Teachers are notified on every style change.',
    chip: 'Per-subject' },
  { icon: '✨', color: 'o', title: 'AI Tutor',
    desc: 'Groq-powered LLaMA 70B with full syllabus awareness, teacher directives, and your library injected as context — never generic.',
    chip: 'llama-3.3-70b' },
  { icon: '📚', color: 'b', title: 'Smart Library',
    desc: 'Teachers upload text, links, images, and PDFs filtered by grade and subject. pgvector RAG queued for Phase 2 deep retrieval.',
    chip: 'RAG-ready' },
  { icon: '⚠️', color: 'v', title: 'Struggling Detection',
    desc: 'Identifies at-risk students automatically with 24-hour deduplication — actionable teacher alerts before anyone falls too far behind.',
    chip: 'Real-time' },
  { icon: '🏆', color: 'g', title: 'Quiz Engine',
    desc: 'Adaptive scoring awards 1–5 points based on hint and tutor usage. Session time adds 1 point per 10-minute block of engagement.',
    chip: 'Smart scoring' },
];

export default function Landing() {
  const { isAuthenticated, isTeacher, loading } = useAuth();
  const doubled = [...MARQUEE_ITEMS, ...MARQUEE_ITEMS];

  // If user is already logged in, send them straight to their dashboard
  if (!loading && isAuthenticated) {
    return <Navigate to={isTeacher ? '/teacher' : '/student'} replace />;
  }

  return (
    <div className={styles.page}>
      {/* ── Hero ── */}
      <section className={styles.hero}>
        <div className={styles.mesh} />
        <div className={styles.gridLines} />

        <div className={styles.badge}>
          <span className={styles.pulseDot} />
          AI-Powered Adaptive Learning · CSC402
        </div>

        <h1 className={styles.h1}>
          Learn the way<br />
          <span className={styles.outline}>your brain</span><br />
          <span className={styles.green}>actually works.</span>
        </h1>

        <p className={styles.sub}>
          SiveAdapt maps your VARK learning profile, tracks your Fused Cognitive
          Level in real-time, and reshapes every lesson around how you grow best.
        </p>

        <div className={styles.btns}>
          <Link to="/auth?tab=register" className="btn-g">Start learning free →</Link>
          <Link to="/auth" className="btn-outline">Sign in</Link>
        </div>

        <div className={styles.stats}>
          <div className={styles.statItem}>
            <div className={styles.statVal}>20<span>×</span></div>
            <div className={styles.statLab}>FCL Levels</div>
          </div>
          <div className={styles.statDivider} />
          <div className={styles.statItem}>
            <div className={styles.statVal}>4<span>+</span></div>
            <div className={styles.statLab}>Learning styles</div>
          </div>
          <div className={styles.statDivider} />
          <div className={styles.statItem}>
            <div className={styles.statVal}>∞</div>
            <div className={styles.statLab}>Adaptations</div>
          </div>
        </div>
      </section>

      {/* ── Marquee ── */}
      <div className={styles.marquee}>
        <div className={styles.mqTrack}>
          {doubled.map((item, i) => (
            <span key={i} className={styles.mqItem}>
              <span className={styles.mqDot} />{item}
            </span>
          ))}
        </div>
      </div>

      {/* ── Features ── */}
      <section className={styles.features} id="features">
        <div className={styles.featHeader}>
          <div>
            <div className="sec-eyebrow">Core Platform</div>
            <div className="sec-h">Everything you need<br />to learn smarter</div>
          </div>
          <p className={styles.featSub}>
            Built with FastAPI, React 18, Supabase, and Groq — designed for every
            learner from Grade 1 to tertiary level.
          </p>
        </div>
        <div className={styles.featGrid}>
          {FEATURES.map((f, i) => (
            <div key={i} className={styles.featCard}>
              <div className={`${styles.featIcon} ${styles[`ic_${f.color}`]}`}>{f.icon}</div>
              <h3 className={styles.featTitle}>{f.title}</h3>
              <p className={styles.featDesc}>{f.desc}</p>
              <div className={`${styles.featChip} ${styles[`chip_${f.color}`]}`}>{f.chip}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA ── */}
      <div className={styles.ctaWrap}>
        <div className={styles.cta}>
          <h2 className={styles.ctaH}>Ready to adapt<br />the way you learn?</h2>
          <p className={styles.ctaSub}>Join students at the University of Eswatini already using SiveAdapt.</p>
          <div className={styles.ctaBtns}>
            <Link to="/auth?tab=register" className="btn-g">Get started free →</Link>
            <Link to="/auth" className="btn-outline">Sign in</Link>
          </div>
        </div>
      </div>

      {/* ── Footer ── */}
      <footer className={styles.footer}>
        <div className={styles.footerLogo}>Sive<em>Adapt</em></div>
        <div className={styles.footerLinks}>
          <a href="#">Privacy</a><a href="#">Terms</a>
          <a href="#">Contact</a><a href="#">CSC402</a>
        </div>
        <div className={styles.footerCopy}>© 2026 SiveAdapt · University of Eswatini</div>
      </footer>
    </div>
  );
}