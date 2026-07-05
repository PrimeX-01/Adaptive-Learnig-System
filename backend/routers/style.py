from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from db.database import get_db
from auth import get_current_student
from services.style_service import (
    get_all_subject_styles, set_subject_style,
    set_overall_style, log_interaction_and_commit,
    run_detection_for_all_subjects, detect_and_update_style,
    get_vark_scores, update_vark_scores,
    log_interaction,
)

router = APIRouter()


# ══════════════════════════════════════════════════════════════════
#  SCHEMAS
# ══════════════════════════════════════════════════════════════════

class StyleUpdateRequest(BaseModel):
    style:      str
    subject_id: Optional[int] = None  # None = update overall style

class InteractionLogRequest(BaseModel):
    student_id: int
    subject_id: int
    modality:   str   # visual | auditory | reading | kinesthetic
    source:     str   # quiz | tutor | library | hint | audio_button


class AudioButtonLogRequest(BaseModel):
    """
    Sent from the frontend when a student clicks the audio/listen button
    on a tutor response.  This is a strong (3×-weighted) auditory signal.
    """
    student_id: int
    subject_id: Optional[int] = 1


# ══════════════════════════════════════════════════════════════════
#  EXISTING ENDPOINTS (unchanged)
# ══════════════════════════════════════════════════════════════════

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
        # Trigger a VARK recompute immediately so the change reflects at once
        update_vark_scores(student_id, db)
        return {'message': f'Subject style updated to {body.style}'}
    else:
        set_overall_style(student_id, body.style, db)
        update_vark_scores(student_id, db)
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


# ══════════════════════════════════════════════════════════════════
#  NEW: VARK SCORE ENDPOINTS
# ══════════════════════════════════════════════════════════════════

@router.get('/{student_id}/vark-scores')
def get_vark_score_endpoint(
    student_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_student),
):
    """
    Return the student's current four-dimensional VARK profile.
    Response: { v, a, r, k, total_interactions, dominant }

    If no profile exists yet (new student), seeds it from their
    registration self-report and returns immediately.

    Used by:
      - StudentDashboard.jsx  — VARK bar chart
      - StudentProfile.jsx    — learning style panel
    """
    scores = get_vark_scores(student_id, db)
    return {
        'v_score':            scores['v'],
        'a_score':            scores['a'],
        'r_score':            scores['r'],
        'k_score':            scores['k'],
        'total_interactions': scores.get('total_interactions', 0),
        'dominant':           scores.get('dominant', 'reading'),
        # Convenience: percentage dict the frontend chart can use directly
        'percentages': {
            'Visual':         scores['v'],
            'Auditory':       scores['a'],
            'Reading/Writing':scores['r'],
            'Kinesthetic':    scores['k'],
        },
    }


@router.post('/{student_id}/vark-scores/recompute')
def recompute_vark(
    student_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_student),
):
    """
    Manually trigger a VARK recompute for a student.
    Normally the scheduler does this weekly, but teachers or the student
    profile page can call this to get an immediate update.
    """
    scores = update_vark_scores(student_id, db)
    return {
        'status':             'recomputed',
        'v_score':            scores['v'],
        'a_score':            scores['a'],
        'r_score':            scores['r'],
        'k_score':            scores['k'],
        'total_interactions': scores.get('total_interactions', 0),
        'dominant':           scores.get('dominant', 'reading'),
    }


@router.post('/log-audio-button')
def log_audio_button_click(
    body: AudioButtonLogRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_student),
):
    """
    Called by TutorChat.jsx / AudioPlayer.jsx when the student clicks
    the listen/play button on a tutor response.

    This is weighted 3× in the VARK scoring formula because clicking
    to listen is an unambiguous auditory preference signal.
    We achieve the higher weight by logging 3 separate interaction rows.
    """
    for _ in range(3):
        log_interaction(
            student_id = body.student_id,
            subject_id = body.subject_id or 1,
            modality   = 'auditory',
            source     = 'audio_button',
            db         = db,
        )
    db.commit()
    return {'status': 'logged', 'signal': 'auditory', 'weight': 3}