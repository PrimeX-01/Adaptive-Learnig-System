from sqlalchemy.orm import Session
from sqlalchemy import text
from db.models import (
    Notification, Student, Subject, Course,
    Assessment, LibraryContent, ComprehensionEvent,
)
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

FCL_MAX        = 20
POINTS_PER_FCL = 1000


# ══════════════════════════════════════════════════════════════════
#  GRADE → INITIAL FCL
# ══════════════════════════════════════════════════════════════════

def grade_to_initial_fcl(grade: int) -> int:
    """
    Map a student's school grade (order_index) to starting FCL (1–20).
    """
    if not grade or grade < 1: return 5
    if grade <= 2:   return 1
    if grade <= 4:   return 2
    if grade <= 6:   return 4
    if grade <= 7:   return 5
    if grade <= 9:   return 7
    if grade <= 10:  return 8
    if grade <= 12:  return 9
    if grade <= 13:  return 11
    if grade <= 15:  return 12
    if grade <= 17:  return 14
    if grade == 18:  return 17
    return 19


# ══════════════════════════════════════════════════════════════════
#  POINT CALCULATION — pure functions (unchanged)
# ══════════════════════════════════════════════════════════════════

def calculate_quiz_points(is_correct: bool,
                           hints_used: int,
                           tutor_consulted: bool) -> int:
    if not is_correct:
        return 0
    if tutor_consulted and hints_used >= 3:
        return 1
    if hints_used == 0:
        return 5
    elif hints_used == 1:
        return 4
    elif hints_used == 2:
        return 3
    else:
        return 2


def fcl_from_points(total_points: int) -> int:
    return min(FCL_MAX, total_points // POINTS_PER_FCL)


def points_within_level(total_points: int) -> int:
    return total_points % POINTS_PER_FCL


def points_to_next_fcl(total_points: int) -> int:
    current = fcl_from_points(total_points)
    if current >= FCL_MAX:
        return 0
    return (current + 1) * POINTS_PER_FCL - total_points


# ══════════════════════════════════════════════════════════════════
#  NEW: FK COLUMN ROUTER
#  Returns ('subject_id', val) for school students or
#  ('course_id', val) for tertiary students.
#  Used by all SQL builders so one code path handles both.
# ══════════════════════════════════════════════════════════════════

def _col(subject_id: Optional[int],
         course_id:  Optional[int]) -> tuple:
    if course_id is not None:
        return 'course_id', course_id
    return 'subject_id', subject_id


# ══════════════════════════════════════════════════════════════════
#  GET / INIT TOPIC FCL ROW
#  CHANGED: subject_id is now Optional; course_id param added.
#  SQL dynamically uses the right FK column via _col().
# ══════════════════════════════════════════════════════════════════

def _get_or_init_topic_row(student_id: int, topic_id: str, db: Session,
                            subject_id: Optional[int] = None,
                            course_id:  Optional[int] = None,
                            initial_fcl: int = None) -> dict:
    col, col_val = _col(subject_id, course_id)

    result = db.execute(text(
        f'SELECT id, total_points, current_fcl FROM topic_fcl '
        f'WHERE student_id=:sid AND {col}=:col_val AND topic_id=:tid'
    ), {'sid': student_id, 'col_val': col_val, 'tid': topic_id}).fetchone()

    if result:
        return {'id': result[0], 'total_points': result[1], 'current_fcl': result[2]}

    # First time — initialise the row
    if initial_fcl is None:
        student = db.query(Student).filter(Student.id == student_id).first()
        # CHANGED: student.grade is now a relationship object, not an integer.
        # Read the order_index from the Grade model.
        if student and student.grade:
            grade_idx = student.grade.order_index
        elif student and student.current_level:
            grade_idx = 12 + student.current_level   # rough tertiary mapping
        else:
            grade_idx = 1
        initial_fcl = grade_to_initial_fcl(grade_idx)

    starting_points = initial_fcl * POINTS_PER_FCL
    db.execute(text(
        f'INSERT INTO topic_fcl '
        f'(student_id, {col}, topic_id, total_points, current_fcl) '
        f'VALUES (:sid, :col_val, :tid, :pts, :fcl) '
        f'ON CONFLICT (student_id, {col}, topic_id) DO NOTHING'
    ), {'sid': student_id, 'col_val': col_val, 'tid': topic_id,
        'pts': starting_points, 'fcl': initial_fcl})
    db.flush()

    return {'id': None, 'total_points': starting_points, 'current_fcl': initial_fcl}


# ══════════════════════════════════════════════════════════════════
#  AWARD POINTS (core function)
#  CHANGED: subject_id now Optional; course_id param added.
#  All SQL uses _col() to route to the right FK column.
# ══════════════════════════════════════════════════════════════════

def award_topic_points(student_id: int, topic_id: str,
                        points: int, reason: str, db: Session,
                        subject_id:  Optional[int] = None,
                        course_id:   Optional[int] = None,
                        source_id:   str = None,
                        initial_fcl: int = None,
                        session_id:  int = None) -> dict:

    if points <= 0:
        return _empty_result(student_id, topic_id, db,
                             subject_id=subject_id, course_id=course_id)

    col, col_val = _col(subject_id, course_id)
    row      = _get_or_init_topic_row(student_id, topic_id, db,
                                       subject_id=subject_id,
                                       course_id=course_id,
                                       initial_fcl=initial_fcl)
    old_fcl   = row['current_fcl']
    new_total = row['total_points'] + points
    new_fcl   = fcl_from_points(new_total)

    # Update topic_fcl
    db.execute(text(
        f'UPDATE topic_fcl SET total_points=:pts, current_fcl=:fcl, updated_at=now() '
        f'WHERE student_id=:sid AND {col}=:col_val AND topic_id=:tid'
    ), {'pts': new_total, 'fcl': new_fcl,
        'sid': student_id, 'col_val': col_val, 'tid': topic_id})

    # Log transaction
    db.execute(text(
        f'INSERT INTO topic_point_transactions '
        f'(student_id, {col}, topic_id, points, reason, source_id) '
        f'VALUES (:sid, :col_val, :tid, :pts, :reason, :src)'
    ), {'sid': student_id, 'col_val': col_val, 'tid': topic_id,
        'pts': points, 'reason': reason, 'src': source_id})

    # FCL advance event
    if new_fcl > old_fcl:
        db.add(ComprehensionEvent(
            student_id  = student_id,
            session_id  = session_id,
            event_type  = 'FCL_ADVANCE',
            title       = f'FCL Advanced to Level {new_fcl}',
            message     = (
                f"You've advanced from FCL {old_fcl} to {new_fcl} in "
                f"{topic_id.replace('_', ' ')}! "
                f"Questions will now be more challenging."
            ),
            tier_before = old_fcl,
            tier_after  = new_fcl,
            trigger     = f'Points earned: +{points}',
        ))

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


def _empty_result(student_id, topic_id, db,
                   subject_id=None, course_id=None) -> dict:
    row = _get_or_init_topic_row(student_id, topic_id, db,
                                  subject_id=subject_id, course_id=course_id)
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
#  GET FCL VALUES
#  CHANGED: all functions now accept optional subject_id / course_id.
#  get_overall_fcl no longer queries StudentSubject (removed from
#  schema). It reads topic_fcl directly — works for both student types.
#  get_topic_fcl fixes student.grade → student.grade.order_index.
# ══════════════════════════════════════════════════════════════════

def get_topic_fcl(student_id: int, topic_id: str, db: Session,
                   subject_id: Optional[int] = None,
                   course_id:  Optional[int] = None) -> int:
    col, col_val = _col(subject_id, course_id)
    row = db.execute(text(
        f'SELECT total_points FROM topic_fcl '
        f'WHERE student_id=:sid AND {col}=:col_val AND topic_id=:tid'
    ), {'sid': student_id, 'col_val': col_val, 'tid': topic_id}).fetchone()

    if not row:
        student = db.query(Student).filter(Student.id == student_id).first()
        # CHANGED: student.grade is a relationship now, not an integer
        grade_idx = (student.grade.order_index
                     if (student and student.grade) else 1)
        return grade_to_initial_fcl(grade_idx)
    return fcl_from_points(row[0])


def get_subject_fcl(student_id: int, db: Session,
                     subject_id: Optional[int] = None,
                     course_id:  Optional[int] = None) -> float:
    """Average FCL across all active topics for one subject or course."""
    col, col_val = _col(subject_id, course_id)
    rows = db.execute(text(
        f'SELECT total_points FROM topic_fcl '
        f'WHERE student_id=:sid AND {col}=:col_val AND is_active=true'
    ), {'sid': student_id, 'col_val': col_val}).fetchall()

    if not rows:
        student   = db.query(Student).filter(Student.id == student_id).first()
        grade_idx = (student.grade.order_index
                     if (student and student.grade) else 1)
        return float(grade_to_initial_fcl(grade_idx))

    fcl_values = [fcl_from_points(r[0]) for r in rows]
    return round(sum(fcl_values) / len(fcl_values), 1)


def get_overall_fcl(student_id: int, db: Session) -> float:
    """
    CHANGED: no longer queries StudentSubject (removed from schema).
    Reads all active topic_fcl rows directly — works for both school
    students (subject_id rows) and tertiary students (course_id rows).
    """
    rows = db.execute(text(
        'SELECT total_points FROM topic_fcl '
        'WHERE student_id=:sid AND is_active=true'
    ), {'sid': student_id}).fetchall()

    if not rows:
        student   = db.query(Student).filter(Student.id == student_id).first()
        grade_idx = (student.grade.order_index
                     if (student and student.grade) else 1)
        return float(grade_to_initial_fcl(grade_idx))

    fcl_values = [fcl_from_points(r[0]) for r in rows]
    return round(sum(fcl_values) / len(fcl_values), 1)


def get_student_points_summary(student_id: int, db: Session) -> list:
    """
    CHANGED: no longer queries StudentSubject enrollments.
    Groups topic_fcl rows by subject_id / course_id directly.
    Works for both school and tertiary students.
    """
    rows = db.execute(text(
        'SELECT topic_id, total_points, current_fcl, subject_id, course_id '
        'FROM topic_fcl WHERE student_id=:sid AND is_active=true'
    ), {'sid': student_id}).fetchall()

    # Group rows by (kind, fk_id)
    groups: dict = {}
    for r in rows:
        key = ('subject', r[3]) if r[3] else ('course', r[4])
        groups.setdefault(key, []).append(r)

    result = []
    for (kind, fk_id), group_rows in groups.items():
        if kind == 'subject':
            obj  = db.query(Subject).filter(Subject.id == fk_id).first()
            name = obj.name if obj else '—'
            code = obj.code if obj else '—'
        else:
            obj  = db.query(Course).filter(Course.id == fk_id).first()
            name = obj.name if obj else '—'
            code = obj.code if obj else '—'

        topic_fcls = [fcl_from_points(r[1]) for r in group_rows]
        sub_fcl    = round(sum(topic_fcls) / len(topic_fcls), 1)
        total_pts  = sum(r[1] for r in group_rows)

        result.append({
            'subject_id':   fk_id if kind == 'subject' else None,
            'course_id':    fk_id if kind == 'course'  else None,
            'subject_name': name,
            'subject_code': code,
            'subject_fcl':  sub_fcl,
            'total_points': total_pts,
            'topics': [
                {
                    'topic_id':            r[0],
                    'total_points':        r[1],
                    'current_fcl':         r[2],
                    'points_within_level': points_within_level(r[1]),
                    'points_to_next':      points_to_next_fcl(r[1]),
                }
                for r in group_rows
            ],
        })
    return result


# ══════════════════════════════════════════════════════════════════
#  PROCESS QUIZ ANSWER (main entry point from quiz.py)
#  CHANGED: subject_id now Optional; course_id and lecturer_id added.
# ══════════════════════════════════════════════════════════════════

def process_quiz_answer(student_id: int, topic_id: str,
                         is_correct: bool, hints_used: int,
                         tutor_consulted: bool, question_id: str,
                         student_name: str, subject_name: str,
                         db: Session,
                         subject_id:  Optional[int] = None,
                         course_id:   Optional[int] = None,
                         teacher_id:  Optional[int] = None,
                         lecturer_id: Optional[int] = None,
                         session_id:  int = None) -> dict:

    pts = calculate_quiz_points(is_correct, hints_used, tutor_consulted)

    result = award_topic_points(
        student_id = student_id,
        topic_id   = topic_id,
        points     = pts,
        reason     = _build_reason(is_correct, hints_used, tutor_consulted),
        source_id  = question_id,
        db         = db,
        subject_id = subject_id,
        course_id  = course_id,
        session_id = session_id,
    )

    # Struggling detection — works for teacher or lecturer
    educator_id   = teacher_id or lecturer_id
    educator_type = 'teacher' if teacher_id else ('lecturer' if lecturer_id else None)
    check_struggling_student(
        student_id    = student_id,
        topic_id      = topic_id,
        educator_id   = educator_id,
        educator_type = educator_type,
        student_name  = student_name,
        subject_name  = subject_name,
        db            = db,
        subject_id    = subject_id,
        course_id     = course_id,
        session_id    = session_id,
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
        'subject_fcl':         get_subject_fcl(student_id, db,
                                               subject_id=subject_id,
                                               course_id=course_id),
        'overall_fcl':         get_overall_fcl(student_id, db),
    }


# ══════════════════════════════════════════════════════════════════
#  SESSION TIME POINTS
#  CHANGED: subject_id Optional; course_id added.
# ══════════════════════════════════════════════════════════════════

def award_session_time_points(student_id: int, topic_id: str,
                               duration_minutes: int, session_type: str,
                               db: Session,
                               subject_id:  Optional[int] = None,
                               course_id:   Optional[int] = None,
                               session_id:  int = None) -> dict:
    blocks = duration_minutes // 10
    if blocks <= 0:
        return {'points_awarded': 0}

    return award_topic_points(
        student_id = student_id,
        topic_id   = topic_id,
        points     = blocks,
        reason     = f'{session_type}_session_{duration_minutes}min',
        db         = db,
        subject_id = subject_id,
        course_id  = course_id,
        session_id = session_id,
    )


# ══════════════════════════════════════════════════════════════════
#  TEACHER / LECTURER MANUAL AWARD
#  CHANGED: subject_id Optional; course_id added.
# ══════════════════════════════════════════════════════════════════

def award_teacher_points(teacher_id: int, student_id: int,
                          topic_id: str, points: int, reason: str,
                          db: Session,
                          subject_id:  Optional[int] = None,
                          course_id:   Optional[int] = None,
                          session_id:  int = None) -> dict:
    if points <= 0:
        return {'error': 'Points must be positive'}

    result = award_topic_points(
        student_id = student_id,
        topic_id   = topic_id,
        points     = points,
        reason     = f'teacher_award: {reason}',
        source_id  = f'teacher_{teacher_id}',
        db         = db,
        subject_id = subject_id,
        course_id  = course_id,
        session_id = session_id,
    )

    col, col_val = _col(subject_id, course_id)
    try:
        db.execute(text(
            f'INSERT INTO teacher_point_awards '
            f'(teacher_id, student_id, {col}, topic_id, points, reason) '
            f'VALUES (:tid, :sid, :col_val, :topic, :pts, :reason)'
        ), {'tid': teacher_id, 'sid': student_id, 'col_val': col_val,
            'topic': topic_id, 'pts': points, 'reason': reason})
        db.commit()
    except Exception:
        pass

    return result


# ══════════════════════════════════════════════════════════════════
#  LIBRARY SESSION POINTS
#  CHANGED: passes both content.subject_id and content.course_id
#  to award_topic_points so tertiary library sessions are handled.
# ══════════════════════════════════════════════════════════════════

def award_library_session_points(student_id: int, content_id: int,
                                  duration_minutes: int, ai_tutor_used: bool,
                                  db: Session,
                                  session_id: int = None) -> dict:
    content = db.query(LibraryContent).filter(LibraryContent.id == content_id).first()
    if not content:
        logger.warning(f'Library content {content_id} not found for points award')
        return {'points_earned': 0, 'error': 'Content not found'}

    subject_id = content.subject_id
    course_id  = content.course_id
    topic_id   = 'library_general'

    blocks = duration_minutes // 10
    if blocks <= 0:
        return {'points_earned': 0, 'total_points': 0, 'new_fcl': 0, 'fcl_changed': False}

    total_pts_awarded = blocks + (5 if ai_tutor_used else 0)

    result = award_topic_points(
        student_id = student_id,
        topic_id   = topic_id,
        points     = total_pts_awarded,
        reason     = f'library_session_{content_id}_{duration_minutes}min_ai{ai_tutor_used}',
        source_id  = f'content_{content_id}',
        db         = db,
        subject_id = subject_id,
        course_id  = course_id,
        session_id = session_id,
    )

    return {
        'points_earned': result['points_awarded'],
        'total_points':  result['total_points'],
        'new_fcl':       result['new_fcl'],
        'fcl_changed':   result['fcl_changed'],
    }


# ══════════════════════════════════════════════════════════════════
#  STRUGGLING STUDENT DETECTION
#  CHANGED: Notification now uses receiver_type/receiver_id/
#  sender_type/sender_id (new schema). Old columns student_id and
#  sender_id no longer exist on the Notification model.
#  Also accepts educator_type param for teacher vs lecturer routing.
# ══════════════════════════════════════════════════════════════════

def check_struggling_student(student_id: int, topic_id: str,
                               student_name: str, subject_name: str,
                               db: Session,
                               educator_id:   Optional[int] = None,
                               educator_type: Optional[str] = None,
                               subject_id:    Optional[int] = None,
                               course_id:     Optional[int] = None,
                               session_id:    int = None):
    if not educator_id:
        return

    recent = db.execute(text(
        'SELECT is_correct FROM assessments '
        'WHERE student_id=:sid AND topic_id=:tid '
        'ORDER BY created_at DESC LIMIT 10'
    ), {'sid': student_id, 'tid': topic_id}).fetchall()

    if not recent:
        return

    is_correct_list   = [bool(r[0]) for r in recent]
    consecutive_wrong = 0
    for correct in is_correct_list:
        if not correct:
            consecutive_wrong += 1
        else:
            break
    wrong_count = sum(1 for c in is_correct_list if not c)

    trigger    = None
    event_type = None
    if consecutive_wrong >= 3:
        trigger    = f'{consecutive_wrong} consecutive wrong answers on {topic_id.replace("_"," ")}'
        event_type = 'STRUGGLING_CONSECUTIVE_WRONG'
    elif wrong_count >= 6:
        trigger    = f'{wrong_count} of last {len(is_correct_list)} attempts wrong on {topic_id.replace("_"," ")}'
        event_type = 'STRUGGLING_HIGH_WRONG_RATE'

    if not trigger:
        return

    # CHANGED: deduplication query uses new receiver_type/receiver_id columns
    existing = db.execute(text(
        "SELECT id FROM notifications "
        "WHERE receiver_type=:rtype AND receiver_id=:rid "
        "  AND sender_id=:sid AND type='struggling_alert' "
        "  AND created_at > now() - interval '24 hours' LIMIT 1"
    ), {'rtype': educator_type, 'rid': educator_id, 'sid': student_id}).fetchone()

    if not existing:
        notif_kwargs = dict(
            receiver_type = educator_type,
            receiver_id   = educator_id,
            sender_type   = 'student',
            sender_id     = student_id,
            type          = 'struggling_alert',
            title         = f'⚠️ {student_name} is struggling in {subject_name}',
            body          = (
                f'{student_name} may need support: {trigger}. '
                'Consider a direct message, point award, or AI directive.'
            ),
            action_url    = f'/{educator_type}',
        )
        if subject_id:
            notif_kwargs['subject_id'] = subject_id
        if course_id:
            notif_kwargs['course_id'] = course_id
        db.add(Notification(**notif_kwargs))

    db.add(ComprehensionEvent(
        student_id = student_id,
        session_id = session_id,
        event_type = event_type,
        title      = f'Struggling detected in {topic_id.replace("_"," ")}',
        message    = trigger,
        trigger    = trigger,
    ))
    db.commit()


# ══════════════════════════════════════════════════════════════════
#  FCL ADVANCE NOTIFICATION
#  CHANGED: Notification uses receiver_type/receiver_id/sender_type/
#  sender_id instead of old student_id/sender_id columns.
# ══════════════════════════════════════════════════════════════════

def _notify_fcl_advance(student_id: int, topic_id: str,
                         old_fcl: int, new_fcl: int,
                         educator_id:   Optional[int],
                         educator_type: Optional[str],
                         student_name: str, subject_name: str,
                         db: Session,
                         subject_id: Optional[int] = None,
                         course_id:  Optional[int] = None):
    topic_label = topic_id.replace('_', ' ').title()

    # Notify student
    db.add(Notification(
        receiver_type = 'student',
        receiver_id   = student_id,
        type          = 'fcl_advance',
        title         = f'🎉 FCL Level Up! {topic_label} → FCL {new_fcl}',
        body          = (
            f'You advanced from FCL {old_fcl} to FCL {new_fcl} in {topic_label}. '
            'Questions and explanations will now be more challenging. '
            'Keep up the great work!'
        ),
        action_url    = '/student/progress',
    ))

    # Notify educator
    if educator_id and educator_type:
        notif_kwargs = dict(
            receiver_type = educator_type,
            receiver_id   = educator_id,
            sender_type   = 'student',
            sender_id     = student_id,
            type          = 'student_level_change',
            title         = f'📈 {student_name} reached FCL {new_fcl} in {topic_label}',
            body          = (
                f'{student_name} advanced from FCL {old_fcl} to FCL {new_fcl} '
                f'in {topic_label} ({subject_name}) through quiz performance.'
            ),
            action_url    = f'/{educator_type}',
        )
        if subject_id:
            notif_kwargs['subject_id'] = subject_id
        if course_id:
            notif_kwargs['course_id'] = course_id
        db.add(Notification(**notif_kwargs))


def _build_reason(is_correct: bool, hints_used: int, tutor_consulted: bool) -> str:
    if not is_correct:
        return 'wrong_answer'
    if tutor_consulted and hints_used >= 3:
        return 'correct_3hints_tutor'
    return f'correct_hints_{hints_used}'