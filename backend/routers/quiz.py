from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from db.database import get_db
from db.schemas  import AssessmentSubmitRequest, AssessmentResponse
from db.models   import (Assessment, Student, Subject,
                          StudentSubject, Notification)
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
    student_id: int
    topic:      str
    fcl_level:  int = 5
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

def _get_student_grade(student_id: int, db: Session) -> int:
    student = db.query(Student).filter(Student.id == student_id).first()
    return student.grade if student else 1


def _get_real_fcl(student_id: int, topic_id: str,
                   subject_id: int, db: Session) -> int:
    try:
        return get_topic_fcl(student_id, subject_id, topic_id, db)
    except Exception:
        grade = _get_student_grade(student_id, db)
        return grade_to_initial_fcl(grade)


def _get_learning_style(student_id: int, subject_id: int,
                          db: Session) -> str:
    try:
        from db.models import StudentSubjectStyle, StudentPreference
        style = db.query(StudentSubjectStyle).filter(
            StudentSubjectStyle.student_id == student_id,
            StudentSubjectStyle.subject_id == subject_id,
        ).first()
        if style:
            return style.learning_style
        pref = db.query(StudentPreference).filter(
            StudentPreference.student_id == student_id
        ).first()
        return pref.preferred_learning_style if pref else 'reading'
    except Exception:
        return 'reading'


# ══════════════════════════════════════════════════════════════════
#  GENERATE QUESTION
# ══════════════════════════════════════════════════════════════════

@router.post('/generate-question')
def generate_quiz_question(req: QuizGenerateRequest,
                            db: Session = Depends(get_db),
                            current_user = Depends(get_current_student)):
    # Resolve subject
    try:
        from services.subject_service import TOPIC_PREFIX_MAP
        code = next((c for p,c in TOPIC_PREFIX_MAP.items() if req.topic.startswith(p)), 'MATH')
        subject_db_id = None
        subj = db.query(Subject).filter(Subject.code == code).first()
        if subj:
            subject_db_id = subj.id
    except Exception:
        subject_db_id = None

    real_fcl       = _get_real_fcl(req.student_id, req.topic, subject_db_id or 1, db)
    learning_style = req.learning_style or _get_learning_style(req.student_id, subject_db_id or 1, db)

    question = generate_question(
        topic           = req.topic,
        fcl_level       = real_fcl,
        app_state       = None,
        learning_style  = learning_style,
    )
    question['fcl_used']       = real_fcl
    question['subject_db_id']  = subject_db_id
    return question


# ══════════════════════════════════════════════════════════════════
#  SUBMIT ANSWER
# ══════════════════════════════════════════════════════════════════

@router.post('/submit', response_model=AssessmentResponse)
def submit_assessment(req: AssessmentSubmitRequest,
                       db: Session = Depends(get_db),
                       current_user = Depends(get_current_student)):
    # ── 1. Resolve subject + teacher ─────────────────────────────
    teacher_id    = None
    subject_db_id = None
    try:
        code = next((c for p,c in TOPIC_PREFIX_MAP.items() if req.topic_id.startswith(p)), None)
        if code:
            subj = db.query(Subject).filter(Subject.code == code).first()
            if subj:
                subject_db_id = subj.id
                enrollment = db.query(StudentSubject).filter(
                    StudentSubject.student_id == req.student_id,
                    StudentSubject.subject_id == subj.id,
                ).first()
                teacher_id = enrollment.teacher_id if enrollment else None
    except Exception:
        pass

    if not subject_db_id:
        raise HTTPException(400, f'Could not resolve subject for topic: {req.topic_id}')

    # ── 2. Grade answer ───────────────────────────────────────────
    is_correct = (req.student_answer.strip().lower() ==
                  req.correct_answer.strip().lower())

    # ── 3. BKT mastery update ─────────────────────────────────────
    try:
        bkt_result = update_mastery(
            req.student_id, subject_db_id, req.topic_id,
            is_correct, db, {}
        )
    except Exception:
        bkt_result = {'new_mastery_prob': 0.5}

    # ── 4. FCL point system ───────────────────────────────────────
    student      = db.query(Student).filter(Student.id == req.student_id).first()
    subject_obj  = db.query(Subject).filter(Subject.id == subject_db_id).first()
    student_name = student.name if student else 'Student'
    subject_name = subject_obj.name if subject_obj else req.topic_id

    pts_result = process_quiz_answer(
        student_id      = req.student_id,
        subject_id      = subject_db_id,
        topic_id        = req.topic_id,
        is_correct      = is_correct,
        hints_used      = req.hints_used,
        tutor_consulted = req.tutor_consulted,
        question_id     = req.question_id or f'q-{req.student_id}-{req.topic_id}',
        teacher_id      = teacher_id,
        student_name    = student_name,
        subject_name    = subject_name,
        db              = db,
        session_id      = None,
    )

    # ── 5. Log assessment ─────────────────────────────────────────
    try:
        db.add(Assessment(
            student_id    = req.student_id,
            subject_id    = subject_db_id,
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
#  QUIZ COMPLETE (award bonus points)
# ══════════════════════════════════════════════════════════════════

@router.post('/complete')
def quiz_complete(req: QuizCompleteRequest,
                  db: Session = Depends(get_db),
                  current_user = Depends(get_current_student)):
    # Calculate bonus: 10 points per correct answer, max 100
    bonus = min(req.correct_count * 10, 100)
    if bonus == 0:
        return {'bonus_awarded': 0, 'fcl_changed': False}

    # Resolve subject from topic_id
    try:
        code = None
        for prefix, c in TOPIC_PREFIX_MAP.items():
            if req.topic_id.startswith(prefix):
                code = c
                break
        if not code:
            return {'bonus_awarded': 0, 'fcl_changed': False}
        subj = db.query(Subject).filter(Subject.code == code).first()
        if not subj:
            return {'bonus_awarded': 0, 'fcl_changed': False}

        result = award_topic_points(
            student_id=req.student_id,
            subject_id=subj.id,
            topic_id=req.topic_id,
            points=bonus,
            reason=f'quiz_completion_{req.correct_count}_correct',
            db=db,
        )
        return {
            'bonus_awarded': bonus,
            'fcl_changed': result.get('fcl_changed', False),
            'new_fcl': result.get('new_fcl') if result.get('fcl_changed') else None,
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
    student_id = current_user.id
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
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(a)
    history = []
    for (topic_id, date_key), group in list(grouped.items())[:limit]:
        correct = sum(1 for a in group if a.is_correct)
        score = round(correct / len(group) * 100) if group else 0
        subject = db.query(Subject).filter(Subject.id == group[0].subject_id).first()
        history.append({
            'id': f'{topic_id}-{date_key}',
            'score': score,
            'completedAt': group[0].created_at.isoformat() if group[0].created_at else None,
            'topicId': topic_id,
            'subjectName': subject.name if subject else topic_id,
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
    from sqlalchemy import text
    row = db.execute(text(
        'SELECT total_points, current_fcl FROM topic_fcl '
        'WHERE student_id=:sid AND subject_id=:subid AND topic_id=:tid'
    ), {'sid': student_id, 'subid': subject_id, 'tid': topic_id}).fetchone()
    if not row:
        grade   = _get_student_grade(student_id, db)
        init_fcl= grade_to_initial_fcl(grade)
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
# ══════════════════════════════════════════════════════════════════

@router.post('/abandoned')
def quiz_abandoned(req: QuizAbandonRequest,
                   db: Session = Depends(get_db),
                   current_user = Depends(get_current_student)):
    try:
        student = db.query(Student).filter(Student.id == req.student_id).first()
        name    = student.name if student else 'A student'
        code    = next((c for p,c in TOPIC_PREFIX_MAP.items() if req.topic_id.startswith(p)), None)
        if not code:
            return {'status': 'no_subject_match'}
        subj = db.query(Subject).filter(Subject.code == code).first()
        if not subj:
            return {'status': 'subject_not_found'}
        enroll = db.query(StudentSubject).filter(
            StudentSubject.student_id == req.student_id,
            StudentSubject.subject_id == subj.id,
        ).first()
        teacher_id = enroll.teacher_id if enroll else None
        if teacher_id and req.abandon_count >= 3:
            db.add(Notification(
                student_id = teacher_id,
                sender_id  = req.student_id,
                subject_id = subj.id,
                type       = 'quiz_abandonment_alert',
                title      = f'⚠️ {name} has abandoned {req.abandon_count} quizzes',
                body       = (
                    f'{name} has left {req.abandon_count} quizzes incomplete '
                    f'in {req.topic_id.replace("_"," ")}. Consider reaching out.'
                ),
                action_url = '/teacher',
            ))
            db.commit()
            return {'status': 'teacher_notified'}
        return {'status': 'recorded'}
    except Exception as e:
        return {'status': 'error', 'detail': str(e)}