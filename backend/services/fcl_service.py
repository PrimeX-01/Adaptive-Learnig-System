from sqlalchemy.orm import Session
from db.models import Student, StudentSubject, Subject, TopicFcl, TopicPointTransaction, ActiveSession, TeacherAward
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Grade to initial overall FCL mapping (as per approved table)
GRADE_TO_FCL = {
    1: 1, 2: 1, 3: 2, 4: 3, 5: 3, 6: 4, 7: 5,
    8: 6, 9: 7, 10: 8, 11: 9, 12: 10,
    13: 10, 14: 10, 15: 11, 16: 12, 17: 12,   # Undergraduate levels 1-5
    18: 13, 19: 13   # Masters, PhD
}

def grade_to_initial_fcl(grade: int) -> int:
    """Return overall FCL based on grade mapping."""
    return GRADE_TO_FCL.get(grade, 5)

def get_or_create_topic_fcl(student_id: int, subject_id: int, topic_id: str, db: Session):
    """Return topic FCL record (create with initial overall FCL if missing)."""
    record = db.query(TopicFcl).filter(
        TopicFcl.student_id == student_id,
        TopicFcl.subject_id == subject_id,
        TopicFcl.topic_id == topic_id
    ).first()
    if record:
        return record

    # Determine initial overall FCL from grade
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
    """Return current FCL for a topic (integer)."""
    record = get_or_create_topic_fcl(student_id, subject_id, topic_id, db)
    return record.current_fcl

def get_subject_fcl(student_id: int, subject_id: int, db: Session) -> float:
    """Compute subject FCL = average of its topic FCLs. If no topics, return grade-based FCL."""
    topics = db.query(TopicFcl).filter(
        TopicFcl.student_id == student_id,
        TopicFcl.subject_id == subject_id
    ).all()
    if not topics:
        # No topics yet → use grade‑based FCL directly (no recursion)
        student = db.query(Student).filter(Student.id == student_id).first()
        if student and student.grade:
            return float(grade_to_initial_fcl(student.grade))
        return 5.0
    avg = sum(t.current_fcl for t in topics) / len(topics)
    return round(avg, 1)

def get_overall_fcl(student_id: int, db: Session) -> float:
    """Compute overall FCL = average of subject FCLs for enrolled subjects."""
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
    """Award points to a topic, update total_points and current_fcl."""
    if points <= 0:
        return
    record = get_or_create_topic_fcl(student_id, subject_id, topic_id, db)
    record.total_points += points
    # Update FCL based on new total_points: FCL = floor(total_points / 1000), capped 1-13
    new_fcl = max(1, min(13, record.total_points // 1000))
    if new_fcl != record.current_fcl:
        logger.info(f"Topic {topic_id} for student {student_id} advanced from FCL {record.current_fcl} to {new_fcl}")
        record.current_fcl = new_fcl
    record.last_updated = datetime.utcnow()
    db.add(record)

    # Log transaction
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