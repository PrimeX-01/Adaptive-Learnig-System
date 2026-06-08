from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import Student, StudentPreference, TeacherAssignment, Subject
from auth import hash_password, get_current_student
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix='/api/admin', tags=['Admin'])

class CreateTeacherRequest(BaseModel):
    name: str
    email: str
    password: str
    username: Optional[str] = None
    subjects: List[int] = []        # list of subject_ids
    grade_min: int = 1
    grade_max: int = 19

@router.post('/create-teacher', status_code=201)
def create_teacher(req: CreateTeacherRequest,
                   db: Session = Depends(get_db),
                   current_user = Depends(get_current_student)):
    # Only admin users can create teachers
    if not current_user.is_admin:
        raise HTTPException(403, 'Admin access required')
    
    # Check if email already exists
    if db.query(Student).filter(Student.email == req.email).first():
        raise HTTPException(400, 'Email already registered')
    
    # Create teacher account
    teacher = Student(
        name=req.name,
        email=req.email,
        password_hash=hash_password(req.password),
        username=req.username,
        is_teacher=True,
        grade=None  # teachers have no grade
    )
    db.add(teacher)
    db.flush()
    
    # Create a dummy student preference (required for foreign key)
    db.add(StudentPreference(
        student_id=teacher.id,
        preferred_modality='text',
        feedback_style='detailed',
        session_length_minutes=30,
        preferred_learning_style='reading'
    ))
    
    # Assign teacher to subjects with grade ranges
    for subject_id in req.subjects:
        assignment = TeacherAssignment(
            teacher_id=teacher.id,
            subject_id=subject_id,
            grade_min=req.grade_min,
            grade_max=req.grade_max
        )
        db.add(assignment)
    
    db.commit()
    return {'message': f'Teacher {teacher.name} created', 'teacher_id': teacher.id}