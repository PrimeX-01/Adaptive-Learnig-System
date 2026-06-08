from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import ActiveSession
from services.fcl_service import award_topic_points
from auth import get_current_student
from pydantic import BaseModel
from datetime import datetime, timezone

router = APIRouter(prefix='/api/session', tags=['Session'])

class StartSessionRequest(BaseModel):
    session_type: str   # 'tutor' or 'library'
    topic_id: str
    subject_id: int

class HeartbeatRequest(BaseModel):
    session_id: int

def end_session_internal(session: ActiveSession, db: Session):
    now = datetime.now(timezone.utc)
    if not session.ended:
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

@router.post('/start')
def start_session(req: StartSessionRequest, db: Session = Depends(get_db),
                  current_user = Depends(get_current_student)):
    # End any open session of the same type (prevents duplicates)
    existing = db.query(ActiveSession).filter(
        ActiveSession.student_id == current_user.id,
        ActiveSession.session_type == req.session_type,
        ActiveSession.ended == False
    ).first()
    if existing:
        end_session_internal(existing, db)

    new_session = ActiveSession(
        student_id=current_user.id,
        session_type=req.session_type,
        topic_id=req.topic_id,
        subject_id=req.subject_id,
        start_time=datetime.now(timezone.utc),
        last_heartbeat=datetime.now(timezone.utc),
        total_seconds=0
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return {'session_id': new_session.id}

@router.post('/heartbeat')
def heartbeat(req: HeartbeatRequest, db: Session = Depends(get_db),
              current_user = Depends(get_current_student)):
    session = db.query(ActiveSession).filter(
        ActiveSession.id == req.session_id,
        ActiveSession.student_id == current_user.id,
        ActiveSession.ended == False
    ).first()
    if not session:
        raise HTTPException(404, 'Active session not found')
    now = datetime.now(timezone.utc)
    elapsed = (now - session.last_heartbeat).total_seconds()
    if elapsed > 0:
        session.total_seconds += elapsed
    session.last_heartbeat = now
    db.commit()
    return {'status': 'ok'}

@router.post('/end')
def end_session(req: HeartbeatRequest, db: Session = Depends(get_db),
                current_user = Depends(get_current_student)):
    session = db.query(ActiveSession).filter(
        ActiveSession.id == req.session_id,
        ActiveSession.student_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(404, 'Session not found')
    end_session_internal(session, db)
    return {'status': 'ended', 'points_awarded': (session.total_seconds // 600) if session.total_seconds else 0}