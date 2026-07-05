from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from db.database import get_db
from db.models   import LibraryContent, LibrarySession, Student, Subject
from auth        import get_current_student
from services.points_service import award_library_session_points

router = APIRouter()


# ══════════════════════════════════════════════════════════════════
#  SCHEMAS
# ══════════════════════════════════════════════════════════════════

class LibraryUploadRequest(BaseModel):
    title:        str
    description:  Optional[str] = None
    content_type: str               # text | link | image | pdf
    file_data:    str
    subject_id:   Optional[int] = None
    course_id:    Optional[int] = None
    grade_id:     Optional[int] = None
    level:        Optional[int] = None
    topic_tags:   Optional[List[str]] = []

class LibraryUpdateRequest(BaseModel):
    title:        Optional[str]       = None
    description:  Optional[str]       = None
    content_type: Optional[str]       = None
    file_data:    Optional[str]       = None
    subject_id:   Optional[int]       = None
    course_id:    Optional[int]       = None
    grade_id:     Optional[int]       = None
    level:        Optional[int]       = None
    topic_tags:   Optional[List[str]] = None
    is_published: Optional[bool]      = None

class SessionEndRequest(BaseModel):
    student_id:       int
    content_id:       int
    duration_minutes: int
    ai_tutor_used:    bool = False


# ══════════════════════════════════════════════════════════════════
#  TEACHER / LECTURER UPLOAD
# ══════════════════════════════════════════════════════════════════

@router.post('/upload')
def upload_content(req: LibraryUploadRequest,
                   db: Session = Depends(get_db),
                   current_user = Depends(get_current_student)):
    uploader_id = current_user.id
    role        = getattr(current_user, 'role', 'student')

    item = LibraryContent(
        teacher_id   = uploader_id if role == 'teacher'  else None,
        lecturer_id  = uploader_id if role == 'lecturer' else None,
        subject_id   = req.subject_id,
        course_id    = req.course_id,
        title        = req.title.strip(),
        description  = req.description,
        content_type = req.content_type,
        file_data    = req.file_data,
        grade_id     = req.grade_id,
        level        = req.level,
        is_published = True,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _format_item(item, db)


@router.get('/teacher/{teacher_id}')
def get_teacher_content(teacher_id: int,
                         db: Session = Depends(get_db),
                         current_user = Depends(get_current_student)):
    items = db.query(LibraryContent).filter(
        LibraryContent.teacher_id == teacher_id
    ).order_by(LibraryContent.uploaded_at.desc()).all()
    return [_format_item(item, db) for item in items]


@router.get('/lecturer/{lecturer_id}')
def get_lecturer_content(lecturer_id: int,
                          db: Session = Depends(get_db),
                          current_user = Depends(get_current_student)):
    items = db.query(LibraryContent).filter(
        LibraryContent.lecturer_id == lecturer_id
    ).order_by(LibraryContent.uploaded_at.desc()).all()
    return [_format_item(item, db) for item in items]


@router.patch('/{content_id}')
def update_content(content_id: int, req: LibraryUpdateRequest,
                   db: Session = Depends(get_db),
                   current_user = Depends(get_current_student)):
    item = db.query(LibraryContent).filter(LibraryContent.id == content_id).first()
    if not item:
        raise HTTPException(404, 'Content not found')

    if req.title        is not None: item.title        = req.title.strip()
    if req.description  is not None: item.description  = req.description
    if req.content_type is not None: item.content_type = req.content_type
    if req.file_data    is not None: item.file_data    = req.file_data
    if req.subject_id   is not None: item.subject_id   = req.subject_id
    if req.course_id    is not None: item.course_id    = req.course_id
    if req.grade_id     is not None: item.grade_id     = req.grade_id
    if req.level        is not None: item.level        = req.level
    if req.is_published is not None: item.is_published = req.is_published

    db.commit()
    db.refresh(item)
    return _format_item(item, db)


@router.delete('/{content_id}')
def delete_content(content_id: int,
                   db: Session = Depends(get_db),
                   current_user = Depends(get_current_student)):
    item = db.query(LibraryContent).filter(LibraryContent.id == content_id).first()
    if not item:
        raise HTTPException(404, 'Content not found')
    db.delete(item)
    db.commit()
    return {'status': 'deleted'}


# ══════════════════════════════════════════════════════════════════
#  STUDENT LIBRARY
#  CHANGED: StudentSubject enrollment replaced with topic_fcl-based
#  subject/course discovery. School students have subject_id rows,
#  tertiary students have course_id rows. We query both and find
#  matching library content accordingly.
# ══════════════════════════════════════════════════════════════════

@router.get('/student/{student_id}')
def get_student_library(student_id: int,
                         db: Session = Depends(get_db),
                         current_user = Depends(get_current_student)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(404, 'Student not found')

    # Determine subject/course IDs from enrolment tables
    if student.student_type == 'school' and student.class_id:
        # School: get subjects from class_subjects for student's class
        rows = db.execute(text('''
            SELECT DISTINCT cs.subject_id
            FROM class_subjects cs
            WHERE cs.class_id = :cid
        '''), {'cid': student.class_id}).fetchall()
        subject_ids = [r[0] for r in rows]
        course_ids  = []
    else:
        # Tertiary: get course_ids from student_course_enrollments
        rows = db.execute(text('''
            SELECT DISTINCT pcl.course_id
            FROM student_course_enrollments sce
            JOIN programme_course_levels pcl ON pcl.id = sce.pcl_id
            WHERE sce.student_id = :sid
        '''), {'sid': student_id}).fetchall()
        course_ids  = [r[0] for r in rows]
        subject_ids = []

    if not subject_ids and not course_ids:
        return []

    # Fetch published content matching subject or course
    if subject_ids:
        items = db.query(LibraryContent).filter(
            LibraryContent.is_published == True,
            LibraryContent.subject_id.in_(subject_ids),
        ).order_by(LibraryContent.uploaded_at.desc()).all()
    else:
        items = db.query(LibraryContent).filter(
            LibraryContent.is_published == True,
            LibraryContent.course_id.in_(course_ids),
        ).order_by(LibraryContent.uploaded_at.desc()).all()

    # Group by subject or course
    grouped = {}
    for item in items:
        group_key = item.subject_id or item.course_id
        if group_key not in grouped:
            label = _get_content_label(item, db)
            grouped[group_key] = {
                'subject_id':   item.subject_id,
                'course_id':    item.course_id,
                'subject_name': label,
                'items':        [],
            }
        grouped[group_key]['items'].append(_format_item(item, db))

    return list(grouped.values())


@router.get('/subject/{subject_id}/student/{student_id}')
def get_subject_content(subject_id: int, student_id: int,
                         db: Session = Depends(get_db),
                         current_user = Depends(get_current_student)):
    items = db.query(LibraryContent).filter(
        LibraryContent.subject_id   == subject_id,
        LibraryContent.is_published == True,
    ).order_by(LibraryContent.uploaded_at.desc()).all()
    return [_format_item(item, db) for item in items]


@router.get('/course/{course_id}/student/{student_id}')
def get_course_content(course_id: int, student_id: int,
                        db: Session = Depends(get_db),
                        current_user = Depends(get_current_student)):
    items = db.query(LibraryContent).filter(
        LibraryContent.course_id    == course_id,
        LibraryContent.is_published == True,
    ).order_by(LibraryContent.uploaded_at.desc()).all()
    return [_format_item(item, db) for item in items]


@router.get('/content/{content_id}')
def get_content_detail(content_id: int,
                        db: Session = Depends(get_db),
                        current_user = Depends(get_current_student)):
    item = db.query(LibraryContent).filter(LibraryContent.id == content_id).first()
    if not item:
        raise HTTPException(404, 'Content not found')
    return _format_item(item, db)


# ══════════════════════════════════════════════════════════════════
#  STUDY SESSIONS
# ══════════════════════════════════════════════════════════════════

@router.post('/session/start')
def start_session(student_id: int, content_id: int,
                   db: Session = Depends(get_db),
                   current_user = Depends(get_current_student)):
    session = LibrarySession(
        student_id = student_id,
        content_id = content_id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {'session_id': session.id, 'started_at': session.started_at}


@router.post('/session/end')
def end_session(req: SessionEndRequest,
                db: Session = Depends(get_db),
                current_user = Depends(get_current_student)):
    content = db.query(LibraryContent).filter(
        LibraryContent.id == req.content_id
    ).first()
    if not content:
        raise HTTPException(404, 'Content not found')

    session = db.query(LibrarySession).filter(
        LibrarySession.student_id == req.student_id,
        LibrarySession.content_id == req.content_id,
        LibrarySession.ended_at   == None,
    ).order_by(LibrarySession.started_at.desc()).first()

    if session:
        session.ended_at      = datetime.utcnow()
        session.ai_tutor_used = req.ai_tutor_used
        db.commit()

    # CHANGED: pass both subject_id and course_id —
    # award_library_session_points now accepts both and routes accordingly.
    result = award_library_session_points(
        student_id       = req.student_id,
        content_id       = req.content_id,
        duration_minutes = req.duration_minutes,
        ai_tutor_used    = req.ai_tutor_used,
        db               = db,
    )
    return {
        'session_ended': True,
        'duration':      req.duration_minutes,
        'points_earned': result.get('points_earned', 0),
        'fcl_changed':   result.get('fcl_changed', False),
    }


# ══════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════

def _get_content_label(item: LibraryContent, db: Session) -> str:
    """Return subject or course name for a content item."""
    if item.subject_id:
        subj = db.query(Subject).filter(Subject.id == item.subject_id).first()
        return subj.name if subj else '—'
    if item.course_id:
        from db.models import Course
        crs = db.query(Course).filter(Course.id == item.course_id).first()
        return crs.name if crs else '—'
    return '—'


def _format_item(item: LibraryContent, db: Session) -> dict:
    label = _get_content_label(item, db)
    return {
        'id':           item.id,
        'teacher_id':   item.teacher_id,
        'lecturer_id':  item.lecturer_id,
        'subject_id':   item.subject_id,
        'course_id':    item.course_id,
        'subject_name': label,
        'title':        item.title,
        'description':  item.description,
        'content_type': item.content_type,
        'file_data':    item.file_data,
        'grade_id':     item.grade_id,
        'level':        item.level,
        'is_published': item.is_published,
        'uploaded_at':  item.uploaded_at.isoformat() if item.uploaded_at else None,
    }
