from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import ConversationSession
from services.llm_service import generate_explanation
from auth import get_current_student
from pydantic import BaseModel

router = APIRouter()

class NewSessionRequest(BaseModel):
    student_id: int
    subject_id: int = None

@router.post('/new-session')
def new_session(req: NewSessionRequest, db: Session=Depends(get_db),
                current_user=Depends(get_current_student)):
    session = ConversationSession(student_id=req.student_id, subject_id=req.subject_id)
    db.add(session); db.commit()
    return {'session_id': session.id}

class ChatRequest(BaseModel):
    session_id: int
    student_id: int
    message:    str
    topic:      str
    fcl_level:  int
    learning_style: str = 'reading'   # <-- ADDED

@router.post('/message')
def chat_message(req: ChatRequest, request: Request,
                 db: Session=Depends(get_db),
                 current_user=Depends(get_current_student)):
    result = generate_explanation(
        session_id=req.session_id,
        student_id=req.student_id,
        user_message=req.message,
        topic=req.topic,
        fcl_level=req.fcl_level,
        app_state=request.app.state,
        db=db,
        learning_style=req.learning_style   # <-- PASS IT
    )
    return result