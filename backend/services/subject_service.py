from sqlalchemy.orm import Session
from db.models import Subject, StudentSubject, Notification
from fastapi import HTTPException

# fallback map when topic_id isn't in fcl_mapping.json
TOPIC_PREFIX_MAP = {
    'mathematics': 'MATH',
    'science':     'SCI',
    'english':     'ENG',
    'social':      'SOC',
    'civics':      'SOC',
    'computer':    'CS',
    'programming': 'CS',
}

def get_subject_code_for_topic(topic_id: str, fcl_mapping: dict) -> str:
    topic_map    = fcl_mapping.get('topic_subject_map', {})
    subject_code = topic_map.get(topic_id)

    if not subject_code:
        # Fallback: derive from topic_id prefix instead of crashing with 400
        for prefix, code in TOPIC_PREFIX_MAP.items():
            if topic_id.startswith(prefix):
                return code
        raise HTTPException(400,
            f'topic_id "{topic_id}" not in fcl_mapping.json and no prefix match found. '
            f'Add it to fcl_mapping.json → topic_subject_map.')
    return subject_code

def get_subject_db_id(subject_code: str, db: Session) -> int:
    subj = db.query(Subject).filter(Subject.code == subject_code).first()
    if not subj:
        raise HTTPException(404, f'Subject code {subject_code} not in subjects table')
    return subj.id

def resolve_subject_and_teacher(topic_id: str, student_id: int,
                                 fcl_mapping: dict, db: Session) -> dict:
    subject_code  = get_subject_code_for_topic(topic_id, fcl_mapping)
    subject_db_id = get_subject_db_id(subject_code, db)
    enrollment    = db.query(StudentSubject).filter(
        StudentSubject.student_id == student_id,
        StudentSubject.subject_id == subject_db_id
    ).first()
    return {
        'subject_code':  subject_code,
        'subject_db_id': subject_db_id,
        'teacher_id':    enrollment.teacher_id if enrollment else None,
    }

def notify_subject_teacher(student_id: int, subject_db_id: int, teacher_id: int | None,
                            student_name: str, notif_type: str, title: str,
                            body: str, action_url: str, db: Session):
    if not teacher_id:
        return
    db.add(Notification(student_id=teacher_id, sender_id=student_id,
                         subject_id=subject_db_id, type=notif_type,
                         title=title, body=body, action_url=action_url))