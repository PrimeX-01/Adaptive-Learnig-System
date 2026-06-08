import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { BarChart, Bar, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import PageShell from '../components/PageShell';
import api from '../services/api';

const CHART_TOOLTIP = { contentStyle:{ background:'#0F172A', border:'1px solid #1E293B', borderRadius:'8px', color:'#F1F5F9', fontSize:11 }, labelStyle:{color:'#64748B'} };
const STYLE_INFO = {
  visual:      { icon:'👁️', label:'Visual',         color:'text-blue-400' },
  auditory:    { icon:'🎧', label:'Auditory',        color:'text-purple-400' },
  reading:     { icon:'📖', label:'Reading/Writing', color:'text-green-400' },
  kinesthetic: { icon:'🧪', label:'Kinesthetic',     color:'text-amber-400' },
};

function gradeLabel(fcl) {
  if (fcl<=4)  return 'Foundation';
  if (fcl<=7)  return 'Developing';
  if (fcl<=10) return 'Proficient';
  return 'Advanced';
}

export default function SubjectProfile() {
  const nav = useNavigate();
  const { subjectId } = useParams();
  const sid = window.__studentId;

  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState('');

  useEffect(() => {
    if (!subjectId || !sid) return;
    Promise.all([
      api.get(`/api/students/${sid}/subject-performance`),
      api.get(`/api/students/${sid}/topic-mastery`),
      api.get(`/api/students/${sid}/fcl-history`),
      api.get(`/api/quiz/points/${sid}`),
      api.get(`/api/style/${sid}`).catch(()=>({data:[]})),
    ]).then(([perfRes, masteryRes, fclRes, pointsRes, styleRes]) => {
      const subj    = (perfRes.data?.subjects||[]).find(s => String(s.subject_id)===String(subjectId));
      const mastery = (masteryRes.data||[]).filter(m => String(m.subject_id)===String(subjectId));
      const fclHist = (fclRes.data||[]).filter(h => String(h.subject_id)===String(subjectId));
      const points  = (pointsRes.data||[]).find(p => String(p.subject_id)===String(subjectId));
      const style   = (styleRes.data||[]).find(s => String(s.subject_id)===String(subjectId));
      setData({ subj, mastery, fclHist, points, style });
    }).catch(()=>setError('Failed to load subject data.'))
    .finally(()=>setLoading(false));
  }, [subjectId, sid]);

  if (loading) return (
    <div className='min-h-screen bg-app flex items-center justify-center flex-col gap-4'>
      <div className='w-12 h-12 border-4 border-teal/30 border-t-teal rounded-full animate-spin'/>
      <p className='text-muted text-sm'>Loading subject profile…</p>
    </div>
  );

  if (error || !data?.subj) return (
    <PageShell title='Subject Profile' subtitle=''>
      <div className='py-20 text-center'><p className='text-muted text-sm'>{error || 'Subject not found.'}</p><button onClick={()=>nav('/subjects')} className='btn-ghost text-sm mt-4'>← Back</button></div>
    </PageShell>
  );

  const { subj, mastery, fclHist, points, style } = data;
  const styleInfo   = STYLE_INFO[style?.learning_style] || STYLE_INFO.reading;
  const currentFcl  = subj.fcl_level || 1;
  const curPts      = points?.current_points || 0;
  const neededPts   = points?.points_needed  || (currentFcl * 100);
  const progressPct = neededPts > 0 ? Math.min(100, Math.round(curPts/neededPts*100)) : 100;

  const masteryChart = mastery.map(m => ({
    name: m.topic_id.replace(/_/g,' ').split(' ').slice(-1)[0],
    prob: Math.round((m.mastery_prob||0)*100),
    full: m.topic_id.replace(/_/g,' ').replace(/\b\w/g,l=>l.toUpperCase()),
  }));

  const fclChartData = fclHist.map(h => ({ date: h.date?.slice(5), fcl: h.fcl_level }));

  return (
    <PageShell title={subj.subject_name} subtitle={`Subject Profile · ${gradeLabel(currentFcl)} Level`}>
      <div className='space-y-6 max-w-4xl'>

        {/* ── Header cards ── */}
        <div className='grid grid-cols-4 gap-4'>
          {[
            { icon:'🧠', label:'Subject FCL',   value:`FCL ${currentFcl}`, sub:gradeLabel(currentFcl),         color:'text-teal' },
            { icon:'🎯', label:'Accuracy',       value:subj.accuracy?`${subj.accuracy}%`:'—', sub:'Quiz accuracy', color:'text-blue-400' },
            { icon:'🏆', label:'Topics Mastered',value:(mastery.filter(m=>m.mastery==='mastered').length), sub:`of ${mastery.length} topics`, color:'text-green-400' },
            { icon:'⭐', label:'Total Points',   value:points?.total_earned||0, sub:'Lifetime points earned', color:'text-amber-400' },
          ].map(card=>(
            <div key={card.label} className='card p-5'>
              <div className='flex justify-between items-center mb-2'><span className='text-muted text-xs uppercase tracking-wide'>{card.label}</span><span className='text-xl'>{card.icon}</span></div>
              <div className={`stat-number text-2xl font-bold ${card.color}`}>{card.value}</div>
              <p className='text-muted text-xs mt-1'>{card.sub}</p>
            </div>
          ))}
        </div>

        {/* ── FCL Points Progress ── */}
        <div className='card p-5'>
          <div className='flex items-center justify-between mb-3'>
            <div><h3 className='text-primary font-semibold text-sm'>FCL Points Progress</h3><p className='text-muted text-xs'>Points toward FCL {currentFcl+1}</p></div>
            <span className='stat-number text-teal text-sm'>{curPts} / {neededPts} pts</span>
          </div>
          <div className='w-full bg-border rounded-full h-3 mb-2'>
            <div className='h-3 rounded-full bg-teal transition-all duration-700' style={{width:`${progressPct}%`}}/>
          </div>
          <div className='flex justify-between text-xs text-muted'>
            <span>FCL {currentFcl}</span>
            <span>{progressPct}% — {neededPts-curPts} pts remaining</span>
            <span>FCL {Math.min(currentFcl+1,13)}</span>
          </div>
        </div>

        {/* ── Learning Style ── */}
        <div className='card p-5'>
          <div className='flex items-start justify-between'>
            <div>
              <h3 className='text-primary font-semibold text-sm mb-1'>Learning Style for {subj.subject_name}</h3>
              <div className='flex items-center gap-2'>
                <span className='text-2xl'>{styleInfo.icon}</span>
                <span className={`font-semibold ${styleInfo.color}`}>{styleInfo.label}</span>
                {style?.auto_detected && <span className='text-muted text-xs'>(auto-detected)</span>}
              </div>
            </div>
            <button onClick={()=>nav('/profile')} className='text-teal text-xs hover:underline'>Change →</button>
          </div>
          <div className='mt-3 flex flex-wrap gap-2 text-xs text-muted'>
            <span className='px-2 py-0.5 bg-border/50 rounded'>✓ Quiz questions personalised</span>
            <span className='px-2 py-0.5 bg-border/50 rounded'>✓ AI Tutor responses personalised</span>
            <span className='px-2 py-0.5 bg-border/50 rounded'>✓ Library content adapted</span>
          </div>
        </div>

        <div className='grid grid-cols-2 gap-4'>
          {/* ── FCL History ── */}
          <div className='card p-5'>
            <h3 className='text-primary font-semibold text-sm mb-4'>FCL History</h3>
            {fclChartData.length > 1 ? (
              <ResponsiveContainer width='100%' height={160}>
                <AreaChart data={fclChartData} margin={{top:5,right:5,bottom:0,left:-20}}>
                  <defs><linearGradient id='fclg' x1='0' y1='0' x2='0' y2='1'><stop offset='5%' stopColor='#00D4C8' stopOpacity={0.25}/><stop offset='95%' stopColor='#00D4C8' stopOpacity={0}/></linearGradient></defs>
                  <CartesianGrid strokeDasharray='3 3' stroke='#1E293B'/>
                  <XAxis dataKey='date' tick={{fontSize:10,fill:'#64748B'}} tickLine={false}/>
                  <YAxis domain={[1,13]} tick={{fontSize:10,fill:'#64748B'}} tickLine={false}/>
                  <Tooltip {...CHART_TOOLTIP} formatter={v=>[`FCL ${v}`,'Level']}/>
                  <Area type='monotone' dataKey='fcl' stroke='#00D4C8' strokeWidth={2} fill='url(#fclg)' dot={{r:3,fill:'#00D4C8',strokeWidth:0}}/>
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className='h-40 flex items-center justify-center text-muted text-xs'>Complete quizzes to build FCL history</div>
            )}
          </div>

          {/* ── Topic Mastery ── */}
          <div className='card p-5'>
            <h3 className='text-primary font-semibold text-sm mb-4'>Topic Mastery</h3>
            {masteryChart.length > 0 ? (
              <ResponsiveContainer width='100%' height={160}>
                <BarChart data={masteryChart} margin={{top:5,right:5,bottom:0,left:-20}}>
                  <CartesianGrid strokeDasharray='3 3' stroke='#1E293B'/>
                  <XAxis dataKey='name' tick={{fontSize:10,fill:'#64748B'}} tickLine={false}/>
                  <YAxis domain={[0,100]} tick={{fontSize:10,fill:'#64748B'}} tickLine={false}/>
                  <Tooltip {...CHART_TOOLTIP} formatter={(v,_,p)=>[`${v}%`,p.payload.full]}/>
                  <Bar dataKey='prob' fill='#3B82F6' radius={[3,3,0,0]}/>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className='h-40 flex items-center justify-center text-muted text-xs'>No mastery data yet</div>
            )}
          </div>
        </div>

        {/* ── Mastery detail list ── */}
        {mastery.length > 0 && (
          <div className='card'>
            <div className='px-5 py-4 border-b border-border'><h3 className='text-primary font-semibold text-sm'>Topic Breakdown</h3></div>
            <div className='divide-y divide-border'>
              {mastery.map(m=>{
                const pct=Math.round((m.mastery_prob||0)*100);
                return (
                  <div key={m.topic_id} className='px-5 py-3 flex items-center gap-4'>
                    <div className='flex-1 min-w-0'>
                      <p className='text-primary text-sm font-medium'>{m.topic_id.replace(/_/g,' ').replace(/\b\w/g,l=>l.toUpperCase())}</p>
                      <div className='flex items-center gap-2 mt-1'>
                        <div className='flex-1 bg-border rounded-full h-1.5 max-w-48'>
                          <div className='h-1.5 rounded-full transition-all' style={{width:`${pct}%`,background:pct>=80?'#10B981':pct>=50?'#00D4C8':'#F59E0B'}}/>
                        </div>
                        <span className='text-muted text-xs stat-number'>{pct}%</span>
                      </div>
                    </div>
                    <span className={`text-xs font-medium px-2 py-0.5 rounded ${m.mastery==='mastered'?'bg-green-500/10 text-green-400':m.mastery==='developing'?'bg-amber-500/10 text-amber-400':'bg-red-500/10 text-red-400'}`}>
                      {m.mastery==='mastered'?'Mastered':m.mastery==='developing'?'Developing':'Needs Work'}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        <div className='flex gap-3'>
          <button onClick={()=>nav(`/quiz?topic=${mastery[0]?.topic_id||''}`)} className='btn-primary text-sm'>Take a Quiz →</button>
          <button onClick={()=>nav('/dashboard')} className='btn-ghost text-sm'>← Dashboard</button>
          <button onClick={()=>nav('/library')} className='btn-ghost text-sm'>📚 Library</button>
        </div>
      </div>
    </PageShell>
  );
}