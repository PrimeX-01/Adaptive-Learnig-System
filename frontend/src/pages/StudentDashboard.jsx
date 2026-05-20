import { useEffect, useState, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import PageShell from '../components/PageShell';
import api from '../services/api';

const CHART_TOOLTIP = { contentStyle:{ background:'#0F172A', border:'1px solid #1E293B', borderRadius:'8px', color:'#F1F5F9', fontSize:11 }, labelStyle:{color:'#64748B'} };
const SUBJECT_COLORS = ['#00D4C8','#3B82F6','#8B5CF6','#F59E0B','#10B981','#EF4444'];
const TIMEFRAMES = [{label:'24h',value:'24h'},{label:'Week',value:'week'},{label:'Month',value:'month'},{label:'Year',value:'year'}];
const ACTIVITY_META = {
  ai_tutor:{icon:'◈',label:'AI Tutor',color:'text-teal'},
  quiz:    {icon:'◎',label:'Quiz',    color:'text-blue-400'},
  content: {icon:'◫',label:'Library', color:'text-purple-400'},
  review:  {icon:'📅',label:'Review', color:'text-amber-400'},
};

const STYLE_INFO = {
  visual:      { icon:'👁️', label:'Visual',          desc:'You learn best through diagrams, charts and visual aids.', color:'text-blue-400' },
  auditory:    { icon:'🎧', label:'Auditory',         desc:'You learn best through listening, discussion and verbal explanations.', color:'text-purple-400' },
  reading:     { icon:'📖', label:'Reading/Writing',  desc:'You learn best through written notes, lists and text-based content.', color:'text-green-400' },
  kinesthetic: { icon:'🧪', label:'Kinesthetic',      desc:'You learn best through hands-on practice and worked examples.', color:'text-amber-400' },
};

/*  Mini Sparkline  */
function MiniSparkline({ data, dataKey, color }) {
  if (!data || data.length < 2) return null;
  return (
    <ResponsiveContainer width={80} height={40}>
      <AreaChart data={data} margin={{top:2,right:0,bottom:0,left:0}}>
        <defs>
          <linearGradient id={`sg-${color.replace('#','')}`} x1='0' y1='0' x2='0' y2='1'>
            <stop offset='5%'  stopColor={color} stopOpacity={0.35}/>
            <stop offset='95%' stopColor={color} stopOpacity={0}/>
          </linearGradient>
        </defs>
        <Area type='monotone' dataKey={dataKey} stroke={color} strokeWidth={1.5} fill={`url(#sg-${color.replace('#','')})`} dot={false} isAnimationActive={false}/>
      </AreaChart>
    </ResponsiveContainer>
  );
}

/*  Stat Card  */
function StatCard({ icon, label, value, sub, trend, sparkData, sparkKey, sparkColor='#00D4C8' }) {
  return (
    <div className='card-hover p-5 flex flex-col gap-2'>
      <div className='flex items-start justify-between'>
        <span className='text-muted text-xs font-medium uppercase tracking-wide'>{label}</span>
        <span className='text-xl leading-none'>{icon}</span>
      </div>
      <div className='stat-number text-3xl font-bold text-primary leading-none'>{value}</div>
      <div className='flex items-end justify-between mt-1'>
        <div>
          {sub && <p className='text-muted text-xs'>{sub}</p>}
          {trend && <p className={`text-xs font-medium mt-0.5 flex items-center gap-1 ${trend.positive!==false?'text-green-400':'text-red-400'}`}><span>{trend.positive!==false?'↑':'↓'}</span>{trend.text}</p>}
        </div>
        <MiniSparkline data={sparkData} dataKey={sparkKey} color={sparkColor}/>
      </div>
    </div>
  );
}

/*  Personalization Panel  */
function PersonalizationPanel({ style, subjectStyles, onChangeStyle }) {
  const info = STYLE_INFO[style] || STYLE_INFO.reading;
  const [expanded, setExpanded] = useState(false);
  return (
    <div className='card p-5 mb-6'>
      <div className='flex items-start justify-between mb-4'>
        <div>
          <h3 className='text-primary font-semibold text-sm'>Your Learning Profile</h3>
          <p className='text-muted text-xs mt-0.5'>How SiveAdapt personalises content for you</p>
        </div>
        <button onClick={onChangeStyle} className='text-teal text-xs hover:underline flex-shrink-0'>Change style →</button>
      </div>

      {/* Overall style */}
      <div className='flex items-start gap-4 p-4 bg-app border border-border rounded-xl mb-4'>
        <span className='text-3xl'>{info.icon}</span>
        <div className='flex-1'>
          <div className='flex items-center gap-2 mb-1'>
            <span className={`font-semibold text-sm ${info.color}`}>{info.label} Learner</span>
            <span className='badge-teal text-xs'>Overall Style</span>
          </div>
          <p className='text-muted text-xs leading-relaxed'>{info.desc}</p>
          <div className='mt-2 flex flex-wrap gap-2 text-xs text-muted'>
            <span className='px-2 py-0.5 bg-border/50 rounded'>✓ Quiz questions adapted</span>
            <span className='px-2 py-0.5 bg-border/50 rounded'>✓ AI tutor responses adapted</span>
            <span className='px-2 py-0.5 bg-border/50 rounded'>✓ Library content adapted</span>
          </div>
        </div>
      </div>

      {/* Per-subject styles */}
      {subjectStyles && subjectStyles.length > 0 && (
        <div>
          <button onClick={()=>setExpanded(!expanded)} className='text-muted text-xs hover:text-primary flex items-center gap-1 mb-3'>
            <span>{expanded?'▼':'▶'}</span> Per-subject styles ({subjectStyles.length})
          </button>
          {expanded && (
            <div className='space-y-2'>
              {subjectStyles.map((s,i) => {
                const si = STYLE_INFO[s.learning_style] || STYLE_INFO.reading;
                return (
                  <div key={i} className='flex items-center justify-between px-3 py-2 bg-app border border-border rounded-lg'>
                    <span className='text-primary text-xs font-medium'>{s.subject_name}</span>
                    <div className='flex items-center gap-2'>
                      <span className='text-sm'>{si.icon}</span>
                      <span className={`text-xs ${si.color}`}>{si.label}</span>
                      {s.auto_detected && <span className='text-muted text-xs'>(auto-detected)</span>}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/*  Subject FCL Points Section  */
function SubjectPointsSection({ pointsData }) {
  if (!pointsData || pointsData.length === 0) return null;
  return (
    <div className='card p-5 mb-6'>
      <div className='flex items-center justify-between mb-4'>
        <div>
          <h3 className='text-primary text-sm font-semibold'>FCL Points Progress</h3>
          <p className='text-muted text-xs mt-0.5'>Points earned per subject toward your next FCL level</p>
        </div>
      </div>
      <div className='space-y-4'>
        {pointsData.map((s, i) => (
          <div key={s.subject_id}>
            <div className='flex items-center justify-between mb-1.5'>
              <div className='flex items-center gap-2'>
                <span className='text-primary text-xs font-medium'>{s.subject_name}</span>
                <span className='badge-teal text-xs stat-number'>FCL {s.current_fcl}</span>
              </div>
              <div className='flex items-center gap-3 text-xs'>
                <span className='text-muted stat-number'>{s.current_points} / {s.points_needed} pts</span>
                <span className={`font-medium ${s.progress_pct >= 75 ? 'text-green-400' : s.progress_pct >= 40 ? 'text-amber-400' : 'text-muted'}`}>
                  {s.progress_pct}%
                </span>
              </div>
            </div>
            <div className='w-full bg-border rounded-full h-2'>
              <div className='h-2 rounded-full transition-all duration-700'
                style={{ width:`${s.progress_pct}%`, background: SUBJECT_COLORS[i % SUBJECT_COLORS.length] }}/>
            </div>
            <p className='text-muted text-xs mt-1'>
              {s.points_needed - s.current_points} pts to FCL {s.current_fcl + 1} · {s.total_earned} pts total earned
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

/*    MAIN DASHBOARD */
export default function StudentDashboard() {
  const [data,            setData]            = useState(null);
  const [unread,          setUnread]          = useState(0);
  const [loading,         setLoading]         = useState(true);
  const [refreshing,      setRefreshing]      = useState(false);
  const [activity,        setActivity]        = useState([]);
  const [activityLoading, setActivityLoading] = useState(false);
  const [timeframe,       setTimeframe]       = useState('week');
  const [pointsData,      setPointsData]      = useState([]);
  const [subjectStyles,   setSubjectStyles]   = useState([]);
  const [showStyleChange, setShowStyleChange] = useState(false);

  const nav      = useNavigate();
  const location = useLocation();
  const sid      = window.__studentId;

  /*  Load all dashboard data  */
  const loadDashboardData = useCallback((isRefresh=false) => {
    if (!sid) return;
    if (isRefresh) setRefreshing(true); else setLoading(true);

    Promise.all([
      api.get(`/api/students/${sid}/profile`),
      api.get(`/api/students/${sid}/subject-performance`),
      api.get(`/api/students/${sid}/fcl-history`),
      api.get(`/api/students/${sid}/topic-mastery`),
      api.post('/api/content/recommend', { student_id: sid }),
      api.get(`/api/review/pending/${sid}`),
      api.get(`/api/messages/inbox/${sid}`),
    ]).then(([prof,subPerf,fclHist,mastery,content,reviews,inbox]) => {
      setData({ prof:prof.data, subPerf:subPerf.data, fclHist:fclHist.data, mastery:mastery.data, content:content.data.items, reviews:reviews.data.items });
      setUnread(inbox.data.filter(m=>!m.is_read).length);
    }).catch(() => {
      setData({ prof:{}, subPerf:{subjects:[],overall:{}}, fclHist:[], mastery:[], content:[], reviews:[] });
    }).finally(() => { setLoading(false); setRefreshing(false); });

    // Load points data
    api.get(`/api/quiz/points/${sid}`)
      .then(r => setPointsData(r.data || []))
      .catch(() => setPointsData([]));

    // Load per-subject styles (Phase 2 endpoint — graceful fallback)
    api.get(`/api/style/${sid}`)
      .then(r => setSubjectStyles(r.data || []))
      .catch(() => setSubjectStyles([]));
  }, [sid]);

  useEffect(() => { loadDashboardData(); }, [location.key]);

  /*  Activity  */
  const loadActivity = useCallback(() => {
    if (!sid) return;
    setActivityLoading(true);
    api.get(`/api/students/${sid}/activity?timeframe=${timeframe}`)
      .then(r => setActivity(r.data || []))
      .catch(() => setActivity([]))
      .finally(() => setActivityLoading(false));
  }, [sid, timeframe]);

  useEffect(() => { loadActivity(); }, [loadActivity]);
  useEffect(() => { loadActivity(); }, [location.key]);

  if (loading) return (
    <div className='min-h-screen bg-app flex items-center justify-center flex-col gap-4'>
      <div className='w-12 h-12 border-4 border-teal/30 border-t-teal rounded-full animate-spin'/>
      <p className='text-muted text-sm'>Loading your dashboard…</p>
    </div>
  );

  const { prof, subPerf, fclHist, mastery, content, reviews } = data;
  const overall     = subPerf?.overall || {};
  const masterCount = (mastery||[]).filter(m=>m.mastery==='mastered').length;
  const masteryChart= (mastery||[]).map(m=>({ name:m.topic_name?.split(' ')[0]||m.topic_id, prob:Math.round((m.mastery_prob||0)*100) }));

  const fclSparkData     = (fclHist||[]).slice(-10).map((h,i)=>({i,v:h.fcl_level}));
  const accuracySparkData= (mastery||[]).slice(-10).map((m,i)=>({i,v:Math.round((m.mastery_prob||0)*100)}));
  const masterySparkData = masteryChart.slice(-10).map((m,i)=>({i,v:m.prob}));
  const studyStreak = (() => {
    if (!fclHist?.length) return 0;
    const days=[...new Set(fclHist.map(h=>h.date?.slice(0,10)))].sort().reverse();
    let streak=0,check=new Date().toISOString().slice(0,10);
    for(const d of days){if(d===check){streak++;check=new Date(new Date(check)-864e5).toISOString().slice(0,10);}else break;}
    return streak;
  })();
  const streakSparkData=Array.from({length:10},(_,i)=>({i,v:Math.random()>0.25?1:0}));
  const subjectDonut=(subPerf?.subjects||[]).slice(0,5).map((s,i)=>({name:s.subject_name,value:s.accuracy||50,color:SUBJECT_COLORS[i%SUBJECT_COLORS.length]}));

  const fmt_duration=(mins)=>{ if(!mins)return'—'; return mins<60?`${mins}m`:`${Math.floor(mins/60)}h ${mins%60}m`; };
  const fmt_time=(ts)=>{ if(!ts)return'—'; const d=new Date(ts),now=new Date(),diff=Math.floor((now-d)/60000); if(diff<60)return`${diff}m ago`; if(diff<1440)return`${Math.floor(diff/60)}h ago`; return d.toLocaleDateString(); };

  const learningStyle = prof?.preferred_learning_style || 'reading';

  const refreshAction = (
    <button onClick={()=>{loadDashboardData(true);loadActivity();}} disabled={refreshing}
      className='text-muted hover:text-primary text-xs flex items-center gap-1.5 transition-colors disabled:opacity-50'>
      <span className={refreshing?'animate-spin inline-block':''}>🔄</span>
      {refreshing?'Refreshing…':'Refresh'}
    </button>
  );

  return (
    <PageShell title='Dashboard' subtitle={`Welcome back, ${prof?.name?.split(' ')[0]||'Student'} 👋`} unreadCount={unread} actions={refreshAction}>

      {/* Review alert */}
      {reviews?.length > 0 && (
        <div className='mb-6 px-4 py-3 bg-amber-500/10 border border-amber-500/30 rounded-xl flex items-center justify-between'>
          <div className='flex items-center gap-3'>
            <span className='text-amber-400 text-xl'>📅</span>
            <div>
              <p className='text-amber-300 text-sm font-semibold'>{reviews.length} topic{reviews.length>1?'s':''} due for review today</p>
              <p className='text-amber-400/60 text-xs mt-0.5'>Complete them to maintain mastery scores</p>
            </div>
          </div>
          <button onClick={()=>nav(`/quiz?topic=${reviews[0]?.topic_id}&review=true`)} className='btn-primary text-xs px-4 py-2 flex-shrink-0'>Start Review →</button>
        </div>
      )}

      {/*  PERSONALIZATION PANEL  */}
      <PersonalizationPanel
        style={learningStyle}
        subjectStyles={subjectStyles}
        onChangeStyle={() => setShowStyleChange(true)}
      />

      {/* Change Learning Style Modal */}
      {showStyleChange && (
        <div className='fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4'>
          <div className='card p-6 w-full max-w-md'>
            <h2 className='text-primary font-bold text-lg mb-2'>Change Learning Style</h2>
            <p className='text-muted text-sm mb-5'>Retake the VARK assessment to update how SiveAdapt personalises your content.</p>
            <div className='flex gap-3'>
              <button onClick={()=>{setShowStyleChange(false);nav('/profile?retake=true');}} className='btn-primary flex-1'>Retake VARK Quiz</button>
              <button onClick={()=>setShowStyleChange(false)} className='btn-ghost flex-1'>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* ── ROW 1 — STAT CARDS ── */}
      <div className='grid grid-cols-4 gap-4 mb-6'>
        <StatCard icon='🧠' label='Overall FCL' value={overall.avg_fcl||'—'} sub={overall.overall_label}
          trend={overall.avg_fcl?{text:`Level ${overall.avg_fcl}/13`,positive:true}:null}
          sparkData={fclSparkData} sparkKey='v' sparkColor='#00D4C8'/>
        <StatCard icon='🏆' label='Topics Mastered' value={masterCount} sub={`of ${mastery?.length||0} topics`}
          trend={masterCount>0?{text:`${Math.round(masterCount/(mastery?.length||1)*100)}% complete`,positive:true}:null}
          sparkData={masterySparkData} sparkKey='v' sparkColor='#10B981'/>
        <StatCard icon='🎯' label='Overall Accuracy' value={overall.avg_accuracy?`${overall.avg_accuracy}%`:'—'} sub={`Across ${overall.subjects_count||0} subjects`}
          trend={overall.avg_accuracy?{text:overall.avg_accuracy>=70?'Performing well':'Room to improve',positive:overall.avg_accuracy>=70}:null}
          sparkData={accuracySparkData} sparkKey='v' sparkColor='#3B82F6'/>
        <StatCard icon='🔥' label='Study Streak' value={studyStreak} sub={studyStreak>0?'days in a row':'Start today!'}
          trend={studyStreak>0?{text:'Keep it going!',positive:true}:{text:'No streak yet',positive:false}}
          sparkData={streakSparkData} sparkKey='v' sparkColor='#F59E0B'/>
      </div>

      {/* ── ROW 2 — FCL CHART + SUBJECT PANEL ── */}
      <div className='grid grid-cols-3 gap-4 mb-6'>
        <div className='col-span-2 card p-5'>
          <div className='flex items-start justify-between mb-4'>
            <div><h3 className='text-primary text-sm font-semibold'>Cognitive Level Progress</h3><p className='text-muted text-xs mt-0.5'>FCL trajectory — updates after every quiz and tutor session</p></div>
            <span className='badge-teal text-xs'>Live</span>
          </div>
          <ResponsiveContainer width='100%' height={190}>
            <AreaChart data={fclHist||[]} margin={{top:5,right:5,bottom:0,left:-20}}>
              <defs><linearGradient id='fclArea' x1='0' y1='0' x2='0' y2='1'><stop offset='5%' stopColor='#00D4C8' stopOpacity={0.25}/><stop offset='95%' stopColor='#00D4C8' stopOpacity={0}/></linearGradient></defs>
              <CartesianGrid strokeDasharray='3 3' stroke='#1E293B'/>
              <XAxis dataKey='date' tick={{fontSize:10,fill:'#64748B'}} tickLine={false}/>
              <YAxis domain={[1,13]} tick={{fontSize:10,fill:'#64748B'}} tickLine={false}/>
              <Tooltip {...CHART_TOOLTIP} formatter={v=>[`FCL ${v}`,'Level']}/>
              <Area type='monotone' dataKey='fcl_level' stroke='#00D4C8' strokeWidth={2} fill='url(#fclArea)' dot={{r:3,fill:'#00D4C8',strokeWidth:0}}/>
            </AreaChart>
          </ResponsiveContainer>
          <div className='mt-3 flex flex-wrap gap-x-5 gap-y-1'>
            {[['#EF4444','FCL 1–4: Foundation'],['#F59E0B','FCL 5–7: Developing'],['#00D4C8','FCL 8–10: Proficient'],['#8B5CF6','FCL 11–13: Advanced']].map(([c,l])=>(
              <span key={l} className='flex items-center gap-1.5 text-xs text-muted'><span className='w-2 h-2 rounded-full inline-block flex-shrink-0' style={{background:c}}/>{l}</span>
            ))}
          </div>
        </div>

        <div className='flex flex-col gap-4'>
          <div className='card p-5 flex-1'>
            <div className='flex items-center justify-between mb-4'>
              <h3 className='text-primary text-sm font-semibold'>Subject Performance</h3>
              <button onClick={()=>nav('/subjects')} className='text-teal text-xs hover:underline'>View all →</button>
            </div>
            <div className='space-y-3'>
              {(subPerf?.subjects||[]).slice(0,4).map((s,i)=>(
                <div key={s.subject_code}>
                  <div className='flex items-center justify-between mb-1'>
                    <span className='text-primary text-xs font-medium truncate'>{s.subject_name}</span>
                    <div className='flex items-center gap-2 flex-shrink-0 ml-2'>
                      {s.fcl_level&&<span className='stat-number text-teal text-xs'>FCL {s.fcl_level}</span>}
                      <span className='text-muted text-xs'>{s.accuracy?`${s.accuracy}%`:'—'}</span>
                    </div>
                  </div>
                  <div className='w-full bg-border rounded-full h-1.5'>
                    <div className='h-1.5 rounded-full' style={{width:`${s.accuracy||0}%`,background:SUBJECT_COLORS[i%SUBJECT_COLORS.length],transition:'width 0.8s ease'}}/>
                  </div>
                </div>
              ))}
              {(!subPerf?.subjects||subPerf.subjects.length===0)&&<p className='text-muted text-xs text-center py-3'>No subjects yet. <button onClick={()=>nav('/subjects')} className='text-teal hover:underline'>Enrol now →</button></p>}
            </div>
          </div>

          <div className='card p-5'>
            <h3 className='text-primary text-sm font-semibold mb-3'>Score Distribution</h3>
            {subjectDonut.length>0?(
              <div className='flex items-center gap-3'>
                <div className='flex-shrink-0'>
                  <ResponsiveContainer width={72} height={72}>
                    <PieChart><Pie data={subjectDonut} cx='50%' cy='50%' innerRadius={22} outerRadius={34} dataKey='value' strokeWidth={0}>{subjectDonut.map((e,idx)=><Cell key={idx} fill={e.color}/>)}</Pie></PieChart>
                  </ResponsiveContainer>
                </div>
                <div className='flex-1 space-y-1.5 min-w-0'>
                  {subjectDonut.map((s,i)=>(
                    <div key={i} className='flex items-center gap-1.5'>
                      <span className='w-2 h-2 rounded-full flex-shrink-0' style={{background:s.color}}/>
                      <span className='text-muted text-xs truncate'>{s.name}</span>
                      <span className='text-primary text-xs ml-auto stat-number flex-shrink-0'>{s.value}%</span>
                    </div>
                  ))}
                </div>
              </div>
            ):<p className='text-muted text-xs text-center py-2'>Complete quizzes to see data</p>}
          </div>
        </div>
      </div>

      {/*  FCL POINTS PROGRESS  */}
      <SubjectPointsSection pointsData={pointsData}/>

      {/*  TOPIC MASTERY  */}
      {masteryChart.length>0&&(
        <div className='card p-5 mb-6'>
          <div className='flex items-start justify-between mb-4'>
            <div><h3 className='text-primary text-sm font-semibold'>Topic Mastery Probability</h3><p className='text-muted text-xs mt-0.5'>BKT scores per topic — higher = more confident</p></div>
          </div>
          <ResponsiveContainer width='100%' height={120}>
            <BarChart data={masteryChart} margin={{top:0,right:0,bottom:0,left:-20}}>
              <CartesianGrid strokeDasharray='3 3' stroke='#1E293B'/>
              <XAxis dataKey='name' tick={{fontSize:10,fill:'#64748B'}} tickLine={false}/>
              <YAxis domain={[0,100]} tick={{fontSize:10,fill:'#64748B'}} tickLine={false}/>
              <Tooltip {...CHART_TOOLTIP} formatter={v=>[`${v}%`,'P(Mastery)']}/>
              <Bar dataKey='prob' fill='#00D4C8' radius={[3,3,0,0]}/>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/*  RECENT ACTIVITY  */}
      <div className='card'>
        <div className='px-5 py-4 border-b border-border flex items-center justify-between flex-wrap gap-3'>
          <div><h3 className='text-primary font-semibold text-sm'>Recent Activity</h3><p className='text-muted text-xs mt-0.5'>Quiz sessions, AI tutor, library and reviews</p></div>
          <div className='flex items-center gap-1 p-1 bg-app border border-border rounded-lg'>
            {TIMEFRAMES.map(opt=>(
              <button key={opt.value} onClick={()=>setTimeframe(opt.value)} className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${timeframe===opt.value?'bg-teal text-app':'text-muted hover:text-primary'}`}>{opt.label}</button>
            ))}
          </div>
        </div>

        {activityLoading?(
          <div className='px-5 py-10 text-center'><div className='w-6 h-6 border-2 border-teal/30 border-t-teal rounded-full animate-spin mx-auto'/></div>
        ):activity.length>0?(
          <>
            <div className='overflow-x-auto'>
              <table className='w-full'>
                <thead><tr className='border-b border-border'>{['Activity','Subject','Topic','Duration / Score','When'].map(h=><th key={h} className='py-3 px-5 text-left text-muted text-xs uppercase tracking-wide font-medium'>{h}</th>)}</tr></thead>
                <tbody>
                  {activity.map((item,i)=>{
                    const meta=ACTIVITY_META[item.type]||{icon:'📌',label:item.type,color:'text-muted'};
                    return(
                      <tr key={i} className='border-b border-border/50 hover:bg-border/20 transition-colors'>
                        <td className='py-3 px-5'><div className='flex items-center gap-2'><span className='text-base'>{meta.icon}</span><span className={`text-sm font-medium ${meta.color}`}>{meta.label}</span></div></td>
                        <td className='py-3 px-5'>{item.subject_name?<span className='badge-teal text-xs'>{item.subject_name}</span>:<span className='text-muted text-xs'>—</span>}</td>
                        <td className='py-3 px-5 text-muted text-sm'>{item.topic_id?item.topic_id.replace(/_/g,' ').replace(/\b\w/g,l=>l.toUpperCase()):'—'}</td>
                        <td className='py-3 px-5 stat-number text-primary text-sm'>
                          {item.type==='quiz'&&item.score!==undefined
                            ?<span className={item.score>=70?'text-green-400':'text-amber-400'}>{item.score}% ({item.questions_count||'?'} Q)</span>
                            :fmt_duration(item.duration_minutes)}
                        </td>
                        <td className='py-3 px-5 text-muted text-sm'>{fmt_time(item.timestamp)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className='px-5 py-3 border-t border-border flex items-center justify-between'>
              <p className='text-muted text-xs'>{activity.length} activities</p>
              <button onClick={()=>nav('/progress')} className='text-teal text-xs hover:underline'>View full progress →</button>
            </div>
          </>
        ):(
          <div className='px-5 py-14 text-center'>
            <span className='text-5xl block mb-4'>📚</span>
            <p className='text-primary text-sm font-semibold mb-1'>No activity in this period</p>
            <p className='text-muted text-xs mb-5'>Take a quiz or chat with the AI Tutor to see activity here</p>
            <div className='flex gap-3 justify-center'>
              <button onClick={()=>nav('/chat')} className='btn-primary text-xs'>Start AI Tutor ◈</button>
              <button onClick={()=>nav('/quiz')} className='btn-ghost  text-xs'>Take a Quiz ◎</button>
            </div>
          </div>
        )}
      </div>
    </PageShell>
  );
}