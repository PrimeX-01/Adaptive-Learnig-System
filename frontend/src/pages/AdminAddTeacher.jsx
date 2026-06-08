import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import PageShell from '../components/PageShell';
import api from '../services/api';

export default function AdminAddTeacher() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: '',
    email: '',
    password: '',
    username: '',
    subjects: [],
    grade_min: 1,
    grade_max: 19,
  });
  const [subjects, setSubjects] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    api.get('/api/subjects/available')
      .then(res => setSubjects(res.data))
      .catch(err => console.error(err));
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post('/api/admin/create-teacher', form);
      setMessage({ type: 'success', text: 'Teacher created successfully!' });
      setForm({ name: '', email: '', password: '', username: '', subjects: [], grade_min: 1, grade_max: 19 });
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.detail || 'Creation failed' });
    } finally {
      setLoading(false);
      setTimeout(() => setMessage(null), 4000);
    }
  };

  const toggleSubject = (id) => {
    setForm(prev => ({
      ...prev,
      subjects: prev.subjects.includes(id) ? prev.subjects.filter(s => s !== id) : [...prev.subjects, id]
    }));
  };

  return (
    <PageShell title="Admin" subtitle="Create a new teacher account">
      <div className="max-w-2xl mx-auto">
        <div className="card p-6">
          <h2 className="text-primary font-bold text-xl mb-4">Add Teacher</h2>
          {message && (
            <div className={`mb-4 p-3 rounded-lg text-sm ${message.type === 'success' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
              {message.text}
            </div>
          )}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-muted text-xs uppercase block mb-1">Full Name</label>
              <input type="text" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} required className="w-full bg-input border border-border rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-muted text-xs uppercase block mb-1">Email</label>
              <input type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} required className="w-full bg-input border border-border rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-muted text-xs uppercase block mb-1">Password</label>
              <input type="password" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} required className="w-full bg-input border border-border rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-muted text-xs uppercase block mb-1">Username (optional)</label>
              <input type="text" value={form.username} onChange={e => setForm({ ...form, username: e.target.value })} className="w-full bg-input border border-border rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-muted text-xs uppercase block mb-1">Subjects Taught</label>
              <div className="flex flex-wrap gap-2">
                {subjects.map(s => (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => toggleSubject(s.id)}
                    className={`text-xs px-3 py-1 rounded-lg border ${form.subjects.includes(s.id) ? 'border-teal bg-teal/10 text-teal' : 'border-border text-muted'}`}
                  >
                    {s.name}
                  </button>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-muted text-xs uppercase block mb-1">Grade Min</label>
                <input type="number" value={form.grade_min} onChange={e => setForm({ ...form, grade_min: parseInt(e.target.value) })} className="w-full bg-input border border-border rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="text-muted text-xs uppercase block mb-1">Grade Max</label>
                <input type="number" value={form.grade_max} onChange={e => setForm({ ...form, grade_max: parseInt(e.target.value) })} className="w-full bg-input border border-border rounded-lg px-3 py-2 text-sm" />
              </div>
            </div>
            <button type="submit" disabled={loading} className="w-full btn-primary py-2">
              {loading ? 'Creating...' : 'Create Teacher'}
            </button>
          </form>
        </div>
      </div>
    </PageShell>
  );
}