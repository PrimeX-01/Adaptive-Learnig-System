from sqlalchemy.orm import Session
from db.models import Student, StudentSubject, Subject, TopicFcl, TopicPointTransaction, ActiveSession, TeacherAward
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# ── Grade to Overall FCL (now 1‑20) ─────────────────────────────
GRADE_TO_FCL = {
    1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7,
    8: 8, 9: 9, 10: 10, 11: 11, 12: 12,
    13: 13,  # Undergraduate Level 1
    14: 14,  # Level 2
    15: 15,  # Level 3
    16: 16,  # Level 4
    17: 17,  # Level 5
    18: 18,  # Masters (coursework)
    19: 19,  # Masters (dissertation / year 2)
    20: 20,  # PhD
}

def grade_to_initial_fcl(grade: int) -> int:
    """Return overall FCL based on grade mapping (capped 1-20)."""
    return GRADE_TO_FCL.get(grade, 5)

def get_or_create_topic_fcl(student_id: int, subject_id: int, topic_id: str, db: Session) -> TopicFcl:
    record = db.query(TopicFcl).filter(
        TopicFcl.student_id == student_id,
        TopicFcl.subject_id == subject_id,
        TopicFcl.topic_id == topic_id
    ).first()
    if record:
        return record

    student = db.query(Student).filter(Student.id == student_id).first()
    overall_fcl = grade_to_initial_fcl(student.grade) if student and student.grade else 5
    initial_points = overall_fcl * 1000
    new_record = TopicFcl(
        student_id=student_id,
        subject_id=subject_id,
        topic_id=topic_id,
        total_points=initial_points,
        current_fcl=overall_fcl
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    return new_record

def get_topic_fcl(student_id: int, subject_id: int, topic_id: str, db: Session) -> int:
    record = get_or_create_topic_fcl(student_id, subject_id, topic_id, db)
    return record.current_fcl

def get_subject_fcl(student_id: int, subject_id: int, db: Session) -> float:
    topics = db.query(TopicFcl).filter(
        TopicFcl.student_id == student_id,
        TopicFcl.subject_id == subject_id
    ).all()
    if not topics:
        student = db.query(Student).filter(Student.id == student_id).first()
        if student and student.grade:
            return float(grade_to_initial_fcl(student.grade))
        return 5.0
    avg = sum(t.current_fcl for t in topics) / len(topics)
    return round(avg, 1)

def get_overall_fcl(student_id: int, db: Session) -> float:
    enrollments = db.query(StudentSubject).filter(
        StudentSubject.student_id == student_id
    ).all()
    if not enrollments:
        student = db.query(Student).filter(Student.id == student_id).first()
        if student and student.grade:
            return float(grade_to_initial_fcl(student.grade))
        return 5.0
    fcls = [get_subject_fcl(student_id, e.subject_id, db) for e in enrollments]
    avg = sum(fcls) / len(fcls)
    return round(avg, 1)

def award_topic_points(student_id: int, subject_id: int, topic_id: str,
                       points: int, reason: str, db: Session,
                       source_id: str = None):
    if points <= 0:
        return
    record = get_or_create_topic_fcl(student_id, subject_id, topic_id, db)
    record.total_points += points
    new_fcl = max(1, min(20, record.total_points // 1000))
    if new_fcl != record.current_fcl:
        logger.info(f"Topic {topic_id} for student {student_id} advanced from FCL {record.current_fcl} to {new_fcl}")
        record.current_fcl = new_fcl
    record.last_updated = datetime.utcnow()
    db.add(record)

    tx = TopicPointTransaction(
        student_id=student_id,
        subject_id=subject_id,
        topic_id=topic_id,
        points=points,
        reason=reason,
        source_id=source_id
    )
    db.add(tx)
    db.commit()