from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional

from db.database import get_db
from db.schemas  import AssessmentSubmitRequest, AssessmentResponse
from db.models   import Assessment, Student, Subject, Notification
from services.subject_service   import (resolve_subject_and_teacher,
                                         notify_subject_teacher, TOPIC_PREFIX_MAP)
from services.bkt_service        import update_mastery
from services.llm_service        import generate_question, generate_feedback
from services.points_service     import (
    process_quiz_answer,
    get_topic_fcl, get_subject_fcl, get_overall_fcl,
    grade_to_initial_fcl, award_topic_points,
)
from auth import get_current_student

router = APIRouter()


# ══════════════════════════════════════════════════════════════════
#  SCHEMAS
# ══════════════════════════════════════════════════════════════════

class QuizGenerateRequest(BaseModel):
    student_id:     int
    topic:          str
    fcl_level:      int = 5
    learning_style: Optional[str] = 'reading'

class QuizAbandonRequest(BaseModel):
    student_id:    int
    topic_id:      str
    abandon_count: int

class QuizCompleteRequest(BaseModel):
    student_id:    int
    topic_id:      str
    correct_count: int
    total_count:   int


# ══════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════

def _get_student(student_id: int, db: Session) -> Student:
    return db.query(Student).filter(Student.id == student_id).first()


def _get_real_fcl(student_id: int, topic_id: str,
                   subject_id: Optional[int], db: Session,
                   course_id: Optional[int] = None) -> int:
    try:
        return get_topic_fcl(student_id, topic_id, db,
                              subject_id=subject_id, course_id=course_id)
    except Exception:
        student = _get_student(student_id, db)
        grade   = student.grade.order_index if (student and student.grade) else 1
        return grade_to_initial_fcl(grade)


def _get_learning_style(student_id: int, subject_id: Optional[int],
                          db: Session, course_id: Optional[int] = None) -> str:
    """
    CHANGED: StudentPreference no longer exists.
    Learning style is read from:
      1. StudentSubjectStyle (per-subject override if set)
      2. student.learning_style (global preference on Student model)
    """
    try:
        from db.models import StudentSubjectStyle
        q = db.query(StudentSubjectStyle).filter(
            StudentSubjectStyle.student_id == student_id
        )
        if subject_id:
            q = q.filter(StudentSubjectStyle.subject_id == subject_id)
        elif course_id:
            q = q.filter(StudentSubjectStyle.course_id == course_id)
        style = q.first()
        if style and style.learning_style:
            return style.learning_style
    except Exception:
        pass
    # Fall back to student's global learning style
    student = _get_student(student_id, db)
    return (student.learning_style or 'reading') if student else 'reading'


def _get_teacher_for_subject(student: Student, subject_id: Optional[int],
                               db: Session) -> Optional[int]:
    """
    CHANGED: replaces StudentSubject.teacher_id lookup.
    Finds the teacher assigned to this student's class + subject
    via teacher_class_subjects → class_subjects.
    """
    if not student or not student.class_id or not subject_id:
        return None
    row = db.execute(text('''
        SELECT tcs.teacher_id
        FROM teacher_class_subjects tcs
        JOIN class_subjects cs ON cs.id = tcs.class_subject_id
        WHERE cs.class_id   = :cid
          AND cs.subject_id = :sid
        LIMIT 1
    '''), {'cid': student.class_id, 'sid': subject_id}).fetchone()
    return row[0] if row else None


def _get_lecturer_for_course(student_id: int, course_id: Optional[int],
                               db: Session) -> Optional[int]:
    """Finds the lecturer assigned to a course via lecturer_course_assignments."""
    if not course_id:
        return None
    row = db.execute(text('''
        SELECT lca.lecturer_id
        FROM lecturer_course_assignments lca
        JOIN programme_course_levels pcl ON pcl.id = lca.pcl_id
        JOIN student_course_enrollments sce ON sce.pcl_id = pcl.id
        WHERE sce.student_id = :sid AND pcl.course_id = :cid
        LIMIT 1
    '''), {'sid': student_id, 'cid': course_id}).fetchone()
    return row[0] if row else None


# ══════════════════════════════════════════════════════════════════
#  GENERATE QUESTION
# ══════════════════════════════════════════════════════════════════

@router.post('/generate-question')
def generate_quiz_question(req: QuizGenerateRequest,
                            db: Session = Depends(get_db),
                            current_user = Depends(get_current_student)):
    try:
        code = next((c for p, c in TOPIC_PREFIX_MAP.items()
                     if req.topic.startswith(p)), 'MATH')
        subj = db.query(Subject).filter(Subject.code == code).first()
        subject_db_id = subj.id if subj else None
    except Exception:
        subject_db_id = None

    real_fcl       = _get_real_fcl(req.student_id, req.topic, subject_db_id, db)
    learning_style = req.learning_style or _get_learning_style(
        req.student_id, subject_db_id, db
    )

    question = generate_question(
        topic          = req.topic,
        fcl_level      = real_fcl,
        app_state      = None,
        learning_style = learning_style,
    )
    question['fcl_used']      = real_fcl
    question['subject_db_id'] = subject_db_id
    return question


# ══════════════════════════════════════════════════════════════════
#  SUBMIT ANSWER
#  CHANGED: StudentSubject enrollment → _get_teacher_for_subject()
#  which uses teacher_class_subjects/class_subjects tables.
#  Also accepts course_id for tertiary students.
# ══════════════════════════════════════════════════════════════════

@router.post('/submit', response_model=AssessmentResponse)
def submit_assessment(req: AssessmentSubmitRequest,
                       db: Session = Depends(get_db),
                       current_user = Depends(get_current_student)):

    # ── 1. Resolve subject/course + educator ─────────────────────
    teacher_id    = None
    lecturer_id   = None
    subject_db_id = None
    course_db_id  = None
    student       = _get_student(req.student_id, db)

    try:
        code = next((c for p, c in TOPIC_PREFIX_MAP.items()
                     if req.topic_id.startswith(p)), None)
        if code:
            subj = db.query(Subject).filter(Subject.code == code).first()
            if subj:
                subject_db_id = subj.id
                teacher_id    = _get_teacher_for_subject(student, subject_db_id, db)
    except Exception:
        pass

    # Tertiary — try to resolve course if no subject matched
    if not subject_db_id and hasattr(req, 'course_id') and req.course_id:
        course_db_id  = req.course_id
        lecturer_id   = _get_lecturer_for_course(req.student_id, course_db_id, db)

    if not subject_db_id and not course_db_id:
        # Soft fail — log without subject rather than crashing
        subject_db_id = None

    # ── 2. Grade answer ───────────────────────────────────────────
    is_correct = (req.student_answer.strip().lower() ==
                  req.correct_answer.strip().lower())

    # ── 3. BKT mastery update ─────────────────────────────────────
    try:
        bkt_result = update_mastery(
            req.student_id,
            subject_db_id or course_db_id or 0,
            req.topic_id,
            is_correct, db, {}
        )
    except Exception:
        bkt_result = {'new_mastery_prob': 0.5}

    # ── 4. FCL point system ───────────────────────────────────────
    subject_obj  = (db.query(Subject).filter(Subject.id == subject_db_id).first()
                    if subject_db_id else None)
    student_name = student.name      if student     else 'Student'
    subject_name = subject_obj.name  if subject_obj else req.topic_id

    pts_result = process_quiz_answer(
        student_id      = req.student_id,
        topic_id        = req.topic_id,
        is_correct      = is_correct,
        hints_used      = req.hints_used,
        tutor_consulted = req.tutor_consulted,
        question_id     = req.question_id or f'q-{req.student_id}-{req.topic_id}',
        teacher_id      = teacher_id,
        lecturer_id     = lecturer_id,
        student_name    = student_name,
        subject_name    = subject_name,
        db              = db,
        subject_id      = subject_db_id,
        course_id       = course_db_id,
        session_id      = None,
    )

    # ── 5. Log assessment ─────────────────────────────────────────
    try:
        db.add(Assessment(
            student_id    = req.student_id,
            subject_id    = subject_db_id,
            course_id     = course_db_id,
            topic_id      = req.topic_id,
            question_id   = req.question_id or f'q-{req.student_id}-{req.topic_id}',
            is_correct    = is_correct,
            fcl_level     = pts_result['topic_fcl'],
            hints_used    = req.hints_used,
            points_earned = pts_result['points_earned'],
            aids_used     = req.hints_used + (1 if req.tutor_consulted else 0),
        ))
        db.commit()
    except Exception as e:
        print(f'[Assessment log warning] {e}')
        db.rollback()

    # ── 6. Generate AI feedback ───────────────────────────────────
    try:
        feedback_result = generate_feedback(
            question_text   = req.question_text or '',
            selected_answer = req.student_answer,
            correct_answer  = req.correct_answer,
            topic           = req.topic_id,
            fcl_level       = pts_result['topic_fcl'],
            app_state       = None,
            db              = db,
            student_id      = req.student_id,
        )
        feedback_text = (
            feedback_result.get('feedback', '') + ' ' +
            (feedback_result.get('explanation') or '')
        ).strip()
    except Exception as e:
        print(f'[Feedback warning] {e}')
        feedback_text = (
            'Correct! Well done.' if is_correct
            else f'Incorrect. The correct answer was: {req.correct_answer}'
        )

    # ── 7. Return result ──────────────────────────────────────────
    return AssessmentResponse(
        is_correct          = is_correct,
        feedback_text       = feedback_text,
        new_mastery_prob    = bkt_result.get('new_mastery_prob', 0.5),
        fcl_changed         = pts_result['fcl_changed'],
        new_fcl             = pts_result['new_fcl'] if pts_result['fcl_changed'] else None,
        adaptation_decision = None,
        points_earned       = pts_result['points_earned'],
        total_points        = pts_result['total_points'],
        topic_fcl           = pts_result['topic_fcl'],
        points_within_level = pts_result['points_within_level'],
        points_to_next_fcl  = pts_result['points_to_next_fcl'],
        subject_fcl         = pts_result['subject_fcl'],
        overall_fcl         = pts_result['overall_fcl'],
    )


# ══════════════════════════════════════════════════════════════════
#  QUIZ COMPLETE (bonus points)
# ══════════════════════════════════════════════════════════════════

@router.post('/complete')
def quiz_complete(req: QuizCompleteRequest,
                  db: Session = Depends(get_db),
                  current_user = Depends(get_current_student)):
    bonus = min(req.correct_count * 10, 100)
    if bonus == 0:
        return {'bonus_awarded': 0, 'fcl_changed': False}

    try:
        code = next((c for p, c in TOPIC_PREFIX_MAP.items()
                     if req.topic_id.startswith(p)), None)
        if not code:
            return {'bonus_awarded': 0, 'fcl_changed': False}
        subj = db.query(Subject).filter(Subject.code == code).first()
        if not subj:
            return {'bonus_awarded': 0, 'fcl_changed': False}

        result = award_topic_points(
            student_id = req.student_id,
            topic_id   = req.topic_id,
            points     = bonus,
            reason     = f'quiz_completion_{req.correct_count}_correct',
            db         = db,
            subject_id = subj.id,
        )
        return {
            'bonus_awarded': bonus,
            'fcl_changed':   result.get('fcl_changed', False),
            'new_fcl':       result.get('new_fcl') if result.get('fcl_changed') else None,
        }
    except Exception as e:
        print(f'[Quiz complete error] {e}')
        return {'bonus_awarded': 0, 'fcl_changed': False}


# ══════════════════════════════════════════════════════════════════
#  QUIZ HISTORY
# ══════════════════════════════════════════════════════════════════

@router.get('/history')
def get_quiz_history(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_student),
):
    student_id  = current_user.id
    assessments = (
        db.query(Assessment)
        .filter(Assessment.student_id == student_id)
        .order_by(Assessment.created_at.desc())
        .all()
    )
    grouped = {}
    for a in assessments:
        date_key = a.created_at.date() if a.created_at else 'unknown'
        key = (a.topic_id, date_key)
        grouped.setdefault(key, []).append(a)

    history = []
    for (topic_id, date_key), group in list(grouped.items())[:limit]:
        correct = sum(1 for a in group if a.is_correct)
        score   = round(correct / len(group) * 100) if group else 0
        subject = (db.query(Subject).filter(Subject.id == group[0].subject_id).first()
                   if group[0].subject_id else None)
        history.append({
            'id':             f'{topic_id}-{date_key}',
            'score':          score,
            'completedAt':    group[0].created_at.isoformat() if group[0].created_at else None,
            'topicId':        topic_id,
            'subjectName':    subject.name if subject else topic_id,
            'questionsCount': len(group),
        })
    return history


# ══════════════════════════════════════════════════════════════════
#  POINTS SUMMARY
# ══════════════════════════════════════════════════════════════════

@router.get('/points/{student_id}')
def get_points_summary(student_id: int,
                        db: Session = Depends(get_db),
                        current_user = Depends(get_current_student)):
    from services.points_service import get_student_points_summary
    return get_student_points_summary(student_id, db)


@router.get('/topic-fcl/{student_id}/{subject_id}/{topic_id}')
def get_single_topic_fcl(student_id: int, subject_id: int, topic_id: str,
                           db: Session = Depends(get_db),
                           current_user = Depends(get_current_student)):
    row = db.execute(text(
        'SELECT total_points, current_fcl FROM topic_fcl '
        'WHERE student_id=:sid AND subject_id=:subid AND topic_id=:tid'
    ), {'sid': student_id, 'subid': subject_id, 'tid': topic_id}).fetchone()
    if not row:
        student  = _get_student(student_id, db)
        grade    = student.grade.order_index if (student and student.grade) else 1
        init_fcl = grade_to_initial_fcl(grade)
        return {
            'topic_fcl':           init_fcl,
            'total_points':        init_fcl * 1000,
            'points_within_level': 0,
            'points_to_next_fcl':  1000,
        }
    from services.points_service import fcl_from_points, points_within_level, points_to_next_fcl
    tp = row[0]
    return {
        'topic_fcl':           fcl_from_points(tp),
        'total_points':        tp,
        'points_within_level': points_within_level(tp),
        'points_to_next_fcl':  points_to_next_fcl(tp),
    }


# ══════════════════════════════════════════════════════════════════
#  QUIZ ABANDONMENT
#  CHANGED: StudentSubject teacher lookup → teacher_class_subjects.
#  Notification now uses receiver_type/receiver_id.
# ══════════════════════════════════════════════════════════════════

@router.post('/abandoned')
def quiz_abandoned(req: QuizAbandonRequest,
                   db: Session = Depends(get_db),
                   current_user = Depends(get_current_student)):
    try:
        student = _get_student(req.student_id, db)
        name    = student.name if student else 'A student'
        code    = next((c for p, c in TOPIC_PREFIX_MAP.items()
                        if req.topic_id.startswith(p)), None)
        if not code:
            return {'status': 'no_subject_match'}
        subj = db.query(Subject).filter(Subject.code == code).first()
        if not subj:
            return {'status': 'subject_not_found'}

        teacher_id = _get_teacher_for_subject(student, subj.id, db)

        if teacher_id and req.abandon_count >= 3:
            db.add(Notification(
                receiver_type = 'teacher',
                receiver_id   = teacher_id,
                sender_type   = 'student',
                sender_id     = req.student_id,
                subject_id    = subj.id,
                type          = 'quiz_abandonment_alert',
                title         = f'⚠️ {name} has abandoned {req.abandon_count} quizzes',
                body          = (
                    f'{name} has left {req.abandon_count} quizzes incomplete '
                    f'in {req.topic_id.replace("_", " ")}. Consider reaching out.'
                ),
                action_url    = '/teacher',
            ))
            db.commit()
            return {'status': 'teacher_notified'}
        return {'status': 'recorded'}
    except Exception as e:
        return {'status': 'error', 'detail': str(e)}
