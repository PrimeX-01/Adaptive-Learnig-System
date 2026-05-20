from sqlalchemy.orm import Session
from db.models import Student, Subject
from services.fcl_service import award_topic_points, get_topic_fcl, get_subject_fcl, get_overall_fcl
import logging

logger = logging.getLogger(__name__)

POINTS_PER_FCL = 1000  # every FCL level requires exactly 1000 points

def _points_needed_for_fcl(fcl: int) -> int:
    return POINTS_PER_FCL


# ================================================================
#  QUIZ POINT CALCULATION (5-point scale)
# ================================================================
def calculate_quiz_points(is_correct: bool, hints_used: int, tutor_consulted: bool) -> int:
    """
    - Correct, 0 hints, no tutor → 5
    - Correct, 1 hint            → 4
    - Correct, 2 hints           → 3
    - Correct, 3 hints           → 2
    - Correct + tutor consulted  → -1 additional
    - Wrong                      → 0
    """
    if not is_correct:
        return 0
    pts = 5 - hints_used
    if tutor_consulted:
        pts -= 1
    return max(0, pts)


# ================================================================
#  MAIN FUNCTION — called from quiz.py
# ================================================================
def process_quiz_answer_with_topic(student_id: int, subject_id: int, topic_id: str,
                                   is_correct: bool, hints_used: int,
                                   tutor_consulted: bool, question_id: str,
                                   teacher_id: int | None, student_name: str,
                                   subject_name: str, db: Session) -> dict:
    # 1. Calculate points earned this question
    points = calculate_quiz_points(is_correct, hints_used, tutor_consulted)

    # 2. Award points — fcl_service updates the topic record
    try:
        award_result = award_topic_points(
            student_id=student_id,
            subject_id=subject_id,
            topic_id=topic_id,
            points=points,
            reason='quiz_answer',
            source_id=question_id,
            db=db,
        )
    except Exception as e:
        logger.warning(f"award_topic_points failed: {e}")
        award_result = {}

    # 3. Get updated FCL levels
    try:
        topic_fcl = get_topic_fcl(student_id, subject_id, topic_id, db) or 1
    except Exception:
        topic_fcl = 1

    try:
        subject_fcl = get_subject_fcl(student_id, subject_id, db) or 1
    except Exception:
        subject_fcl = 1

    try:
        overall_fcl = get_overall_fcl(student_id, db) or 1
    except Exception:
        overall_fcl = 1

    # 4. Pull current_points and fcl_changed from award_result if available,
    #    otherwise fall back to safe defaults so Pydantic never gets None.
    current_points   = award_result.get('current_points')   if isinstance(award_result, dict) else None
    points_to_next   = award_result.get('points_to_next_fcl') if isinstance(award_result, dict) else None
    fcl_changed      = award_result.get('fcl_changed', False) if isinstance(award_result, dict) else False
    new_fcl          = award_result.get('new_fcl')           if isinstance(award_result, dict) else None

    # Guarantee integers — never return None to the caller
    if current_points is None:
        current_points = 0
    if points_to_next is None:
        # How many points remain until the next FCL level
        points_into_level = int(current_points) % POINTS_PER_FCL
        points_to_next = POINTS_PER_FCL - points_into_level

    return {
        'points_earned':      points,
        'current_points':     int(current_points),
        'points_to_next_fcl': int(points_to_next),
        'fcl_changed':        bool(fcl_changed),
        'old_fcl':            None,
        'new_fcl':            new_fcl,
        'overall_fcl':        overall_fcl,
        'subject_fcl':        subject_fcl,
    }


# ================================================================
#  Legacy stub — kept so old call sites don't crash
# ================================================================
def process_quiz_answer(student_id: int, subject_id: int,
                        is_correct: bool, hints_used: int,
                        tutor_consulted: bool, question_id: str,
                        teacher_id: int | None, student_name: str,
                        subject_name: str, db: Session) -> dict:
    raise NotImplementedError(
        "Call process_quiz_answer_with_topic instead — topic_id is required."
    )


# ================================================================
#  Helper
# ================================================================
def _build_reason(is_correct: bool, hints_used: int, tutor_consulted: bool) -> str:
    if not is_correct:
        return 'wrong_answer'
    if tutor_consulted:
        return f'correct_tutor_{hints_used}_hints'
    return f'correct_{hints_used}_hints'


# ================================================================
#  Library / tutor session stubs
# ================================================================
def award_library_session_points(student_id: int, subject_id: int, content_id: int,
                                 duration_minutes: int, db: Session) -> dict:
    logger.warning(f"award_library_session_points not yet implemented — {duration_minutes} min")
    return {'points_earned': 0}


def award_tutor_session_points(student_id: int, subject_id: int, session_id: int,
                               exchange_count: int, teacher_id: int | None,
                               student_name: str, subject_name: str, db: Session) -> dict:
    logger.warning(f"award_tutor_session_points not yet implemented — {exchange_count} exchanges")
    return {'points_earned': 0, 'fcl_changed': False, 'new_fcl': None}