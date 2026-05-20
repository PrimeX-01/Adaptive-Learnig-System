from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import active_sessions
from services.fcl_service import award_topic_points
from auth import get_current_student
from pydantic import BaseModel
from datetime import datetime, timedelta

router = APIRouter(prefix='/api/session', tags=['Session'])

class StartSessionRequest(BaseModel):
    session_type: str   # 'tutor' or 'library'
    topic_id: str
    subject_id: int

class HeartbeatRequest(BaseModel):
    session_id: int

@router.post('/start')
def start_session(req: StartSessionRequest, db: Session = Depends(get_db),
                  current_user = Depends(get_current_student)):
    # End any open sessions of the same type (optional)
    active = db.query(active_sessions).filter(
        active_sessions.student_id == current_user.id,
        active_sessions.session_type == req.session_type,
        active_sessions.ended == False
    ).first()
    if active:
        # auto-close previous session (e.g., browser refresh)
        end_session_internal(active, db)
    session = active_sessions(
        student_id=current_user.id,
        session_type=req.session_type,
        topic_id=req.topic_id,
        subject_id=req.subject_id,
        start_time=datetime.utcnow(),
        last_heartbeat=datetime.utcnow(),
        total_seconds=0
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {'session_id': session.id}

@router.post('/heartbeat')
def heartbeat(req: HeartbeatRequest, db: Session = Depends(get_db),
              current_user = Depends(get_current_student)):
    session = db.query(active_sessions).filter(
        active_sessions.id == req.session_id,
        active_sessions.student_id == current_user.id,
        active_sessions.ended == False
    ).first()
    if not session:
        raise HTTPException(404, 'Active session not found')
    now = datetime.utcnow()
    elapsed = (now - session.last_heartbeat).total_seconds()
    if elapsed > 0:
        session.total_seconds += elapsed
    session.last_heartbeat = now
    db.commit()
    return {'status': 'ok'}

def end_session_internal(session: active_sessions, db: Session):
    now = datetime.utcnow()
    if not session.ended:
        # Add final elapsed time
        elapsed = (now - session.last_heartbeat).total_seconds()
        if elapsed > 0:
            session.total_seconds += elapsed
        session.ended = True
        db.commit()

        # Award points: 1 point per 10 full minutes
        minutes = int(session.total_seconds // 60)
        points_to_award = minutes // 10
        if points_to_award > 0:
            award_topic_points(
                student_id=session.student_id,
                subject_id=session.subject_id,
                topic_id=session.topic_id,
                points=points_to_award,
                reason=f'{session.session_type}_session_time',
                source_id=str(session.id),
                db=db
            )

@router.post('/end')
def end_session(req: HeartbeatRequest, db: Session = Depends(get_db),
                current_user = Depends(get_current_student)):
    session = db.query(active_sessions).filter(
        active_sessions.id == req.session_id,
        active_sessions.student_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(404, 'Session not found')
    end_session_internal(session, db)
    return {'status': 'ended', 'points_awarded': (session.total_seconds // 600) if session.total_seconds else 0}