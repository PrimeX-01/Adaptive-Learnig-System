from sqlalchemy.orm import Session
from sqlalchemy import text
from db.models import (Notification, Student, Subject,
                        StudentSubject, Assessment, LibraryContent, ComprehensionEvent)
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

FCL_MAX        = 20
POINTS_PER_FCL = 1000   # advance when total_points crosses next multiple of 1000


# ══════════════════════════════════════════════════════════════════
#  GRADE → INITIAL FCL
# ══════════════════════════════════════════════════════════════════

def grade_to_initial_fcl(grade: int) -> int:
    """
    Map a student's school grade to their starting FCL (1–20).
    Mirrors the frontend gradeToFCL but on the 1–20 scale.
    """
    if not grade or grade < 1: return 5
    if grade <= 2:   return 1
    if grade <= 4:   return 2
    if grade <= 6:   return 4
    if grade <= 7:   return 5
    if grade <= 9:   return 7
    if grade <= 10:  return 8
    if grade <= 12:  return 9
    if grade <= 13:  return 11   # Undergrad L1
    if grade <= 15:  return 12   # Undergrad L2–L3
    if grade <= 17:  return 14   # Undergrad L4–L5
    if grade == 18:  return 17   # Masters
    return 19                    # PhD


# ══════════════════════════════════════════════════════════════════
#  POINT CALCULATION — pure functions
# ══════════════════════════════════════════════════════════════════

def calculate_quiz_points(is_correct: bool,
                           hints_used: int,
                           tutor_consulted: bool) -> int:
    """Points for a single quiz answer."""
    if not is_correct:
        return 0   # No points for wrong answers — no punishment, no reward

    if tutor_consulted and hints_used >= 3:
        return 1
    if hints_used == 0:
        return 5
    elif hints_used == 1:
        return 4
    elif hints_used == 2:
        return 3
    else:  # 3 hints, no tutor
        return 2


def fcl_from_points(total_points: int) -> int:
    """FCL is simply the floor of total_points / 1000, capped at 20."""
    return min(FCL_MAX, total_points // POINTS_PER_FCL)


def points_within_level(total_points: int) -> int:
    """Points earned within the current FCL level (0–999)."""
    return total_points % POINTS_PER_FCL


def points_to_next_fcl(total_points: int) -> int:
    """How many more points needed to reach the next FCL level."""
    current = fcl_from_points(total_points)
    if current >= FCL_MAX:
        return 0
    next_threshold = (current + 1) * POINTS_PER_FCL
    return next_threshold - total_points


# ══════════════════════════════════════════════════════════════════
#  DATABASE — GET / INIT TOPIC FCL ROW
# ══════════════════════════════════════════════════════════════════

def _get_or_init_topic_row(student_id: int, subject_id: int,
                            topic_id: str, db: Session,
                            initial_fcl: int = None) -> dict:
    """
    Get or create a topic_fcl row.
    If creating, initialise total_points = initial_fcl × 1000.
    Returns the row as a plain dict.
    """
    result = db.execute(text(
        'SELECT id, total_points, current_fcl FROM topic_fcl '
        'WHERE student_id=:sid AND subject_id=:subid AND topic_id=:tid'
    ), {'sid': student_id, 'subid': subject_id, 'tid': topic_id}).fetchone()

    if result:
        return {'id': result[0], 'total_points': result[1], 'current_fcl': result[2]}

    # First time this student touches this topic — initialise
    if initial_fcl is None:
        student = db.query(Student).filter(Student.id == student_id).first()
        initial_fcl = grade_to_initial_fcl(student.grade if student else 1)

    starting_points = initial_fcl * POINTS_PER_FCL
    db.execute(text(
        'INSERT INTO topic_fcl (student_id, subject_id, topic_id, total_points, current_fcl) '
        'VALUES (:sid, :subid, :tid, :pts, :fcl) '
        'ON CONFLICT (student_id, subject_id, topic_id) DO NOTHING'
    ), {'sid': student_id, 'subid': subject_id, 'tid': topic_id,
        'pts': starting_points, 'fcl': initial_fcl})
    db.flush()

    return {'id': None, 'total_points': starting_points, 'current_fcl': initial_fcl}


# ══════════════════════════════════════════════════════════════════
#  AWARD POINTS (core function)
# ══════════════════════════════════════════════════════════════════

def award_topic_points(student_id: int, subject_id: int,
                        topic_id: str, points: int,
                        reason: str, db: Session,
                        source_id: str = None,
                        initial_fcl: int = None,
                        session_id: int = None) -> dict:

    if points <= 0:
        return _empty_result(student_id, subject_id, topic_id, db)

    row     = _get_or_init_topic_row(student_id, subject_id, topic_id, db, initial_fcl)
    old_fcl = row['current_fcl']
    new_total = row['total_points'] + points
    new_fcl   = fcl_from_points(new_total)

    # Update topic_fcl
    db.execute(text(
        'UPDATE topic_fcl SET total_points=:pts, current_fcl=:fcl, updated_at=now() '
        'WHERE student_id=:sid AND subject_id=:subid AND topic_id=:tid'
    ), {'pts': new_total, 'fcl': new_fcl,
        'sid': student_id, 'subid': subject_id, 'tid': topic_id})

    # Log transaction
    db.execute(text(
        'INSERT INTO topic_point_transactions '
        '(student_id, subject_id, topic_id, points, reason, source_id) '
        'VALUES (:sid, :subid, :tid, :pts, :reason, :src)'
    ), {'sid': student_id, 'subid': subject_id, 'tid': topic_id,
        'pts': points, 'reason': reason, 'src': source_id})

    # If FCL advanced, create a comprehension event
    if new_fcl > old_fcl:
        event_title = f"FCL Advanced to Level {new_fcl}"
        event_message = f"You've advanced from FCL {old_fcl} to {new_fcl} in {topic_id.replace('_', ' ')}! Questions will now be more challenging."
        event = ComprehensionEvent(
            student_id=student_id,
            session_id=session_id,
            event_type='FCL_ADVANCE',
            title=event_title,
            message=event_message,
            tier_before=old_fcl,
            tier_after=new_fcl,
            trigger=f'Points earned: +{points}'
        )
        db.add(event)

    db.commit()

    return {
        'points_awarded':      points,
        'total_points':        new_total,
        'old_fcl':             old_fcl,
        'new_fcl':             new_fcl,
        'fcl_changed':         new_fcl > old_fcl,
        'levels_gained':       new_fcl - old_fcl,
        'points_within_level': points_within_level(new_total),
        'points_to_next':      points_to_next_fcl(new_total),
    }


def _empty_result(student_id, subject_id, topic_id, db) -> dict:
    row = _get_or_init_topic_row(student_id, subject_id, topic_id, db)
    tp  = row['total_points']
    return {
        'points_awarded':      0,
        'total_points':        tp,
        'old_fcl':             row['current_fcl'],
        'new_fcl':             row['current_fcl'],
        'fcl_changed':         False,
        'levels_gained':       0,
        'points_within_level': points_within_level(tp),
        'points_to_next':      points_to_next_fcl(tp),
    }


# ══════════════════════════════════════════════════════════════════
#  GET FCL VALUES (computed on demand)
# ══════════════════════════════════════════════════════════════════

def get_topic_fcl(student_id: int, subject_id: int,
                   topic_id: str, db: Session) -> int:
    """Current FCL for a specific topic."""
    row = db.execute(text(
        'SELECT total_points FROM topic_fcl '
        'WHERE student_id=:sid AND subject_id=:subid AND topic_id=:tid'
    ), {'sid': student_id, 'subid': subject_id, 'tid': topic_id}).fetchone()
    if not row:
        student = db.query(Student).filter(Student.id == student_id).first()
        return grade_to_initial_fcl(student.grade if student else 1)
    return fcl_from_points(row[0])


def get_subject_fcl(student_id: int, subject_id: int,
                     db: Session) -> float:
    """
    Subject FCL = average of topic FCLs in that subject.
    Computed on demand, not stored.
    """
    rows = db.execute(text(
        'SELECT total_points FROM topic_fcl '
        'WHERE student_id=:sid AND subject_id=:subid'
    ), {'sid': student_id, 'subid': subject_id}).fetchall()

    if not rows:
        student = db.query(Student).filter(Student.id == student_id).first()
        return float(grade_to_initial_fcl(student.grade if student else 1))

    fcl_values = [fcl_from_points(r[0]) for r in rows]
    return round(sum(fcl_values) / len(fcl_values), 1)


def get_overall_fcl(student_id: int, db: Session) -> float:
    """
    Overall FCL = average of all subject FCLs.
    Computed on demand from topic_fcl rows.
    """
    enrollments = db.query(StudentSubject).filter(
        StudentSubject.student_id == student_id
    ).all()

    if not enrollments:
        student = db.query(Student).filter(Student.id == student_id).first()
        return float(grade_to_initial_fcl(student.grade if student else 1))

    subject_fcls = [
        get_subject_fcl(student_id, e.subject_id, db)
        for e in enrollments
    ]
    return round(sum(subject_fcls) / len(subject_fcls), 1)


def get_student_points_summary(student_id: int, db: Session) -> list:
    """
    Returns FCL + points data for all enrolled subjects.
    Used by dashboard and progress pages.
    """
    enrollments = db.query(StudentSubject).filter(
        StudentSubject.student_id == student_id
    ).all()

    result = []
    for e in enrollments:
        subj = db.query(Subject).filter(Subject.id == e.subject_id).first()
        rows = db.execute(text(
            'SELECT topic_id, total_points, current_fcl FROM topic_fcl '
            'WHERE student_id=:sid AND subject_id=:subid'
        ), {'sid': student_id, 'subid': e.subject_id}).fetchall()

        topic_fcls = [fcl_from_points(r[1]) for r in rows] if rows else []
        sub_fcl    = round(sum(topic_fcls)/len(topic_fcls), 1) if topic_fcls else get_subject_fcl(student_id, e.subject_id, db)
        total_pts  = sum(r[1] for r in rows) if rows else 0

        result.append({
            'subject_id':    e.subject_id,
            'subject_name':  subj.name if subj else '—',
            'subject_code':  subj.code if subj else '—',
            'subject_fcl':   sub_fcl,
            'total_points':  total_pts,
            'topics':        [
                {
                    'topic_id':            r[0],
                    'total_points':        r[1],
                    'current_fcl':         r[2],
                    'points_within_level': points_within_level(r[1]),
                    'points_to_next':      points_to_next_fcl(r[1]),
                }
                for r in rows
            ],
        })
    return result


# ══════════════════════════════════════════════════════════════════
#  PROCESS QUIZ ANSWER (main entry point from quiz.py)
# ══════════════════════════════════════════════════════════════════

def process_quiz_answer(student_id: int, subject_id: int,
                         topic_id: str, is_correct: bool,
                         hints_used: int, tutor_consulted: bool,
                         question_id: str,
                         teacher_id: int | None,
                         student_name: str,
                         subject_name: str,
                         db: Session,
                         session_id: int = None) -> dict:
    """
    Main function called on every quiz answer submission.
    1. Calculates points
    2. Awards points to topic (and logs FCL advance event)
    3. Notifies student + teacher (already in award_topic_points)
    4. Checks struggling student thresholds → notifies teacher and logs event
    Returns full result dict for API response.
    """
    pts = calculate_quiz_points(is_correct, hints_used, tutor_consulted)

    result = award_topic_points(
        student_id  = student_id,
        subject_id  = subject_id,
        topic_id    = topic_id,
        points      = pts,
        reason      = _build_reason(is_correct, hints_used, tutor_consulted),
        source_id   = question_id,
        db          = db,
        session_id  = session_id,
    )

    # Check for struggling student (also logs an event)
    check_struggling_student(
        student_id=student_id, subject_id=subject_id, topic_id=topic_id,
        teacher_id=teacher_id, student_name=student_name,
        subject_name=subject_name, db=db, session_id=session_id,
    )

    return {
        'points_earned':       pts,
        'total_points':        result['total_points'],
        'topic_fcl':           result['new_fcl'],
        'fcl_changed':         result['fcl_changed'],
        'old_fcl':             result['old_fcl'],
        'new_fcl':             result['new_fcl'],
        'points_within_level': result['points_within_level'],
        'points_to_next_fcl':  result['points_to_next'],
        'subject_fcl':         get_subject_fcl(student_id, subject_id, db),
        'overall_fcl':         get_overall_fcl(student_id, db),
    }


# ══════════════════════════════════════════════════════════════════
#  SESSION TIME POINTS (tutor + library)
# ══════════════════════════════════════════════════════════════════

def award_session_time_points(student_id: int, subject_id: int,
                               topic_id: str, duration_minutes: int,
                               session_type: str,   # 'tutor' | 'library'
                               db: Session,
                               session_id: int = None) -> dict:
    """
    Award 1 point per 10-minute block of session time.
    Called when a session ends.
    """
    blocks = duration_minutes // 10   # floor — only full 10-min blocks count
    if blocks <= 0:
        return {'points_awarded': 0}

    result = award_topic_points(
        student_id = student_id,
        subject_id = subject_id,
        topic_id   = topic_id,
        points     = blocks,
        reason     = f'{session_type}_session_{duration_minutes}min',
        db         = db,
        session_id = session_id,
    )
    return result


# ══════════════════════════════════════════════════════════════════
#  TEACHER MANUAL POINT AWARD
# ══════════════════════════════════════════════════════════════════

def award_teacher_points(teacher_id: int, student_id: int,
                          subject_id: int, topic_id: str,
                          points: int, reason: str,
                          db: Session,
                          session_id: int = None) -> dict:
    """Teacher manually awards points to a student on a topic."""
    if points <= 0:
        return {'error': 'Points must be positive'}

    result = award_topic_points(
        student_id = student_id,
        subject_id = subject_id,
        topic_id   = topic_id,
        points     = points,
        reason     = f'teacher_award: {reason}',
        source_id  = f'teacher_{teacher_id}',
        db         = db,
        session_id = session_id,
    )

    # Log in teacher_point_awards if table exists
    try:
        db.execute(text(
            'INSERT INTO teacher_point_awards (teacher_id, student_id, subject_id, points, reason) '
            'VALUES (:tid, :sid, :subid, :pts, :reason)'
        ), {'tid': teacher_id, 'sid': student_id, 'subid': subject_id,
            'pts': points, 'reason': reason})
        db.commit()
    except Exception:
        pass

    return result


# ══════════════════════════════════════════════════════════════════
#  LIBRARY SESSION POINTS
# ══════════════════════════════════════════════════════════════════

def award_library_session_points(student_id: int, content_id: int,
                                  duration_minutes: int, ai_tutor_used: bool,
                                  db: Session,
                                  session_id: int = None) -> dict:
    """
    Award points to a student for completing a library session.
    Fetches the library content to determine subject_id.
    Uses a generic topic_id = 'library_general' (or you can parse from content tags).
    Award formula: 1 point per 10 minutes + 5 bonus if AI tutor used.
    """
    # Fetch library content to get subject_id
    content = db.query(LibraryContent).filter(LibraryContent.id == content_id).first()
    if not content:
        logger.warning(f"Library content {content_id} not found for points award")
        return {'points_earned': 0, 'error': 'Content not found'}

    subject_id = content.subject_id
    # Ideally you'd have a topic tag, but for simplicity we use a placeholder
    topic_id = 'library_general'

    # Points: 1 point per full 10 minutes (same as other sessions)
    blocks = duration_minutes // 10
    if blocks <= 0:
        return {'points_earned': 0, 'total_points': 0, 'new_fcl': 0, 'fcl_changed': False}

    base_points = blocks
    bonus = 5 if ai_tutor_used else 0
    total_points_awarded = base_points + bonus

    # Award points using your existing logic
    result = award_topic_points(
        student_id = student_id,
        subject_id = subject_id,
        topic_id   = topic_id,
        points     = total_points_awarded,
        reason     = f'library_session_{content_id}_{duration_minutes}min_ai{ai_tutor_used}',
        source_id  = f'content_{content_id}',
        db         = db,
        session_id = session_id,
    )

    # Return in the format expected by the router
    return {
        'points_earned': result['points_awarded'],
        'total_points': result['total_points'],
        'new_fcl': result['new_fcl'],
        'fcl_changed': result['fcl_changed'],
    }


# ══════════════════════════════════════════════════════════════════
#  STRUGGLING STUDENT DETECTION (with event logging)
# ══════════════════════════════════════════════════════════════════

def check_struggling_student(student_id: int, subject_id: int,
                               topic_id: str, teacher_id: int | None,
                               student_name: str, subject_name: str,
                               db: Session,
                               session_id: int = None):
    """
    Check two struggling thresholds and notify teacher:
      1. 3 consecutive wrong answers on this topic
      2. 6 or more wrong answers in the last 10 attempts on this topic

    Also creates a ComprehensionEvent if struggling is detected.
    Avoids duplicate notifications within 24 hours.
    """
    if not teacher_id:
        return

    # Get last 10 assessments for this student+topic
    recent = db.execute(text(
        'SELECT is_correct FROM assessments '
        'WHERE student_id=:sid AND topic_id=:tid '
        'ORDER BY created_at DESC LIMIT 10'
    ), {'sid': student_id, 'tid': topic_id}).fetchall()

    if not recent:
        return

    is_correct_list = [bool(r[0]) for r in recent]

    # Threshold 1: 3 consecutive wrong
    consecutive_wrong = 0
    for correct in is_correct_list:
        if not correct:
            consecutive_wrong += 1
        else:
            break

    # Threshold 2: 6+ wrong out of last 10
    wrong_count = sum(1 for c in is_correct_list if not c)

    trigger = None
    event_type = None
    if consecutive_wrong >= 3:
        trigger = f'{consecutive_wrong} consecutive wrong answers on {topic_id.replace("_"," ")}'
        event_type = 'STRUGGLING_CONSECUTIVE_WRONG'
    elif wrong_count >= 6:
        trigger = f'{wrong_count} out of last {len(is_correct_list)} attempts wrong on {topic_id.replace("_"," ")}'
        event_type = 'STRUGGLING_HIGH_WRONG_RATE'

    if not trigger:
        return

    # Avoid duplicate notifications in the last 24 hours
    existing = db.execute(text(
        "SELECT id FROM notifications "
        "WHERE student_id=:tid AND sender_id=:sid AND type='struggling_alert' "
        "AND created_at > now() - interval '24 hours' LIMIT 1"
    ), {'tid': teacher_id, 'sid': student_id}).fetchone()

    if not existing:
        db.add(Notification(
            student_id = teacher_id,
            sender_id  = student_id,
            subject_id = subject_id,
            type       = 'struggling_alert',
            title      = f'⚠️ {student_name} is struggling in {subject_name}',
            body       = (
                f'{student_name} may need support: {trigger}. '
                f'Consider a direct message, point award, or AI directive to help them.'
            ),
            action_url = '/teacher',
        ))

    # Log a comprehension event for struggling (for dashboard notifications)
    event = ComprehensionEvent(
        student_id=student_id,
        session_id=session_id,
        event_type=event_type,
        title=f'Struggling detected in {topic_id.replace("_"," ")}',
        message=trigger,
        trigger=trigger
    )
    db.add(event)
    db.commit()


# ══════════════════════════════════════════════════════════════════
#  NOTIFICATIONS
# ══════════════════════════════════════════════════════════════════

def _notify_fcl_advance(student_id: int, subject_id: int, topic_id: str,
                         old_fcl: int, new_fcl: int,
                         teacher_id: int | None,
                         student_name: str, subject_name: str,
                         db: Session):
    """Notify student and teacher when FCL advances. Does NOT commit."""
    topic_label = topic_id.replace('_', ' ').title()

    # Notify student
    db.add(Notification(
        student_id = student_id,
        type       = 'fcl_advance',
        title      = f'🎉 FCL Level Up! {topic_label} → FCL {new_fcl}',
        body       = (
            f'You advanced from FCL {old_fcl} to FCL {new_fcl} in {topic_label}. '
            f'Questions and explanations will now be more challenging. '
            f'Keep up the great work!'
        ),
        action_url = '/progress',
    ))

    # Notify teacher
    if teacher_id:
        db.add(Notification(
            student_id = teacher_id,
            sender_id  = student_id,
            subject_id = subject_id,
            type       = 'student_level_change',
            title      = f'📈 {student_name} reached FCL {new_fcl} in {topic_label}',
            body       = (
                f'{student_name} advanced from FCL {old_fcl} to FCL {new_fcl} '
                f'in {topic_label} ({subject_name}) through quiz performance.'
            ),
            action_url = '/teacher',
        ))


def _build_reason(is_correct: bool, hints_used: int, tutor_consulted: bool) -> str:
    if not is_correct:
        return 'wrong_answer'
    if tutor_consulted and hints_used >= 3:
        return 'correct_3hints_tutor'
    return f'correct_hints_{hints_used}'