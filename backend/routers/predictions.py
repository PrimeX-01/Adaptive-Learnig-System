from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from db.database import get_db
from db.schemas import PredictionRequest
from db.models import FCLHistory
from services.ml_service import predict_cognitive_level
from auth import get_current_student

router = APIRouter()

@router.post('/cognitive-level')
def predict(req: PredictionRequest, request: Request,
            db: Session=Depends(get_db), current_user=Depends(get_current_student)):
    result = predict_cognitive_level(req.dict(), request.app.state)
    # Store initial FCL — subject_id is NULL here (pre-subject assignment)
    if req.student_id:
        db.add(FCLHistory(student_id=req.student_id, subject_id=1, fcl_level=result['fcl_level']))
        db.commit()
    return result
