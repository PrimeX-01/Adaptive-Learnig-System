from sqlalchemy.orm import Session
from sqlalchemy import text
from db.models import Subject, Notification
from fastapi import HTTPException

# Fallback map when topic_id is not in fcl_mapping.json
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
        for prefix, code in TOPIC_PREFIX_MAP.items():
            if topic_id.startswith(prefix):
                return code
        raise HTTPException(
            400,
            f'topic_id "{topic_id}" not in fcl_mapping.json and no prefix match. '
            'Add it to fcl_mapping.json → topic_subject_map.'
        )
    return subject_code


def get_subject_db_id(subject_code: str, db: Session) -> int:
    subj = db.query(Subject).filter(Subject.code == subject_code).first()
    if not subj:
        raise HTTPException(404, f'Subject code {subject_code} not in subjects table')
    return subj.id


def resolve_subject_and_teacher(topic_id: str, student_id: int,
                                  fcl_mapping: dict, db: Session) -> dict:
    """
    CHANGED: StudentSubject.teacher_id lookup removed.
    Now resolves the teacher by joining teacher_class_subjects →
    class_subjects to find who teaches this subject in the
    student's class.
    """
    subject_code  = get_subject_code_for_topic(topic_id, fcl_mapping)
    subject_db_id = get_subject_db_id(subject_code, db)

    # Find the student's class_id
    student_row = db.execute(
        text('SELECT class_id FROM students WHERE id=:sid'),
        {'sid': student_id}
    ).fetchone()
    class_id = student_row[0] if student_row else None

    teacher_id = None
    if class_id:
        row = db.execute(text('''
            SELECT tcs.teacher_id
            FROM teacher_class_subjects tcs
            JOIN class_subjects cs ON cs.id = tcs.class_subject_id
            WHERE cs.class_id   = :cid
              AND cs.subject_id = :sid
            LIMIT 1
        '''), {'cid': class_id, 'sid': subject_db_id}).fetchone()
        teacher_id = row[0] if row else None

    return {
        'subject_code':  subject_code,
        'subject_db_id': subject_db_id,
        'teacher_id':    teacher_id,
    }


def notify_subject_teacher(student_id: int, subject_db_id: int,
                             teacher_id: int | None,
                             student_name: str, notif_type: str,
                             title: str, body: str, action_url: str,
                             db: Session):
    """
    CHANGED: old Notification used student_id=teacher_id (overloaded column).
    New schema uses receiver_type/receiver_id + sender_type/sender_id.
    """
    if not teacher_id:
        return
    db.add(Notification(
        receiver_type = 'teacher',
        receiver_id   = teacher_id,
        sender_type   = 'student',
        sender_id     = student_id,
        subject_id    = subject_db_id,
        type          = notif_type,
        title         = title,
        body          = body,
        action_url    = action_url,
    ))
