import { useState, useEffect } from 'react';
import PageShell from '../components/PageShell';
import api from '../services/api';

const SUBJECTS = [
  { code: 'MATH', name: 'Mathematics' },
  { code: 'SCI',  name: 'Science' },
  { code: 'ENG',  name: 'English' },
  { code: 'SOC',  name: 'Social Studies' },
  { code: 'CS',   name: 'Computer Science' },
];

export default function TeacherUpload() {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [contentType, setContentType] = useState('text');
  const [subjectCode, setSubjectCode] = useState('MATH');
  const [topicTags, setTopicTags] = useState('');
  const [gradeMin, setGradeMin] = useState(1);
  const [gradeMax, setGradeMax] = useState(19);
  const [contentData, setContentData] = useState('');
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [preview, setPreview] = useState('');

  const handleFileChange = (e) => {
    const f = e.target.files[0];
    if (!f) return;
    setFile(f);
    const reader = new FileReader();
    reader.onload = (ev) => {
      const base64 = ev.target.result.split(',')[1];
      setContentData(base64);
      setPreview(f.name);
    };
    reader.readAsDataURL(f);
  };

  const handleSubmit = async () => {
    if (!title.trim() || !subjectCode) {
      setMessage({ type: 'error', text: 'Title and subject are required.' });
      return;
    }
    if (!contentData && contentType !== 'video_link') {
      setMessage({ type: 'error', text: 'Please select a file.' });
      return;
    }
    setLoading(true);
    try {
      await api.post('/api/library/upload', {
        title,
        description,
        content_type: contentType,
        content_data: contentType === 'video_link' ? contentData : contentData,
        subject_code: subjectCode,
        topic_tags: topicTags.split(',').map(t => t.trim()).filter(t => t),
        grade_min: gradeMin,
        grade_max: gradeMax,
      });
      setMessage({ type: 'success', text: 'Upload successful!' });
      setTitle('');
      setDescription('');
      setContentData('');
      setFile(null);
      setPreview('');
      setTopicTags('');
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.detail || 'Upload failed.' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageShell title="Upload Content" subtitle="Add learning materials for your students">
      <div className="max-w-2xl mx-auto">
        <div className="card p-6">
          {message && (
            <div className={`mb-4 p-3 rounded-lg text-sm ${
              message.type === 'success' ? 'bg-green-500/10 border border-green-500/30 text-green-400' : 'bg-red-500/10 border border-red-500/30 text-red-400'
            }`}>
              {message.text}
            </div>
          )}
          <div className="space-y-4">
            <div>
              <label className="text-muted text-xs uppercase tracking-wide block mb-1.5">Title *</label>
              <input type="text" value={title} onChange={e => setTitle(e.target.value)} className="w-full bg-input border border-border rounded-lg px-4 py-2 text-primary text-sm focus:border-teal/60 focus:outline-none" />
            </div>
            <div>
              <label className="text-muted text-xs uppercase tracking-wide block mb-1.5">Description</label>
              <textarea rows={3} value={description} onChange={e => setDescription(e.target.value)} className="w-full bg-input border border-border rounded-lg px-4 py-2 text-primary text-sm focus:border-teal/60 focus:outline-none" />
            </div>
            <div>
              <label className="text-muted text-xs uppercase tracking-wide block mb-1.5">Content Type</label>
              <select value={contentType} onChange={e => setContentType(e.target.value)} className="w-full bg-input border border-border rounded-lg px-4 py-2 text-primary text-sm focus:border-teal/60 focus:outline-none">
                <option value="text">Text / Notes</option>
                <option value="pdf">PDF Document</option>
                <option value="video_link">YouTube / Video Link</option>
                <option value="image">Image</option>
              </select>
            </div>
            {(contentType === 'text' || contentType === 'pdf' || contentType === 'image') && (
              <div>
                <label className="text-muted text-xs uppercase tracking-wide block mb-1.5">File</label>
                <input type="file" onChange={handleFileChange} accept={contentType === 'image' ? 'image/*' : contentType === 'pdf' ? '.pdf' : '.txt,.md'} className="w-full text-muted text-sm" />
                {preview && <p className="text-teal text-xs mt-1">✓ {preview}</p>}
              </div>
            )}
            {contentType === 'video_link' && (
              <div>
                <label className="text-muted text-xs uppercase tracking-wide block mb-1.5">Video URL</label>
                <input type="url" value={contentData} onChange={e => setContentData(e.target.value)} placeholder="https://youtube.com/..." className="w-full bg-input border border-border rounded-lg px-4 py-2 text-primary text-sm focus:border-teal/60 focus:outline-none" />
              </div>
            )}
            <div>
              <label className="text-muted text-xs uppercase tracking-wide block mb-1.5">Subject *</label>
              <select value={subjectCode} onChange={e => setSubjectCode(e.target.value)} className="w-full bg-input border border-border rounded-lg px-4 py-2 text-primary text-sm focus:border-teal/60 focus:outline-none">
                {SUBJECTS.map(s => <option key={s.code} value={s.code}>{s.name}</option>)}
              </select>
            </div>
            <div>
              <label className="text-muted text-xs uppercase tracking-wide block mb-1.5">Topic Tags (comma-separated)</label>
              <input type="text" value={topicTags} onChange={e => setTopicTags(e.target.value)} placeholder="e.g., algebra, equations" className="w-full bg-input border border-border rounded-lg px-4 py-2 text-primary text-sm focus:border-teal/60 focus:outline-none" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-muted text-xs uppercase tracking-wide block mb-1.5">Minimum Grade</label>
                <input type="number" min={1} max={19} value={gradeMin} onChange={e => setGradeMin(parseInt(e.target.value))} className="w-full bg-input border border-border rounded-lg px-4 py-2 text-primary text-sm focus:border-teal/60 focus:outline-none" />
              </div>
              <div>
                <label className="text-muted text-xs uppercase tracking-wide block mb-1.5">Maximum Grade</label>
                <input type="number" min={1} max={19} value={gradeMax} onChange={e => setGradeMax(parseInt(e.target.value))} className="w-full bg-input border border-border rounded-lg px-4 py-2 text-primary text-sm focus:border-teal/60 focus:outline-none" />
              </div>
            </div>
            <button onClick={handleSubmit} disabled={loading} className="w-full btn-primary py-2.5 mt-2">
              {loading ? 'Uploading...' : 'Upload Content'}
            </button>
          </div>
        </div>
      </div>
    </PageShell>
  );
}