import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import Sidebar from '../components/Sidebar';
import Navbar  from '../components/Navbar';
import {
  getTeacherDashboard, getStrugglingStudents,
  getDirectives, upsertDirective, deleteDirective,
  getMySubjects,
} from '../services/teacher';
import { api } from '../services/client';          // fixed import
import styles from './TeacherDashboard.module.css';

const TABS = ['overview', 'students', 'directives', 'heatmap', 'engagement'];

export default function TeacherDashboard({ tab: initialTab = 'overview' }) {
  const { user } = useAuth();
  const [activeTab, setActiveTab]   = useState(initialTab);
  const [sideOpen, setSideOpen]     = useState(false);
  const [loading, setLoading]       = useState(true);
  const [dashboard, setDashboard]   = useState(null);
  const [students, setStudents]     = useState([]);
  const [struggling, setStruggling] = useState([]);
  const [directives, setDirectives] = useState([]);
  const [subjects, setSubjects]     = useState([]);
  const [filterSubject, setFilterSubject] = useState('');
  const teacherId = user?.id;

  // Heatmap state
  const [heatmapData, setHeatmapData] = useState(null);
  const [selectedSubjectId, setSelectedSubjectId] = useState('');
  const [heatmapLoading, setHeatmapLoading] = useState(false);

  // Engagement state
  const [engagementData, setEngagementData] = useState(null);
  const [engagementLoading, setEngagementLoading] = useState(false);

  // Load main data
  useEffect(() => {
    Promise.all([
      getTeacherDashboard(),
      getStrugglingStudents(),
      getDirectives(),
      getMySubjects(),
    ]).then(([dash, strugglingRes, dirs, subs]) => {
      setDashboard(dash);
      setStruggling(strugglingRes ?? []);
      setDirectives(dirs ?? []);

      // Build enriched student list from dashboard.students
      const studentMap = new Map();
      if (dash?.students) {
        dash.students.forEach(row => {
          const sid = row.student_id;
          if (!studentMap.has(sid)) {
            studentMap.set(sid, {
              id: sid,
              name: row.name,
              email: row.email,
              grade_label: row.grade_label,
              class_name: row.class_name,
              subject_ids: [],
              fcl_values: [],
              total_quizzes: 0,
              is_struggling: false,
              dominant_vark: '—',
            });
          }
          const stu = studentMap.get(sid);
          stu.subject_ids.push(row.subject_id);
          stu.fcl_values.push(row.fcl_level);
          stu.total_quizzes += (row.total_attempts || 0);
          if (row.is_at_risk) stu.is_struggling = true;
        });
      }
      const studentList = Array.from(studentMap.values()).map(s => ({
        ...s,
        fcl_level: s.fcl_values.length
          ? (s.fcl_values.reduce((a, b) => a + b, 0) / s.fcl_values.length).toFixed(1)
          : 1,
      }));
      setStudents(studentList);

      // Enrich subjects with student counts
      const subjectCounts = {};
      if (dash?.students) {
        dash.students.forEach(row => {
          const subjId = row.subject_id;
          subjectCounts[subjId] = (subjectCounts[subjId] || 0) + 1;
        });
      }
      const enrichedSubjects = (subs || []).map(sub => ({
        ...sub,
        student_count: subjectCounts[sub.id] || 0,
        grade_level: 'N/A',
      }));
      setSubjects(enrichedSubjects);

    }).catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  // Load heatmap when tab changes
  useEffect(() => {
    if (activeTab === 'heatmap' && teacherId && !heatmapData) {
      loadHeatmap();
    }
  }, [activeTab, teacherId]);

  // Load engagement when tab changes
  useEffect(() => {
    if (activeTab === 'engagement' && teacherId && !engagementData) {
      loadEngagement();
    }
  }, [activeTab, teacherId]);

  const loadHeatmap = async () => {
    if (!teacherId) return;
    setHeatmapLoading(true);
    try {
      const params = selectedSubjectId ? `?subject_id=${selectedSubjectId}` : '';
      const res = await api.get(`/api/teachers/heatmap/${teacherId}${params}`);
      setHeatmapData(res);
    } catch (err) {
      console.error('Failed to load heatmap', err);
    } finally {
      setHeatmapLoading(false);
    }
  };

  const loadEngagement = async () => {
    if (!teacherId) return;
    setEngagementLoading(true);
    try {
      const res = await api.get(`/api/teachers/engagement/${teacherId}`);
      setEngagementData(res);
    } catch (err) {
      console.error('Failed to load engagement', err);
    } finally {
      setEngagementLoading(false);
    }
  };

  const handleSubjectChange = (e) => {
    setSelectedSubjectId(e.target.value);
    setHeatmapData(null);
    loadHeatmap();
  };

  useEffect(() => { setActiveTab(initialTab); }, [initialTab]);

  const getMasteryColor = (level) => {
    const colors = { 0: '#64748B', 1: '#F59E0B', 2: '#3B82F6', 3: '#10B981' };
    return colors[level] || '#64748B';
  };

  return (
    <div className="dashboard-shell">
      <Sidebar open={sideOpen} onClose={() => setSideOpen(false)} />
      <div className="dashboard-main" style={{ paddingTop: 'var(--navbar-height)' }}>
        <Navbar onMenuToggle={() => setSideOpen(p => !p)} />

        <div className="dashboard-content">
          <div className={styles.header}>
            <div>
              <h1 className={styles.title}>Welcome, <span>{user?.first_name}</span></h1>
              <p className={styles.subtitle}>Manage your class and AI instructions</p>
            </div>
          </div>

          <div className={styles.tabs}>
            {TABS.map(t => (
              <button
                key={t}
                className={`${styles.tab} ${activeTab === t ? styles.activeTab : ''}`}
                onClick={() => setActiveTab(t)}
              >
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </button>
            ))}
          </div>

          {loading ? (
            <div className={styles.loading}>Loading dashboard…</div>
          ) : (
            <>
              {activeTab === 'overview'    && <OverviewTab   dashboard={dashboard} struggling={struggling} subjects={subjects} />}
              {activeTab === 'students'   && <StudentsTab    students={students} subjects={subjects} filterSubject={filterSubject} setFilterSubject={setFilterSubject} />}
              {activeTab === 'directives' && <DirectivesTab  directives={directives} setDirectives={setDirectives} students={students} subjects={subjects} />}
              
              {activeTab === 'heatmap' && (
                <div className="space-y-6">
                  <div className="card p-4 flex items-center gap-4">
                    <label className="text-muted text-sm">Filter by subject:</label>
                    <select
                      className="input w-64"
                      value={selectedSubjectId}
                      onChange={handleSubjectChange}
                    >
                      <option value="">All subjects</option>
                      {subjects.map(sub => (
                        <option key={sub.id} value={sub.id}>{sub.name}</option>
                      ))}
                    </select>
                    <button onClick={loadHeatmap} className="btn-ghost text-sm">Refresh</button>
                  </div>
                  {heatmapLoading ? (
                    <div className="card p-10 text-center text-muted">Loading heatmap…</div>
                  ) : heatmapData && heatmapData.students?.length > 0 ? (
                    <div className="card p-4 overflow-x-auto">
                      <h3 className="text-primary font-semibold mb-4">Topic Mastery Heatmap</h3>
                      <p className="text-muted text-xs mb-4">
                        Colour: Grey = Introduced | Amber = Practising | Blue = Proficient | Green = Mastered
                      </p>
                      <table className="min-w-full border-collapse text-sm">
                        <thead>
                          <tr>
                            <th className="p-2 text-left text-muted">Student</th>
                            {heatmapData.topics.map(topic => (
                              <th key={topic} className="p-2 text-left text-muted font-normal">
                                {topic.replace(/_/g, ' ').split(' ').slice(-1)[0]}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {heatmapData.students.map((student, idx) => (
                            <tr key={student.id} className="border-t border-border">
                              <td className="p-2 font-medium text-primary">{student.name}</td>
                              {heatmapData.data[idx].map((value, colIdx) => (
                                <td key={colIdx} className="p-1">
                                  <div
                                    className="w-6 h-6 rounded-md"
                                    style={{ backgroundColor: getMasteryColor(value) }}
                                    title={`${heatmapData.topics[colIdx]}: ${['Introduced','Practising','Proficient','Mastered'][value]}`}
                                  />
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="card p-10 text-center text-muted">No heatmap data available.</div>
                  )}
                </div>
              )}

              {activeTab === 'engagement' && (
                <div className="card p-6">
                  <h3 className="text-primary font-semibold mb-4">Engagement Report</h3>
                  <p className="text-muted text-sm mb-4">
                    Students inactive for more than {engagementData?.days_inactive || 7} days.
                  </p>
                  {engagementLoading ? (
                    <div className="text-center text-muted py-10">Loading engagement data…</div>
                  ) : engagementData && engagementData.students?.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full border-collapse text-sm">
                        <thead>
                          <tr className="border-b border-border">
                            <th className="p-3 text-left text-muted">Student</th>
                            <th className="p-3 text-left text-muted">Grade</th>
                            <th className="p-3 text-left text-muted">Email</th>
                            <th className="p-3 text-left text-muted">Days Inactive</th>
                            <th className="p-3 text-left text-muted">Last Activity</th>
                          </tr>
                        </thead>
                        <tbody>
                          {engagementData.students.map(student => (
                            <tr key={student.student_id} className="border-b border-border/50">
                              <td className="p-3 text-primary">{student.name}</td>
                              <td className="p-3 text-muted">{student.grade_label || '—'}</td>
                              <td className="p-3 text-muted">{student.email}</td>
                              <td className="p-3 text-red-400 font-medium">{student.days_inactive} days</td>
                              <td className="p-3 text-muted">
                                {student.last_activity ? new Date(student.last_activity).toLocaleDateString() : 'Never'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="text-center text-green-400 py-10">
                      ✅ All students are active! No one has been inactive for &gt;7 days.
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ------------------------------------------------------------
// Overview Tab
// ------------------------------------------------------------
function OverviewTab({ dashboard, struggling, subjects }) {
  const s = dashboard?.stats ?? {};
  return (
    <div>
      <div className={styles.statsGrid}>
        <StatCard label="Total Students" value={s.total_students ?? '—'} icon="👥" />
        <StatCard label="Subjects"        value={s.subjects_count ?? subjects.length} icon="📚" />
        <StatCard label="Avg Class FCL"   value={s.avg_fcl ? `L${s.avg_fcl}` : '—'} icon="📊" />
        <StatCard label="Struggling"      value={struggling.length} icon="⚠️" accent="warn" />
      </div>

      {struggling.length > 0 && (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Students Needing Attention</h2>
          <div className={styles.alertList}>
            {struggling.map(st => (
              <div key={st.id} className={styles.alertRow}>
                <div className={styles.alertAvatar}>{st.first_name?.[0]}{st.last_name?.[0]}</div>
                <div>
                  <p className={styles.alertName}>{st.first_name} {st.last_name}</p>
                  <p className={styles.alertReason}>{st.alert_reason ?? `FCL Level ${st.fcl_level} — below class average`}</p>
                </div>
                <span className="badge badge-warn">FCL L{st.fcl_level}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className={styles.section} style={{ marginTop: 'var(--space-6)' }}>
        <h2 className={styles.sectionTitle}>My Subjects</h2>
        <div className={styles.subjectCards}>
          {subjects.map(sub => (
            <div key={sub.id} className={styles.subjectCard}>
              <p className={styles.subjectName}>{sub.name}</p>
              <p className={styles.subjectMeta}>{sub.student_count ?? 0} students</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

// ------------------------------------------------------------
// Students Tab
// ------------------------------------------------------------
function StudentsTab({ students, subjects, filterSubject, setFilterSubject }) {
  const filtered = filterSubject
    ? students.filter(s => s.subject_ids?.includes(Number(filterSubject)))
    : students;
  return (
    <div>
      <div className={styles.tableControls}>
        <select
          className="input"
          style={{ maxWidth: 220 }}
          value={filterSubject}
          onChange={e => setFilterSubject(e.target.value)}
        >
          <option value="">All subjects</option>
          {subjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
        <span className={styles.count}>{filtered.length} students</span>
      </div>
      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Student</th>
              <th>FCL Level</th>
              <th>VARK</th>
              <th>Quizzes</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(st => (
              <tr key={st.id}>
                <td>
                  <div className={styles.studentCell}>
                    <div className={styles.smallAvatar}>
                      {st.name?.split(' ').map(w => w[0]).join('')}
                    </div>
                    <div>
                      <p className={styles.studentName}>{st.name}</p>
                      <p className={styles.studentEmail}>{st.email}</p>
                    </div>
                  </div>
                </td>
                <td><span className={`fcl-badge fcl-${st.fcl_level ?? 1}`}>L{st.fcl_level ?? 1}</span></td>
                <td><span className={styles.varkPill}>{st.dominant_vark}</span></td>
                <td className={styles.quizCount}>{st.total_quizzes}</td>
                <td>
                  <span className={`badge ${st.is_struggling ? 'badge-warn' : 'badge-success'}`}>
                    {st.is_struggling ? 'Needs help' : 'On track'}
                  </span>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr><td colSpan={5} className={styles.empty}>No students found</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ------------------------------------------------------------
// Directives Tab (fixed)
// ------------------------------------------------------------
function DirectivesTab({ directives, setDirectives, students, subjects }) {
  const [form, setForm]       = useState({ student_id: '', subject_id: '', instruction: '' });
  const [saving, setSaving]   = useState(false);
  const [msg, setMsg]         = useState('');

  const handleSave = async () => {
    if (!form.instruction.trim()) return;
    setSaving(true);
    try {
      // Backend expects 'directive', not 'instruction'
      const payload = {
        student_id: form.student_id || null,
        subject_id: form.subject_id || null,
        directive:  form.instruction.trim(),
        label:      form.label || null,
      };
      const saved = await upsertDirective(payload);
      setDirectives(prev => {
        const idx = prev.findIndex(
          d => d.student_id === saved.student_id && d.subject_id === saved.subject_id
        );
        if (idx >= 0) {
          const copy = [...prev];
          copy[idx] = saved;
          return copy;
        }
        return [...prev, saved];
      });
      setMsg('Directive saved!');
      setTimeout(() => setMsg(''), 2500);
      setForm({ student_id: '', subject_id: '', instruction: '' });
    } catch {
      setMsg('Save failed');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    await deleteDirective(id);
    setDirectives(prev => prev.filter(d => d.id !== id));
  };

  return (
    <div>
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>New AI Directive</h2>
        <p className={styles.directiveHelp}>
          AI directives are custom instructions the tutor AI follows when helping a specific student. 
          Leave student/subject blank to apply globally.
        </p>
        <div className={styles.directiveForm}>
          <select
            className="input"
            value={form.student_id}
            onChange={e => setForm(p => ({ ...p, student_id: e.target.value }))}
          >
            <option value="">All students</option>
            {students.map(s => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
          <select
            className="input"
            value={form.subject_id}
            onChange={e => setForm(p => ({ ...p, subject_id: e.target.value }))}
          >
            <option value="">All subjects</option>
            {subjects.map(s => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
          <textarea
            className={`input ${styles.directiveTextarea}`}
            placeholder="e.g. Always use visual diagrams when explaining math. Avoid long text blocks. Praise effort before correcting mistakes."
            value={form.instruction}
            onChange={e => setForm(p => ({ ...p, instruction: e.target.value }))}
            rows={4}
          />
          <div className={styles.directiveActions}>
            {msg && <span className={styles.msg}>{msg}</span>}
            <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
              {saving ? 'Saving…' : 'Save Directive'}
            </button>
          </div>
        </div>
      </section>
      <section className={styles.section} style={{ marginTop: 'var(--space-6)' }}>
        <h2 className={styles.sectionTitle}>Active Directives</h2>
        <div className={styles.directiveList}>
          {directives.length === 0 && <p className={styles.empty}>No directives yet</p>}
          {directives.map(d => {
            const st  = students.find(s => s.id === d.student_id);
            const sub = subjects.find(s => s.id === d.subject_id);
            return (
              <div key={d.id} className={styles.directiveItem}>
                <div className={styles.directiveMeta}>
                  <span className="badge badge-accent">{st ? st.name : 'All students'}</span>
                  <span className="badge badge-accent">{sub ? sub.name : 'All subjects'}</span>
                </div>
                <p className={styles.directiveText}>{d.instruction || d.directive}</p>
                <button className={styles.deleteBtn} onClick={() => handleDelete(d.id)}>✕ Remove</button>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}

// ------------------------------------------------------------
// Shared Components
// ------------------------------------------------------------
function StatCard({ label, value, icon, accent }) {
  return (
    <div className={`card ${styles.statCard}`}>
      <span className={styles.statIcon}>{icon}</span>
      <p className={styles.statValue} style={accent === 'warn' ? { color: 'var(--accent-warn)' } : {}}>{value}</p>
      <p className={styles.statLabel}>{label}</p>
    </div>
  );
}