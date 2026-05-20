from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import HintRequest as HintRequestModel
from auth import get_current_student
from services.llm_service import generate_hint
from pydantic import BaseModel

router = APIRouter()

class HintRecordRequest(BaseModel):
    student_id:  int
    question_id: str
    hint_level:  int
    subject_id:  int = None

# ── Record only (kept for compatibility) ──────────────────────────
@router.post('/request')
def record_hint(req: HintRecordRequest, db: Session = Depends(get_db),
                current_user = Depends(get_current_student)):
    if req.hint_level not in (1, 2, 3):
        raise HTTPException(400, 'hint_level must be 1, 2, or 3')
    db.add(HintRequestModel(
        student_id=req.student_id, subject_id=req.subject_id,
        question_id=req.question_id, hint_level_requested=req.hint_level
    ))
    db.commit()
    return {'status': 'recorded', 'hint_level': req.hint_level}

# ── Generate hint AND record it ───────────────────────────────────
@router.get('/{question_id}/{level}')
def get_hint(question_id: str, level: int, request: Request,
             topic: str = 'general', fcl_level: int = 6, student_id: int = 0,
             db: Session = Depends(get_db),
             current_user = Depends(get_current_student)):

    if level not in (1, 2, 3):
        raise HTTPException(400, 'Hint level must be 1, 2, or 3')

    # Generate hint via Groq LLM
    hint = generate_hint(
        f'Question {question_id}', '', topic, fcl_level, level,
        request.app.state, db, student_id
    )

    # ✅ FIXED — now also records the hint request in the database
    if student_id:
        db.add(HintRequestModel(
            student_id=student_id,
            question_id=question_id,
            hint_level_requested=level,
        ))
        db.commit()

    return {'hint_text': hint, 'hint_level': level}