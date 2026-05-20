from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import and_
from db.database import get_db
from db.models import ContentItem, StudentPreference, StudentSubject, FCLHistory
from auth import get_current_student
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class ContentRecommendRequest(BaseModel):
    student_id: int
    subject_id: Optional[int] = None
    max_items:  int = 6

@router.post('/recommend')
def recommend(req: ContentRecommendRequest, db: Session=Depends(get_db),
              current_user=Depends(get_current_student)):
    pref      = db.query(StudentPreference).filter(StudentPreference.student_id==req.student_id).first()
    modality  = pref.preferred_modality if pref else 'text'
    # Get enrolled subject IDs
    enrolled  = [e.subject_id for e in db.query(StudentSubject).filter(StudentSubject.student_id==req.student_id).all()]
    # Get FCL for this subject
    fcl_q = db.query(FCLHistory).filter(FCLHistory.student_id==req.student_id)
    if req.subject_id: fcl_q = fcl_q.filter(FCLHistory.subject_id==req.subject_id)
    fcl_row = fcl_q.order_by(FCLHistory.updated_at.desc()).first()
    fcl     = fcl_row.fcl_level if fcl_row else 6
    filters = [ContentItem.modality==modality,
               ContentItem.difficulty_level.between(max(1,fcl-2), min(13,fcl+2))]
    if req.subject_id:  filters.append(ContentItem.subject_id==req.subject_id)
    elif enrolled:      filters.append(ContentItem.subject_id.in_(enrolled))
    items = db.query(ContentItem).filter(and_(*filters)).limit(req.max_items).all()
    if not items:
        items = db.query(ContentItem).filter(
            ContentItem.difficulty_level.between(max(1,fcl-2),min(13,fcl+2))).limit(req.max_items).all()
    return {'items': [{'id':i.id,'title':i.title,'topic':i.topic,'subject_id':i.subject_id,
                       'modality':i.modality,'difficulty_level':i.difficulty_level} for i in items]}

@router.get('/all')
def get_all(db: Session=Depends(get_db), current_user=Depends(get_current_student)):
    return [{'id':i.id,'title':i.title,'topic':i.topic,'subject_id':i.subject_id,
             'modality':i.modality,'difficulty_level':i.difficulty_level}
            for i in db.query(ContentItem).all()]

@router.get('/{content_id}')
def get_item(content_id: int, db: Session=Depends(get_db), current_user=Depends(get_current_student)):
    i = db.query(ContentItem).filter(ContentItem.id==content_id).first()
    if not i: from fastapi import HTTPException; raise HTTPException(404,'Not found')
    return {'id':i.id,'title':i.title,'topic':i.topic,'modality':i.modality,
            'content_text':i.content_text,'diagram_code':i.diagram_code}
