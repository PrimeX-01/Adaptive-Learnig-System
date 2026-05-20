from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import re, math, base64, os
import urllib.parse

from db.database import get_db
from db.schemas import QuizGenerateRequest, AssessmentSubmitRequest, AssessmentResponse
from db.models import Assessment, Student, Subject, StudentSubject, Notification
from services.subject_service import resolve_subject_and_teacher, notify_subject_teacher, TOPIC_PREFIX_MAP
from services.llm_service import generate_question, generate_feedback
from services.points_service import process_quiz_answer_with_topic
from services.fcl_service import award_topic_points, get_topic_fcl, get_subject_fcl, get_overall_fcl
from auth import get_current_student

router = APIRouter()

# ================================================================
# Helper: grade to baseline FCL
# ================================================================
def _grade_to_fcl(grade: int | None) -> int:
    if not grade or grade <= 0: return 5
    if grade <= 4:  return 2
    if grade <= 7:  return 4
    if grade <= 9:  return 6
    if grade <= 12: return 8
    if grade <= 15: return 9
    if grade <= 17: return 11
    return 13

# ================================================================
# Determine starting FCL
# ================================================================
def _resolve_starting_fcl(student_id: int, topic: str,
                           requested_fcl: int, db: Session) -> int:
    student = db.query(Student).filter(Student.id == student_id).first()
    if student and student.grade:
        grade_fcl = _grade_to_fcl(student.grade)
        print(f"[DEBUG] Using grade-based FCL: {grade_fcl} (grade {student.grade})")
        return grade_fcl
    print(f"[DEBUG] Using requested FCL: {requested_fcl}")
    return max(1, min(13, requested_fcl or 5))

# ================================================================
# SVG coordinate-plane image generator (no external API needed)
# ================================================================
def _build_pollinations_url(question_text: str) -> str:
    """Build an educational image prompt from question text for Pollinations."""
    # Strip option labels and clean up
    clean = re.sub(r'\b[A-D]\.\s*', '', question_text)
    clean = re.sub(r'\s+', ' ', clean).strip()[:200]
    prompt = (
        f"educational illustration for children: {clean}, "
        "colorful cartoon style, simple clear visuals, no text, white background"
    )
    encoded = urllib.parse.quote(prompt)
    return f"https://image.pollinations.ai/prompt/{encoded}?width=512&height=512&nologo=true&seed=42"


def _extract_coordinates(question_text: str) -> list[tuple[float, float]]:
    """Extract numeric coordinate pairs from question text."""
    matches = re.findall(r"\(\s*([+-]?\d+(?:\.\d+)?)\s*,\s*([+-]?\d+(?:\.\d+)?)\s*\)", question_text)
    coords = []
    for x_str, y_str in matches:
        x = float(x_str)
        y = float(y_str)
        if x.is_integer():
            x = int(x)
        if y.is_integer():
            y = int(y)
        coords.append((x, y))
    return coords


def _generate_question_image(question_text: str) -> Optional[str]:
    """
    1. If coordinates found → generate SVG diagram (instant, no API).
    2. Otherwise → return a Pollinations URL for the browser to load.
    """
    # Try coordinate-based SVG first
    coords = _extract_coordinates(question_text)
    if coords:
        result = _generate_math_svg_from_coords(coords, question_text)
        if result:
            print(f"[Image] SVG generated from {len(coords)} coordinate(s)")
            return result

    # Fall back to Pollinations for all other questions
    url = _build_pollinations_url(question_text)
    print(f"[Image] Pollinations URL built for question")
    return url

def _generate_math_svg_from_coords(coords: list, question_text: str) -> Optional[str]:
    """Takes pre-extracted coords and returns a base64 SVG data URI."""
    if not coords:
        return None

    W, H, PAD = 320, 320, 48
    xs, ys = [p[0] for p in coords], [p[1] for p in coords]
    x_min, x_max = min(xs) - 1, max(xs) + 1
    y_min, y_max = min(ys) - 1, max(ys) + 1
    span = max(x_max - x_min, y_max - y_min, 4)
    cx, cy = (x_min + x_max) / 2, (y_min + y_max) / 2
    x_min, x_max = cx - span / 2, cx + span / 2
    y_min, y_max = cy - span / 2, cy + span / 2
    pw, ph = W - 2 * PAD, H - 2 * PAD

    def to_px(x, y):
        return (
            round(PAD + (x - x_min) / (x_max - x_min) * pw, 1),
            round(H - PAD - (y - y_min) / (y_max - y_min) * ph, 1),
        )

    step = 1 if span <= 8 else (2 if span <= 16 else 5)
    grid_lines = []
    x_tick = math.ceil(x_min / step) * step
    while x_tick <= x_max:
        gx, _ = to_px(x_tick, y_min)
        _, gt = to_px(x_tick, y_max)
        _, gb = to_px(x_tick, y_min)
        grid_lines.append(f'<line x1="{gx}" y1="{gt}" x2="{gx}" y2="{gb}" stroke="#e2e8f0" stroke-width="0.8"/>')
        if x_tick != 0:
            lx, ly = to_px(x_tick, max(y_min, min(0, y_max)))
            label = int(x_tick) if x_tick == int(x_tick) else x_tick
            grid_lines.append(f'<text x="{lx}" y="{ly+14}" text-anchor="middle" font-size="9" fill="#94a3b8">{label}</text>')
        x_tick = round(x_tick + step, 6)

    y_tick = math.ceil(y_min / step) * step
    while y_tick <= y_max:
        _, gy = to_px(x_min, y_tick)
        xl, _ = to_px(x_min, y_tick)
        xr, _ = to_px(x_max, y_tick)
        grid_lines.append(f'<line x1="{xl}" y1="{gy}" x2="{xr}" y2="{gy}" stroke="#e2e8f0" stroke-width="0.8"/>')
        if y_tick != 0:
            lx, ly = to_px(max(x_min, min(0, x_max)), y_tick)
            label = int(y_tick) if y_tick == int(y_tick) else y_tick
            grid_lines.append(f'<text x="{lx-6}" y="{ly+3}" text-anchor="end" font-size="9" fill="#94a3b8">{label}</text>')
        y_tick = round(y_tick + step, 6)

    axes = []
    if y_min <= 0 <= y_max:
        a1, a2 = to_px(x_min, 0), to_px(x_max, 0)
        axes.append(f'<line x1="{a1[0]}" y1="{a1[1]}" x2="{a2[0]}" y2="{a2[1]}" stroke="#475569" stroke-width="1.5" marker-end="url(#arr)"/>')
    if x_min <= 0 <= x_max:
        b1, b2 = to_px(0, y_min), to_px(0, y_max)
        axes.append(f'<line x1="{b1[0]}" y1="{b1[1]}" x2="{b2[0]}" y2="{b2[1]}" stroke="#475569" stroke-width="1.5" marker-end="url(#arr)"/>')

    if len(coords) >= 3:
        pts = ' '.join(f'{to_px(x, y)[0]},{to_px(x, y)[1]}' for x, y in coords)
        shape = f'<polygon points="{pts}" fill="rgba(20,184,166,0.12)" stroke="#14b8a6" stroke-width="1.8"/>'
    elif len(coords) == 2:
        p1, p2 = to_px(*coords[0]), to_px(*coords[1])
        shape = f'<line x1="{p1[0]}" y1="{p1[1]}" x2="{p2[0]}" y2="{p2[1]}" stroke="#14b8a6" stroke-width="2"/>'
    else:
        shape = ''

    COLORS = ['#f43f5e', '#3b82f6', '#a855f7', '#f97316', '#22c55e']
    dots = []
    for i, (x, y) in enumerate(coords):
        ppx, ppy = to_px(x, y)
        col = COLORS[i % len(COLORS)]
        lbl = 'ABCDEFGH'[i] if len(coords) <= 8 else ''
        lx = ppx + 8 if ppx < W - 30 else ppx - 18
        ly = ppy - 8 if ppy > 20 else ppy + 16
        xi = int(x) if x == int(x) else x
        yi = int(y) if y == int(y) else y
        dots.append(f'<circle cx="{ppx}" cy="{ppy}" r="5" fill="{col}" stroke="white" stroke-width="1.5"/>')
        dots.append(f'<text x="{lx}" y="{ly}" font-size="11" font-weight="bold" fill="{col}">{lbl}({xi},{yi})</text>')

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
        f'<defs><marker id="arr" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">'
        f'<path d="M0,0 L0,6 L6,3 z" fill="#475569"/></marker></defs>'
        f'<rect width="{W}" height="{H}" fill="white" rx="8"/>'
        f'{"".join(grid_lines)}{"".join(axes)}{shape}{"".join(dots)}'
        f'<text x="{W//2}" y="{H-8}" text-anchor="middle" font-size="10" fill="#64748b" font-family="sans-serif">Coordinate Plane</text>'
        f'</svg>'
    )
    b64 = base64.b64encode(svg.encode()).decode()
    return f"data:image/svg+xml;base64,{b64}"


# ================================================================
# Generate question endpoint
# ================================================================
@router.post('/generate-question')
def generate_quiz_question(req: QuizGenerateRequest, request: Request,
                            db: Session = Depends(get_db),
                            current_user = Depends(get_current_student)):
    try:
        real_fcl = _resolve_starting_fcl(
            student_id=req.student_id,
            topic=req.topic,
            requested_fcl=req.fcl_level,
            db=db,
        )

        learning_style = req.learning_style
        if not learning_style or learning_style == 'reading':
            student = db.query(Student).filter(Student.id == req.student_id).first()
            if student and student.preferences:
                learning_style = student.preferences.preferred_learning_style or 'reading'

        question = generate_question(
            topic=req.topic,
            fcl_level=real_fcl,
            app_state=request.app.state,
            learning_style=learning_style,
            recent_questions=None,
        )

        if not question or not question.get('question_text') or not question.get('options'):
            raise HTTPException(500, 'Question generation returned incomplete data')

        question['fcl_used'] = real_fcl

        # Strip [IMAGE: ...] placeholders the LLM embeds in question text
        question['question_text'] = re.sub(r'\[IMAGE:[^\]]*\]', '', question['question_text']).strip()

        if learning_style == 'visual':
            print(f"[Image] Generating for visual learner: {req.student_id}")
            image_url = _generate_question_image(question['question_text'])
            if image_url:
                question['image_url'] = image_url
            else:
                print("[Image] No coordinates in question, skipping image")

        return question  # <-- THIS WAS MISSING

    except HTTPException:
        raise
    except Exception as e:
        print(f'[ERROR] generate_quiz_question: {e}')
        raise HTTPException(status_code=500, detail=f'Question generation failed: {str(e)}')

# ================================================================
# Submit answer endpoint (uses new topic-based points)
# ================================================================
@router.post('/submit', response_model=AssessmentResponse)
def submit_assessment(req: AssessmentSubmitRequest, request: Request,
                       db: Session = Depends(get_db),
                       current_user = Depends(get_current_student)):
    # 1. Resolve subject and teacher
    try:
        subj = resolve_subject_and_teacher(
            req.topic_id, req.student_id,
            request.app.state.fcl_mapping, db,
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(500, f'Subject resolution failed: {e}')

    subject_db_id = subj['subject_db_id']
    teacher_id = subj['teacher_id']

    # 2. Grade the answer
    is_correct = req.student_answer.strip().lower() == req.correct_answer.strip().lower()

    # 3. Get student and subject names for notifications
    student = db.query(Student).filter(Student.id == req.student_id).first()
    student_name = student.name if student else 'Student'
    subject_obj = db.query(Subject).filter(Subject.id == subject_db_id).first()
    subject_name = subject_obj.name if subject_obj else req.topic_id

    # 4. Process quiz answer using the new topic-based points system
    pts_result = process_quiz_answer_with_topic(
        student_id=req.student_id,
        subject_id=subject_db_id,
        topic_id=req.topic_id,
        is_correct=is_correct,
        hints_used=req.hints_used,
        tutor_consulted=req.tutor_consulted,
        question_id=req.question_id or f'q-{req.student_id}-{req.topic_id}',
        teacher_id=teacher_id,
        student_name=student_name,
        subject_name=subject_name,
        db=db,
    )

    # 5. Log the assessment
    db.add(Assessment(
        student_id=req.student_id,
        subject_id=subject_db_id,
        topic_id=req.topic_id,
        question_id=req.question_id or f'q-{req.student_id}-{req.topic_id}',
        is_correct=is_correct,
        fcl_level=req.fcl_level,
        hints_used=req.hints_used,
    ))
    db.commit()

    # 6. Notify teacher if FCL changed
    if pts_result.get('fcl_changed') and teacher_id:
        try:
            notify_subject_teacher(
                student_id=req.student_id,
                subject_db_id=subject_db_id,
                teacher_id=teacher_id,
                student_name=student_name,
                notif_type='student_level_change',
                title=f'{student_name} advanced in {subject_name}',
                body=f'Topic {req.topic_id} reached a new level.',
                action_url='/teacher',
                db=db,
            )
            db.commit()
        except Exception as e:
            print(f'[Notify Warning] {e}')

    # 7. Generate AI feedback
    try:
        feedback_result = generate_feedback(
            question_text=req.question_text or '',
            selected_answer=req.student_answer,
            correct_answer=req.correct_answer,
            topic=req.topic_id,
            fcl_level=req.fcl_level,
            app_state=request.app.state,
            db=db,
            student_id=req.student_id,
        )
        feedback_text = (feedback_result.get('feedback', '') + ' ' + (feedback_result.get('explanation') or '')).strip()
    except Exception as e:
        print(f'[Feedback Warning] {e}')
        feedback_text = 'Correct! Well done.' if is_correct else f'Incorrect. The correct answer was: {req.correct_answer}'

    # 8. Prepare response
    return AssessmentResponse(
        is_correct=is_correct,
        feedback_text=feedback_text,
        new_mastery_prob=0.5,
        fcl_changed=pts_result.get('fcl_changed', False),
        new_fcl=pts_result.get('new_fcl'),
        adaptation_decision=None,
        points_earned=pts_result.get('points_earned') or 0,
        current_points=pts_result.get('current_points') or 0,
        points_to_next_fcl=pts_result.get('points_to_next_fcl') or 100,
        subject_fcl=pts_result.get('subject_fcl'),
    )

# ================================================================
# Quiz abandonment
# ================================================================
class QuizAbandonRequest(BaseModel):
    student_id: int
    topic_id: str
    abandon_count: int

@router.post('/abandoned')
def quiz_abandoned(req: QuizAbandonRequest, db: Session = Depends(get_db),
                   current_user = Depends(get_current_student)):
    try:
        student = db.query(Student).filter(Student.id == req.student_id).first()
        name = student.name if student else 'A student'
        code = next((c for p, c in TOPIC_PREFIX_MAP.items() if req.topic_id.startswith(p)), None)
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
                student_id=teacher_id,
                sender_id=req.student_id,
                subject_id=subj.id,
                type='quiz_abandonment_alert',
                title=f'⚠️ {name} has abandoned {req.abandon_count} quizzes',
                body=f'{name} has left {req.abandon_count} quizzes incomplete in {req.topic_id.replace("_", " ")}. Consider reaching out to offer support.',
                action_url='/teacher',
            ))
            db.commit()
            return {'status': 'teacher_notified', 'abandon_count': req.abandon_count}
        return {'status': 'recorded', 'abandon_count': req.abandon_count}
    except Exception as e:
        return {'status': 'error', 'detail': str(e)}

@router.get('/points/{student_id}')
def get_points_summary(student_id: int, db: Session = Depends(get_db),
                       current_user = Depends(get_current_student)):
    """Deprecated — kept to avoid frontend errors."""
    return []