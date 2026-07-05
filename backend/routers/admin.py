from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from db.database import get_db
from db.models import (
    Admin, Teacher, Lecturer, Student,
    Grade, Class, Subject, ClassSubject, TeacherClassSubject,
    StudentClassEnrollment,
    Faculty, Programme, Course, ProgrammeCourseLevel,
    ProgrammeLevelSemester, LecturerCourseAssignment,
    StudentCourseEnrollment, Notification,
)
from auth import get_current_admin, hash_password

router = APIRouter(prefix='/api/admin', tags=['Admin'])


# ═══════════════════════════════════════════════════════════════════
#  SCHEMAS
# ═══════════════════════════════════════════════════════════════════

class GradeCreate(BaseModel):
    label:       str
    order_index: int = 0

class ClassCreate(BaseModel):
    grade_id: int
    name:     str

class SubjectCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None

class SubjectAssign(BaseModel):
    subject_id: int
    class_id:   int

class FacultyCreate(BaseModel):
    name:        str
    description: Optional[str] = None

class ProgrammeCreate(BaseModel):
    faculty_id:      int 
    name:            str
    duration_levels: int = 3

class CourseCreate(BaseModel):
    name:        str
    code:        str
    description: Optional[str] = None

class CourseAssign(BaseModel):
    programme_id: int
    course_code:  str
    level:        int
    semester:     int = 1

class SetSemesterRequest(BaseModel):
    programme_id: int
    level:        int
    semester:     int

class ApprovalRequest(BaseModel):
    action: str   # approve | reject


# ═══════════════════════════════════════════════════════════════════
#  PUBLIC ENDPOINTS — no auth required (used by Register.jsx)
# ═══════════════════════════════════════════════════════════════════

@router.get('/grades-public')
def grades_public(db: Session = Depends(get_db)):
    grades = db.query(Grade).order_by(Grade.order_index).all()
    return [{'id': g.id, 'label': g.label, 'order_index': g.order_index}
            for g in grades]


@router.get('/classes-public')
def classes_public(grade_id: int, db: Session = Depends(get_db)):
    classes = db.query(Class).filter(Class.grade_id == grade_id).order_by(Class.name).all()
    return [{'id': c.id, 'name': c.name, 'grade_id': c.grade_id} for c in classes]


@router.get('/class-subjects-public')
def class_subjects_public(class_id: int, db: Session = Depends(get_db)):
    rows = db.execute(text('''
        SELECT cs.id, s.name AS subject_name, s.code AS subject_code,
               (SELECT COUNT(*) FROM teacher_class_subjects tcs
                WHERE tcs.class_subject_id = cs.id) > 0 AS taken
        FROM class_subjects cs
        JOIN subjects s ON s.id = cs.subject_id
        WHERE cs.class_id = :cid
        ORDER BY s.name
    '''), {'cid': class_id}).fetchall()
    return [
        {'id': r[0], 'subject_name': r[1], 'subject_code': r[2], 'taken': bool(r[3])}
        for r in rows
    ]


@router.get('/faculties-public')
def faculties_public(db: Session = Depends(get_db)):
    faculties = db.query(Faculty).order_by(Faculty.name).all()
    return [{'id': f.id, 'name': f.name, 'description': f.description}
            for f in faculties]


@router.get('/programmes-public')
def programmes_public(faculty_id: int, db: Session = Depends(get_db)):
    progs = db.query(Programme).filter(
        Programme.faculty_id == faculty_id
    ).order_by(Programme.name).all()
    return [{'id': p.id, 'name': p.name, 'duration_levels': p.duration_levels}
            for p in progs]


@router.get('/courses-public')
def courses_public(programme_id: int, level: str, db: Session = Depends(get_db)):
    """
    Courses for a programme at a specific level.
    level can be an integer or the string 'all' (used by AdminDashboard).
    When numeric, filters to the active semester for that programme+level.
    """
    if level == 'all':
        rows = db.execute(text('''
            SELECT pcl.id AS pcl_id, c.name AS course_name, c.code AS course_code,
                   pcl.level, pcl.semester
            FROM programme_course_levels pcl
            JOIN courses c ON c.id = pcl.course_id
            WHERE pcl.programme_id = :pid
            ORDER BY pcl.level, c.name
        '''), {'pid': programme_id}).fetchall()
        return {
            'active_semester': None,
            'courses': [
                {'pcl_id': r[0], 'course_name': r[1], 'course_code': r[2],
                 'level': r[3], 'semester': r[4], 'taken': False}
                for r in rows
            ],
        }

    level_int = int(level)
    pls = db.query(ProgrammeLevelSemester).filter(
        ProgrammeLevelSemester.programme_id == programme_id,
        ProgrammeLevelSemester.level        == level_int,
    ).first()
    active_sem = pls.active_semester if pls else 1

    rows = db.execute(text('''
        SELECT pcl.id AS pcl_id, c.name AS course_name, c.code AS course_code,
               pcl.level, pcl.semester,
               (SELECT COUNT(*) FROM lecturer_course_assignments lca
                WHERE lca.pcl_id = pcl.id) > 0 AS taken
        FROM programme_course_levels pcl
        JOIN courses c ON c.id = pcl.course_id
        WHERE pcl.programme_id = :pid
          AND pcl.level        = :level
          AND pcl.semester     = :sem
        ORDER BY c.name
    '''), {'pid': programme_id, 'level': level_int, 'sem': active_sem}).fetchall()

    return {
        'active_semester': active_sem,
        'courses': [
            {
                'pcl_id':      r[0],
                'course_name': r[1],
                'course_code': r[2],
                'level':       r[3],
                'semester':    r[4],
                'taken':       bool(r[5]),
            }
            for r in rows
        ],
    }


@router.get('/faculty-levels-public')
def faculty_levels_public(faculty_id: int, db: Session = Depends(get_db)):
    rows = db.execute(text('''
        SELECT DISTINCT pcl.level
        FROM programme_course_levels pcl
        JOIN programmes p ON p.id = pcl.programme_id
        WHERE p.faculty_id = :fid
        ORDER BY pcl.level
    '''), {'fid': faculty_id}).fetchall()
    return [r[0] for r in rows]


@router.get('/faculty-courses-public')
def faculty_courses_public(faculty_id: int, level: int,
                            db: Session = Depends(get_db)):
    rows = db.execute(text('''
        SELECT pcl.id AS pcl_id, c.name AS course_name, c.code AS course_code,
               pcl.level, pcl.semester, p.name AS programme_name,
               (SELECT COUNT(*) FROM lecturer_course_assignments lca
                WHERE lca.pcl_id = pcl.id) > 0 AS taken
        FROM programme_course_levels pcl
        JOIN courses   c ON c.id  = pcl.course_id
        JOIN programmes p ON p.id = pcl.programme_id
        WHERE p.faculty_id = :fid AND pcl.level = :level
        ORDER BY p.name, c.name
    '''), {'fid': faculty_id, 'level': level}).fetchall()

    return [
        {
            'pcl_id':        r[0],
            'course_name':   r[1],
            'course_code':   r[2],
            'level':         r[3],
            'semester':      r[4],
            'programme_name':r[5],
            'taken':         bool(r[6]),
        }
        for r in rows
    ]


@router.get('/subjects-public')
def subjects_public(db: Session = Depends(get_db)):
    subjects = db.query(Subject).order_by(Subject.name).all()
    return [{'id': s.id, 'name': s.name, 'code': s.code} for s in subjects]


@router.get('/semesters')
def get_semesters(programme_id: int, db: Session = Depends(get_db)):
    prog = db.query(Programme).filter(Programme.id == programme_id).first()
    if not prog:
        raise HTTPException(404, 'Programme not found')

    result = []
    for level in range(1, prog.duration_levels + 1):
        pls = db.query(ProgrammeLevelSemester).filter(
            ProgrammeLevelSemester.programme_id == programme_id,
            ProgrammeLevelSemester.level        == level,
        ).first()
        active_sem = pls.active_semester if pls else 1

        student_count = db.query(Student).filter(
            Student.programme_id  == programme_id,
            Student.current_level == level,
        ).count()

        result.append({
            'programme_id':   programme_id,
            'level':          level,
            'active_semester':active_sem,
            'student_count':  student_count,
        })
    return result


# ═══════════════════════════════════════════════════════════════════
#  ADMIN STATS
# ═══════════════════════════════════════════════════════════════════

@router.get('/stats')
def admin_stats(db: Session = Depends(get_db),
                admin: Admin = Depends(get_current_admin)):
    pending_teachers  = db.query(Teacher).filter(Teacher.status  == 'pending').count()
    pending_lecturers = db.query(Lecturer).filter(Lecturer.status == 'pending').count()
    return {
        'school_students':   db.query(Student).filter(Student.student_type == 'school').count(),
        'tertiary_students': db.query(Student).filter(Student.student_type == 'tertiary').count(),
        'teachers':          db.query(Teacher).filter(Teacher.status  == 'active').count(),
        'lecturers':         db.query(Lecturer).filter(Lecturer.status == 'active').count(),
        'pending_count':     pending_teachers + pending_lecturers,
        'grades':            db.query(Grade).count(),
        'classes':           db.query(Class).count(),
        'subjects':          db.query(Subject).count(),
        'faculties':         db.query(Faculty).count(),
        'programmes':        db.query(Programme).count(),
        'courses':           db.query(Course).count(),
    }


# ═══════════════════════════════════════════════════════════════════
#  PENDING APPROVALS
# ═══════════════════════════════════════════════════════════════════

@router.get('/pending')
def get_pending(db: Session = Depends(get_db),
                admin: Admin = Depends(get_current_admin)):
    result = []

    teachers = db.query(Teacher).filter(Teacher.status == 'pending').all()
    for t in teachers:
        assignments = []
        for tcs in t.class_subjects:
            cs = tcs.class_subject
            assignments.append({
                'label': f'{cs.class_.grade.label} — {cs.class_.name} — {cs.subject.name}',
                'cs_id': cs.id,
                'taken': False,
            })
        result.append({
            'id':          t.id,
            'name':        t.name,
            'email':       t.email,
            'role':        'teacher',
            'registered_at': t.registered_at.isoformat() if t.registered_at else None,
            'assignments': assignments,
        })

    lecturers = db.query(Lecturer).filter(Lecturer.status == 'pending').all()
    for l in lecturers:
        assignments = []
        for lca in l.course_assignments:
            pcl = lca.pcl
            assignments.append({
                'label': (f'Level {pcl.level} Sem {pcl.semester} — '
                          f'{pcl.course.name} ({pcl.course.code}) — '
                          f'{pcl.programme.name}'),
                'pcl_id': pcl.id,
                'taken': False,
            })
        result.append({
            'id':          l.id,
            'name':        l.name,
            'email':       l.email,
            'role':        'lecturer',
            'faculty':     l.faculty.name if l.faculty else '—',
            'registered_at': l.registered_at.isoformat() if l.registered_at else None,
            'assignments': assignments,
        })

    return result


# ═══════════════════════════════════════════════════════════════════
#  APPROVE / REJECT TEACHER
# ═══════════════════════════════════════════════════════════════════

@router.post('/teachers/{teacher_id}/approve')
def approve_teacher(teacher_id: int, req: ApprovalRequest,
                    db: Session = Depends(get_db),
                    admin: Admin = Depends(get_current_admin)):
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(404, 'Teacher not found')

    if req.action == 'approve':
        teacher.status = 'active'
        db.commit()

        _backfill_students_for_teacher(teacher, db)

        db.add(Notification(
            receiver_type = 'teacher',
            receiver_id   = teacher.id,
            type          = 'account_approved',
            title         = 'Your account has been approved!',
            body          = 'You can now log in and access your dashboard.',
            action_url    = '/teacher',
        ))
        db.commit()
        return {'message': f'{teacher.name} approved successfully'}

    elif req.action == 'reject':
        teacher.status = 'rejected'
        db.commit()
        return {'message': f'{teacher.name} rejected'}

    raise HTTPException(400, "action must be 'approve' or 'reject'")


def _backfill_students_for_teacher(teacher: Teacher, db: Session):
    from auth import _init_topic_fcl_for_subject, _grade_to_fcl

    for tcs in teacher.class_subjects:
        cs    = tcs.class_subject
        class_ = cs.class_
        enrollments = db.query(StudentClassEnrollment).filter(
            StudentClassEnrollment.class_id == class_.id
        ).all()
        for enr in enrollments:
            initial_fcl = _grade_to_fcl(class_.grade_id, db)
            _init_topic_fcl_for_subject(
                enr.student_id, cs.subject_id, initial_fcl, db
            )
    db.flush()


# ═══════════════════════════════════════════════════════════════════
#  APPROVE / REJECT LECTURER
# ═══════════════════════════════════════════════════════════════════

@router.post('/lecturers/{lecturer_id}/approve')
def approve_lecturer(lecturer_id: int, req: ApprovalRequest,
                     db: Session = Depends(get_db),
                     admin: Admin = Depends(get_current_admin)):
    lecturer = db.query(Lecturer).filter(Lecturer.id == lecturer_id).first()
    if not lecturer:
        raise HTTPException(404, 'Lecturer not found')

    if req.action == 'approve':
        lecturer.status = 'active'
        db.commit()
        db.add(Notification(
            receiver_type = 'lecturer',
            receiver_id   = lecturer.id,
            type          = 'account_approved',
            title         = 'Your account has been approved!',
            body          = 'You can now log in and access your dashboard.',
            action_url    = '/lecturer',
        ))
        db.commit()
        return {'message': f'{lecturer.name} approved successfully'}

    elif req.action == 'reject':
        lecturer.status = 'rejected'
        db.commit()
        return {'message': f'{lecturer.name} rejected'}

    raise HTTPException(400, "action must be 'approve' or 'reject'")


# ═══════════════════════════════════════════════════════════════════
#  SCHOOL CRUD
# ═══════════════════════════════════════════════════════════════════

@router.post('/grades', status_code=201)
def create_grade(req: GradeCreate, db: Session = Depends(get_db),
                 admin: Admin = Depends(get_current_admin)):
    if db.query(Grade).filter(Grade.label == req.label.strip()).first():
        raise HTTPException(400, 'A grade with this label already exists')
    grade = Grade(label=req.label.strip(), order_index=req.order_index)
    db.add(grade)
    db.commit()
    db.refresh(grade)
    return {'id': grade.id, 'label': grade.label, 'order_index': grade.order_index}


@router.delete('/grades/{grade_id}')
def delete_grade(grade_id: int, db: Session = Depends(get_db),
                 admin: Admin = Depends(get_current_admin)):
    grade = db.query(Grade).filter(Grade.id == grade_id).first()
    if not grade:
        raise HTTPException(404, 'Grade not found')
    db.delete(grade)
    db.commit()
    return {'status': 'deleted'}


@router.post('/classes', status_code=201)
def create_class(req: ClassCreate, db: Session = Depends(get_db),
                 admin: Admin = Depends(get_current_admin)):
    grade = db.query(Grade).filter(Grade.id == req.grade_id).first()
    if not grade:
        raise HTTPException(404, 'Grade not found')
    existing = db.query(Class).filter(
        Class.grade_id == req.grade_id,
        Class.name     == req.name.strip(),
    ).first()
    if existing:
        raise HTTPException(400, 'A class with this name already exists in this grade')
    class_ = Class(grade_id=req.grade_id, name=req.name.strip())
    db.add(class_)
    db.commit()
    db.refresh(class_)
    return {'id': class_.id, 'name': class_.name, 'grade_id': class_.grade_id}


@router.delete('/classes/{class_id}')
def delete_class(class_id: int, db: Session = Depends(get_db),
                 admin: Admin = Depends(get_current_admin)):
    class_ = db.query(Class).filter(Class.id == class_id).first()
    if not class_:
        raise HTTPException(404, 'Class not found')
    db.delete(class_)
    db.commit()
    return {'status': 'deleted'}


@router.post('/subjects', status_code=201)
def create_subject(req: SubjectCreate, db: Session = Depends(get_db),
                   admin: Admin = Depends(get_current_admin)):
    code = req.code.strip().upper()
    if db.query(Subject).filter(Subject.code == code).first():
        raise HTTPException(400, 'A subject with this code already exists')
    subject = Subject(
        name        = req.name.strip(),
        code        = code,
        description = req.description,
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return {'id': subject.id, 'name': subject.name, 'code': subject.code}


@router.post('/subjects/assign', status_code=201)
def assign_subject_to_class(req: SubjectAssign, db: Session = Depends(get_db),
                             admin: Admin = Depends(get_current_admin)):
    if not db.query(Subject).filter(Subject.id == req.subject_id).first():
        raise HTTPException(404, 'Subject not found')
    if not db.query(Class).filter(Class.id == req.class_id).first():
        raise HTTPException(404, 'Class not found')
    existing = db.query(ClassSubject).filter(
        ClassSubject.class_id   == req.class_id,
        ClassSubject.subject_id == req.subject_id,
    ).first()
    if existing:
        raise HTTPException(400, 'Subject already assigned to this class')
    cs = ClassSubject(class_id=req.class_id, subject_id=req.subject_id)
    db.add(cs)
    db.commit()
    db.refresh(cs)
    return {'id': cs.id, 'class_id': cs.class_id, 'subject_id': cs.subject_id}


# ═══════════════════════════════════════════════════════════════════
#  TERTIARY CRUD
# ═══════════════════════════════════════════════════════════════════

@router.post('/faculties', status_code=201)
def create_faculty(req: FacultyCreate, db: Session = Depends(get_db),
                   admin: Admin = Depends(get_current_admin)):
    if db.query(Faculty).filter(Faculty.name == req.name.strip()).first():
        raise HTTPException(400, 'Faculty already exists')
    faculty = Faculty(name=req.name.strip(), description=req.description)
    db.add(faculty)
    db.commit()
    db.refresh(faculty)
    return {'id': faculty.id, 'name': faculty.name}


@router.post('/programmes', status_code=201)
def create_programme(req: ProgrammeCreate, db: Session = Depends(get_db),
                     admin: Admin = Depends(get_current_admin)):
    if not db.query(Faculty).filter(Faculty.id == req.faculty_id).first():
        raise HTTPException(404, 'Faculty not found')
    if db.query(Programme).filter(
        Programme.faculty_id == req.faculty_id,
        Programme.name       == req.name.strip(),
    ).first():
        raise HTTPException(400, 'Programme already exists in this faculty')
    prog = Programme(
        faculty_id      = req.faculty_id,
        name            = req.name.strip(),
        duration_levels = req.duration_levels,
    )
    db.add(prog)
    db.commit()
    db.refresh(prog)
    return {'id': prog.id, 'name': prog.name, 'duration_levels': prog.duration_levels}


@router.post('/courses', status_code=201)
def create_course(req: CourseCreate, db: Session = Depends(get_db),
                  admin: Admin = Depends(get_current_admin)):
    code = req.code.strip().upper()
    if db.query(Course).filter(Course.code == code).first():
        raise HTTPException(400, 'A course with this code already exists')
    course = Course(name=req.name.strip(), code=code, description=req.description)
    db.add(course)
    db.commit()
    db.refresh(course)
    return {'id': course.id, 'name': course.name, 'code': course.code}


@router.post('/courses/assign', status_code=201)
def assign_course(req: CourseAssign, db: Session = Depends(get_db),
                  admin: Admin = Depends(get_current_admin)):
    course = db.query(Course).filter(
        Course.code == req.course_code.strip().upper()
    ).first()
    if not course:
        raise HTTPException(404, f'Course with code {req.course_code} not found')

    existing = db.query(ProgrammeCourseLevel).filter(
        ProgrammeCourseLevel.programme_id == req.programme_id,
        ProgrammeCourseLevel.course_id    == course.id,
        ProgrammeCourseLevel.level        == req.level,
        ProgrammeCourseLevel.semester     == req.semester,
    ).first()
    if existing:
        raise HTTPException(400, 'Course already assigned to this programme/level/semester')

    pcl = ProgrammeCourseLevel(
        programme_id = req.programme_id,
        course_id    = course.id,
        level        = req.level,
        semester     = req.semester,
    )
    db.add(pcl)
    db.commit()
    db.refresh(pcl)
    return {
        'id':           pcl.id,
        'programme_id': pcl.programme_id,
        'course_id':    pcl.course_id,
        'level':        pcl.level,
        'semester':     pcl.semester,
    }


# ═══════════════════════════════════════════════════════════════════
#  SEMESTER MANAGEMENT
# ═══════════════════════════════════════════════════════════════════

@router.post('/programmes/set-semester')
def set_active_semester(req: SetSemesterRequest,
                        db: Session = Depends(get_db),
                        admin: Admin = Depends(get_current_admin)):
    if req.semester not in (1, 2):
        raise HTTPException(400, 'Semester must be 1 or 2')

    prog = db.query(Programme).filter(Programme.id == req.programme_id).first()
    if not prog:
        raise HTTPException(404, 'Programme not found')

    pls = db.query(ProgrammeLevelSemester).filter(
        ProgrammeLevelSemester.programme_id == req.programme_id,
        ProgrammeLevelSemester.level        == req.level,
    ).first()
    if pls:
        old_sem = pls.active_semester
        pls.active_semester = req.semester
        pls.updated_at      = datetime.utcnow()
    else:
        old_sem = None
        pls = ProgrammeLevelSemester(
            programme_id    = req.programme_id,
            level           = req.level,
            active_semester = req.semester,
        )
        db.add(pls)
    db.flush()

    if old_sem == req.semester:
        db.commit()
        return {'message': f'Semester {req.semester} is already active — no change.'}

    students = db.query(Student).filter(
        Student.programme_id  == req.programme_id,
        Student.current_level == req.level,
    ).all()

    for s in students:
        s.current_semester = req.semester
        db.add(Notification(
            receiver_type = 'student',
            receiver_id   = s.id,
            type          = 'semester_change',
            title         = f'Semester {req.semester} is now active',
            body          = (
                f'The administrator has switched {prog.name} Level {req.level} '
                f'to Semester {req.semester}. Your course list has been updated.'
            ),
            action_url    = '/student',
        ))

    db.commit()
    return {
        'message':  f'Switched to Semester {req.semester}',
        'notified': len(students),
    }
