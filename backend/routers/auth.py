from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing  import Optional, List
from passlib.context import CryptContext
from jose   import jwt
import os
from datetime import datetime, timedelta

from db.database import get_db
from db.models   import Student, Subject, StudentSubject, StudentPreference

router = APIRouter(prefix="/auth")
router  = APIRouter()
pwd_ctx = CryptContext(schemes=['bcrypt'], bcrypt__rounds=12)

SECRET_KEY       = os.getenv('SECRET_KEY', 'change-me-in-production')
ALGORITHM        = 'HS256'
TOKEN_EXPIRY_DAYS= 30



#  SCHEMAS


class RegisterRequest(BaseModel):
    name:               str
    email:              str
    password:           str
    is_teacher:         bool  = False
    learning_style:     Optional[str] = None   # ← Allow null
    # Student
    grade:              Optional[int]       = None
    subject_ids:        Optional[List[int]] = []
    # Teacher — creates a subject, teaches specific grades
    teach_grades:       Optional[List[int]] = None
    teach_subject_name: Optional[str] = None
    teach_subject_code: Optional[str] = None

class LoginRequest(BaseModel):
    email:    str
    password: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token:        str
    new_password: str


# ══════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════

def _hash(pw: str) -> str:       return pwd_ctx.hash(pw)
def _verify(plain, hashed) -> bool: return pwd_ctx.verify(plain, hashed)

def _make_token(student_id: int, is_teacher: bool) -> str:
    return jwt.encode({
        'sub':        str(student_id),
        'is_teacher': is_teacher,
        'exp':        datetime.utcnow() + timedelta(days=TOKEN_EXPIRY_DAYS),
    }, SECRET_KEY, algorithm=ALGORITHM)


def _get_or_create_subject(name: str, code: str, db: Session) -> Subject:
    existing = db.query(Subject).filter(Subject.code == code.upper()).first()
    if existing:
        return existing
    subj = Subject(name=name.strip(), code=code.upper().strip())
    db.add(subj)
    db.flush()
    return subj


def _init_topic_fcl(student_id: int, subject_id: int,
                     initial_fcl: int, db: Session):
    SUBJECT_TOPICS = {
        'MATH': ['mathematics_algebra','mathematics_geometry','mathematics_calculus','mathematics_statistics'],
        'SCI':  ['science_biology','science_chemistry','science_physics'],
        'ENG':  ['english_comprehension','english_writing','english_literature'],
        'SOC':  ['social_studies','civics'],
        'CS':   ['computer_science','programming'],
    }
    subj = db.query(Subject).filter(Subject.id == subject_id).first()
    topics = SUBJECT_TOPICS.get(subj.code if subj else '', [])
    pts = initial_fcl * 1000
    for tid in topics:
        db.execute(text(
            'INSERT INTO topic_fcl (student_id,subject_id,topic_id,total_points,current_fcl) '
            'VALUES (:sid,:subid,:tid,:pts,:fcl) '
            'ON CONFLICT (student_id,subject_id,topic_id) DO NOTHING'
        ), {'sid':student_id,'subid':subject_id,'tid':tid,'pts':pts,'fcl':initial_fcl})


def _enroll_student(student_id: int, subject_id: int,
                     teacher_id: int, initial_fcl: int, db: Session):
    db.execute(text(
        'INSERT INTO student_subjects (student_id,subject_id,teacher_id) '
        'VALUES (:sid,:subid,:tid) ON CONFLICT DO NOTHING'
    ), {'sid':student_id,'subid':subject_id,'tid':teacher_id})
    _init_topic_fcl(student_id, subject_id, initial_fcl, db)


def _auto_enroll_grade_1_12(student_id: int, grade: int,
                              initial_fcl: int, db: Session) -> list:
    rows = db.execute(text(
        'SELECT DISTINCT ga.subject_id, s.name, ga.teacher_id '
        'FROM teacher_grade_assignments ga '
        'JOIN subjects s ON s.id = ga.subject_id '
        'WHERE ga.grade = :grade'
    ), {'grade': grade}).fetchall()

    enrolled = []
    for r in rows:
        subj_id, subj_name, teacher_id = r[0], r[1], r[2]
        already = db.execute(text(
            'SELECT id FROM student_subjects WHERE student_id=:sid AND subject_id=:subid'
        ), {'sid':student_id,'subid':subj_id}).fetchone()
        if not already:
            _enroll_student(student_id, subj_id, teacher_id, initial_fcl, db)
            enrolled.append(subj_name)
    db.flush()
    return enrolled


def _enroll_tertiary(student_id: int, subject_ids: List[int],
                      grade: int, initial_fcl: int, db: Session) -> list:
    enrolled = []
    for subj_id in subject_ids:
        teacher_row = db.execute(text(
            'SELECT teacher_id FROM teacher_grade_assignments '
            'WHERE subject_id=:sid AND grade=:g LIMIT 1'
        ), {'sid':subj_id,'g':grade}).fetchone()
        teacher_id = teacher_row[0] if teacher_row else None
        already = db.execute(text(
            'SELECT id FROM student_subjects WHERE student_id=:stid AND subject_id=:subid'
        ), {'stid':student_id,'subid':subj_id}).fetchone()
        if not already:
            _enroll_student(student_id, subj_id, teacher_id, initial_fcl, db)
            subj = db.query(Subject).filter(Subject.id==subj_id).first()
            if subj: enrolled.append(subj.name)
    db.flush()
    return enrolled


def _backfill_existing_students(teacher_id: int, subject_id: int,
                                 grades: List[int], db: Session):
    from services.points_service import grade_to_initial_fcl
    for grade in grades:
        students = db.execute(text(
            'SELECT id,grade FROM students '
            'WHERE grade=:g AND is_teacher=false'
        ), {'g': grade}).fetchall()
        for s in students:
            sid, g = s[0], s[1]
            already = db.execute(text(
                'SELECT id FROM student_subjects WHERE student_id=:sid AND subject_id=:subid'
            ), {'sid':sid,'subid':subject_id}).fetchone()
            if not already:
                init_fcl = grade_to_initial_fcl(g or 1)
                _enroll_student(sid, subject_id, teacher_id, init_fcl, db)
    db.flush()


# ══════════════════════════════════════════════════════════════════
#  REGISTER
# ══════════════════════════════════════════════════════════════════

@router.post('/register')
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    # Email uniqueness
    existing = db.query(Student).filter(
        Student.email == req.email.lower().strip()
    ).first()
    if existing:
        raise HTTPException(400, 'An account with this email already exists')

    if len(req.password) < 6:
        raise HTTPException(400, 'Password must be at least 6 characters')

    # Create account
    student = Student(
        name       = req.name.strip(),
        email      = req.email.lower().strip(),
        password_hash = _hash(req.password),
        is_teacher = req.is_teacher,
        grade      = req.grade if not req.is_teacher else None,
    )
    db.add(student)
    db.flush()

    enrolled_subjects = []
    initial_fcl       = 1

    #  STUDENT 
    if not req.is_teacher:
        from services.points_service import grade_to_initial_fcl
        initial_fcl = grade_to_initial_fcl(req.grade or 1)

        if req.grade and req.grade <= 12:
            enrolled_subjects = _auto_enroll_grade_1_12(
                student.id, req.grade, initial_fcl, db
            )
        elif req.grade and req.grade >= 13 and req.subject_ids:
            enrolled_subjects = _enroll_tertiary(
                student.id, req.subject_ids, req.grade, initial_fcl, db
            )

        # Use provided learning style or default to 'reading'
        final_style = req.learning_style if req.learning_style else 'reading'
        db.add(StudentPreference(
            student_id               = student.id,
            preferred_learning_style = final_style,
        ))

    #  TEACHER 
    else:
        if not req.teach_subject_name or not req.teach_subject_code:
            raise HTTPException(400, 'Subject name and code are required for teachers')
        if not req.teach_grades or len(req.teach_grades) == 0:
            raise HTTPException(400, 'At least one grade must be selected for the teacher')
        for g in req.teach_grades:
            if g < 1 or g > 19:
                raise HTTPException(400, f'Invalid grade {g}. Grades must be between 1 and 19.')

        code = req.teach_subject_code.upper().strip()
        if len(code) < 2 or len(code) > 6:
            raise HTTPException(400, 'Subject code must be 2–6 characters')

        subj = _get_or_create_subject(req.teach_subject_name, code, db)

        for grade in req.teach_grades:
            db.execute(text(
                'INSERT INTO teacher_grade_assignments '
                '(teacher_id, subject_id, grade) '
                'VALUES (:tid, :sid, :grade) ON CONFLICT DO NOTHING'
            ), {
                'tid':  student.id,
                'sid':  subj.id,
                'grade': grade,
            })

        _backfill_existing_students(
            student.id, subj.id,
            req.teach_grades, db
        )

        # Teachers always get 'reading' as default learning style (or ignore)
        db.add(StudentPreference(
            student_id               = student.id,
            preferred_learning_style = 'reading',
        ))

        enrolled_subjects = [subj.name]

    db.commit()

    msg = (
        f'Welcome {student.name}! '
        + (f'Auto-enrolled in {len(enrolled_subjects)} subject(s): {", ".join(enrolled_subjects)}.'
           if enrolled_subjects else
           'Account created. You will be enrolled when a teacher registers your grade.')
    )

    return {
        'access_token':     _make_token(student.id, req.is_teacher),
        'token_type':       'bearer',
        'student_id':       student.id,
        'name':             student.name,
        'is_teacher':       student.is_teacher,
        'grade':            student.grade,
        'initial_fcl':      initial_fcl,
        'enrolled_subjects':enrolled_subjects,
        'learning_style':   req.learning_style if req.learning_style else 'reading',
        'message':          msg,
    }


# ══════════════════════════════════════════════════════════════════
#  LOGIN (unchanged)
# ══════════════════════════════════════════════════════════════════

@router.post('/login')
def login(req: LoginRequest, db: Session = Depends(get_db)):
    student = db.query(Student).filter(
        Student.email == req.email.lower().strip()
    ).first()
    if not student or not _verify(req.password, student.password_hash):
        raise HTTPException(401, 'Invalid email or password')

    pref = db.query(StudentPreference).filter(
        StudentPreference.student_id == student.id
    ).first()
    learning_style = pref.preferred_learning_style if pref else 'reading'

    try:
        from services.points_service import get_overall_fcl
        overall_fcl = get_overall_fcl(student.id, db)
    except Exception:
        overall_fcl = 1.0

    return {
        'access_token':  _make_token(student.id, student.is_teacher),
        'token_type':    'bearer',
        'student_id':    student.id,
        'name':          student.name,
        'is_teacher':    student.is_teacher,
        'grade':         student.grade,
        'overall_fcl':   overall_fcl,
        'learning_style':learning_style,
        'profile_pic':   getattr(student,'profile_picture',None) or '',
    }


# ══════════════════════════════════════════════════════════════════
#  CHANGE PASSWORD (unchanged)
# ══════════════════════════════════════════════════════════════════

@router.post('/change-password/{student_id}')
def change_password(student_id: int, req: ChangePasswordRequest,
                    db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id==student_id).first()
    if not student:
        raise HTTPException(404, 'Student not found')
    if not _verify(req.old_password, student.password_hash):
        raise HTTPException(400, 'Current password is incorrect')
    if len(req.new_password) < 6:
        raise HTTPException(400, 'New password must be at least 6 characters')
    student.password_hash = _hash(req.new_password)
    db.commit()
    return {'message': 'Password changed successfully'}


# ══════════════════════════════════════════════════════════════════
#  FORGOT / RESET PASSWORD (unchanged)
# ══════════════════════════════════════════════════════════════════

@router.post('/forgot-password')
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    student = db.query(Student).filter(
        Student.email == req.email.lower().strip()
    ).first()
    if student:
        import secrets
        token  = secrets.token_urlsafe(32)
        expiry = datetime.utcnow() + timedelta(hours=1)
        try:
            student.reset_token         = token
            student.reset_token_expires = expiry
            db.commit()
            print(f'[DEV] Reset token for {req.email}: {token}')
        except Exception:
            pass
    return {'message': 'If that email is registered, a reset link has been sent.'}


@router.post('/reset-password')
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    student = db.query(Student).filter(
        Student.reset_token == req.token
    ).first()
    if not student:
        raise HTTPException(400, 'Invalid or expired reset token')
    try:
        if student.reset_token_expires < datetime.utcnow():
            raise HTTPException(400, 'Reset token has expired')
    except TypeError:
        pass
    if len(req.new_password) < 6:
        raise HTTPException(400, 'Password must be at least 6 characters')
    student.password_hash = _hash(req.new_password)
    student.reset_token         = None
    student.reset_token_expires = None
    db.commit()
    return {'message': 'Password reset successfully. You can now log in.'}