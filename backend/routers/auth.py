from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import Student, StudentPreference, StudentSubject, Subject
from db.schemas import RegisterRequest, LoginRequest, LoginResponse
from auth import hash_password, verify_password, create_access_token
import secrets
from datetime import datetime, timedelta

router = APIRouter()

@router.post('/register', status_code=201)
def register(req: RegisterRequest, db: Session=Depends(get_db)):
    if db.query(Student).filter(Student.email==req.email).first():
        raise HTTPException(400, 'Email already registered')
    
    student = Student(
        name=req.name,
        email=req.email,
        password_hash=hash_password(req.password),
        grade=req.grade
    )
    db.add(student)
    db.flush()  # get student.id

    # Create student preferences (includes overall learning style)
    db.add(StudentPreference(
        student_id=student.id,
        preferred_modality=req.preferred_modality,
        feedback_style=req.feedback_style,
        session_length_minutes=req.session_length_minutes,
        preferred_learning_style=req.preferred_modality,
    ))

    # Create subject enrollments
    for enroll in (req.subject_enrollments or []):
        subj = db.query(Subject).filter(Subject.code==enroll.get('subject_code')).first()
        if subj:
            db.add(StudentSubject(
                student_id=student.id,
                subject_id=subj.id,
                teacher_id=enroll.get('teacher_id')
            ))

    db.commit()
    return {'message': 'Registration successful', 'student_id': student.id}

@router.post('/login', response_model=LoginResponse)
def login(req: LoginRequest, db: Session=Depends(get_db)):
    student = db.query(Student).filter(Student.email == req.email).first()
    if not student:
        raise HTTPException(401, 'No account found with that email address.')
    if not verify_password(req.password, student.password_hash):
        raise HTTPException(401, 'Incorrect password. Please try again.')
    token = create_access_token({'sub': student.id})
    return LoginResponse(
        access_token=token,
        student_id=student.id,
        is_teacher=student.is_teacher,
        name=student.name
    )

@router.post('/forgot-password')
def forgot_password(payload: dict, db: Session = Depends(get_db)):
    email = payload.get('email', '').strip().lower()
    student = db.query(Student).filter(Student.email == email).first()
    base_msg = {'message': 'If that email is registered, a reset link has been generated.'}
    if not student:
        return base_msg
    token = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(hours=1)
    student.reset_token = token
    student.reset_token_expires = expires
    db.commit()
    reset_url = f'http://localhost:3000/reset-password?token={token}'
    return {**base_msg, 'dev_reset_url': reset_url, 'expires_in': '1 hour'}

@router.post('/reset-password')
def reset_password(payload: dict, db: Session = Depends(get_db)):
    token = payload.get('token', '')
    new_password = payload.get('new_password', '')
    if not token or not new_password:
        raise HTTPException(400, 'Token and new password are required.')
    if len(new_password) < 8:
        raise HTTPException(400, 'Password must be at least 8 characters.')
    student = db.query(Student).filter(Student.reset_token == token).first()
    if not student:
        raise HTTPException(400, 'Invalid or expired reset link.')
    if student.reset_token_expires and datetime.utcnow() > student.reset_token_expires:
        student.reset_token = None
        student.reset_token_expires = None
        db.commit()
        raise HTTPException(400, 'This reset link has expired.')
    student.password_hash = hash_password(new_password)
    student.reset_token = None
    student.reset_token_expires = None
    db.commit()
    return {'message': 'Password updated successfully.'}