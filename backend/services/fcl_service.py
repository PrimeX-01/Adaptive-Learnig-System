from sqlalchemy.orm import Session
from sqlalchemy import text
from db.models import Student, Subject, TopicFcl, TopicPointTransaction, ActiveSession
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# ── Grade to FCL mapping ─────────────────────────────────────────
GRADE_TO_FCL = {
    1: 1,  2: 2,  3: 3,  4: 4,  5: 5,  6: 6,
    7: 7,  8: 8,  9: 9,  10: 10, 11: 11, 12: 12,
    13: 13, 14: 14, 15: 15, 16: 16,
    17: 17, 18: 18, 19: 19, 20: 20,
}


def grade_to_initial_fcl(grade: int) -> int:
    """Return overall FCL based on grade mapping (capped 1–20)."""
    return GRADE_TO_FCL.get(grade, 5)


def get_or_create_topic_fcl(student_id: int, topic_id: str, db: Session,
                              subject_id: int = None,
                              course_id:  int = None) -> TopicFcl:
    """
    CHANGED: subject_id is now Optional; course_id param added.
    School students have subject_id rows, tertiary students have
    course_id rows. The correct FK is used based on which is provided.
    """
    q = db.query(TopicFcl).filter(
        TopicFcl.student_id == student_id,
        TopicFcl.topic_id   == topic_id,
        TopicFcl.is_active  == True,
    )
    if subject_id:
        q = q.filter(TopicFcl.subject_id == subject_id)
    elif course_id:
        q = q.filter(TopicFcl.course_id == course_id)
    record = q.first()
    if record:
        return record

    student     = db.query(Student).filter(Student.id == student_id).first()
    grade_idx   = student.grade.order_index if (student and student.grade) else 5
    overall_fcl = grade_to_initial_fcl(grade_idx)
    initial_pts = overall_fcl * 1000

    new_record = TopicFcl(
        student_id   = student_id,
        subject_id   = subject_id,
        course_id    = course_id,
        topic_id     = topic_id,
        total_points = initial_pts,
        current_fcl  = overall_fcl,
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    return new_record


def get_topic_fcl(student_id: int, topic_id: str, db: Session,
                   subject_id: int = None,
                   course_id:  int = None) -> int:
    record = get_or_create_topic_fcl(student_id, topic_id, db,
                                      subject_id=subject_id,
                                      course_id=course_id)
    return record.current_fcl


def get_subject_fcl(student_id: int, db: Session,
                     subject_id: int = None,
                     course_id:  int = None) -> float:
    """
    Average FCL across all topics for one subject or course.
    CHANGED: StudentSubject removed. Topics are read from topic_fcl directly.
    """
    q = db.query(TopicFcl).filter(
        TopicFcl.student_id == student_id,
        TopicFcl.is_active  == True,
    )
    if subject_id:
        q = q.filter(TopicFcl.subject_id == subject_id)
    elif course_id:
        q = q.filter(TopicFcl.course_id == course_id)
    topics = q.all()

    if not topics:
        student = db.query(Student).filter(Student.id == student_id).first()
        grade   = student.grade.order_index if (student and student.grade) else 5
        return float(grade_to_initial_fcl(grade))

    avg = sum(t.current_fcl for t in topics) / len(topics)
    return round(avg, 1)


def get_overall_fcl(student_id: int, db: Session) -> float:
    """
    Overall FCL = average across all active topic_fcl rows.
    CHANGED: no longer queries StudentSubject enrollments —
    that table is gone. Reads topic_fcl directly which already
    contains rows for every subject and course the student has
    engaged with, regardless of student type.
    """
    rows = db.execute(text(
        'SELECT total_points FROM topic_fcl '
        'WHERE student_id=:sid AND is_active=true'
    ), {'sid': student_id}).fetchall()

    if not rows:
        student = db.query(Student).filter(Student.id == student_id).first()
        grade   = student.grade.order_index if (student and student.grade) else 5
        return float(grade_to_initial_fcl(grade))

    fcl_values = [max(1, r[0] // 1000) for r in rows]
    return round(sum(fcl_values) / len(fcl_values), 1)


def award_topic_points(student_id: int, topic_id: str,
                        points: int, reason: str, db: Session,
                        subject_id: int = None,
                        course_id:  int = None,
                        source_id:  str = None):
    """
    CHANGED: subject_id is now Optional; course_id param added.
    Writes to the correct topic_fcl row based on which FK is provided.
    """
    if points <= 0:
        return

    record = get_or_create_topic_fcl(student_id, topic_id, db,
                                      subject_id=subject_id,
                                      course_id=course_id)
    record.total_points += points
    new_fcl = max(1, min(20, record.total_points // 1000))
    if new_fcl != record.current_fcl:
        logger.info(
            f'Topic {topic_id} for student {student_id} '
            f'advanced from FCL {record.current_fcl} to {new_fcl}'
        )
        record.current_fcl = new_fcl
    record.updated_at = datetime.utcnow()
    db.add(record)

    tx = TopicPointTransaction(
        student_id = student_id,
        subject_id = subject_id,
        course_id  = course_id,
        topic_id   = topic_id,
        points     = points,
        reason     = reason,
        source_id  = source_id,
    )
    db.add(tx)
    db.commit()
