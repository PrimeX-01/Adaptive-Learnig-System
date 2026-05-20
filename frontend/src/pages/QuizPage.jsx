import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import PageShell from '../components/PageShell';
import api from '../services/api';

const QUIZ_LENGTH = 10;

const SUBJECT_MAP = {
  MATH:['mathematics_algebra','mathematics_geometry','mathematics_calculus','mathematics_statistics'],
  SCI: ['science_biology','science_chemistry','science_physics'],
  ENG: ['english_comprehension','english_writing','english_literature'],
  SOC: ['social_studies','civics'],
  CS:  ['computer_science','programming'],
};
const SUBJECT_NAMES = { MATH:'Mathematics',SCI:'Science',ENG:'English',SOC:'Social Studies',CS:'Computer Science' };
const SUBJECT_TOPICS = {
  MATH:{name:'Mathematics',topics:['mathematics_algebra','mathematics_geometry','mathematics_calculus','mathematics_statistics']},
  SCI: {name:'Science',    topics:['science_biology','science_chemistry','science_physics']},
  ENG: {name:'English',    topics:['english_comprehension','english_writing','english_literature']},
  SOC: {name:'Social Studies',topics:['social_studies','civics']},
  CS:  {name:'Computer Science',topics:['computer_science','programming']},
};

function gradeToFCL(g){if(!g||g<=0)return 5;if(g<=4)return 2;if(g<=7)return 4;if(g<=9)return 6;if(g<=12)return 8;if(g<=15)return 9;if(g<=17)return 11;return 13;}

/*  Points Progress Bar  */
function PointsBar({ current, needed, fcl, pointsJustEarned }) {
  const pct = needed > 0 ? Math.min(100, Math.round((current / needed) * 100)) : 100;
  return (
    <div className='card p-4 mb-4'>
      <div className='flex items-center justify-between mb-2'>
        <div className='flex items-center gap-2'>
          <span className='text-muted text-xs'>FCL {fcl} Progress</span>
          {pointsJustEarned > 0 && (
            <span className='text-green-400 text-xs font-bold animate-pulse'>+{pointsJustEarned} pts</span>
          )}
        </div>
        <span className='text-muted text-xs stat-number'>{current} / {needed} pts</span>
      </div>
      <div className='w-full bg-border rounded-full h-2.5'>
        <div className='h-2.5 rounded-full bg-teal transition-all duration-700'
          style={{ width:`${pct}%` }} />
      </div>
      <p className='text-muted text-xs mt-1'>{needed - current} points to FCL {fcl + 1}</p>
    </div>
  );
}

/*  Progress Bar  */
function ProgressBar({ current, total }) {
  const pct = total > 0 ? Math.round((current / total) * 100) : 0;
  return (
    <div className='mb-4'>
      <div className='flex items-center justify-between mb-1'>
        <span className='text-muted text-xs'>Question {current} of {total}</span>
        <span className='text-muted text-xs'>{pct}% complete</span>
      </div>
      <div className='w-full bg-border rounded-full h-2'>
        <div className='h-2 rounded-full bg-teal transition-all duration-500' style={{width:`${pct}%`}} />
      </div>
    </div>
  );
}

/*  Mini Tutor Panel  */
function TutorPanel({ isOpen, onClose, question, topicId, fcl, sid, subjectId }) {
  const [sessionId,   setSessionId]   = useState(null);
  const [messages,    setMessages]    = useState([]);
  const [input,       setInput]       = useState('');
  const [sending,     setSending]     = useState(false);
  const [initialized, setInitialized] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({behavior:'smooth'}); }, [messages]);

  useEffect(() => {
    if (!isOpen || initialized || !question) return;
    setInitialized(true);
    (async () => {
      try {
        const { data } = await api.post('/api/chat/new-session', { student_id:parseInt(sid), subject_id:subjectId });
        const newSid = data.session_id;
        setSessionId(newSid);
        const autoMsg = `I need help with this question:\n\n"${question.question_text}"\n\nOptions:\n${question.options.map((o,i)=>`${String.fromCharCode(65+i)}. ${o}`).join('\n')}\n\nGive me a hint without revealing the answer.`;
        setMessages([{role:'user',content:autoMsg}]);
        setSending(true);
        const res = await api.post('/api/chat/message', {session_id:newSid,student_id:parseInt(sid),message:autoMsg,topic:topicId,fcl_level:fcl},{timeout:90000});
        setMessages([{role:'user',content:autoMsg},{role:'assistant',content:res.data.response}]);
      } catch { setMessages(prev=>[...prev,{role:'assistant',content:'Sorry, could not connect. Please try again.'}]); }
      finally { setSending(false); }
    })();
  }, [isOpen, initialized, question]);

  useEffect(() => { if (!isOpen) setInitialized(false); }, [isOpen]);

  const sendMessage = async () => {
    if (!input.trim() || sending || !sessionId) return;
    const msg = input.trim(); setInput('');
    setMessages(prev=>[...prev,{role:'user',content:msg}]); setSending(true);
    try {
      const res = await api.post('/api/chat/message',{session_id:sessionId,student_id:parseInt(sid),message:msg,topic:topicId,fcl_level:fcl},{timeout:90000});
      setMessages(prev=>[...prev,{role:'assistant',content:res.data.response}]);
    } catch { setMessages(prev=>[...prev,{role:'assistant',content:'Connection error. Try again.'}]); }
    finally { setSending(false); }
  };

  if (!isOpen) return null;
  return (
    <>
      <div className='fixed inset-0 bg-black/30 z-40' onClick={onClose} />
      <div className='fixed right-0 top-0 bottom-0 w-96 bg-sidebar border-l border-border z-50 flex flex-col shadow-2xl'>
        <div className='px-4 py-3 border-b border-border flex items-center justify-between flex-shrink-0'>
          <div><h3 className='text-primary font-semibold text-sm'>AI Tutor</h3><p className='text-muted text-xs'>Helping with current question</p></div>
          <button onClick={onClose} className='text-muted hover:text-primary text-lg'>✕</button>
        </div>
        <div className='px-4 py-2 bg-amber-500/10 border-b border-amber-500/20 flex-shrink-0'>
          <p className='text-amber-400 text-xs'>💡 Tutor use is tracked and affects your points.</p>
        </div>
        <div className='flex-1 overflow-y-auto px-4 py-3 space-y-3'>
          {messages.map((m,i)=>(
            <div key={i} className={`flex ${m.role==='user'?'justify-end':'justify-start'}`}>
              {m.role==='assistant'&&<div className='w-6 h-6 rounded-md bg-teal/15 border border-teal/30 flex items-center justify-center text-teal text-xs mr-2 mt-0.5 flex-shrink-0'>AI</div>}
              <div className={`max-w-[280px] rounded-xl px-3 py-2 text-xs leading-relaxed ${m.role==='user'?'bg-teal/10 border border-teal/30':'bg-card border border-border'} text-primary`}>
                <ReactMarkdown>{m.content}</ReactMarkdown>
              </div>
            </div>
          ))}
          {sending&&<div className='flex justify-start'><div className='w-6 h-6 rounded-md bg-teal/15 border border-teal/30 flex items-center justify-center text-teal text-xs mr-2'>AI</div><div className='bg-card border border-border rounded-xl px-3 py-2 flex gap-1'>{[0,1,2].map(i=><div key={i} className='w-1.5 h-1.5 rounded-full bg-teal animate-bounce' style={{animationDelay:`${i*150}ms`}}/>)}</div></div>}
          <div ref={bottomRef}/>
        </div>
        <div className='px-4 py-3 border-t border-border flex gap-2 flex-shrink-0'>
          <input value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>e.key==='Enter'&&sendMessage()} placeholder='Ask a follow-up…' className='flex-1 bg-input border border-border rounded-lg px-3 py-2 text-primary text-xs focus:outline-none focus:border-teal/60'/>
          <button onClick={sendMessage} disabled={sending||!input.trim()} className='btn-primary px-3 py-2 text-xs rounded-lg disabled:opacity-50'>Send</button>
        </div>
      </div>
    </>
  );
}

/*  Resume Modal  */
function ResumeModal({ saved, onResume, onNew }) {
  const ago = saved?.startedAt ? Math.round((Date.now()-saved.startedAt)/60000) : 0;
  return (
    <div className='fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4'>
      <div className='card p-6 w-full max-w-md'>
        <div className='text-center mb-5'><span className='text-4xl block mb-3'>📋</span>
          <h2 className='text-primary font-bold text-lg mb-1'>Incomplete Quiz Found</h2>
          <p className='text-muted text-sm'>You left a quiz {ago}m ago</p>
        </div>
        <div className='bg-app border border-border rounded-lg p-4 mb-5'>
          <p className='text-primary text-sm font-medium'>{saved?.subjectName}</p>
          <p className='text-muted text-xs mb-2'>{saved?.topicId?.replace(/_/g,' ')}</p>
          <div className='flex gap-4 text-xs'>
            <span className='text-green-400'>✓ {saved?.stats?.correct||0} correct</span>
            <span className='text-red-400'>✗ {saved?.stats?.wrong||0} wrong</span>
            <span className='text-muted'>Q{(saved?.questionNum||0)+1} of {QUIZ_LENGTH}</span>
          </div>
        </div>
        <div className='flex flex-col gap-3'>
          <button onClick={onResume} className='btn-primary py-2.5 text-sm'>▶ Resume Quiz</button>
          <button onClick={onNew}    className='btn-ghost   py-2.5 text-sm'>🔄 Start New Quiz</button>
        </div>
      </div>
    </div>
  );
}

/*  Results Screen  */
function ResultsScreen({ stats, topicId, subjectName, sid, onRetry, onDashboard, onChat }) {
  const accuracy = QUIZ_LENGTH > 0 ? Math.round((stats.correct/QUIZ_LENGTH)*100) : 0;
  const g = accuracy>=90?{label:'Excellent!',colour:'text-green-400',icon:'🏆'}:accuracy>=70?{label:'Good work!',colour:'text-teal',icon:'✅'}:accuracy>=50?{label:'Keep going!',colour:'text-amber-400',icon:'📈'}:{label:'Needs practice',colour:'text-red-400',icon:'📚'};
  const history = (() => { try{return JSON.parse(localStorage.getItem(`quiz_history_${sid}`)||'[]');}catch{return [];} })();
  return (
    <div className='max-w-2xl mx-auto'>
      <div className='card p-8 text-center mb-6'>
        <span className='text-6xl block mb-4'>{g.icon}</span>
        <h2 className={`text-2xl font-bold mb-1 ${g.colour}`}>{g.label}</h2>
        <p className='text-muted text-sm mb-5'>{subjectName} — {topicId.replace(/_/g,' ')}</p>
        <div className='w-28 h-28 rounded-full border-4 border-teal/30 flex flex-col items-center justify-center mx-auto mb-5 bg-teal/5'>
          <span className={`stat-number text-3xl font-bold ${g.colour}`}>{accuracy}%</span>
          <span className='text-muted text-xs mt-0.5'>Accuracy</span>
        </div>
        <div className='grid grid-cols-5 gap-3 mb-4'>
          {[['Correct',stats.correct,'text-green-400'],['Wrong',stats.wrong,'text-red-400'],['Hints',stats.hints,'text-amber-400'],['Streak',stats.bestStreak,'text-teal'],['Tutor',stats.tutorConsultations,'text-purple-400']].map(([l,v,c])=>(
            <div key={l} className='bg-app border border-border rounded-lg p-3'><div className={`stat-number text-xl font-bold ${c}`}>{v}</div><div className='text-muted text-xs mt-0.5'>{l}</div></div>
          ))}
        </div>
        {stats.pointsEarned > 0 && (
          <div className='px-4 py-2.5 bg-teal/10 border border-teal/30 rounded-lg text-teal text-sm mb-3'>
            🎯 You earned <strong>{stats.totalPointsEarned}</strong> points this quiz!
            {stats.bonusEarned > 0 && <span className='text-green-400'> (+{stats.bonusEarned} completion bonus)</span>}
          </div>
        )}
        {stats.fclChanged && <div className='px-4 py-2.5 bg-teal/10 border border-teal/30 rounded-lg text-teal text-sm'>🧠 FCL advanced to <strong>{stats.newFcl}</strong>!</div>}
      </div>
      {history.length > 0 && (
        <div className='card mb-6'>
          <div className='px-5 py-3 border-b border-border'><h3 className='text-primary font-semibold text-sm'>Quiz History</h3></div>
          <div className='divide-y divide-border'>
            {history.slice(0,5).map((h,i)=>(
              <div key={i} className='px-5 py-3 flex items-center justify-between'>
                <div><p className='text-primary text-xs font-medium'>{h.subjectName}</p><p className='text-muted text-xs'>{new Date(h.completedAt).toLocaleDateString()}</p></div>
                <div className='flex items-center gap-3 text-xs'>
                  {h.tutorConsultations>0&&<span className='text-purple-400'>◈×{h.tutorConsultations}</span>}
                  <span className={`stat-number font-bold ${h.score>=70?'text-green-400':'text-amber-400'}`}>{h.score}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      <div className='flex flex-col gap-3'>
        <button onClick={onRetry}     className='btn-primary py-3 text-sm'>🔄 Try Again</button>
        <button onClick={onChat}      className='btn-ghost   py-3 text-sm'>◈ Discuss with AI Tutor</button>
        <button onClick={onDashboard} className='btn-ghost   py-3 text-sm'>← Back to Dashboard</button>
      </div>
    </div>
  );
}

/*   MAIN QUIZ PAGE */

export default function QuizPage() {
  const navigate = useNavigate();
  const sid      = window.__studentId;

  const [enrolled,    setEnrolled]    = useState([]);
  const [subjectCode, setSubjectCode] = useState('MATH');
  const [subjectId,   setSubjectId]   = useState(null);
  const [subjectName, setSubjectName] = useState('Mathematics');
  const [topicId,     setTopicId]     = useState('mathematics_algebra');
  const [fcl,         setFcl]         = useState(5);
  const [grade,       setGrade]       = useState(null);

  // Add learning style state
  const [learningStyle, setLearningStyle] = useState('reading');

  const [question,    setQuestion]    = useState(null);
  const [selected,    setSelected]    = useState(null);
  const [feedback,    setFeedback]    = useState(null);
  const [hintLevel,   setHintLevel]   = useState(0);
  const [hintText,    setHintText]    = useState('');
  const [hintError,   setHintError]   = useState('');
  const [loading,     setLoading]     = useState(false);
  const [hintLoading, setHintLoading] = useState(false);
  const [submitting,  setSubmitting]  = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [questionNum, setQuestionNum] = useState(0);
  const [quizDone,    setQuizDone]    = useState(false);
  const [ready,       setReady]       = useState(false);
  const [showTutor,   setShowTutor]   = useState(false);
  const [tutorConsultedThisQ, setTutorConsultedThisQ] = useState(false);

  // Points state
  const [pointsJustEarned,   setPointsJustEarned]   = useState(0);
  const [currentPoints,      setCurrentPoints]       = useState(0);
  const [pointsToNextFcl,    setPointsToNextFcl]     = useState(100);
  const [subjectFclDisplay,  setSubjectFclDisplay]   = useState(fcl);

  const [savedQuiz,       setSavedQuiz]       = useState(null);
  const [showResumeModal, setShowResumeModal] = useState(false);

  const [stats, setStats] = useState({
    correct:0,wrong:0,hints:0,streak:0,bestStreak:0,
    fclChanged:false,newFcl:null,tutorConsultations:0,
    totalPointsEarned:0,bonusEarned:0,pointsEarned:0,
  });

  // Refs for cleanup
  const quizDoneRef    = useRef(false);
  const questionNumRef = useRef(0);
  const statsRef       = useRef(stats);
  const topicIdRef     = useRef(topicId);
  const subjectNameRef = useRef(subjectName);
  const fclRef         = useRef(fcl);
  const subjectCodeRef = useRef(subjectCode);
  const subjectIdRef   = useRef(subjectId);

  useEffect(()=>{ quizDoneRef.current=quizDone; },[quizDone]);
  useEffect(()=>{ questionNumRef.current=questionNum; },[questionNum]);
  useEffect(()=>{ statsRef.current=stats; },[stats]);
  useEffect(()=>{ topicIdRef.current=topicId; },[topicId]);
  useEffect(()=>{ subjectNameRef.current=subjectName; },[subjectName]);
  useEffect(()=>{ fclRef.current=fcl; },[fcl]);
  useEffect(()=>{ subjectCodeRef.current=subjectCode; },[subjectCode]);
  useEffect(()=>{ subjectIdRef.current=subjectId; },[subjectId]);

  // Save incomplete quiz on unmount
  useEffect(() => {
    return () => {
      if (!quizDoneRef.current && questionNumRef.current > 0) {
        localStorage.setItem(`quiz_incomplete_${sid}`, JSON.stringify({
          topicId:topicIdRef.current, subjectCode:subjectCodeRef.current,
          subjectName:subjectNameRef.current, fcl:fclRef.current,
          questionNum:questionNumRef.current, stats:statsRef.current, startedAt:Date.now(),
        }));
        const countKey=`quiz_abandon_${sid}`;
        const count=parseInt(localStorage.getItem(countKey)||'0')+1;
        localStorage.setItem(countKey,count.toString());
        if(count>=3){
          api.post('/api/quiz/abandoned',{student_id:parseInt(sid),topic_id:topicIdRef.current,abandon_count:count}).catch(()=>{});
        }
      } else if (quizDoneRef.current) {
        localStorage.removeItem(`quiz_incomplete_${sid}`);
        localStorage.removeItem(`quiz_abandon_${sid}`);
      }
    };
  }, []); 

  const saveToHistory = useCallback((finalStats) => {
    try {
      const key=`quiz_history_${sid}`;
      const existing=JSON.parse(localStorage.getItem(key)||'[]');
      existing.unshift({topicId:topicIdRef.current,subjectName:subjectNameRef.current,score:Math.round(finalStats.correct/QUIZ_LENGTH*100),correct:finalStats.correct,wrong:finalStats.wrong,hintsUsed:finalStats.hints,tutorConsultations:finalStats.tutorConsultations,completedAt:new Date().toISOString()});
      localStorage.setItem(key,JSON.stringify(existing.slice(0,20)));
    } catch{}
  },[sid]);

  // Load enrolled subjects + grade + learning style
  useEffect(() => {
    Promise.all([
      api.get(`/api/subjects/enrolled/${sid}`),
      api.get(`/api/students/${sid}/profile`),
    ]).then(([enrollRes,profRes]) => {
      const enrollments=enrollRes.data||[];
      const studentGrade=profRes.data?.grade||null;
      const style = profRes.data?.preferred_learning_style || 'reading';  // get learning style
      setGrade(studentGrade); setEnrolled(enrollments);
      setLearningStyle(style);
      if (enrollments.length>0) {
        const first=enrollments[0];
        const avgFcl=enrollments.filter(e=>e.fcl_level).reduce((s,e,_,a)=>s+e.fcl_level/a.length,0);
        setSubjectCode(first.subject_code); setSubjectId(first.subject_id);
        setSubjectName(first.subject_name);
        const fclVal=first.fcl_level||Math.round(avgFcl)||gradeToFCL(studentGrade);
        setFcl(fclVal); setSubjectFclDisplay(fclVal);
        const urlTopic=new URLSearchParams(window.location.search).get('topic');
        const topics=SUBJECT_TOPICS[first.subject_code]?.topics||[];
        setTopicId(urlTopic&&topics.includes(urlTopic)?urlTopic:topics[0]||'mathematics_algebra');
      } else {
        const urlTopic=new URLSearchParams(window.location.search).get('topic')||'mathematics_algebra';
        const code=Object.entries(SUBJECT_MAP).find(([,t])=>t.includes(urlTopic))?.[0]||'MATH';
        setTopicId(urlTopic); setSubjectCode(code); setSubjectName(SUBJECT_NAMES[code]||'Mathematics');
        setFcl(gradeToFCL(studentGrade));
      }
      setReady(true);
      try {
        const saved=JSON.parse(localStorage.getItem(`quiz_incomplete_${sid}`)||'null');
        if(saved&&Date.now()-saved.startedAt<24*60*60*1000){setSavedQuiz(saved);setShowResumeModal(true);}
        else if(saved){localStorage.removeItem(`quiz_incomplete_${sid}`);}
      } catch{}
    }).catch(()=>{
      const urlTopic=new URLSearchParams(window.location.search).get('topic')||'mathematics_algebra';
      const code=Object.entries(SUBJECT_MAP).find(([,t])=>t.includes(urlTopic))?.[0]||'MATH';
      setTopicId(urlTopic);setSubjectCode(code);setSubjectName(SUBJECT_NAMES[code]||'Mathematics');setReady(true);
    });
  },[sid]);

  function handleSubjectChange(code) {
    const enrollment=enrolled.find(x=>x.subject_code===code);
    setSubjectCode(code);
    if(enrollment){
      setSubjectId(enrollment.subject_id); setSubjectName(enrollment.subject_name);
      const avgFcl=enrolled.filter(e=>e.fcl_level).reduce((s,e,_,a)=>s+e.fcl_level/a.length,0);
      const fclVal=enrollment.fcl_level||Math.round(avgFcl)||gradeToFCL(grade);
      setFcl(fclVal); setSubjectFclDisplay(fclVal);
    } else { setSubjectName(SUBJECT_NAMES[code]||code); setFcl(gradeToFCL(grade)); }
    setTopicId(SUBJECT_TOPICS[code]?.topics[0]||'mathematics_algebra');
    resetQuiz();
  }

  function handleTopicChange(t){setTopicId(t);resetQuiz();}

  function resetQuiz(){
    setQuestion(null);setSelected(null);setFeedback(null);setSubmitError('');
    setHintLevel(0);setHintText('');setHintError('');setQuestionNum(0);
    setQuizDone(false);setShowTutor(false);setTutorConsultedThisQ(false);
    setPointsJustEarned(0);
    setStats({correct:0,wrong:0,hints:0,streak:0,bestStreak:0,fclChanged:false,newFcl:null,tutorConsultations:0,totalPointsEarned:0,bonusEarned:0,pointsEarned:0});
  }

  //fetchQuestion now includes learning_style
  const fetchQuestion = useCallback(async (topic, fclLevel) => {
    setLoading(true); setSelected(null); setFeedback(null); setSubmitError('');
    setHintLevel(0); setHintText(''); setHintError('');
    setShowTutor(false); setTutorConsultedThisQ(false); setPointsJustEarned(0);
    try {
const { data } = await api.post('/api/quiz/generate-question',{
        student_id: parseInt(sid),
        topic,
        fcl_level: fclLevel,
        learning_style: learningStyle,   
      });
      if (!data || !data.question_text) {
        console.error('Question fetch failed: empty response from server');
        return;
      }
      setQuestion(data);
      if(data.fcl_used){setFcl(data.fcl_used);setSubjectFclDisplay(data.fcl_used);}
    } catch(err){console.error('Question fetch failed:',err);}
    finally{setLoading(false);}
  },[sid, learningStyle]); 

  useEffect(()=>{if(ready&&topicId)fetchQuestion(topicId,fcl);},[ready]);

  const prevTopicRef=useRef('');
  useEffect(()=>{
    if(ready&&topicId&&topicId!==prevTopicRef.current){prevTopicRef.current=topicId;fetchQuestion(topicId,fcl);}
  },[topicId,ready]);

  const submitAnswer = async (option) => {
    if(feedback||submitting)return;
    setSelected(option);setSubmitting(true);setSubmitError('');
    const qId=question?.question_id??question?.id??`local-${Date.now()}`;
    try {
      const { data } = await api.post('/api/quiz/submit',{
        student_id:parseInt(sid),
        question_id:qId,
        question_text:question.question_text||'',
        topic_id:topicId,
        student_answer:option,
        correct_answer:question.correct_answer,
        fcl_level:Math.round(Number(fcl))||5,
        hints_used:hintLevel,
        tutor_consulted:tutorConsultedThisQ,
      });
      setFeedback(data);
      const pts=data.points_earned||0;
      setPointsJustEarned(pts);
      setCurrentPoints(data.current_points||0);
      setPointsToNextFcl(data.points_to_next_fcl||100);
      if(data.subject_fcl){setSubjectFclDisplay(data.subject_fcl);}
      setStats(prev=>{
        const newStreak=data.is_correct?prev.streak+1:0;
        return{...prev,
          correct:prev.correct+(data.is_correct?1:0),
          wrong:prev.wrong+(data.is_correct?0:1),
          hints:prev.hints+hintLevel,
          streak:newStreak,
          bestStreak:Math.max(prev.bestStreak,newStreak),
          fclChanged:data.fcl_changed||prev.fclChanged,
          newFcl:data.new_fcl||prev.newFcl,
          totalPointsEarned:prev.totalPointsEarned+pts,
        };
      });
    } catch {
      const isCorrect=option===question.correct_answer;
      setFeedback({is_correct:isCorrect,correct_answer:question.correct_answer,feedback_text:isCorrect?'Correct! (not saved)':(`Incorrect. Answer: ${question.correct_answer} (not saved)`)});
      setSubmitError('⚠ Graded locally — server unreachable.');
      setStats(prev=>{const ns=isCorrect?prev.streak+1:0;return{...prev,correct:prev.correct+(isCorrect?1:0),wrong:prev.wrong+(isCorrect?0:1),hints:prev.hints+hintLevel,streak:ns,bestStreak:Math.max(prev.bestStreak,ns)};});
    } finally{setSubmitting(false);}
  };

  const handleNext = async () => {
    const next=questionNum+1;
    if(next>=QUIZ_LENGTH){
      // Call quiz complete for bonus points
      try {
        const res=await api.post('/api/quiz/complete',{student_id:parseInt(sid),topic_id:topicId,correct_count:stats.correct,total_count:QUIZ_LENGTH});
        if(res.data.bonus_awarded>0){
          setStats(prev=>({...prev,bonusEarned:res.data.bonus_awarded,totalPointsEarned:prev.totalPointsEarned+res.data.bonus_awarded,fclChanged:res.data.fcl_changed||prev.fclChanged,newFcl:res.data.new_fcl||prev.newFcl}));
        }
      } catch{}
      saveToHistory(stats);
      setQuizDone(true);
    } else {
      setQuestionNum(next);
      fetchQuestion(topicId,fcl);
    }
  };

  const handleRetry=()=>{resetQuiz();setTimeout(()=>fetchQuestion(topicId,fcl),50);};

  const openTutor=()=>{
    setShowTutor(true);
    if(!tutorConsultedThisQ){
      setTutorConsultedThisQ(true);
      setStats(prev=>({...prev,tutorConsultations:prev.tutorConsultations+1}));
    }
  };

  const requestHint=async()=>{
    if(hintLevel>=3||!question)return;
    const nextLevel=hintLevel+1; setHintLoading(true); setHintError('');
    try {
      const {data}=await api.get(`/api/hints/${question.question_id}/${nextLevel}`,{params:{topic:topicId,fcl_level:fcl,student_id:parseInt(sid)}});
      const text=data.hint_text||data.hint||'';
      if(text){setHintText(text);setHintLevel(nextLevel);}
      else{setHintError('Hint not available for this question.');}
    } catch{setHintError('Could not load hint. Please try again.');}
    finally{setHintLoading(false);}
  };

  const hintStyle={1:'bg-amber-500/10 border border-amber-500/30 text-amber-300',2:'bg-orange-500/10 border border-orange-500/30 text-orange-300',3:'bg-red-500/10 border border-red-500/30 text-red-300'}[hintLevel]||'';
  const currentTopics=SUBJECT_TOPICS[subjectCode]?.topics||[];

  const headerActions=(
    <div className='flex items-center gap-3'>
      <select value={subjectCode} onChange={e=>handleSubjectChange(e.target.value)} className='bg-input border border-border rounded-lg px-3 py-1.5 text-primary text-sm focus:border-teal/60 focus:outline-none'>
        {enrolled.length>0?enrolled.map(e=><option key={e.subject_code} value={e.subject_code}>{e.subject_name}</option>):Object.entries(SUBJECT_TOPICS).map(([code,s])=><option key={code} value={code}>{s.name}</option>)}
      </select>
      <select value={topicId} onChange={e=>handleTopicChange(e.target.value)} className='bg-input border border-border rounded-lg px-3 py-1.5 text-primary text-sm focus:border-teal/60 focus:outline-none'>
        {currentTopics.map(t=><option key={t} value={t}>{t.replace(/_/g,' ').replace(/\b\w/g,l=>l.toUpperCase())}</option>)}
      </select>
      <span className='badge-teal stat-number text-xs'>FCL {subjectFclDisplay}</span>
    </div>
  );

  if(showResumeModal&&savedQuiz) return (
    <PageShell title='Quiz' subtitle={subjectName} actions={headerActions}>
      <ResumeModal saved={savedQuiz} onResume={()=>{
        setSubjectCode(savedQuiz.subjectCode);setSubjectName(savedQuiz.subjectName);
        setTopicId(savedQuiz.topicId);setFcl(savedQuiz.fcl);
        setQuestionNum(savedQuiz.questionNum);setStats(savedQuiz.stats);
        setShowResumeModal(false);localStorage.removeItem(`quiz_incomplete_${sid}`);
        fetchQuestion(savedQuiz.topicId,savedQuiz.fcl);
      }} onNew={()=>{setShowResumeModal(false);localStorage.removeItem(`quiz_incomplete_${sid}`);setSavedQuiz(null);}}/>
    </PageShell>
  );

  if(quizDone) return (
    <PageShell title='Quiz Results' subtitle={subjectName} actions={headerActions}>
      <ResultsScreen stats={stats} topicId={topicId} subjectName={subjectName} sid={sid} onRetry={handleRetry} onDashboard={()=>navigate('/dashboard')} onChat={()=>navigate(`/chat?topic=${topicId}`)}/>
    </PageShell>
  );

  return (
    <PageShell title='Quiz' subtitle={subjectName} actions={headerActions}>
      <TutorPanel isOpen={showTutor} onClose={()=>setShowTutor(false)} question={question} topicId={topicId} fcl={fcl} sid={sid} subjectId={subjectId}/>
      <ProgressBar current={questionNum} total={QUIZ_LENGTH}/>
      <PointsBar current={currentPoints} needed={pointsToNextFcl} fcl={subjectFclDisplay} pointsJustEarned={pointsJustEarned}/>

      {/* Stats strip */}
      <div className='card p-4 mb-6 flex flex-wrap gap-6 items-center'>
        {[['Correct',stats.correct,'text-teal'],['Wrong',stats.wrong,'text-red-400'],['Hints',stats.hints,'text-amber-400'],['Streak',stats.streak,'text-green-400'],['Tutor',stats.tutorConsultations,'text-purple-400']].map(([l,v,c])=>(
          <div key={l} className='flex flex-col'><span className={`stat-number text-2xl font-bold ${c}`}>{v}</span><span className='text-xs text-muted uppercase tracking-wide'>{l}</span></div>
        ))}
        <div className='ml-auto text-sm text-muted'>Topic: <span className='text-primary font-medium'>{topicId.replace(/_/g,' ').replace(/\b\w/g,l=>l.toUpperCase())}</span></div>
      </div>

      {/* Question */}
      {loading?(
        <div className='card p-10 text-center text-muted animate-pulse'>Generating question…</div>
      ):question?(
        <div className='card-hover p-6 mb-4'>
          <p className='text-primary text-lg font-medium mb-6 leading-relaxed'>{question.question_text}</p>
          {question.image_url && (
  <div className="mb-4">
    <img 
      src={question.image_url} 
      alt="Question illustration" 
      className="rounded-lg max-w-full border border-teal/30 mx-auto"
    />
  </div>
)}
          <div className='grid grid-cols-1 gap-3'>
            {question.options.map((opt,i)=>{
              const isSelected=selected===opt;
              const isCorrect=feedback?.correct_answer===opt||(feedback?.is_correct&&isSelected);
              let cls='border rounded-lg px-4 py-3 text-sm transition-all duration-150 text-left w-full ';
              if(feedback){if(isCorrect)cls+='border-green-500 bg-green-500/10 text-green-400 font-medium cursor-default';else if(isSelected)cls+='border-red-500 bg-red-500/10 text-red-400 cursor-default';else cls+='border-border text-muted opacity-50 cursor-default';}
              else if(isSelected)cls+='border-teal bg-teal/10 text-teal font-medium';
              else cls+='border-border text-muted hover:border-teal/40 hover:text-primary cursor-pointer';
              return(<button key={i} className={cls} onClick={()=>submitAnswer(opt)} disabled={!!feedback||submitting}><span className='font-mono mr-3 text-xs opacity-60'>{String.fromCharCode(65+i)}.</span>{opt}</button>);
            })}
          </div>
        </div>
      ):(
        <div className='card p-10 text-center text-muted'>No question loaded.</div>
      )}

      {/* Hints */}
      {question&&!feedback&&(
        <div className='mb-4'>
          {hintText&&<div className={`rounded-lg p-4 mb-3 text-sm ${hintStyle}`}><span className='font-semibold mr-2'>Hint {hintLevel} of 3:</span>{hintText}</div>}
          {hintError&&<p className='text-red-400 text-xs mb-2'>{hintError}</p>}
          {hintLevel<3?(<button className='btn-ghost text-amber-400 border-amber-500/30 hover:border-amber-400 text-sm' onClick={requestHint} disabled={hintLoading}>{hintLoading?'Loading hint…':`💡 Get Hint ${hintLevel+1} of 3`}</button>)
          :(<p className='text-muted text-xs'>No more hints available.</p>)}
        </div>
      )}

      {submitError&&<div className='rounded-lg px-4 py-2.5 mb-3 bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs'>{submitError}</div>}

      {/* Feedback */}
      {feedback&&(
        <div className={`rounded-lg p-5 mb-6 ${feedback.is_correct?'border-l-4 border-green-500 bg-green-500/5':'border-l-4 border-red-500 bg-red-500/5'}`}>
          <p className={`font-semibold mb-1 ${feedback.is_correct?'text-green-400':'text-red-400'}`}>{feedback.is_correct?'✓ Correct!':'✗ Incorrect'}</p>
          {feedback.feedback_text&&<p className='text-sm text-muted leading-relaxed'>{feedback.feedback_text}</p>}
          {pointsJustEarned>0&&<p className='text-xs text-teal mt-2'>+{pointsJustEarned} points earned</p>}
          {feedback.new_mastery_prob!==undefined&&<p className='text-xs text-muted mt-1'>Mastery: <span className='text-teal stat-number'>{(feedback.new_mastery_prob*100).toFixed(1)}%</span></p>}
          {feedback.fcl_changed&&<p className='text-xs text-green-400 mt-1'>🧠 FCL advanced to {feedback.new_fcl}!</p>}
          <p className='text-xs text-muted mt-3 pt-3 border-t border-border/50'>Question {questionNum+1} of {QUIZ_LENGTH} — {QUIZ_LENGTH-questionNum-1>0?`${QUIZ_LENGTH-questionNum-1} remaining`:'Last question!'}</p>
        </div>
      )}

      <div className='flex gap-3 flex-wrap'>
        {feedback&&<button className='btn-primary' onClick={handleNext}>{questionNum+1>=QUIZ_LENGTH?'See Results 🏆':'Next Question →'}</button>}
        <button className={`btn-ghost text-sm flex items-center gap-2 ${showTutor?'border-teal/40 text-teal':''}`} onClick={openTutor}>
          ◈ Ask AI Tutor {stats.tutorConsultations>0&&<span className='badge-teal text-xs'>{stats.tutorConsultations}</span>}
        </button>
        <button className='btn-ghost text-sm' onClick={()=>navigate('/dashboard')}>← Dashboard</button>
      </div>
    </PageShell>
  );
}

