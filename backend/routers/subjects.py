from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy     import text
from pydantic import BaseModel
from typing   import Optional

from db.database import get_db
from db.models   import Subject, StudentSubject, Student
from auth        import get_current_student

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────
class EnrollRequest(BaseModel):
    student_id: int
    subject_id: int
    teacher_id: Optional[int] = None


# ══════════════════════════════════════════════════════════════════
#  SUBJECT DISCOVERY
# ══════════════════════════════════════════════════════════════════

@router.get('/available')
def get_available_subjects(db: Session = Depends(get_db)):
    """
    All subjects. Used by:
      - Teacher registration (to pick what they teach)
      - Tertiary student registration (subject selection)
    No auth required — public endpoint.
    """
    subjects = db.query(Subject).order_by(Subject.name).all()
    return [{'id': s.id, 'name': s.name, 'code': s.code} for s in subjects]


@router.get('/for-grade/{grade}')
def get_subjects_for_grade(grade: int, db: Session = Depends(get_db)):
    """
    Subjects available for a specific grade.
    Used by Register.jsx to show auto-enrollment preview for grades 1–12.
    """
    rows = db.execute(text('''
        SELECT DISTINCT s.id, s.name, s.code
        FROM teacher_grade_assignments ga
        JOIN subjects s ON s.id = ga.subject_id
        WHERE ga.grade = :grade
        ORDER BY s.name
    '''), {'grade': grade}).fetchall()
    return [{'id': r[0], 'name': r[1], 'code': r[2]} for r in rows]


# ══════════════════════════════════════════════════════════════════
#  ENROLLED SUBJECTS
# ══════════════════════════════════════════════════════════════════

@router.get('/enrolled/{student_id}')
def get_enrolled_subjects(student_id: int,
                           db: Session = Depends(get_db),
                           current_user = Depends(get_current_student)):
    """
    Get all subjects a student is enrolled in, with per-subject FCL data.
    Used by QuizPage, TutorChat, LibraryPage.
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(404, 'Student not found')
    enrollments = db.query(StudentSubject).filter(
        StudentSubject.student_id == student_id
    ).all()
    result = []
    for e in enrollments:
        subj = db.query(Subject).filter(Subject.id == e.subject_id).first()
        if not subj:
            continue
        try:
            from services.points_service import get_subject_fcl
            subject_fcl = get_subject_fcl(student_id, e.subject_id, db)
        except Exception:
            subject_fcl = 1.0
        try:
            from db.models import StudentSubjectStyle, StudentPreference
            style = db.query(StudentSubjectStyle).filter(
                StudentSubjectStyle.student_id == student_id,
                StudentSubjectStyle.subject_id == e.subject_id,
            ).first()
            if not style:
                pref = db.query(StudentPreference).filter(
                    StudentPreference.student_id == student_id
                ).first()
                learning_style = pref.preferred_learning_style if pref else 'reading'
            else:
                learning_style = style.learning_style
        except Exception:
            learning_style = 'reading'
        result.append({
            'subject_id':    e.subject_id,
            'subject_code':  subj.code,
            'subject_name':  subj.name,
            'teacher_id':    e.teacher_id,
            'fcl_level':     subject_fcl,
            'learning_style': learning_style,
        })
    return result


# ══════════════════════════════════════════════════════════════════
#  NEW: Get current student's enrolled subjects (with both slash variants)
# ══════════════════════════════════════════════════════════════════

@router.get('/')
@router.get('')
def get_my_subjects(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_student),
):
    """
    Get all subjects the current student is enrolled in.
    Used by TutorChat.jsx to populate subject filter.
    Handles both /api/subjects and /api/subjects/.
    """
    student_id = current_user.id
    enrollments = db.query(StudentSubject).filter(
        StudentSubject.student_id == student_id
    ).all()
    subjects = []
    for e in enrollments:
        subj = db.query(Subject).filter(Subject.id == e.subject_id).first()
        if subj:
            subjects.append({
                'id': subj.id,
                'name': subj.name,
                'code': subj.code,
            })
    return subjects


# ══════════════════════════════════════════════════════════════════
#  SUBJECT PERFORMANCE (for dashboard)
# ══════════════════════════════════════════════════════════════════

@router.get('/{student_id}/performance')
def get_subject_performance(student_id: int,
                             db: Session = Depends(get_db),
                             current_user = Depends(get_current_student)):
    """
    Per-subject performance summary for the student dashboard.
    """
    from services.points_service import get_subject_fcl
    enrollments = db.query(StudentSubject).filter(
        StudentSubject.student_id == student_id
    ).all()
    subjects_data = []
    for e in enrollments:
        subj = db.query(Subject).filter(Subject.id == e.subject_id).first()
        if not subj:
            continue
        acc_row = db.execute(text('''
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) AS correct
            FROM assessments
            WHERE student_id=:sid AND subject_id=:subid
        '''), {'sid': student_id, 'subid': e.subject_id}).fetchone()
        total   = acc_row[0] or 0
        correct = acc_row[1] or 0
        accuracy = round(correct/total*100) if total > 0 else 0
        subject_fcl = get_subject_fcl(student_id, e.subject_id, db)
        subjects_data.append({
            'subject_id':   e.subject_id,
            'subject_code': subj.code,
            'subject_name': subj.name,
            'fcl_level':    subject_fcl,
            'accuracy':     accuracy,
            'total_attempts': total,
        })
    all_fcls = [s['fcl_level'] for s in subjects_data]
    all_accs = [s['accuracy'] for s in subjects_data]
    overall_fcl = round(sum(all_fcls)/len(all_fcls), 1) if all_fcls else 1.0
    avg_accuracy = round(sum(all_accs)/len(all_accs)) if all_accs else 0
    overall_label = (
        'Foundation'  if overall_fcl <= 5  else
        'Developing'  if overall_fcl <= 10 else
        'Proficient'  if overall_fcl <= 15 else
        'Advanced'
    )
    return {
        'subjects': subjects_data,
        'overall': {
            'avg_fcl': overall_fcl,
            'overall_label': overall_label,
            'avg_accuracy': avg_accuracy,
            'subjects_count': len(subjects_data),
        },
    }


# ══════════════════════════════════════════════════════════════════
#  ENROLL
# ══════════════════════════════════════════════════════════════════

@router.post('/enroll')
def enroll_student(req: EnrollRequest,
                   db: Session = Depends(get_db),
                   current_user = Depends(get_current_student)):
    exists = db.query(StudentSubject).filter(
        StudentSubject.student_id == req.student_id,
        StudentSubject.subject_id == req.subject_id,
    ).first()
    if exists:
        return {'message': 'Already enrolled', 'subject_id': req.subject_id}
    db.add(StudentSubject(
        student_id = req.student_id,
        subject_id = req.subject_id,
        teacher_id = req.teacher_id,
    ))
    db.commit()
    from services.points_service import grade_to_initial_fcl
    student = db.query(Student).filter(Student.id == req.student_id).first()
    init_fcl = grade_to_initial_fcl(student.grade if student else 1)
    try:
        from auth import _init_topic_fcl_for_subject
        _init_topic_fcl_for_subject(req.student_id, req.subject_id, init_fcl, db)
    except ImportError:
        from auth import _init_topic_fcl
        _init_topic_fcl(req.student_id, req.subject_id, init_fcl, db)
    db.commit()
    return {'message': 'Enrolled successfully', 'subject_id': req.subject_id}



@router.get('/enrolled-students/{subject_id}')
def get_enrolled_students(subject_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_student)):
    students = db.query(Student).join(StudentSubject).filter(StudentSubject.subject_id == subject_id).all()
    return [{'id': s.id, 'name': s.name} for s in students]