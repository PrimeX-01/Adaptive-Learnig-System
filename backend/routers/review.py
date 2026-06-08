from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date
from db.database import get_db
from db.models import ReviewSchedule
from auth import get_current_student

router = APIRouter()

@router.get('/pending/{student_id}')
def pending_reviews(student_id: int, db: Session=Depends(get_db),
                    current_user=Depends(get_current_student)):
    due = db.query(ReviewSchedule).filter(
        ReviewSchedule.student_id==student_id,
        ReviewSchedule.next_review_date<=date.today()).all()
    return {'items': [{'id':r.id,'topic_id':r.topic_id,'subject_id':r.subject_id,
                       'next_review_date':str(r.next_review_date),'repetition_count':r.repetition_count}
                      for r in due]}

@router.get('/schedule/{student_id}')
def full_schedule(student_id: int, db: Session=Depends(get_db),
                  current_user=Depends(get_current_student)):
    rows = db.query(ReviewSchedule).filter(ReviewSchedule.student_id==student_id).order_by(ReviewSchedule.next_review_date).all()
    return [{'id':r.id,'topic_id':r.topic_id,'topic_name':r.topic_id.replace('_',' ').title(),
             'subject_id':r.subject_id,'next_review_date':str(r.next_review_date),
             'interval_days':r.interval_days} for r in rows]

# NEW: upcoming reviews (future dates)
@router.get('/upcoming/{student_id}')
def upcoming_reviews(
    student_id: int,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_student)
):
    """Get upcoming reviews (future dates) for the student's calendar."""
    rows = db.query(ReviewSchedule).filter(
        ReviewSchedule.student_id == student_id,
        ReviewSchedule.next_review_date > date.today()
    ).order_by(ReviewSchedule.next_review_date).limit(limit).all()
    return [
        {
            'id': r.id,
            'topic_id': r.topic_id,
            'topic_name': r.topic_id.replace('_', ' ').title(),
            'subject_id': r.subject_id,
            'next_review_date': r.next_review_date.isoformat(),
            'interval_days': r.interval_days,
        }
        for r in rows
    ]