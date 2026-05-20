from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from db.database import get_db
from auth import get_current_student
from services.style_service import (get_all_subject_styles, set_subject_style,
                                     set_overall_style, log_interaction,
                                     run_detection_for_all_subjects, detect_and_update_style)

router = APIRouter()

class StyleUpdateRequest(BaseModel):
    style:      str
    subject_id: Optional[int] = None  # None = update overall style

class InteractionLogRequest(BaseModel):
    student_id: int
    subject_id: int
    modality:   str   # visual | auditory | reading | kinesthetic
    source:     str   # quiz | tutor | library | hint

@router.get('/{student_id}')
def get_styles(student_id: int, db: Session = Depends(get_db),
               current_user = Depends(get_current_student)):
    """Get per-subject learning styles for a student. Used by dashboard."""
    return get_all_subject_styles(student_id, db)

@router.post('/{student_id}/update')
def update_style(student_id: int, body: StyleUpdateRequest,
                 db: Session = Depends(get_db),
                 current_user = Depends(get_current_student)):
    """Manually update learning style (overall or per-subject)."""
    if body.subject_id:
        set_subject_style(student_id, body.subject_id, body.style,
                          auto_detected=False, confidence=1.0, db=db)
        return {'message': f'Subject style updated to {body.style}'}
    else:
        set_overall_style(student_id, body.style, db)
        return {'message': f'Overall style updated to {body.style}'}

@router.post('/log-interaction')
def log_style_interaction(body: InteractionLogRequest,
                           db: Session = Depends(get_db),
                           current_user = Depends(get_current_student)):
    """Log a single learning interaction for adaptive detection."""
    log_interaction(body.student_id, body.subject_id, body.modality, body.source, db)
    db.commit()
    return {'status': 'logged'}

@router.post('/{student_id}/detect')
def run_detection(student_id: int, db: Session = Depends(get_db),
                  current_user = Depends(get_current_student)):
    """Run adaptive style detection across all subjects for a student."""
    results = run_detection_for_all_subjects(student_id, db)
    return {'results': results}

@router.post('/{student_id}/detect/{subject_id}')
def detect_subject(student_id: int, subject_id: int,
                   db: Session = Depends(get_db),
                   current_user = Depends(get_current_student)):
    """Run adaptive detection for one subject."""
    return detect_and_update_style(student_id, subject_id, db)
