from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import and_, text
from db.database import get_db
from db.models import ContentItem, Student, FclHistory
from auth import get_current_student
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class ContentRecommendRequest(BaseModel):
    student_id: int
    subject_id: Optional[int] = None
    course_id:  Optional[int] = None
    max_items:  int = 6


# ══════════════════════════════════════════════════════════════════
#  RECOMMEND
#  CHANGED:
#  - StudentPreference removed — modality derived from
#    student.learning_style directly.
#  - StudentSubject enrolled list replaced with a direct topic_fcl
#    query grouping by subject_id/course_id.
#  - FCLHistory model rename: FCLHistory → FclHistory.
# ══════════════════════════════════════════════════════════════════

@router.post('/recommend')
def recommend(req: ContentRecommendRequest,
              db: Session = Depends(get_db),
              current_user = Depends(get_current_student)):

    student = db.query(Student).filter(Student.id == req.student_id).first()

    # Learning modality from student model (StudentPreference is gone)
    style_to_modality = {
        'visual':      'image',
        'auditory':    'audio',
        'reading':     'text',
        'kinesthetic': 'interactive',
    }
    learning_style = student.learning_style if student else 'reading'
    modality       = style_to_modality.get(learning_style, 'text')

    # Get enrolled subject or course IDs from topic_fcl
    # (topic_fcl rows are created on registration/enrolment)
    if req.subject_id:
        enrolled_subject_ids = [req.subject_id]
    else:
        rows = db.execute(text(
            'SELECT DISTINCT subject_id FROM topic_fcl '
            'WHERE student_id=:sid AND subject_id IS NOT NULL AND is_active=true'
        ), {'sid': req.student_id}).fetchall()
        enrolled_subject_ids = [r[0] for r in rows]

    if req.course_id:
        enrolled_course_ids = [req.course_id]
    else:
        rows = db.execute(text(
            'SELECT DISTINCT course_id FROM topic_fcl '
            'WHERE student_id=:sid AND course_id IS NOT NULL AND is_active=true'
        ), {'sid': req.student_id}).fetchall()
        enrolled_course_ids = [r[0] for r in rows]

    # Get FCL level for filtering difficulty
    fcl_q = db.query(FclHistory).filter(FclHistory.student_id == req.student_id)
    if req.subject_id:
        fcl_q = fcl_q.filter(FclHistory.subject_id == req.subject_id)
    elif req.course_id:
        fcl_q = fcl_q.filter(FclHistory.course_id == req.course_id)
    fcl_row = fcl_q.order_by(FclHistory.updated_at.desc()).first()
    fcl     = fcl_row.fcl_level if fcl_row else 6

    # Build filters
    filters = [
        ContentItem.modality == modality,
        ContentItem.difficulty_level.between(max(1, fcl - 2), min(13, fcl + 2)),
    ]
    if req.subject_id:
        filters.append(ContentItem.subject_id == req.subject_id)
    elif req.course_id:
        filters.append(ContentItem.course_id == req.course_id)
    elif enrolled_subject_ids:
        filters.append(ContentItem.subject_id.in_(enrolled_subject_ids))
    elif enrolled_course_ids:
        filters.append(ContentItem.course_id.in_(enrolled_course_ids))

    items = db.query(ContentItem).filter(and_(*filters)).limit(req.max_items).all()

    # Fallback — widen difficulty if nothing found
    if not items:
        items = db.query(ContentItem).filter(
            ContentItem.difficulty_level.between(max(1, fcl - 2), min(13, fcl + 2))
        ).limit(req.max_items).all()

    return {
        'items': [
            {
                'id':               i.id,
                'title':            i.title,
                'topic':            i.topic,
                'subject_id':       i.subject_id,
                'course_id':        i.course_id,
                'modality':         i.modality,
                'difficulty_level': i.difficulty_level,
            }
            for i in items
        ]
    }


@router.get('/all')
def get_all(db: Session = Depends(get_db),
            current_user = Depends(get_current_student)):
    return [
        {
            'id':               i.id,
            'title':            i.title,
            'topic':            i.topic,
            'subject_id':       i.subject_id,
            'course_id':        i.course_id,
            'modality':         i.modality,
            'difficulty_level': i.difficulty_level,
        }
        for i in db.query(ContentItem).all()
    ]


@router.get('/{content_id}')
def get_item(content_id: int,
             db: Session = Depends(get_db),
             current_user = Depends(get_current_student)):
    i = db.query(ContentItem).filter(ContentItem.id == content_id).first()
    if not i:
        from fastapi import HTTPException
        raise HTTPException(404, 'Not found')
    return {
        'id':           i.id,
        'title':        i.title,
        'topic':        i.topic,
        'modality':     i.modality,
        'content_text': i.content_text,
        'diagram_code': i.diagram_code,
        'subject_id':   i.subject_id,
        'course_id':    i.course_id,
    }
