from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing   import Optional
from datetime import datetime

from services.llm_service import generate_explanation
from db.database import get_db
from db.models   import (ConversationSession, ConversationMessage,
                          Student, Subject, StudentSubject)
from auth import get_current_student

router = APIRouter()


# ══════════════════════════════════════════════════════════════════
#  SCHEMAS
# ══════════════════════════════════════════════════════════════════

class NewSessionRequest(BaseModel):
    student_id: int
    subject_id: Optional[int] = None

class ChatRequest(BaseModel):
    session_id: int
    student_id: int
    message:    str
    topic:      str
    fcl_level:  int
    learning_style: str = 'reading'

class ChatMessageRequest(BaseModel):
    session_id:     int
    student_id:     int
    message:        str
    topic:          str
    fcl_level:      int
    learning_style: Optional[str] = 'reading'
    subject_id:     Optional[int] = None
    grade:          Optional[int] = None

class SessionEndRequest(BaseModel):
    session_id:      int
    student_id:      int
    subject_id:      int
    exchange_count:  int
    topic_id:        Optional[str] = None
    duration_minutes:Optional[int] = None

class SimpleChatRequest(BaseModel):
    message: str
    subject_id: Optional[int] = None


# ══════════════════════════════════════════════════════════════════
#  NEW SESSION
# ══════════════════════════════════════════════════════════════════

@router.post('/new-session')
def new_session(req: NewSessionRequest, db: Session=Depends(get_db),
                current_user=Depends(get_current_student)):
    session = ConversationSession(
        student_id=req.student_id,
        subject_id=req.subject_id
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {'session_id': session.id}


# ══════════════════════════════════════════════════════════════════
#  SEND MESSAGE (full schema) – updated to match new generate_explanation
# ══════════════════════════════════════════════════════════════════

@router.post('/message')
async def send_message(req: ChatMessageRequest,
                       db: Session = Depends(get_db),
                       current_user = Depends(get_current_student)):
    session = db.query(ConversationSession).filter(
        ConversationSession.id == req.session_id
    ).first()
    if not session:
        raise HTTPException(404, 'Session not found')
    grade = req.grade
    if not grade:
        student = db.query(Student).filter(Student.id == req.student_id).first()
        grade = student.grade if student else 1
    # Get real FCL (but we trust the passed fcl_level for simplicity)
    real_fcl = req.fcl_level
    if req.subject_id:
        try:
            from services.points_service import get_topic_fcl
            real_fcl = get_topic_fcl(req.student_id, req.subject_id, req.topic, db)
        except Exception:
            real_fcl = req.fcl_level
    # The new generate_explanation does not use subject_id or grade
    result = generate_explanation(
        session_id    = req.session_id,
        student_id    = req.student_id,
        user_message  = req.message,
        topic         = req.topic,
        fcl_level     = real_fcl,
        app_state     = None,
        db            = db,
        learning_style= req.learning_style or 'reading',
    )
    return result


# ══════════════════════════════════════════════════════════════════
#  SIMPLE CHAT (auto session, auto topic) – fixed
# ══════════════════════════════════════════════════════════════════

@router.post('/simple')
async def simple_chat(
    req: SimpleChatRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_student)
):
    student_id = current_user.id
    grade = current_user.grade or 1  # not used in generate_explanation, but kept for context
    
    # Get or create active session
    subject_id = req.subject_id
    session = db.query(ConversationSession).filter(
        ConversationSession.student_id == student_id,
        ConversationSession.subject_id == subject_id if subject_id else None,
        ConversationSession.ended_at == None
    ).first()
    if not session:
        session = ConversationSession(
            student_id=student_id,
            subject_id=subject_id
        )
        db.add(session)
        db.commit()
        db.refresh(session)
    
    # Simple topic detection
    msg_lower = req.message.lower()
    topic = "general"
    if any(kw in msg_lower for kw in ["quadratic", "equation", "algebra", "factor", "polynomial"]):
        topic = "mathematics_algebra"
    elif any(kw in msg_lower for kw in ["photosynthesis", "plant", "chlorophyll", "cell"]):
        topic = "science_biology"
    elif any(kw in msg_lower for kw in ["fraction", "decimal", "percent", "ratio"]):
        topic = "mathematics_arithmetic"
    elif any(kw in msg_lower for kw in ["gravity", "force", "motion", "newton"]):
        topic = "science_physics"
    elif any(kw in msg_lower for kw in ["shakespeare", "poem", "literature"]):
        topic = "english_literature"
    
    # Get FCL
    fcl_level = 5
    if subject_id:
        try:
            from services.points_service import get_subject_fcl
            fcl_level = int(get_subject_fcl(student_id, subject_id, db))
        except Exception:
            fcl_level = 5
    else:
        try:
            from services.points_service import get_overall_fcl
            fcl_level = int(get_overall_fcl(student_id, db))
        except Exception:
            fcl_level = 5
    
    # Get learning style
    learning_style = "reading"
    try:
        from db.models import StudentPreference
        pref = db.query(StudentPreference).filter(StudentPreference.student_id == student_id).first()
        if pref and pref.preferred_learning_style:
            learning_style = pref.preferred_learning_style
    except Exception:
        pass
    
    # Call LLM (without subject_id and grade)
    from services.llm_service import generate_explanation
    result = generate_explanation(
        session_id=session.id,
        student_id=student_id,
        user_message=req.message,
        topic=topic,
        fcl_level=fcl_level,
        app_state=None,
        db=db,
        learning_style=learning_style,
    )
    
    # Ensure the result contains a 'response' field
    if isinstance(result, dict):
        if 'response' not in result:
            result['response'] = result.get('reply', 'No response generated.')
    else:
        result = {'response': str(result)}
    
    return result


# ══════════════════════════════════════════════════════════════════
#  STREAM (alias)
# ══════════════════════════════════════════════════════════════════

@router.post('/stream')
async def chat_stream(req: SimpleChatRequest,
                      db: Session = Depends(get_db),
                      current_user = Depends(get_current_student)):
    return await simple_chat(req, db, current_user)


# ══════════════════════════════════════════════════════════════════
#  HISTORY (all sessions)
# ══════════════════════════════════════════════════════════════════

@router.get('/history')
def get_chat_history(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_student),
):
    student_id = current_user.id
    sessions = db.query(ConversationSession).filter(
        ConversationSession.student_id == student_id
    ).order_by(ConversationSession.started_at.desc()).all()
    result = []
    for s in sessions:
        messages = db.query(ConversationMessage).filter(
            ConversationMessage.session_id == s.id
        ).order_by(ConversationMessage.created_at).all()
        result.append({
            'session_id': s.id,
            'subject_id': s.subject_id,
            'started_at': s.started_at.isoformat() if s.started_at else None,
            'ended_at': s.ended_at.isoformat() if s.ended_at else None,
            'messages': [
                {
                    'role': m.role,
                    'content': m.content,
                    'created_at': m.created_at.isoformat() if m.created_at else None,
                }
                for m in messages
            ]
        })
    return result


# ══════════════════════════════════════════════════════════════════
#  SESSION END
# ══════════════════════════════════════════════════════════════════

@router.post('/session-end')
def end_session(req: SessionEndRequest,
                db: Session = Depends(get_db),
                current_user = Depends(get_current_student)):
    if req.exchange_count < 3:
        return {'points_earned': 0, 'reason': 'Session too short (less than 3 exchanges)'}
    topic_id = req.topic_id
    if not topic_id:
        session = db.query(ConversationSession).filter(
            ConversationSession.id == req.session_id
        ).first()
        topic_id = session.topic_id if session else 'general'
    student = db.query(Student).filter(Student.id == req.student_id).first()
    subject = db.query(Subject).filter(Subject.id == req.subject_id).first()
    enrollment = db.query(StudentSubject).filter(
        StudentSubject.student_id == req.student_id,
        StudentSubject.subject_id == req.subject_id,
    ).first()
    teacher_id = enrollment.teacher_id if enrollment else None
    student_name = student.name if student else 'Student'
    subject_name = subject.name if subject else 'Subject'
    pts_result = {'points_awarded': 0}
    if req.duration_minutes and req.duration_minutes >= 10 and topic_id:
        try:
            from services.points_service import award_session_time_points
            pts_result = award_session_time_points(
                student_id = req.student_id,
                subject_id = req.subject_id,
                topic_id = topic_id,
                duration_minutes = req.duration_minutes,
                session_type = 'tutor',
                db = db,
            )
        except Exception as e:
            print(f'[Session end points error] {e}')
    try:
        session = db.query(ConversationSession).filter(
            ConversationSession.id == req.session_id
        ).first()
        if session and hasattr(session, 'ended_at'):
            session.ended_at = datetime.utcnow()
            db.commit()
    except Exception:
        pass
    return {
        'status': 'session_ended',
        'exchange_count': req.exchange_count,
        'duration_minutes': req.duration_minutes,
        'points_earned': pts_result.get('points_awarded', 0),
        'fcl_changed': pts_result.get('fcl_changed', False),
        'new_fcl': pts_result.get('new_fcl'),
    }


# ══════════════════════════════════════════════════════════════════
#  HISTORY BY SESSION ID
# ══════════════════════════════════════════════════════════════════

@router.get('/history/{session_id}')
def get_history(session_id: int,
                db: Session = Depends(get_db),
                current_user = Depends(get_current_student)):
    messages = db.query(ConversationMessage).filter(
        ConversationMessage.session_id == session_id
    ).order_by(ConversationMessage.created_at).all()
    return [
        {
            'role': m.role,
            'content': m.content,
            'created_at': m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]


# ══════════════════════════════════════════════════════════════════
#  STUDENT SESSIONS LIST
# ══════════════════════════════════════════════════════════════════

@router.get('/sessions/{student_id}')
def get_student_sessions(student_id: int,
                          db: Session = Depends(get_db),
                          current_user = Depends(get_current_student)):
    sessions = db.query(ConversationSession).filter(
        ConversationSession.student_id == student_id
    ).order_by(ConversationSession.created_at.desc()).limit(20).all()
    result = []
    for s in sessions:
        msg_count = db.query(ConversationMessage).filter(
            ConversationMessage.session_id == s.id
        ).count()
        subj = db.query(Subject).filter(Subject.id == s.subject_id).first() if s.subject_id else None
        result.append({
            'session_id': s.id,
            'subject_name': subj.name if subj else '—',
            'topic_id': s.topic_id,
            'message_count': msg_count,
            'created_at': s.created_at.isoformat() if s.created_at else None,
        })
    return result