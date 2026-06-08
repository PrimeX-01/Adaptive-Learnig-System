import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import PageShell from '../components/PageShell';
import api from '../services/api';

/* ─── Grade helpers ──────────────────────────────────────────── */
const ALL_GRADES = [
  { value: 1,  label: 'Grade 1',         group: 'Primary School'           },
  { value: 2,  label: 'Grade 2',         group: 'Primary School'           },
  { value: 3,  label: 'Grade 3',         group: 'Primary School'           },
  { value: 4,  label: 'Grade 4',         group: 'Primary School'           },
  { value: 5,  label: 'Grade 5',         group: 'Primary School'           },
  { value: 6,  label: 'Grade 6',         group: 'Primary School'           },
  { value: 7,  label: 'Grade 7',         group: 'Primary School'           },
  { value: 8,  label: 'Grade 8',         group: 'High School'              },
  { value: 9,  label: 'Grade 9',         group: 'High School'              },
  { value: 10, label: 'Grade 10',        group: 'High School'              },
  { value: 11, label: 'Grade 11',        group: 'High School'              },
  { value: 12, label: 'Grade 12',        group: 'High School'              },
  { value: 13, label: 'UG Level 1',      group: 'Undergraduate'            },
  { value: 14, label: 'UG Level 2',      group: 'Undergraduate'            },
  { value: 15, label: 'UG Level 3',      group: 'Undergraduate'            },
  { value: 16, label: 'UG Level 4',      group: 'Undergraduate'            },
  { value: 17, label: 'UG Level 5',      group: 'Undergraduate'            },
  { value: 18, label: 'Masters',         group: 'Postgraduate'             },
  { value: 19, label: 'PhD',             group: 'Postgraduate'             },
];

const GRADE_BAND_PRESETS = [
  { label: 'Primary (1–7)',      min: 1,  max: 7  },
  { label: 'High School (8–12)', min: 8,  max: 12 },
  { label: 'Undergraduate',      min: 13, max: 17 },
  { label: 'Postgraduate',       min: 18, max: 19 },
  { label: 'All Grades',         min: 1,  max: 19 },
];

/* ─── File type config ───────────────────────────────────────── */
const FILE_TYPES = [
  { value: 'pdf', label: 'PDF Document', icon: '📄', color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/30', accept: '.pdf', maxSizeMB: 20, desc: 'Textbooks, worksheets, past papers' },
  { value: 'image', label: 'Image', icon: '🖼', color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/30', accept: 'image/*', maxSizeMB: 5, desc: 'Diagrams, charts, photos, illustrations' },
  { value: 'text', label: 'Text / Notes', icon: '📝', color: 'text-green-400', bg: 'bg-green-500/10 border-green-500/30', accept: '.txt,.md', maxSizeMB: 2, desc: 'Class notes, summaries, explanations' },
  { value: 'video_link', label: 'Video Link', icon: '🎬', color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/30', accept: null, maxSizeMB: null, desc: 'YouTube, Vimeo or any video URL' },
  { value: 'link', label: 'Web Link', icon: '🔗', color: 'text-purple-400', bg: 'bg-purple-500/10 border-purple-500/30', accept: null, maxSizeMB: null, desc: 'Websites, online tools, references' },
];

/* ─── Uploaded item card ─────────────────────────────────────── */
function UploadedItemCard({ item, onEdit, onDelete }) {
  const ft = FILE_TYPES.find(f => f.value === item.content_type) || FILE_TYPES[2];
  return (
    <div className='card p-4 flex gap-4 group hover:border-teal/30 transition-all'>
      <div className={`w-12 h-12 rounded-xl border flex items-center justify-center text-2xl flex-shrink-0 ${ft.bg}`}>
        {ft.icon}
      </div>
      <div className='flex-1 min-w-0'>
        <h4 className='text-primary text-sm font-semibold truncate'>{item.title}</h4>
        {item.description && <p className='text-muted text-xs mt-0.5 line-clamp-1'>{item.description}</p>}
        <div className='flex flex-wrap gap-2 mt-2'>
          <span className='text-xs px-2 py-0.5 bg-teal/10 border border-teal/30 text-teal rounded-full'>Gr {item.grade_min}–{item.grade_max}</span>
          <span className={`text-xs px-2 py-0.5 rounded-full border ${ft.bg} ${ft.color}`}>{ft.label}</span>
          {(item.topic_tags || []).slice(0, 2).map(tag => (
            <span key={tag} className='text-xs px-2 py-0.5 bg-border/50 text-muted rounded-full'>#{tag}</span>
          ))}
        </div>
      </div>
      <div className='flex flex-col gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0'>
        <button onClick={() => onEdit(item)} className='text-teal text-xs px-3 py-1.5 rounded-lg border border-teal/30 hover:bg-teal/10 transition-colors'>Edit</button>
        <button onClick={() => onDelete(item.id)} className='text-red-400 text-xs px-3 py-1.5 rounded-lg border border-red-500/30 hover:bg-red-500/10 transition-colors'>Delete</button>
      </div>
    </div>
  );
}

/* ─── Drop zone ──────────────────────────────────────────────── */
function DropZone({ accept, onFileDrop, disabled }) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);
  const handleDrop = e => { e.preventDefault(); setDragging(false); if (disabled) return; const file = e.dataTransfer.files?.[0]; if (file) onFileDrop(file); };
  return (
    <div onDragOver={e => { e.preventDefault(); if (!disabled) setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={handleDrop} onClick={() => !disabled && inputRef.current?.click()}
      className={`relative rounded-2xl border-2 border-dashed transition-all duration-200 cursor-pointer flex flex-col items-center justify-center gap-3 py-10 px-6 text-center select-none ${disabled ? 'border-border/40 opacity-40 cursor-not-allowed' : dragging ? 'border-teal bg-teal/10 scale-[1.01]' : 'border-border hover:border-teal/50 hover:bg-teal/5'}`}>
      <input ref={inputRef} type='file' accept={accept} className='hidden' onChange={e => { const f = e.target.files?.[0]; if (f) onFileDrop(f); e.target.value = ''; }}/>
      <div className={`w-14 h-14 rounded-2xl border flex items-center justify-center text-3xl transition-all ${dragging ? 'bg-teal/20 border-teal/50 scale-110' : 'bg-card border-border'}`}>{dragging ? '📂' : '📁'}</div>
      <div><p className='text-primary text-sm font-semibold'>{dragging ? 'Drop it here!' : 'Drag & drop your file'}</p><p className='text-muted text-xs mt-1'>or <span className='text-teal'>click to browse</span></p></div>
      {accept && <p className='text-muted text-xs px-4 py-1.5 bg-app rounded-full border border-border'>Accepted: {accept}</p>}
    </div>
  );
}

/* ─── Upload progress bar ────────────────────────────────────── */
function UploadProgress({ filename, progress, status }) {
  return (
    <div className='px-4 py-3 bg-app border border-border rounded-xl'>
      <div className='flex items-center justify-between mb-2'>
        <span className='text-primary text-xs font-medium truncate mr-4'>{filename}</span>
        <span className={`text-xs flex-shrink-0 ${status === 'done' ? 'text-green-400' : status === 'error' ? 'text-red-400' : 'text-teal'}`}>{status === 'done' ? '✓ Done' : status === 'error' ? '✕ Failed' : `${progress}%`}</span>
      </div>
      <div className='w-full bg-border rounded-full h-1.5'><div className='h-1.5 rounded-full transition-all duration-300' style={{ width: `${progress}%`, background: status === 'error' ? '#EF4444' : status === 'done' ? '#10B981' : '#00D4C8' }}/></div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   MAIN PAGE
═══════════════════════════════════════════════════════════════ */
export default function TeacherLibraryUpload() {
  const { user, isAuthenticated, isTeacher } = useAuth();
  const navigate = useNavigate();
  const teacherId = user?.id;

  // Redirect if not teacher
  useEffect(() => {
    if (!isAuthenticated) navigate('/auth', { replace: true });
    else if (!isTeacher) navigate('/dashboard', { replace: true });
  }, [isAuthenticated, isTeacher, navigate]);

  const [teacherSubjects, setTeacherSubjects] = useState([]);
  const [teacherGrades, setTeacherGrades] = useState([]);
  const [contextLoading, setContextLoading] = useState(true);
  const [step, setStep] = useState(1);
  const [contentType, setContentType] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [fileData, setFileData] = useState('');
  const [fileName, setFileName] = useState('');
  const [fileSize, setFileSize] = useState(0);
  const [subjectId, setSubjectId] = useState('');
  const [gradeMin, setGradeMin] = useState('');
  const [gradeMax, setGradeMax] = useState('');
  const [tagInput, setTagInput] = useState('');
  const [tags, setTags] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProg, setUploadProg] = useState(0);
  const [uploadStatus, setUploadStatus] = useState('idle');
  const [uploadError, setUploadError] = useState('');
  const [myItems, setMyItems] = useState([]);
  const [itemsLoading, setItemsLoading] = useState(true);
  const [editingItem, setEditingItem] = useState(null);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [filterSubject, setFilterSubject] = useState('all');
  const [filterGrade, setFilterGrade] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [activeView, setActiveView] = useState('upload');

  // Load teacher data from dashboard endpoint
  useEffect(() => {
    if (!teacherId) return;
    api.get('/api/teachers/dashboard')
      .then(res => {
        const data = res.data;
        setTeacherSubjects(data.teacher_subjects || []);
        const grades = [...new Set((data.students || []).map(s => s.grade).filter(Boolean))].sort((a,b)=>a-b);
        setTeacherGrades(grades);
        if (data.teacher_subjects?.length) setSubjectId(String(data.teacher_subjects[0].id));
        if (grades.length) { setGradeMin(String(grades[0])); setGradeMax(String(grades[grades.length - 1])); }
      })
      .catch(() => setUploadError('Failed to load teacher data'))
      .finally(() => setContextLoading(false));
  }, [teacherId]);

  // Load teacher's library items
  const loadItems = useCallback(() => {
    if (!teacherId) return;
    setItemsLoading(true);
    api.get(`/api/library/teacher/${teacherId}`)
      .then(r => setMyItems(r.data || []))
      .catch(() => setMyItems([]))
      .finally(() => setItemsLoading(false));
  }, [teacherId]);
  useEffect(() => { loadItems(); }, [loadItems]);

  const allowedGrades = teacherGrades.length ? ALL_GRADES.filter(g => teacherGrades.includes(g.value)) : ALL_GRADES;
  const addTag = () => { const t = tagInput.trim().toLowerCase().replace(/\s+/g, '_'); if (t && !tags.includes(t)) setTags(prev => [...prev, t]); setTagInput(''); };
  const removeTag = tag => setTags(prev => prev.filter(t => t !== tag));
  const handleFileDrop = file => {
    const ft = FILE_TYPES.find(f => f.value === contentType);
    if (ft?.maxSizeMB && file.size > ft.maxSizeMB * 1024 * 1024) { setUploadError(`File is too large. Maximum size is ${ft.maxSizeMB} MB.`); return; }
    setUploadError('');
    setFileName(file.name); setFileSize(file.size);
    if (!title) setTitle(file.name.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' '));
    const reader = new FileReader();
    if (contentType === 'text') { reader.onload = e => setFileData(e.target.result); reader.readAsText(file); }
    else { reader.onload = e => setFileData(e.target.result.split(',')[1]); reader.readAsDataURL(file); }
  };
  const applyGradeBand = preset => {
    const min = Math.max(preset.min, allowedGrades[0]?.value || preset.min);
    const max = Math.min(preset.max, allowedGrades[allowedGrades.length-1]?.value || preset.max);
    setGradeMin(String(min)); setGradeMax(String(max));
  };
  const canProceed = { 1: !!contentType, 2: contentType === 'video_link' || contentType === 'link' ? fileData.trim().startsWith('http') : !!fileData, 3: !!title.trim() && !!subjectId && !!gradeMin && !!gradeMax && parseInt(gradeMin) <= parseInt(gradeMax), 4: true }[step];
  const resetForm = () => { setStep(1); setContentType(''); setTitle(''); setDescription(''); setFileData(''); setFileName(''); setFileSize(0); setTags([]); setTagInput(''); setUploadStatus('idle'); setUploadError(''); setUploadProg(0); setEditingItem(null); };
  const startEdit = item => {
    setEditingItem(item); setContentType(item.content_type); setTitle(item.title); setDescription(item.description || ''); setFileData(item.file_data || ''); setFileName('');
    setSubjectId(String(item.subject_id)); setGradeMin(String(item.grade_min)); setGradeMax(String(item.grade_max)); setTags(item.topic_tags || []);
    setStep(2); setActiveView('upload'); setUploadStatus('idle'); setUploadError('');
  };
  const handleDelete = async id => { try { await api.delete(`/api/library/${id}`); loadItems(); } catch {} setDeleteConfirm(null); };
  const handleSubmit = async () => {
    setUploading(true); setUploadStatus('uploading'); setUploadProg(0);
    const ticker = setInterval(() => { setUploadProg(p => Math.min(p + Math.random() * 15, 88)); }, 220);
    try {
      if (editingItem?.id) {
        await api.put(`/api/library/${editingItem.id}`, {
          title: title.trim(), description: description.trim() || null, content_type: contentType, file_data: fileData,
          subject_id: parseInt(subjectId), topic_tags: tags, grade_min: parseInt(gradeMin), grade_max: parseInt(gradeMax),
        });
      } else {
        await api.post('/api/library/upload', {
          title: title.trim(), description: description.trim() || null, content_type: contentType, file_data: fileData,
          subject_id: parseInt(subjectId), topic_tags: tags, grade_min: parseInt(gradeMin), grade_max: parseInt(gradeMax),
        });
      }
      clearInterval(ticker); setUploadProg(100); setUploadStatus('done');
      loadItems();
      setTimeout(() => { resetForm(); setActiveView('library'); }, 1400);
    } catch (err) {
      clearInterval(ticker); setUploadStatus('error'); setUploadProg(100);
      setUploadError(err.response?.data?.detail || 'Upload failed. Please try again.');
    } finally { setUploading(false); }
  };

  const filteredItems = myItems.filter(item => {
    const subjectOk = filterSubject === 'all' || item.subject_id === parseInt(filterSubject);
    const gradeOk = filterGrade === 'all' ? true : (() => { const map = { primary:[1,7], highschool:[8,12], tertiary:[13,19] }; const [mn, mx] = map[filterGrade] || []; return mn && item.grade_min <= mx && item.grade_max >= mn; })();
    const searchOk = !searchQuery || item.title.toLowerCase().includes(searchQuery.toLowerCase()) || (item.description || '').toLowerCase().includes(searchQuery.toLowerCase());
    return subjectOk && gradeOk && searchOk;
  });
  const selectedFt = FILE_TYPES.find(f => f.value === contentType);
  const STEPS = [{ n: 1, label: 'Content Type' }, { n: 2, label: 'Add Content' }, { n: 3, label: 'Details' }, { n: 4, label: 'Review' }];

  if (contextLoading) return <PageShell title='Library Upload'><div className='flex items-center justify-center py-24'><div className='w-10 h-10 border-4 border-teal/30 border-t-teal rounded-full animate-spin'/></div></PageShell>;
  if (!isTeacher) return null;

  return (
    <PageShell title='Library Upload' subtitle='Share learning materials with your students'>
      {deleteConfirm && (
        <div className='fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4'>
          <div className='card p-6 w-full max-w-sm text-center'>
            <span className='text-5xl block mb-3'>🗑</span>
            <h3 className='text-primary font-bold mb-2'>Delete this item?</h3>
            <p className='text-muted text-sm mb-5'>Students will no longer be able to access this content.</p>
            <div className='flex gap-3'>
              <button onClick={() => handleDelete(deleteConfirm)} className='flex-1 py-2 rounded-lg bg-red-500 hover:bg-red-600 text-white text-sm font-medium transition-colors'>Delete</button>
              <button onClick={() => setDeleteConfirm(null)} className='btn-ghost flex-1'>Cancel</button>
            </div>
          </div>
        </div>
      )}
      <div className='flex items-center gap-3 mb-6'>
        <div className='flex gap-1 p-1 bg-card border border-border rounded-xl'>
          {[['upload', '⬆ Upload New'], ['library', `◫ My Library (${myItems.length})`]].map(([v, lbl]) => (
            <button key={v} onClick={() => { setActiveView(v); if (v === 'upload' && uploadStatus === 'done') resetForm(); }} className={`px-5 py-2 rounded-lg text-sm font-medium transition-all ${activeView === v ? 'bg-teal text-app' : 'text-muted hover:text-primary'}`}>{lbl}</button>
          ))}
        </div>
        {activeView === 'upload' && step > 1 && !editingItem && <button onClick={resetForm} className='text-muted text-xs hover:text-primary transition-colors'>← Start over</button>}
        {activeView === 'upload' && editingItem && <div className='flex items-center gap-2'><span className='badge-amber text-xs'>Editing: {editingItem.title}</span><button onClick={resetForm} className='text-muted text-xs hover:text-red-400 transition-colors'>✕ Cancel edit</button></div>}
      </div>
      {activeView === 'upload' && (
        <div className='max-w-3xl'>
          {uploadStatus !== 'done' && !editingItem && (
            <div className='flex items-center gap-2 mb-8'>
              {STEPS.map((s, i) => (
                <div key={s.n} className='flex items-center gap-2'>
                  <div className='flex items-center gap-2'>
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all ${step > s.n ? 'bg-green-500 text-white' : step === s.n ? 'bg-teal text-app' : 'bg-card border border-border text-muted'}`}>{step > s.n ? '✓' : s.n}</div>
                    <span className={`text-xs font-medium hidden sm:block transition-colors ${step === s.n ? 'text-teal' : step > s.n ? 'text-green-400' : 'text-muted'}`}>{s.label}</span>
                  </div>
                  {i < STEPS.length - 1 && <div className={`w-8 h-0.5 rounded transition-colors ${step > s.n ? 'bg-green-500' : 'bg-border'}`}/>}
                </div>
              ))}
            </div>
          )}
          {(subjectId || gradeMin) && (
            <div className='flex items-center gap-3 mb-5 px-4 py-3 bg-teal/5 border border-teal/20 rounded-xl text-xs text-teal'>
              <span>📌</span>
              <span><strong>Uploading for:</strong> {subjectId && ` ${teacherSubjects.find(s => String(s.id) === subjectId)?.name || '—'}`}{gradeMin && gradeMax && ` · Grades ${gradeMin}–${gradeMax}`}</span>
            </div>
          )}
          {step === 1 && (
            <div>
              <h2 className='text-primary font-bold text-lg mb-1'>What are you uploading?</h2>
              <p className='text-muted text-sm mb-6'>Choose the type of learning material you want to share with your students.</p>
              <div className='grid grid-cols-1 sm:grid-cols-2 gap-3 mb-8'>
                {FILE_TYPES.map(ft => (
                  <button key={ft.value} onClick={() => setContentType(ft.value)} className={`p-5 rounded-2xl border-2 text-left transition-all group ${contentType === ft.value ? 'border-teal bg-teal/10 shadow-teal-glow' : 'border-border hover:border-border/80 hover:bg-card'}`}>
                    <div className='flex items-center gap-3 mb-2'>
                      <span className={`text-3xl w-12 h-12 rounded-xl border flex items-center justify-center flex-shrink-0 ${ft.bg}`}>{ft.icon}</span>
                      <div><div className={`font-semibold text-sm ${contentType === ft.value ? 'text-teal' : 'text-primary'}`}>{ft.label}</div>{ft.maxSizeMB && <div className='text-muted text-xs'>Max {ft.maxSizeMB} MB</div>}</div>
                      {contentType === ft.value && <span className='ml-auto text-teal text-lg'>✓</span>}
                    </div>
                    <p className='text-muted text-xs leading-relaxed'>{ft.desc}</p>
                  </button>
                ))}
              </div>
              <button onClick={() => setStep(2)} disabled={!contentType} className='btn-primary px-8 py-2.5 disabled:opacity-40'>Continue →</button>
            </div>
          )}
          {step === 2 && (
            <div>
              <div className='flex items-center gap-3 mb-6'>
                <span className={`text-3xl w-12 h-12 rounded-xl border flex items-center justify-center flex-shrink-0 ${selectedFt?.bg}`}>{selectedFt?.icon}</span>
                <div><h2 className='text-primary font-bold text-lg'>{selectedFt?.label}</h2><p className='text-muted text-sm'>{selectedFt?.desc}</p></div>
              </div>
              {selectedFt?.accept && (
                <div className='mb-4'>
                  <DropZone accept={selectedFt.accept} onFileDrop={handleFileDrop} disabled={false} />
                  {fileName && (
                    <div className='mt-3 flex items-center gap-3 px-4 py-3 bg-green-500/10 border border-green-500/30 rounded-xl'>
                      <span className='text-green-400 text-lg'>{selectedFt.icon}</span>
                      <div className='flex-1 min-w-0'><p className='text-green-400 text-xs font-semibold truncate'>{fileName}</p><p className='text-muted text-xs'>{(fileSize / 1024).toFixed(1)} KB</p></div>
                      <button onClick={() => { setFileData(''); setFileName(''); setFileSize(0); }} className='text-muted hover:text-red-400 transition-colors text-sm'>✕</button>
                    </div>
                  )}
                </div>
              )}
              {contentType === 'text' && (
                <div className='mb-4'>
                  <label className='text-muted text-xs uppercase tracking-wide block mb-2'>Or type / paste your notes directly</label>
                  <textarea value={fileData} onChange={e => setFileData(e.target.value)} rows={10} placeholder='Type your notes here. Markdown is supported — use **bold**, ## Headings, - lists, etc.' className='w-full bg-input border border-border rounded-xl px-4 py-3 text-primary text-sm focus:border-teal/60 focus:outline-none resize-none font-mono leading-relaxed' />
                  <p className='text-muted text-xs mt-1'>{fileData.length} characters · {fileData.split(/\s+/).filter(Boolean).length} words</p>
                </div>
              )}
              {(contentType === 'video_link' || contentType === 'link') && (
                <div className='mb-4'>
                  <label className='text-muted text-xs uppercase tracking-wide block mb-2'>{contentType === 'video_link' ? 'Video URL (YouTube, Vimeo, etc.)' : 'Web URL'}</label>
                  <div className='relative'><span className='absolute left-4 top-1/2 -translate-y-1/2 text-muted text-sm'>🔗</span><input type='url' value={fileData} onChange={e => setFileData(e.target.value)} placeholder={contentType === 'video_link' ? 'https://youtube.com/watch?v=...' : 'https://'} className='w-full bg-input border border-border rounded-xl pl-10 pr-4 py-3 text-primary text-sm focus:border-teal/60 focus:outline-none' /></div>
                  {fileData.startsWith('http') && <a href={fileData} target='_blank' rel='noreferrer' className='text-teal text-xs mt-2 inline-flex items-center gap-1 hover:underline'>Preview link ↗</a>}
                </div>
              )}
              {uploadError && <p className='text-red-400 text-xs mb-4 flex items-center gap-2'><span>⚠</span> {uploadError}</p>}
              <div className='flex gap-3'>
                {!editingItem && <button onClick={() => setStep(1)} className='btn-ghost px-6 py-2.5'>← Back</button>}
                <button onClick={() => setStep(3)} disabled={!canProceed} className='btn-primary px-8 py-2.5 disabled:opacity-40'>Continue →</button>
              </div>
            </div>
          )}
          {step === 3 && (
            <div className='space-y-6'>
              <div><h2 className='text-primary font-bold text-lg mb-1'>Add details</h2><p className='text-muted text-sm'>Help students find and understand this material.</p></div>
              <div><label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>Title <span className='text-red-400'>*</span></label><input value={title} onChange={e => setTitle(e.target.value)} placeholder='e.g. Introduction to Photosynthesis' maxLength={200} className='w-full bg-input border border-border rounded-xl px-4 py-3 text-primary text-sm focus:border-teal/60 focus:outline-none' /><p className='text-muted text-xs mt-1 text-right'>{title.length}/200</p></div>
              <div><label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>Description <span className='text-muted font-normal'>(optional)</span></label><textarea value={description} onChange={e => setDescription(e.target.value)} rows={3} placeholder='Brief description of what this covers and how students should use it…' className='w-full bg-input border border-border rounded-xl px-4 py-3 text-primary text-sm focus:border-teal/60 focus:outline-none resize-none' /></div>
              <div><label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>Subject <span className='text-red-400'>*</span></label>
                {teacherSubjects.length === 0 ? <div className='px-4 py-3 bg-amber-500/10 border border-amber-500/30 rounded-xl text-amber-400 text-xs'>You have no subjects assigned. Contact your administrator.</div> : (
                  <div className='grid grid-cols-2 sm:grid-cols-3 gap-2'>
                    {teacherSubjects.map(s => (
                      <button key={s.id} type='button' onClick={() => setSubjectId(String(s.id))} className={`p-3 rounded-xl border text-left transition-all ${subjectId === String(s.id) ? 'border-teal bg-teal/10' : 'border-border hover:border-border/80'}`}>
                        <div className='flex items-center justify-between'><span className='text-primary text-xs font-medium'>{s.name}</span>{subjectId === String(s.id) && <span className='text-teal text-xs'>✓</span>}</div>
                        <span className='text-muted text-xs'>{s.code}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <div><label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>Grade Range <span className='text-red-400'>*</span><span className='ml-2 text-muted font-normal normal-case'>— only grades you teach are available</span></label>
                <div className='flex flex-wrap gap-2 mb-3'>
                  {GRADE_BAND_PRESETS.map(p => {
                    const clampedMin = Math.max(p.min, allowedGrades[0]?.value || p.min);
                    const clampedMax = Math.min(p.max, allowedGrades[allowedGrades.length-1]?.value || p.max);
                    const available = clampedMin <= clampedMax;
                    return <button key={p.label} type='button' onClick={() => available && applyGradeBand(p)} disabled={!available} className={`text-xs px-3 py-1.5 rounded-lg border transition-all disabled:opacity-30 disabled:cursor-not-allowed ${String(gradeMin) === String(clampedMin) && String(gradeMax) === String(clampedMax) ? 'border-teal bg-teal/10 text-teal' : 'border-border text-muted hover:text-primary enabled:hover:border-teal/40'}`}>{p.label}</button>;
                  })}
                </div>
                <div className='grid grid-cols-2 gap-3'>
                  <div><label className='text-muted text-xs block mb-1'>From</label><select value={gradeMin} onChange={e => setGradeMin(e.target.value)} className='w-full bg-input border border-border rounded-lg px-3 py-2.5 text-primary text-sm focus:border-teal/60 focus:outline-none'><option value=''>Select…</option>{allowedGrades.map(g => <option key={g.value} value={g.value}>{g.label} — {g.group}</option>)}</select></div>
                  <div><label className='text-muted text-xs block mb-1'>To</label><select value={gradeMax} onChange={e => setGradeMax(e.target.value)} className='w-full bg-input border border-border rounded-lg px-3 py-2.5 text-primary text-sm focus:border-teal/60 focus:outline-none'><option value=''>Select…</option>{allowedGrades.filter(g => !gradeMin || g.value >= parseInt(gradeMin)).map(g => <option key={g.value} value={g.value}>{g.label} — {g.group}</option>)}</select></div>
                </div>
                {gradeMin && gradeMax && parseInt(gradeMin) > parseInt(gradeMax) && <p className='text-red-400 text-xs mt-2 flex items-center gap-1'><span>⚠</span> "From" grade cannot be higher than "To" grade.</p>}
              </div>
              <div><label className='text-muted text-xs uppercase tracking-wide block mb-1.5'>Topic Tags <span className='text-muted font-normal'>(optional — helps students find this)</span></label>
                <div className='flex gap-2 mb-2'><input value={tagInput} onChange={e => setTagInput(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); addTag(); } }} placeholder='Type a tag and press Enter…' className='flex-1 bg-input border border-border rounded-lg px-3 py-2 text-primary text-sm focus:border-teal/60 focus:outline-none' /><button onClick={addTag} className='btn-ghost text-xs px-4'>+ Add</button></div>
                {tags.length > 0 && <div className='flex flex-wrap gap-2'>{tags.map(tag => <span key={tag} className='flex items-center gap-1.5 text-xs px-3 py-1 bg-teal/10 border border-teal/30 text-teal rounded-full'>#{tag}<button onClick={() => removeTag(tag)} className='hover:text-red-400 transition-colors'>✕</button></span>)}</div>}
              </div>
              {subjectId && (
                <div><p className='text-muted text-xs mb-2'>Suggested tags:</p><div className='flex flex-wrap gap-2'>{(SUBJECT_TOPICS_MAP[teacherSubjects.find(s => String(s.id) === subjectId)?.code] || []).map(t => <button key={t} type='button' onClick={() => !tags.includes(t) && setTags(prev => [...prev, t])} disabled={tags.includes(t)} className={`text-xs px-2.5 py-1 rounded-full border transition-all disabled:opacity-40 ${tags.includes(t) ? 'border-teal/30 bg-teal/10 text-teal' : 'border-border text-muted hover:border-teal/40 hover:text-teal'}`}>{tags.includes(t) ? '✓ ' : '+ '}{t.replace(/_/g,' ')}</button>)}</div></div>
              )}
              <div className='flex gap-3 pt-2'><button onClick={() => setStep(2)} className='btn-ghost px-6 py-2.5'>← Back</button><button onClick={() => setStep(4)} disabled={!canProceed} className='btn-primary px-8 py-2.5 disabled:opacity-40'>Review →</button></div>
            </div>
          )}
          {step === 4 && (
            <div>
              <h2 className='text-primary font-bold text-lg mb-1'>{editingItem ? 'Save changes?' : 'Ready to upload?'}</h2>
              <p className='text-muted text-sm mb-6'>Review everything before publishing to students.</p>
              <div className='card p-6 mb-6 space-y-4'>
                <div className='flex items-center gap-4 pb-4 border-b border-border'><span className={`text-3xl w-14 h-14 rounded-2xl border flex items-center justify-center flex-shrink-0 ${selectedFt?.bg}`}>{selectedFt?.icon}</span><div><p className='text-primary font-semibold'>{title}</p><p className='text-muted text-xs mt-0.5'>{selectedFt?.label}{fileName && ` · ${fileName} · ${(fileSize/1024).toFixed(1)} KB`}{(contentType === 'video_link' || contentType === 'link') && ` · ${fileData.substring(0,50)}…`}</p></div></div>
                <div className='grid grid-cols-2 gap-3'>
                  {[['Subject', teacherSubjects.find(s => String(s.id) === subjectId)?.name || '—'], ['Grade Range', gradeMin && gradeMax ? `Grade ${gradeMin} → Grade ${gradeMax}` : '—'], ['Description', description || '(none)'], ['Tags', tags.length ? tags.map(t => `#${t}`).join(', ') : '(none)']].map(([lbl, val]) => <div key={lbl} className='bg-app rounded-lg p-3 border border-border'><p className='text-muted text-xs uppercase tracking-wide mb-1'>{lbl}</p><p className='text-primary text-sm font-medium'>{val}</p></div>)}
                </div>
                <div className='px-4 py-3 bg-teal/5 border border-teal/20 rounded-xl'><p className='text-teal text-xs font-semibold mb-1'>👁 Visible to:</p><p className='text-muted text-xs'>Students enrolled in <strong className='text-primary'>{teacherSubjects.find(s => String(s.id) === subjectId)?.name || '—'}</strong> in grades {gradeMin}–{gradeMax}.</p></div>
              </div>
              {uploadStatus === 'uploading' && <div className='mb-4'><UploadProgress filename={fileName || title} progress={uploadProg} status={uploadStatus} /></div>}
              {uploadStatus === 'done' && <div className='mb-4 px-4 py-3 bg-green-500/10 border border-green-500/30 rounded-xl flex items-center gap-3'><span className='text-green-400 text-xl'>✓</span><div><p className='text-green-400 text-sm font-semibold'>{editingItem ? 'Content updated!' : 'Upload complete!'}</p><p className='text-muted text-xs'>Redirecting to your library…</p></div></div>}
              {uploadStatus === 'error' && <div className='mb-4 px-4 py-3 bg-red-500/10 border border-red-500/30 rounded-xl flex items-center gap-3'><span className='text-red-400 text-xl'>⚠</span><div><p className='text-red-400 text-sm font-semibold'>Upload failed</p><p className='text-muted text-xs'>{uploadError}</p></div></div>}
              <div className='flex gap-3'>
                {uploadStatus !== 'done' && <button onClick={() => setStep(3)} disabled={uploading} className='btn-ghost px-6 py-2.5 disabled:opacity-40'>← Back</button>}
                {uploadStatus !== 'done' && <button onClick={handleSubmit} disabled={uploading} className='btn-primary px-8 py-2.5 disabled:opacity-40 flex items-center gap-2'>{uploading ? <><div className='w-4 h-4 border-2 border-app/30 border-t-app rounded-full animate-spin'/> Uploading…</> : editingItem ? '💾 Save Changes' : '⬆ Publish to Library'}</button>}
              </div>
            </div>
          )}
        </div>
      )}
      {activeView === 'library' && (
        <div>
          <div className='flex flex-wrap items-center gap-3 mb-5'>
            <div className='relative'><span className='absolute left-3 top-1/2 -translate-y-1/2 text-muted text-sm pointer-events-none'>🔍</span><input value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder='Search content…' className='bg-input border border-border rounded-lg pl-9 pr-4 py-1.5 text-primary text-sm focus:border-teal/60 focus:outline-none w-52' /></div>
            <div className='flex items-center gap-2'><span className='text-muted text-xs uppercase tracking-wide'>Subject</span><select value={filterSubject} onChange={e => setFilterSubject(e.target.value)} className='bg-input border border-border rounded-lg px-3 py-1.5 text-primary text-sm focus:border-teal/60 focus:outline-none'><option value='all'>All</option>{teacherSubjects.map(s => <option key={s.id} value={String(s.id)}>{s.name}</option>)}</select></div>
            <div className='flex items-center gap-2'><span className='text-muted text-xs uppercase tracking-wide'>Grade</span><select value={filterGrade} onChange={e => setFilterGrade(e.target.value)} className='bg-input border border-border rounded-lg px-3 py-1.5 text-primary text-sm focus:border-teal/60 focus:outline-none'><option value='all'>All</option>{['primary','highschool','tertiary'].filter(v => { const m = { primary:[1,7], highschool:[8,12], tertiary:[13,19] }; const [mn,mx] = m[v]; return myItems.some(i => i.grade_min <= mx && i.grade_max >= mn); }).map(v => <option key={v} value={v}>{v === 'primary' ? 'Primary (1–7)' : v === 'highschool' ? 'High School (8–12)' : 'Tertiary (13+)'}</option>)}</select></div>
            <p className='text-muted text-xs ml-1'>{filteredItems.length} of {myItems.length} item{myItems.length !== 1 ? 's' : ''}</p>
            <button onClick={() => { resetForm(); setActiveView('upload'); }} className='ml-auto btn-primary text-xs px-4 py-2'>+ Upload New</button>
          </div>
          {itemsLoading && <div className='py-20 text-center'><div className='w-8 h-8 border-4 border-teal/30 border-t-teal rounded-full animate-spin mx-auto'/></div>}
          {!itemsLoading && myItems.length === 0 && <div className='py-24 text-center'><span className='text-6xl block mb-4'>📭</span><h3 className='text-primary font-semibold text-lg mb-2'>No content yet</h3><p className='text-muted text-sm mb-6 max-w-sm mx-auto'>Upload your first piece of learning material and it will appear here for your students.</p><button onClick={() => { resetForm(); setActiveView('upload'); }} className='btn-primary text-sm px-6 py-2.5'>+ Upload First Content</button></div>}
          {!itemsLoading && myItems.length > 0 && filteredItems.length === 0 && <div className='py-16 text-center'><span className='text-4xl block mb-3'>🔍</span><p className='text-primary font-semibold mb-1'>No results</p><p className='text-muted text-sm'>Try adjusting your filters or search term.</p></div>}
          {!itemsLoading && filteredItems.length > 0 && <div className='space-y-3'>{filteredItems.map(item => <UploadedItemCard key={item.id} item={item} onEdit={startEdit} onDelete={id => setDeleteConfirm(id)} />)}</div>}
        </div>
      )}
    </PageShell>
  );
}

const SUBJECT_TOPICS_MAP = {
  MATH: ['mathematics_algebra','mathematics_geometry','mathematics_calculus','mathematics_statistics'],
  SCI:  ['science_biology','science_chemistry','science_physics'],
  ENG:  ['english_comprehension','english_writing','english_literature'],
  SOC:  ['social_studies','civics'],
  CS:   ['computer_science','programming'],
};