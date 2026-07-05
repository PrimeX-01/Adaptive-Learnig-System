from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional

from db.database import get_db
from db.models   import Subject, Student, StudentClassEnrollment, StudentCourseEnrollment
from auth        import get_current_student

router = APIRouter()


# ══════════════════════════════════════════════════════════════════
#  SUBJECT DISCOVERY — public, no auth
# ══════════════════════════════════════════════════════════════════

@router.get('/available')
def get_available_subjects(db: Session = Depends(get_db)):
    """
    All subjects. Public — no auth required.
    Used by TutorChat, QuizPage dropdowns.
    """
    subjects = db.query(Subject).order_by(Subject.name).all()
    return [{'id': s.id, 'name': s.name, 'code': s.code} for s in subjects]


# ══════════════════════════════════════════════════════════════════
#  ENROLLED SUBJECTS
#  CHANGED: StudentSubject no longer exists. Enrolment is now:
#  - School students  → StudentClassEnrollment → ClassSubject → Subject
#  - Tertiary students → StudentCourseEnrollment → ProgrammeCourseLevel → Course
#  Returns a unified list with the same shape as before so frontend
#  components (QuizPage, TutorChat, LibraryPage) need no changes.
# ══════════════════════════════════════════════════════════════════

@router.get('/enrolled/{student_id}')
def get_enrolled_subjects(student_id: int,
                           db: Session = Depends(get_db),
                           current_user = Depends(get_current_student)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(404, 'Student not found')

    result = []

    if student.student_type == 'school':
        # School: subjects come from class_subjects for the student's class
        rows = db.execute(text('''
            SELECT s.id, s.name, s.code,
                   tcs.teacher_id
            FROM student_class_enrollments sce
            JOIN class_subjects cs  ON cs.class_id   = sce.class_id
            JOIN subjects       s   ON s.id           = cs.subject_id
            LEFT JOIN teacher_class_subjects tcs
                   ON tcs.class_subject_id = cs.id
            WHERE sce.student_id = :sid
            ORDER BY s.name
        '''), {'sid': student_id}).fetchall()

        for r in rows:
            try:
                from services.points_service import get_subject_fcl
                subject_fcl = get_subject_fcl(student_id, db, subject_id=r[0])
            except Exception:
                subject_fcl = 1.0

            result.append({
                'subject_id':     r[0],
                'subject_code':   r[2],
                'subject_name':   r[1],
                'teacher_id':     r[3],
                'fcl_level':      subject_fcl,
                'learning_style': student.learning_style or 'reading',
                'type':           'subject',
            })

    else:
        # Tertiary: courses from student_course_enrollments
        rows = db.execute(text('''
            SELECT c.id, c.name, c.code, pcl.level, pcl.semester,
                   lca.lecturer_id
            FROM student_course_enrollments sce
            JOIN programme_course_levels pcl ON pcl.id  = sce.pcl_id
            JOIN courses                  c   ON c.id   = pcl.course_id
            LEFT JOIN lecturer_course_assignments lca
                   ON lca.pcl_id = pcl.id
            WHERE sce.student_id = :sid
            ORDER BY c.name
        '''), {'sid': student_id}).fetchall()

        for r in rows:
            try:
                from services.points_service import get_subject_fcl
                subject_fcl = get_subject_fcl(student_id, db, course_id=r[0])
            except Exception:
                subject_fcl = 1.0

            result.append({
                'subject_id':     r[0],   # course_id exposed as subject_id for compat
                'subject_code':   r[2],
                'subject_name':   r[1],
                'teacher_id':     r[5],   # lecturer_id exposed as teacher_id for compat
                'fcl_level':      subject_fcl,
                'learning_style': student.learning_style or 'reading',
                'type':           'course',
                'level':          r[3],
                'semester':       r[4],
            })

    return result


# ══════════════════════════════════════════════════════════════════
#  GET MY SUBJECTS (current student shortcut)
#  CHANGED: delegates to get_enrolled_subjects using current user id.
# ══════════════════════════════════════════════════════════════════

@router.get('/')
@router.get('')
def get_my_subjects(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_student),
):
    """
    Subjects/courses the current authenticated student is enrolled in.
    Used by TutorChat.jsx to populate subject filter.
    """
    return get_enrolled_subjects(current_user.id, db=db, current_user=current_user)


# ══════════════════════════════════════════════════════════════════
#  SUBJECT PERFORMANCE (dashboard)
#  CHANGED: StudentSubject → StudentClassEnrollment / StudentCourseEnrollment.
#  Uses the same SQL joins as get_enrolled_subjects.
# ══════════════════════════════════════════════════════════════════

@router.get('/{student_id}/performance')
def get_subject_performance(student_id: int,
                             db: Session = Depends(get_db),
                             current_user = Depends(get_current_student)):
    from services.points_service import get_subject_fcl
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(404, 'Student not found')

    subjects_data = []

    if student.student_type == 'school':
        rows = db.execute(text('''
            SELECT s.id, s.name, s.code
            FROM student_class_enrollments sce
            JOIN class_subjects cs ON cs.class_id  = sce.class_id
            JOIN subjects       s  ON s.id          = cs.subject_id
            WHERE sce.student_id = :sid
        '''), {'sid': student_id}).fetchall()

        for r in rows:
            acc_row = db.execute(text('''
                SELECT COUNT(*) AS total,
                       SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) AS correct
                FROM assessments
                WHERE student_id=:sid AND subject_id=:subid
            '''), {'sid': student_id, 'subid': r[0]}).fetchone()
            total    = acc_row[0] or 0
            correct  = acc_row[1] or 0
            accuracy = round(correct / total * 100) if total > 0 else 0
            sfcl     = get_subject_fcl(student_id, db, subject_id=r[0])
            subjects_data.append({
                'subject_id':     r[0],
                'subject_code':   r[2],
                'subject_name':   r[1],
                'fcl_level':      sfcl,
                'accuracy':       accuracy,
                'total_attempts': total,
            })

    else:
        rows = db.execute(text('''
            SELECT c.id, c.name, c.code
            FROM student_course_enrollments sce
            JOIN programme_course_levels pcl ON pcl.id = sce.pcl_id
            JOIN courses                 c   ON c.id   = pcl.course_id
            WHERE sce.student_id = :sid
        '''), {'sid': student_id}).fetchall()

        for r in rows:
            acc_row = db.execute(text('''
                SELECT COUNT(*) AS total,
                       SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) AS correct
                FROM assessments
                WHERE student_id=:sid AND course_id=:cid
            '''), {'sid': student_id, 'cid': r[0]}).fetchone()
            total    = acc_row[0] or 0
            correct  = acc_row[1] or 0
            accuracy = round(correct / total * 100) if total > 0 else 0
            cfcl     = get_subject_fcl(student_id, db, course_id=r[0])
            subjects_data.append({
                'subject_id':     r[0],
                'subject_code':   r[2],
                'subject_name':   r[1],
                'fcl_level':      cfcl,
                'accuracy':       accuracy,
                'total_attempts': total,
            })

    all_fcls = [s['fcl_level'] for s in subjects_data]
    all_accs = [s['accuracy']  for s in subjects_data]
    overall_fcl  = round(sum(all_fcls) / len(all_fcls), 1) if all_fcls else 1.0
    avg_accuracy = round(sum(all_accs) / len(all_accs))    if all_accs else 0

    return {
        'subjects': subjects_data,
        'overall': {
            'avg_fcl':       overall_fcl,
            'overall_label': (
                'Foundation' if overall_fcl <= 5  else
                'Developing' if overall_fcl <= 10 else
                'Proficient' if overall_fcl <= 15 else
                'Advanced'
            ),
            'avg_accuracy':    avg_accuracy,
            'subjects_count':  len(subjects_data),
        },
    }


# ══════════════════════════════════════════════════════════════════
#  ENROLLED STUDENTS FOR A SUBJECT (teacher view)
#  CHANGED: StudentSubject join → class_subjects + student_class_enrollments
# ══════════════════════════════════════════════════════════════════

@router.get('/enrolled-students/{subject_id}')
def get_enrolled_students(subject_id: int,
                           db: Session = Depends(get_db),
                           current_user = Depends(get_current_student)):
    rows = db.execute(text('''
        SELECT DISTINCT s.id, s.name
        FROM students s
        JOIN student_class_enrollments sce ON sce.student_id = s.id
        JOIN class_subjects cs ON cs.class_id = sce.class_id
        WHERE cs.subject_id = :subid
        ORDER BY s.name
    '''), {'subid': subject_id}).fetchall()
    return [{'id': r[0], 'name': r[1]} for r in rows]
