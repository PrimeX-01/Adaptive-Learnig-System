from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List
import base64
from db.database import get_db
from db.models import LibraryContent, LibrarySession, StudentSubject, Student, Subject, ConversationSession
from auth import get_current_student
from services.llm_service import generate_library_explanation
from services.points_service import award_library_session_points
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix='/api/library', tags=['Library'])

# ── Schemas 
class ContentUploadRequest(BaseModel):
    title: str
    description: Optional[str] = None
    content_type: str   # pdf, text, video_link, image
    content_data: str   # base64 for files, URL for links
    subject_code: str
    topic_tags: List[str] = []
    grade_min: int = 1
    grade_max: int = 19

class ContentResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    content_type: str
    subject_id: int
    subject_code: str
    subject_name: str
    topic_tags: List[str]
    grade_min: int
    grade_max: int
    uploaded_at: datetime

class StudySessionRequest(BaseModel):
    content_id: int
    student_id: int
    initial_question: Optional[str] = None

# ── Teacher upload endpoint 
@router.post('/upload', status_code=201)
def upload_content(
    req: ContentUploadRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_student)
):
    if not current_user.is_teacher:
        raise HTTPException(403, 'Only teachers can upload content.')
    
    subj = db.query(Subject).filter(Subject.code == req.subject_code).first()
    if not subj:
        raise HTTPException(404, f'Subject code {req.subject_code} not found.')
    
    content = LibraryContent(
        teacher_id=current_user.id,
        subject_id=subj.id,
        title=req.title,
        description=req.description,
        content_type=req.content_type,
        file_data=req.content_data,
        topic_tags=req.topic_tags,
        grade_min=req.grade_min,
        grade_max=req.grade_max,
        is_published=True
    )
    db.add(content)
    db.commit()
    db.refresh(content)
    return {'message': 'Content uploaded successfully', 'content_id': content.id}

# ── Student library view (filtered) 
@router.get('/student/{student_id}')
def get_student_library(
    student_id: int,
    subject_code: Optional[str] = None,
    topic: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_student)
):
    # Get student's enrolled subjects
    enrollments = db.query(StudentSubject).filter(StudentSubject.student_id == student_id).all()
    subject_ids = [e.subject_id for e in enrollments]
    if not subject_ids:
        return []
    
    student = db.query(Student).filter(Student.id == student_id).first()
    grade = student.grade if student else 1
    
    query = db.query(LibraryContent).filter(
        LibraryContent.subject_id.in_(subject_ids),
        LibraryContent.grade_min <= grade,
        LibraryContent.grade_max >= grade,
        LibraryContent.is_published == True
    )
    if subject_code:
        subj = db.query(Subject).filter(Subject.code == subject_code).first()
        if subj:
            query = query.filter(LibraryContent.subject_id == subj.id)
    if topic:
        query = query.filter(LibraryContent.topic_tags.contains([topic]))
    
    items = query.order_by(LibraryContent.uploaded_at.desc()).all()
    
    result = []
    for item in items:
        subj = db.query(Subject).filter(Subject.id == item.subject_id).first()
        result.append({
            'id': item.id,
            'title': item.title,
            'description': item.description,
            'content_type': item.content_type,
            'subject_id': item.subject_id,
            'subject_code': subj.code if subj else None,
            'subject_name': subj.name if subj else None,
            'topic_tags': item.topic_tags,
            'grade_min': item.grade_min,
            'grade_max': item.grade_max,
            'uploaded_at': item.uploaded_at.isoformat(),
            'file_data': item.file_data[:200] if item.file_data else None  # preview
        })
    return result

# ── Single content item with full data 
@router.get('/content/{content_id}')
def get_content(content_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_student)):
    item = db.query(LibraryContent).filter(LibraryContent.id == content_id).first()
    if not item:
        raise HTTPException(404, 'Content not found')
    subj = db.query(Subject).filter(Subject.id == item.subject_id).first()
    return {
        'id': item.id,
        'title': item.title,
        'description': item.description,
        'content_type': item.content_type,
        'file_data': item.file_data,
        'subject_id': item.subject_id,
        'subject_code': subj.code if subj else None,
        'subject_name': subj.name if subj else None,
        'topic_tags': item.topic_tags,
        'grade_min': item.grade_min,
        'grade_max': item.grade_max,
    }

# ── Study with AI Tutor 
@router.post('/study')
def study_with_ai(
    req: StudySessionRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_student)
):
    # Get content
    content = db.query(LibraryContent).filter(LibraryContent.id == req.content_id).first()
    if not content:
        raise HTTPException(404, 'Content not found')
    
    # Get student's FCL for this subject
    from services.points_service import get_current_subject_fcl
    fcl_level = get_current_subject_fcl(req.student_id, content.subject_id, db)
    if not fcl_level:
        fcl_level = 6  # default
    
    # Get student's learning style for this subject
    from services.style_service import get_subject_style
    learning_style = get_subject_style(req.student_id, content.subject_id, db)
    
    # Create conversation session
    chat_session = ConversationSession(
        student_id=req.student_id,
        subject_id=content.subject_id,
        started_at=datetime.utcnow()
    )
    db.add(chat_session)
    db.flush()
    
    # Generate initial AI response using library explanation
    initial_question = req.initial_question or f"Please help me understand this document: {content.title}"
    
    response = generate_library_explanation(
        content_text=content.file_data or '',
        student_question=initial_question,
        topic=content.topic_tags[0] if content.topic_tags else 'general',
        fcl_level=fcl_level,
        learning_style=learning_style,
        session_id=chat_session.id,
        student_id=req.student_id,
        db=db
    )
    
    # Record library session start
    lib_session = LibrarySession(
        student_id=req.student_id,
        content_id=req.content_id,
        started_at=datetime.utcnow(),
        ai_tutor_used=True
    )
    db.add(lib_session)
    db.commit()
    
    return {
        'session_id': chat_session.id,
        'response': response['response'],
        'content_title': content.title,
        'fcl_level': fcl_level,
        'learning_style': learning_style
    }

# ── End library session (award points) 
@router.post('/end-session/{session_id}')
def end_library_session(
    session_id: int,
    duration_minutes: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_student)
):
    lib_session = db.query(LibrarySession).filter(LibrarySession.id == session_id).first()
    if not lib_session:
        raise HTTPException(404, 'Session not found')
    lib_session.ended_at = datetime.utcnow()
    db.commit()
    
    # Award points if duration >= 10 minutes
    if duration_minutes >= 10:
        points_result = award_library_session_points(
            student_id=lib_session.student_id,
            subject_id=db.query(LibraryContent).filter(LibraryContent.id == lib_session.content_id).first().subject_id,
            content_id=lib_session.content_id,
            duration_minutes=duration_minutes,
            db=db
        )
        return {'points_earned': points_result.get('points_earned', 0)}
    return {'points_earned': 0}