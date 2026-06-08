import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import PageShell from '../components/PageShell';
import api from '../services/api';

export default function TeacherTopics() {
  const { user, isAuthenticated, isTeacher } = useAuth();
  const navigate = useNavigate();
  const teacherId = user?.id;

  useEffect(() => {
    if (!isAuthenticated) navigate('/auth', { replace: true });
    else if (!isTeacher) navigate('/dashboard', { replace: true });
  }, [isAuthenticated, isTeacher, navigate]);

  const [subjects, setSubjects] = useState([]);
  const [selectedSubject, setSelectedSubject] = useState(null);
  const [topics, setTopics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [showForm, setShowForm] = useState(false);
  const [editingTopic, setEditingTopic] = useState(null);
  const [topicName, setTopicName] = useState('');
  const [topicCode, setTopicCode] = useState('');
  const [topicDesc, setTopicDesc] = useState('');
  const [saving, setSaving] = useState(false);

  // Load teacher's subjects from dashboard endpoint
  useEffect(() => {
    if (!teacherId) return;
    api.get('/api/teachers/dashboard')
      .then(res => {
        const teacherData = res.data;
        setSubjects(teacherData.teacher_subjects || []);
      })
      .catch(() => setError('Failed to load subjects'))
      .finally(() => setLoading(false));
  }, [teacherId]);

  const loadTopics = async (subjectId) => {
    setLoading(true);
    try {
      const res = await api.get(`/api/teachers/subjects/${subjectId}/topics`);
      setTopics(res.data || []);
    } catch (err) {
      setError('Failed to load topics');
    } finally {
      setLoading(false);
    }
  };

  const handleSubjectChange = (subjectId) => {
    const subj = subjects.find(s => s.id === parseInt(subjectId));
    setSelectedSubject(subj);
    if (subj) loadTopics(subj.id);
    else setTopics([]);
    setShowForm(false);
    setEditingTopic(null);
  };

  const resetForm = () => {
    setTopicName('');
    setTopicCode('');
    setTopicDesc('');
    setEditingTopic(null);
    setShowForm(false);
  };

  const handleEdit = (topic) => {
    setEditingTopic(topic);
    setTopicName(topic.name);
    setTopicCode(topic.code);
    setTopicDesc(topic.description || '');
    setShowForm(true);
  };

  const handleDelete = async (topicId) => {
    if (!window.confirm('Delete this topic? It may affect existing quizzes.')) return;
    try {
      await api.delete(`/api/teachers/topics/${topicId}`);
      setSuccess('Topic deleted');
      setTimeout(() => setSuccess(''), 3000);
      loadTopics(selectedSubject.id);
    } catch (err) {
      setError('Failed to delete topic');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!topicName.trim() || !topicCode.trim()) {
      setError('Name and code are required');
      return;
    }
    if (topicCode.length < 2 || topicCode.length > 6) {
      setError('Code must be 2–6 characters');
      return;
    }
    setSaving(true);
    setError('');
    try {
      if (editingTopic) {
        await api.patch(`/api/teachers/topics/${editingTopic.id}`, {
          name: topicName.trim(),
          code: topicCode.trim().toUpperCase(),
          description: topicDesc.trim() || null,
        });
        setSuccess('Topic updated');
      } else {
        await api.post(`/api/teachers/subjects/${selectedSubject.id}/topics`, {
          name: topicName.trim(),
          code: topicCode.trim().toUpperCase(),
          description: topicDesc.trim() || null,
        });
        setSuccess('Topic created');
      }
      setTimeout(() => setSuccess(''), 3000);
      resetForm();
      loadTopics(selectedSubject.id);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save topic');
    } finally {
      setSaving(false);
    }
  };

  if (!isTeacher) return null;

  return (
    <PageShell title="Topic Manager" subtitle="Create and manage topics for your subjects">
      <div className="max-w-4xl mx-auto space-y-6">
        {error && <div className="px-4 py-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm">{error}</div>}
        {success && <div className="px-4 py-3 bg-green-500/10 border border-green-500/30 rounded-xl text-green-400 text-sm">{success}</div>}

        <div className="card p-5">
          <label className="text-muted text-xs uppercase tracking-wide block mb-2">Select Subject</label>
          <select
            className="w-full bg-input border border-border rounded-lg px-4 py-2.5 text-primary text-sm"
            value={selectedSubject?.id || ''}
            onChange={(e) => handleSubjectChange(e.target.value)}
          >
            <option value="">-- Choose a subject --</option>
            {subjects.map(sub => (
              <option key={sub.id} value={sub.id}>{sub.name} ({sub.code})</option>
            ))}
          </select>
        </div>

        {selectedSubject && (
          <>
            <div className="card p-5">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-primary font-semibold">Topics for {selectedSubject.name}</h3>
                <button
                  onClick={() => { resetForm(); setShowForm(true); }}
                  className="btn-primary text-sm py-1.5 px-4"
                >
                  + New Topic
                </button>
              </div>

              {loading ? (
                <div className="text-center py-8 text-muted">Loading topics…</div>
              ) : topics.length === 0 ? (
                <div className="text-center py-8 text-muted">No topics yet. Create your first topic.</div>
              ) : (
                <div className="space-y-2">
                  {topics.map(topic => (
                    <div key={topic.id} className="flex items-center justify-between p-3 bg-app border border-border rounded-lg">
                      <div>
                        <p className="text-primary font-medium">{topic.name}</p>
                        <p className="text-muted text-xs">{topic.code} – {topic.description || 'No description'}</p>
                      </div>
                      <div className="flex gap-2">
                        <button onClick={() => handleEdit(topic)} className="text-teal text-xs hover:underline">Edit</button>
                        <button onClick={() => handleDelete(topic.id)} className="text-red-400 text-xs hover:underline">Delete</button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {showForm && (
              <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
                <div className="card p-6 w-full max-w-md">
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="text-primary font-semibold">{editingTopic ? 'Edit Topic' : 'Create Topic'}</h3>
                    <button onClick={resetForm} className="text-muted hover:text-primary">✕</button>
                  </div>
                  <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                      <label className="text-muted text-xs uppercase tracking-wide block mb-1.5">Topic Name</label>
                      <input
                        type="text"
                        value={topicName}
                        onChange={e => setTopicName(e.target.value)}
                        placeholder="e.g. Photosynthesis, Algebra Basics"
                        className="w-full bg-input border border-border rounded-lg px-4 py-2.5 text-primary text-sm"
                        required
                      />
                    </div>
                    <div>
                      <label className="text-muted text-xs uppercase tracking-wide block mb-1.5">Topic Code</label>
                      <input
                        type="text"
                        value={topicCode}
                        onChange={e => setTopicCode(e.target.value.toUpperCase().slice(0, 6))}
                        placeholder="e.g. PHOTO, ALGBAS"
                        maxLength={6}
                        className="w-full bg-input border border-border rounded-lg px-4 py-2.5 text-primary text-sm"
                        required
                      />
                      <p className="text-muted text-xs mt-1">2–6 uppercase characters, used for identification</p>
                    </div>
                    <div>
                      <label className="text-muted text-xs uppercase tracking-wide block mb-1.5">Description (optional)</label>
                      <textarea
                        value={topicDesc}
                        onChange={e => setTopicDesc(e.target.value)}
                        rows={3}
                        placeholder="Brief description of what this topic covers"
                        className="w-full bg-input border border-border rounded-lg px-4 py-2.5 text-primary text-sm resize-none"
                      />
                    </div>
                    <div className="flex gap-3 pt-2">
                      <button type="submit" disabled={saving} className="btn-primary flex-1 py-2 disabled:opacity-50">
                        {saving ? 'Saving…' : (editingTopic ? 'Update Topic' : 'Create Topic')}
                      </button>
                      <button type="button" onClick={resetForm} className="btn-ghost flex-1">Cancel</button>
                    </div>
                  </form>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </PageShell>
  );
}