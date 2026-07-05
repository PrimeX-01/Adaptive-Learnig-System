from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional, List
from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer
import os
from datetime import datetime, timedelta

from db.database import get_db
from db.models import (
    Admin, Teacher, Lecturer, Student,
    Grade, Class, Subject, ClassSubject, TeacherClassSubject,
    StudentClassEnrollment,
    Faculty, Programme, ProgrammeCourseLevel, ProgrammeLevelSemester,
    LecturerCourseAssignment, StudentCourseEnrollment,
    VarkScore, TopicFcl,
)

router = APIRouter(prefix='/api/auth', tags=['Auth'])

# ── Crypto / JWT ────────────────────────────────────────────────
pwd_ctx    = CryptContext(schemes=['bcrypt'], bcrypt__rounds=12)
SECRET_KEY = os.getenv('SECRET_KEY', 'change-me-in-production')
ALGORITHM  = 'HS256'
TOKEN_DAYS = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/auth/login')


def hash_password(pw: str) -> str:
    return pwd_ctx.hash(pw)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)

def make_token(user_id: int, role: str) -> str:
    return jwt.encode(
        {'sub': str(user_id), 'role': role,
         'exp': datetime.utcnow() + timedelta(days=TOKEN_DAYS)},
        SECRET_KEY, algorithm=ALGORITHM,
    )


# ── Auth dependencies ────────────────────────────────────────────

def _decode(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(401, 'Invalid or expired token')

def get_current_user(token: str = Depends(oauth2_scheme),
                     db: Session = Depends(get_db)):
    payload = _decode(token)
    uid  = int(payload.get('sub', 0))
    role = payload.get('role', '')
    mapping = {
        'admin':    Admin,
        'teacher':  Teacher,
        'lecturer': Lecturer,
        'student':  Student,
    }
    model = mapping.get(role)
    if not model:
        raise HTTPException(401, 'Unknown role in token')
    obj = db.query(model).filter(model.id == uid).first()
    if not obj:
        raise HTTPException(401, 'User not found')
    return obj, role

def get_current_student(token: str = Depends(oauth2_scheme),
                        db: Session = Depends(get_db)) -> Student:
    payload = _decode(token)
    if payload.get('role') != 'student':
        raise HTTPException(403, 'Student access required')
    s = db.query(Student).filter(Student.id == int(payload['sub'])).first()
    if not s:
        raise HTTPException(401, 'Student not found')
    return s

def get_current_teacher(token: str = Depends(oauth2_scheme),
                        db: Session = Depends(get_db)) -> Teacher:
    payload = _decode(token)
    if payload.get('role') != 'teacher':
        raise HTTPException(403, 'Teacher access required')
    t = db.query(Teacher).filter(Teacher.id == int(payload['sub'])).first()
    if not t:
        raise HTTPException(401, 'Teacher not found')
    if t.status != 'active':
        raise HTTPException(403, 'Teacher account not yet approved')
    return t

def get_current_lecturer(token: str = Depends(oauth2_scheme),
                         db: Session = Depends(get_db)) -> Lecturer:
    payload = _decode(token)
    if payload.get('role') != 'lecturer':
        raise HTTPException(403, 'Lecturer access required')
    l = db.query(Lecturer).filter(Lecturer.id == int(payload['sub'])).first()
    if not l:
        raise HTTPException(401, 'Lecturer not found')
    if l.status != 'active':
        raise HTTPException(403, 'Lecturer account not yet approved')
    return l

def get_current_admin(token: str = Depends(oauth2_scheme),
                      db: Session = Depends(get_db)) -> Admin:
    payload = _decode(token)
    if payload.get('role') != 'admin':
        raise HTTPException(403, 'Admin access required')
    a = db.query(Admin).filter(Admin.id == int(payload['sub'])).first()
    if not a:
        raise HTTPException(401, 'Admin not found')
    return a


# ═══════════════════════════════════════════════════════════════════
#  SCHEMAS
# ═══════════════════════════════════════════════════════════════════

class LoginRequest(BaseModel):
    email:    str
    password: str

class RegisterStudentRequest(BaseModel):
    name:            str
    email:           str
    password:        str
    student_type:    str
    learning_style:  Optional[str] = 'reading'
    grade_id:        Optional[int] = None
    class_id:        Optional[int] = None
    faculty_id:      Optional[int] = None
    programme_id:    Optional[int] = None
    level:           Optional[int] = None
    course_pcl_ids:  Optional[List[int]] = []

class RegisterTeacherRequest(BaseModel):
    name:             str
    email:            str
    password:         str
    class_subject_ids: List[int]

class RegisterLecturerRequest(BaseModel):
    name:       str
    email:      str
    password:   str
    faculty_id: int
    pcl_ids:    List[int]

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token:        str
    new_password: str


# ═══════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════

def _grade_to_fcl(grade_id: int, db: Session) -> int:
    grade = db.query(Grade).filter(Grade.id == grade_id).first()
    if not grade:
        return 1
    return max(1, grade.order_index)

def _init_topic_fcl_for_subject(student_id: int, subject_id: int,
                                  initial_fcl: int, db: Session):
    SUBJECT_TOPICS = {
        'MATH': ['mathematics_algebra', 'mathematics_geometry',
                 'mathematics_calculus', 'mathematics_statistics'],
        'SCI':  ['science_biology', 'science_chemistry', 'science_physics'],
        'ENG':  ['english_comprehension', 'english_writing', 'english_literature'],
        'SOC':  ['social_studies', 'civics'],
        'CS':   ['computer_science', 'programming'],
    }
    subj = db.query(Subject).filter(Subject.id == subject_id).first()
    topics = SUBJECT_TOPICS.get(subj.code if subj else '', [])
    pts = initial_fcl * 1000
    for tid in topics:
        db.execute(text(
            'INSERT INTO topic_fcl (student_id, subject_id, topic_id, total_points, current_fcl) '
            'VALUES (:sid, :subid, :tid, :pts, :fcl) '
            'ON CONFLICT (student_id, subject_id, topic_id) DO NOTHING'
        ), {'sid': student_id, 'subid': subject_id, 'tid': tid,
            'pts': pts, 'fcl': initial_fcl})

def _init_topic_fcl_for_course(student_id: int, course_id: int,
                                 initial_fcl: int, db: Session):
    from db.models import Course
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return
    topic_id = course.code.lower().replace(' ', '_')
    pts = initial_fcl * 1000
    db.execute(text(
        'INSERT INTO topic_fcl (student_id, course_id, topic_id, total_points, current_fcl) '
        'VALUES (:sid, :cid, :tid, :pts, :fcl) '
        'ON CONFLICT (student_id, course_id, topic_id) DO NOTHING'
    ), {'sid': student_id, 'cid': course_id, 'tid': topic_id,
        'pts': pts, 'fcl': initial_fcl})

def _seed_vark(student_id: int, learning_style: str, db: Session):
    base = {'visual': 25.0, 'auditory': 25.0, 'reading': 25.0, 'kinesthetic': 25.0}
    bias_key = {'visual': 'v_score', 'auditory': 'a_score',
                'reading': 'r_score', 'kinesthetic': 'k_score'}.get(learning_style, 'r_score')
    scores = {
        'v_score': base['visual'],
        'a_score': base['auditory'],
        'r_score': base['reading'],
        'k_score': base['kinesthetic'],
    }
    scores[bias_key] += 25.0

    existing = db.query(VarkScore).filter(VarkScore.student_id == student_id).first()
    if not existing:
        db.add(VarkScore(student_id=student_id, **scores))
    else:
        for k, v in scores.items():
            setattr(existing, k, v)


# ═══════════════════════════════════════════════════════════════════
#  LOGIN
# ═══════════════════════════════════════════════════════════════════

@router.post('/login')
def login(req: LoginRequest, db: Session = Depends(get_db)):
    email = req.email.lower().strip()

    admin = db.query(Admin).filter(Admin.email == email).first()
    if admin and verify_password(req.password, admin.password_hash):
        return {
            'access_token': make_token(admin.id, 'admin'),
            'token_type':   'bearer',
            'user_id':      admin.id,
            'name':         admin.name,
            'role':         'admin',
            'status':       'active',
        }

    teacher = db.query(Teacher).filter(Teacher.email == email).first()
    if teacher and verify_password(req.password, teacher.password_hash):
        if teacher.status == 'pending':
            return {'status': 'pending', 'role': 'teacher',
                    'message': 'Your account is awaiting administrator approval.'}
        if teacher.status == 'rejected':
            raise HTTPException(403, 'Your registration was rejected. Contact the administrator.')
        return {
            'access_token': make_token(teacher.id, 'teacher'),
            'token_type':   'bearer',
            'user_id':      teacher.id,
            'name':         teacher.name,
            'role':         'teacher',
            'status':       'active',
            'profile_pic':  teacher.profile_picture or '',
        }

    lecturer = db.query(Lecturer).filter(Lecturer.email == email).first()
    if lecturer and verify_password(req.password, lecturer.password_hash):
        if lecturer.status == 'pending':
            return {'status': 'pending', 'role': 'lecturer',
                    'message': 'Your account is awaiting administrator approval.'}
        if lecturer.status == 'rejected':
            raise HTTPException(403, 'Your registration was rejected. Contact the administrator.')
        return {
            'access_token': make_token(lecturer.id, 'lecturer'),
            'token_type':   'bearer',
            'user_id':      lecturer.id,
            'name':         lecturer.name,
            'role':         'lecturer',
            'status':       'active',
            'faculty_id':   lecturer.faculty_id,
            'profile_pic':  lecturer.profile_picture or '',
        }

    student = db.query(Student).filter(Student.email == email).first()
    if student and verify_password(req.password, student.password_hash):
        try:
            from services.points_service import get_overall_fcl
            overall_fcl = get_overall_fcl(student.id, db)
        except Exception:
            overall_fcl = 1.0

        return {
            'access_token':   make_token(student.id, 'student'),
            'token_type':     'bearer',
            'user_id':        student.id,
            'name':           student.name,
            'role':           'student',
            'student_type':   student.student_type,
            'learning_style': student.learning_style,
            'overall_fcl':    overall_fcl,
            'grade_id':       student.grade_id,
            'class_id':       student.class_id,
            'faculty_id':     student.faculty_id,
            'programme_id':   student.programme_id,
            'current_level':  student.current_level,
            'current_semester': student.current_semester,
            'profile_pic':    student.profile_picture or '',
            'status':         'active',
        }

    raise HTTPException(401, 'Invalid email or password')


# ═══════════════════════════════════════════════════════════════════
#  REGISTER STUDENT
# ═══════════════════════════════════════════════════════════════════

@router.post('/register/student', status_code=201)
def register_student(req: RegisterStudentRequest, db: Session = Depends(get_db)):
    email = req.email.lower().strip()

    for model in (Admin, Teacher, Lecturer, Student):
        if db.query(model).filter(model.email == email).first():
            raise HTTPException(400, 'An account with this email already exists')

    if len(req.password) < 6:
        raise HTTPException(400, 'Password must be at least 6 characters')

    if req.student_type not in ('school', 'tertiary'):
        raise HTTPException(400, "student_type must be 'school' or 'tertiary'")

    if req.student_type == 'school':
        if not req.grade_id or not req.class_id:
            raise HTTPException(400, 'grade_id and class_id are required for school students')
        grade = db.query(Grade).filter(Grade.id == req.grade_id).first()
        if not grade:
            raise HTTPException(400, 'Grade not found')
        class_ = db.query(Class).filter(
            Class.id == req.class_id, Class.grade_id == req.grade_id
        ).first()
        if not class_:
            raise HTTPException(400, 'Class not found in the selected grade')

    if req.student_type == 'tertiary':
        if not req.faculty_id or not req.programme_id or not req.level:
            raise HTTPException(400, 'faculty_id, programme_id, and level are required for tertiary students')
        if not req.course_pcl_ids:
            raise HTTPException(400, 'At least one course must be selected')

    student = Student(
        name          = req.name.strip(),
        email         = email,
        password_hash = hash_password(req.password),
        student_type  = req.student_type,
        learning_style= req.learning_style or 'reading',
        grade_id      = req.grade_id,
        class_id      = req.class_id,
        faculty_id    = req.faculty_id,
        programme_id  = req.programme_id,
        current_level = req.level or 1,
        current_semester = 1,
    )
    db.add(student)
    db.flush()

    _seed_vark(student.id, req.learning_style or 'reading', db)

    if req.student_type == 'school':
        db.add(StudentClassEnrollment(
            student_id=student.id, class_id=req.class_id
        ))
        db.flush()

        initial_fcl = _grade_to_fcl(req.grade_id, db)
        class_subjects = db.query(ClassSubject).filter(
            ClassSubject.class_id == req.class_id
        ).all()
        for cs in class_subjects:
            _init_topic_fcl_for_subject(student.id, cs.subject_id, initial_fcl, db)

    else:
        pls = db.query(ProgrammeLevelSemester).filter(
            ProgrammeLevelSemester.programme_id == req.programme_id,
            ProgrammeLevelSemester.level        == req.level,
        ).first()
        active_sem = pls.active_semester if pls else 1
        student.current_semester = active_sem

        initial_fcl = max(1, (req.level - 1) * 3 + 1)

        for pcl_id in req.course_pcl_ids:
            pcl = db.query(ProgrammeCourseLevel).filter(
                ProgrammeCourseLevel.id          == pcl_id,
                ProgrammeCourseLevel.programme_id == req.programme_id,
                ProgrammeCourseLevel.level        == req.level,
            ).first()
            if not pcl:
                continue
            db.add(StudentCourseEnrollment(student_id=student.id, pcl_id=pcl_id))
            _init_topic_fcl_for_course(student.id, pcl.course_id, initial_fcl, db)

    db.commit()

    return {
        'access_token':   make_token(student.id, 'student'),
        'token_type':     'bearer',
        'user_id':        student.id,
        'name':           student.name,
        'role':           'student',
        'student_type':   student.student_type,
        'learning_style': student.learning_style,
        'overall_fcl':    1.0,
        'grade_id':       student.grade_id,
        'class_id':       student.class_id,
        'faculty_id':     student.faculty_id,
        'programme_id':   student.programme_id,
        'current_level':  student.current_level,
        'current_semester': student.current_semester,
        'profile_pic':    '',
        'status':         'active',
    }


# ═══════════════════════════════════════════════════════════════════
#  REGISTER TEACHER
# ═══════════════════════════════════════════════════════════════════

@router.post('/register/teacher', status_code=201)
def register_teacher(req: RegisterTeacherRequest, db: Session = Depends(get_db)):
    email = req.email.lower().strip()

    for model in (Admin, Teacher, Lecturer, Student):
        if db.query(model).filter(model.email == email).first():
            raise HTTPException(400, 'An account with this email already exists')

    if len(req.password) < 6:
        raise HTTPException(400, 'Password must be at least 6 characters')

    if not req.class_subject_ids:
        raise HTTPException(400, 'At least one class-subject assignment is required')

    conflicts = []
    for cs_id in req.class_subject_ids:
        existing = db.query(TeacherClassSubject).filter(
            TeacherClassSubject.class_subject_id == cs_id
        ).first()
        if existing:
            cs = db.query(ClassSubject).filter(ClassSubject.id == cs_id).first()
            label = f'{cs.class_.name} — {cs.subject.name}' if cs else str(cs_id)
            conflicts.append(label)
    if conflicts:
        raise HTTPException(
            400,
            f'The following slots are already assigned: {", ".join(conflicts)}. '
            'Choose different ones.'
        )

    teacher = Teacher(
        name          = req.name.strip(),
        email         = email,
        password_hash = hash_password(req.password),
        status        = 'pending',
    )
    db.add(teacher)
    db.flush()

    for cs_id in req.class_subject_ids:
        db.add(TeacherClassSubject(
            teacher_id       = teacher.id,
            class_subject_id = cs_id,
        ))

    db.commit()

    return {
        'teacher_id': teacher.id,
        'status':     'pending',
        'message': (
            'Your registration has been submitted. '
            'You will be able to log in once the administrator approves your account.'
        ),
    }


# ═══════════════════════════════════════════════════════════════════
#  REGISTER LECTURER
# ═══════════════════════════════════════════════════════════════════

@router.post('/register/lecturer', status_code=201)
def register_lecturer(req: RegisterLecturerRequest, db: Session = Depends(get_db)):
    email = req.email.lower().strip()

    for model in (Admin, Teacher, Lecturer, Student):
        if db.query(model).filter(model.email == email).first():
            raise HTTPException(400, 'An account with this email already exists')

    if len(req.password) < 6:
        raise HTTPException(400, 'Password must be at least 6 characters')

    if not req.pcl_ids:
        raise HTTPException(400, 'At least one course assignment is required')

    faculty = db.query(Faculty).filter(Faculty.id == req.faculty_id).first()
    if not faculty:
        raise HTTPException(400, 'Faculty not found')

    conflicts = []
    for pcl_id in req.pcl_ids:
        existing = db.query(LecturerCourseAssignment).filter(
            LecturerCourseAssignment.pcl_id == pcl_id
        ).first()
        if existing:
            pcl = db.query(ProgrammeCourseLevel).filter(
                ProgrammeCourseLevel.id == pcl_id
            ).first()
            label = (f'Level {pcl.level} — {pcl.course.name}'
                     if pcl else str(pcl_id))
            conflicts.append(label)
    if conflicts:
        raise HTTPException(
            400,
            f'The following courses are already assigned: {", ".join(conflicts)}'
        )

    lecturer = Lecturer(
        name          = req.name.strip(),
        email         = email,
        password_hash = hash_password(req.password),
        faculty_id    = req.faculty_id,
        status        = 'pending',
    )
    db.add(lecturer)
    db.flush()

    for pcl_id in req.pcl_ids:
        db.add(LecturerCourseAssignment(
            lecturer_id = lecturer.id,
            pcl_id      = pcl_id,
        ))

    db.commit()

    return {
        'lecturer_id': lecturer.id,
        'status':      'pending',
        'message': (
            'Your registration has been submitted. '
            'You will be able to log in once the administrator approves your account.'
        ),
    }


# ═══════════════════════════════════════════════════════════════════
#  CHANGE PASSWORD
# ═══════════════════════════════════════════════════════════════════

@router.post('/change-password')
def change_password(req: ChangePasswordRequest,
                    current=Depends(get_current_user),
                    db: Session = Depends(get_db)):
    user, _ = current
    if not verify_password(req.old_password, user.password_hash):
        raise HTTPException(400, 'Current password is incorrect')
    if len(req.new_password) < 6:
        raise HTTPException(400, 'New password must be at least 6 characters')
    user.password_hash = hash_password(req.new_password)
    db.commit()
    return {'message': 'Password changed successfully'}


# ═══════════════════════════════════════════════════════════════════
#  FORGOT / RESET PASSWORD
# ═══════════════════════════════════════════════════════════════════

@router.post('/forgot-password')
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    email = req.email.lower().strip()
    import secrets

    for model in (Admin, Teacher, Lecturer, Student):
        user = db.query(model).filter(model.email == email).first()
        if user and hasattr(user, 'reset_token'):
            token  = secrets.token_urlsafe(32)
            expiry = datetime.utcnow() + timedelta(hours=1)
            user.reset_token         = token
            user.reset_token_expires = expiry
            db.commit()
            print(f'[DEV] Reset token for {email}: {token}')
            break

    return {'message': 'If that email is registered, a reset link has been sent.'}


@router.post('/reset-password')
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    if len(req.new_password) < 6:
        raise HTTPException(400, 'Password must be at least 6 characters')

    for model in (Admin, Teacher, Lecturer, Student):
        if not hasattr(model, 'reset_token'):
            continue
        user = db.query(model).filter(model.reset_token == req.token).first()
        if user:
            try:
                if user.reset_token_expires < datetime.utcnow():
                    raise HTTPException(400, 'Reset token has expired')
            except TypeError:
                pass
            user.password_hash       = hash_password(req.new_password)
            user.reset_token         = None
            user.reset_token_expires = None
            db.commit()
            return {'message': 'Password reset successfully. You can now log in.'}

    raise HTTPException(400, 'Invalid or expired reset token')
