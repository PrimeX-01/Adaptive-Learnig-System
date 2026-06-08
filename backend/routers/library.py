from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from db.database import get_db
from db.models   import LibraryContent, LibrarySession, Student, Subject, StudentSubject
from auth        import get_current_student
from services.points_service import award_library_session_points

router = APIRouter()


# ══════════════════════════════════════════════════════════════════
#  SCHEMAS
# ══════════════════════════════════════════════════════════════════

class LibraryUploadRequest(BaseModel):
    title:        str
    description:  Optional[str] = None
    content_type: str            # text | link | image | pdf
    file_data:    str
    subject_id:   int
    grade:        int = 1
    topic_tags:   Optional[List[str]] = []

class LibraryUpdateRequest(BaseModel):
    title:        Optional[str]       = None
    description:  Optional[str]       = None
    content_type: Optional[str]       = None
    file_data:    Optional[str]       = None
    subject_id:   Optional[int]       = None
    grade:        Optional[int]       = None
    topic_tags:   Optional[List[str]] = None
    is_published: Optional[bool]      = None

class SessionEndRequest(BaseModel):
    student_id:    int
    content_id:    int
    duration_minutes: int
    ai_tutor_used: bool = False


# ══════════════════════════════════════════════════════════════════
#  TEACHER ENDPOINTS
# ══════════════════════════════════════════════════════════════════

@router.post('/upload')
def upload_content(req: LibraryUploadRequest,
                   db: Session = Depends(get_db),
                   current_user = Depends(get_current_student)):
    teacher_id = int(current_user.id) if hasattr(current_user,'id') else current_user

    subj = db.query(Subject).filter(Subject.id == req.subject_id).first()
    if not subj:
        raise HTTPException(404, 'Subject not found')

    item = LibraryContent(
        teacher_id   = teacher_id,
        subject_id   = req.subject_id,
        title        = req.title.strip(),
        description  = req.description,
        content_type = req.content_type,
        file_data    = req.file_data,
        grade        = req.grade,
        is_published = True,
    )
    try:
        item.topic_tags = req.topic_tags or []
    except Exception:
        pass

    db.add(item)
    db.commit()
    db.refresh(item)
    return _format_item(item, subj)


@router.get('/teacher/{teacher_id}')
def get_teacher_content(teacher_id: int,
                         db: Session = Depends(get_db),
                         current_user = Depends(get_current_student)):
    items = db.query(LibraryContent).filter(
        LibraryContent.teacher_id == teacher_id
    ).order_by(LibraryContent.uploaded_at.desc()).all()
    return [_format_item(item, db.query(Subject).filter(Subject.id==item.subject_id).first()) for item in items]


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
    if req.grade        is not None: item.grade        = req.grade
    if req.is_published is not None: item.is_published = req.is_published
    if req.topic_tags   is not None:
        try: item.topic_tags = req.topic_tags
        except Exception: pass

    db.commit()
    db.refresh(item)
    subj = db.query(Subject).filter(Subject.id == item.subject_id).first()
    return _format_item(item, subj)


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
#  STUDENT ENDPOINTS
# ══════════════════════════════════════════════════════════════════

@router.get('/student/{student_id}')
def get_student_library(student_id: int,
                         db: Session = Depends(get_db),
                         current_user = Depends(get_current_student)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(404, 'Student not found')

    grade = student.grade or 1
    enrollments = db.query(StudentSubject).filter(
        StudentSubject.student_id == student_id
    ).all()
    subject_ids = [e.subject_id for e in enrollments]

    if not subject_ids:
        return []

    items = db.query(LibraryContent).filter(
        LibraryContent.is_published == True,
        LibraryContent.subject_id.in_(subject_ids),
        LibraryContent.grade == grade
    ).order_by(LibraryContent.uploaded_at.desc()).all()

    grouped = {}
    for item in items:
        subj = db.query(Subject).filter(Subject.id == item.subject_id).first()
        subj_name = subj.name if subj else 'Unknown'
        subj_code = subj.code if subj else '—'
        if item.subject_id not in grouped:
            grouped[item.subject_id] = {
                'subject_id':   item.subject_id,
                'subject_name': subj_name,
                'subject_code': subj_code,
                'items':        [],
            }
        grouped[item.subject_id]['items'].append(_format_item(item, subj))
    return list(grouped.values())


@router.get('/subject/{subject_id}/student/{student_id}')
def get_subject_content(subject_id: int, student_id: int,
                         db: Session = Depends(get_db),
                         current_user = Depends(get_current_student)):
    student = db.query(Student).filter(Student.id == student_id).first()
    grade = student.grade if student else 1

    items = db.query(LibraryContent).filter(
        LibraryContent.subject_id   == subject_id,
        LibraryContent.is_published == True,
        LibraryContent.grade        == grade
    ).order_by(LibraryContent.uploaded_at.desc()).all()

    subj = db.query(Subject).filter(Subject.id == subject_id).first()
    return [_format_item(item, subj) for item in items]


@router.get('/content/{content_id}')
def get_content_detail(content_id: int,
                        db: Session = Depends(get_db),
                        current_user = Depends(get_current_student)):
    item = db.query(LibraryContent).filter(LibraryContent.id == content_id).first()
    if not item:
        raise HTTPException(404, 'Content not found')
    subj = db.query(Subject).filter(Subject.id == item.subject_id).first()
    return _format_item(item, subj)


# ══════════════════════════════════════════════════════════════════
#  STUDY SESSIONS (unchanged)
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
    content = db.query(LibraryContent).filter(LibraryContent.id == req.content_id).first()
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

    result = award_library_session_points(
        student_id    = req.student_id,
        subject_id    = content.subject_id,
        content_id    = req.content_id,
        duration_minutes = req.duration_minutes,
        db            = db,
    )
    return {
        'session_ended':  True,
        'duration':       req.duration_minutes,
        'points_earned':  result.get('points_earned', 0),
        'fcl_changed':    result.get('fcl_changed', False),
    }


# ══════════════════════════════════════════════════════════════════
#  HELPER
# ══════════════════════════════════════════════════════════════════

def _format_item(item: LibraryContent, subj) -> dict:
    return {
        'id':           item.id,
        'teacher_id':   item.teacher_id,
        'subject_id':   item.subject_id,
        'subject_name': subj.name if subj else '—',
        'subject_code': subj.code if subj else '—',
        'title':        item.title,
        'description':  item.description,
        'content_type': item.content_type,
        'file_data':    item.file_data,
        'grade':        item.grade,
        'topic_tags':   getattr(item, 'topic_tags', []) or [],
        'is_published': item.is_published,
        'uploaded_at':  item.uploaded_at.isoformat() if item.uploaded_at else None,
    }