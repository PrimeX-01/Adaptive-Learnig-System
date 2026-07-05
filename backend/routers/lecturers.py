from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta

from db.database import get_db
from db.models import (
    Lecturer, Student, Course, Programme, Faculty,
    ProgrammeCourseLevel, LecturerCourseAssignment,
    StudentCourseEnrollment, Assessment, TopicFcl,
    ConversationSession, Notification, TeacherAiDirective,
    TeacherPointAward,
)
from auth import get_current_lecturer

router = APIRouter(prefix='/api/lecturers', tags=['Lecturers'])


# ═══════════════════════════════════════════════════════════════════
#  SCHEMAS
# ═══════════════════════════════════════════════════════════════════

class ProfileUpdate(BaseModel):
    name:            Optional[str] = None
    username:        Optional[str] = None
    bio:             Optional[str] = None
    email:           Optional[str] = None
    profile_picture: Optional[str] = None

class DirectiveCreate(BaseModel):
    student_id: Optional[int] = None
    course_id:  Optional[int] = None
    directive:  str
    label:      Optional[str] = None

class DirectiveUpdate(BaseModel):
    directive: Optional[str]  = None
    label:     Optional[str]  = None
    is_active: Optional[bool] = None

class AwardPointsRequest(BaseModel):
    student_id: int
    course_id:  int
    topic_id:   str
    points:     int
    reason:     str

class BulkTipRequest(BaseModel):
    student_ids: List[int]
    topic_id:    str
    custom_note: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════

def _get_lecturer_course_ids(lecturer: Lecturer) -> List[int]:
    return list({
        lca.pcl.course_id
        for lca in lecturer.course_assignments
        if lca.pcl
    })

def _get_lecturer_pcl_ids(lecturer: Lecturer) -> List[int]:
    return [lca.pcl_id for lca in lecturer.course_assignments]

def _get_students_for_lecturer(lecturer_id: int, db: Session):
    """All students enrolled in any pcl this lecturer is assigned to."""
    rows = db.execute(text('''
        SELECT DISTINCT s.id, s.name, s.email, s.profile_picture,
                        p.name AS programme_name, pcl.level, pcl.semester,
                        pcl.id AS pcl_id, c.name AS course_name, c.id AS course_id
        FROM lecturer_course_assignments lca
        JOIN programme_course_levels pcl ON pcl.id = lca.pcl_id
        JOIN programmes p ON p.id = pcl.programme_id
        JOIN courses    c ON c.id = pcl.course_id
        JOIN student_course_enrollments sce ON sce.pcl_id = pcl.id
        JOIN students s ON s.id = sce.student_id
        WHERE lca.lecturer_id = :lid
        ORDER BY p.name, pcl.level, s.name
    '''), {'lid': lecturer_id}).fetchall()
    return rows

def _course_fcl(student_id: int, course_id: int, db: Session) -> float:
    rows = db.execute(text(
        'SELECT total_points FROM topic_fcl '
        'WHERE student_id=:sid AND course_id=:cid AND is_active=true'
    ), {'sid': student_id, 'cid': course_id}).fetchall()
    if not rows:
        return 1.0
    fcls = [max(1, r[0] // 1000) for r in rows]
    return round(sum(fcls) / len(fcls), 1)


# ═══════════════════════════════════════════════════════════════════
#  PROFILE
# ═══════════════════════════════════════════════════════════════════

@router.get('/profile/{lecturer_id}')
def get_profile(lecturer_id: int, db: Session = Depends(get_db),
                current: Lecturer = Depends(get_current_lecturer)):
    l = db.query(Lecturer).filter(Lecturer.id == lecturer_id).first()
    if not l:
        raise HTTPException(404, 'Lecturer not found')
    return {
        'id':              l.id,
        'name':            l.name,
        'email':           l.email,
        'username':        l.username,
        'bio':             l.bio,
        'profile_picture': l.profile_picture,
        'faculty_id':      l.faculty_id,
        'faculty_name':    l.faculty.name if l.faculty else '—',
        'status':          l.status,
        'registered_at':   l.registered_at.isoformat() if l.registered_at else None,
    }

@router.patch('/profile/{lecturer_id}')
def update_profile(lecturer_id: int, req: ProfileUpdate,
                   db: Session = Depends(get_db),
                   current: Lecturer = Depends(get_current_lecturer)):
    l = db.query(Lecturer).filter(Lecturer.id == lecturer_id).first()
    if not l:
        raise HTTPException(404, 'Lecturer not found')
    if req.name            is not None: l.name            = req.name.strip()
    if req.username        is not None: l.username        = req.username.strip() or None
    if req.bio             is not None: l.bio             = req.bio.strip() or None
    if req.email           is not None: l.email           = req.email.strip()
    if req.profile_picture is not None: l.profile_picture = req.profile_picture
    db.commit()
    return {'message': 'Profile updated', 'name': l.name}


# ═══════════════════════════════════════════════════════════════════
#  DASHBOARD
# ═══════════════════════════════════════════════════════════════════

@router.get('/dashboard/{lecturer_id}')
def lecturer_dashboard(lecturer_id: int,
                       course_id: Optional[int] = None,
                       db: Session = Depends(get_db),
                       current: Lecturer = Depends(get_current_lecturer)):
    lecturer = db.query(Lecturer).filter(Lecturer.id == lecturer_id).first()
    if not lecturer:
        raise HTTPException(404, 'Lecturer not found')

    student_rows = _get_students_for_lecturer(lecturer_id, db)
    course_ids   = _get_lecturer_course_ids(lecturer)
    filter_course_ids = [course_id] if (course_id and course_id in course_ids) else course_ids

    students_out = []
    at_risk      = []
    fcl_sum      = 0
    fcl_count    = 0
    seen_pairs   = set()

    for r in student_rows:
        sid, c_id = r[0], r[9]
        if c_id not in filter_course_ids:
            continue
        pair = (sid, c_id)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)

        cfcl = _course_fcl(sid, c_id, db)
        fcl_sum   += cfcl
        fcl_count += 1

        total_q = db.query(Assessment).filter(
            Assessment.student_id == sid,
            Assessment.course_id  == c_id,
        ).count()
        correct_q = db.query(Assessment).filter(
            Assessment.student_id == sid,
            Assessment.course_id  == c_id,
            Assessment.is_correct == True,
        ).count()
        accuracy = round(correct_q / total_q * 100) if total_q > 0 else 0
        is_at_risk = accuracy < 50 and total_q >= 5

        row = {
            'student_id':     sid,
            'name':           r[1],
            'email':          r[2],
            'programme_name': r[4],
            'level':          r[5],
            'semester':       r[6],
            'course_id':      c_id,
            'course_name':    r[8],
            'fcl_level':      cfcl,
            'accuracy':       accuracy,
            'total_attempts': total_q,
            'is_at_risk':     is_at_risk,
            'risk_reason':    'Low accuracy' if is_at_risk else '',
        }
        students_out.append(row)
        if is_at_risk:
            at_risk.append(row)

    fcl_buckets = {'FCL 1–5': 0, 'FCL 6–10': 0, 'FCL 11–15': 0, 'FCL 16–20': 0}
    for s in students_out:
        f = s['fcl_level']
        if f <= 5:   fcl_buckets['FCL 1–5']   += 1
        elif f <= 10:fcl_buckets['FCL 6–10']  += 1
        elif f <= 15:fcl_buckets['FCL 11–15'] += 1
        else:        fcl_buckets['FCL 16–20'] += 1
    fcl_distribution = [{'fcl_label': k, 'count': v} for k, v in fcl_buckets.items()]

    lecturer_courses = []
    seen_c = set()
    for lca in lecturer.course_assignments:
        pcl = lca.pcl
        if pcl.course_id not in seen_c:
            seen_c.add(pcl.course_id)
            lecturer_courses.append({
                'id':   pcl.course.id,
                'name': pcl.course.name,
                'code': pcl.course.code,
                'level':pcl.level,
            })

    total_students = len({s['student_id'] for s in students_out})
    avg_fcl        = round(fcl_sum / fcl_count, 1) if fcl_count > 0 else 0

    return {
        'stats': {
            'total_students': total_students,
            'courses_count':  len(lecturer_courses),
            'avg_fcl':        avg_fcl,
        },
        'lecturer_courses': lecturer_courses,
        'students':         students_out,
        'at_risk':          at_risk,
        'fcl_distribution': fcl_distribution,
    }


# ═══════════════════════════════════════════════════════════════════
#  SIMPLIFIED CURRENT-LECTURER ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@router.get('/dashboard')
def my_dashboard(db: Session = Depends(get_db),
                 current: Lecturer = Depends(get_current_lecturer)):
    return lecturer_dashboard(current.id, db=db, current=current)

@router.get('/students')
def my_students(db: Session = Depends(get_db),
                current: Lecturer = Depends(get_current_lecturer)):
    rows = _get_students_for_lecturer(current.id, db)
    seen = set()
    result = []
    for r in rows:
        if r[0] in seen:
            continue
        seen.add(r[0])
        result.append({
            'id': r[0], 'name': r[1], 'email': r[2],
            'programme_name': r[4], 'level': r[5],
        })
    return result

@router.get('/students/struggling')
def struggling_students(db: Session = Depends(get_db),
                        current: Lecturer = Depends(get_current_lecturer)):
    lecturer    = current
    course_ids  = _get_lecturer_course_ids(lecturer)
    rows        = _get_students_for_lecturer(lecturer.id, db)
    struggling  = []
    seen_pairs  = set()

    for r in rows:
        sid, c_id = r[0], r[9]
        if (sid, c_id) in seen_pairs:
            continue
        seen_pairs.add((sid, c_id))

        total = db.query(Assessment).filter(
            Assessment.student_id == sid,
            Assessment.course_id  == c_id,
        ).count()
        correct = db.query(Assessment).filter(
            Assessment.student_id == sid,
            Assessment.course_id  == c_id,
            Assessment.is_correct == True,
        ).count()
        accuracy = round(correct / total * 100) if total > 0 else 0
        if total >= 5 and accuracy < 50:
            cfcl = _course_fcl(sid, c_id, db)
            name_parts = r[1].split(' ', 1)
            struggling.append({
                'id':         sid,
                'first_name': name_parts[0],
                'last_name':  name_parts[1] if len(name_parts) > 1 else '',
                'fcl_level':  round(cfcl),
                'alert_reason': f'Accuracy {accuracy}% in {r[8]}',
                'is_struggling': True,
            })
    return struggling


# ═══════════════════════════════════════════════════════════════════
#  HEATMAP
# ═══════════════════════════════════════════════════════════════════

@router.get('/heatmap/{lecturer_id}')
def topic_heatmap(lecturer_id: int,
                  course_id: Optional[int] = None,
                  db: Session = Depends(get_db),
                  current: Lecturer = Depends(get_current_lecturer)):
    student_rows = _get_students_for_lecturer(lecturer_id, db)
    if not student_rows:
        return {'students': [], 'topics': [], 'data': []}

    lecturer    = db.query(Lecturer).filter(Lecturer.id == lecturer_id).first()
    course_ids  = ([course_id] if course_id else _get_lecturer_course_ids(lecturer))

    topic_ids = []
    for c_id in course_ids:
        rows = db.execute(text(
            'SELECT DISTINCT topic_id FROM topic_fcl WHERE course_id=:cid'
        ), {'cid': c_id}).fetchall()
        topic_ids.extend(r[0] for r in rows if r[0] not in topic_ids)

    if not topic_ids:
        return {'students': [], 'topics': topic_ids, 'data': []}

    seen_sids = []
    matrix = []
    students_meta = []
    for r in student_rows:
        sid = r[0]
        if sid in seen_sids:
            continue
        seen_sids.append(sid)
        row_data = []
        for topic_id in topic_ids:
            res = db.execute(text(
                'SELECT current_fcl FROM topic_fcl '
                'WHERE student_id=:sid AND topic_id=:tid AND is_active=true'
            ), {'sid': sid, 'tid': topic_id}).fetchone()
            fcl = res[0] if res else 0
            mastery = 0 if fcl <= 0 else (1 if fcl <= 5 else (2 if fcl <= 10 else 3))
            row_data.append(mastery)
        matrix.append(row_data)
        students_meta.append({'id': sid, 'name': r[1], 'programme_name': r[4]})

    return {
        'students': students_meta,
        'topics':   topic_ids,
        'data':     matrix,
    }


# ═══════════════════════════════════════════════════════════════════
#  ENGAGEMENT REPORT
# ═══════════════════════════════════════════════════════════════════

@router.get('/engagement/{lecturer_id}')
def engagement_report(lecturer_id: int,
                      days_inactive: int = 7,
                      db: Session = Depends(get_db),
                      current: Lecturer = Depends(get_current_lecturer)):
    student_rows = _get_students_for_lecturer(lecturer_id, db)
    result       = []
    seen_sids    = set()

    for r in student_rows:
        sid = r[0]
        if sid in seen_sids:
            continue
        seen_sids.add(sid)

        last_a = db.execute(text(
            'SELECT MAX(created_at) FROM assessments WHERE student_id=:sid'
        ), {'sid': sid}).scalar()
        last_c = db.execute(text(
            'SELECT MAX(started_at) FROM conversation_sessions WHERE student_id=:sid'
        ), {'sid': sid}).scalar()

        last_activity = None
        if last_a and last_c:
            last_activity = max(last_a, last_c)
        elif last_a:
            last_activity = last_a
        elif last_c:
            last_activity = last_c

        days = (datetime.utcnow() - last_activity).days if last_activity else 999
        if days >= days_inactive:
            result.append({
                'student_id':    sid,
                'name':          r[1],
                'email':         r[2],
                'programme_name':r[4],
                'level':         r[5],
                'days_inactive': days,
                'last_activity': last_activity.isoformat() if last_activity else None,
            })

    result.sort(key=lambda x: x['days_inactive'], reverse=True)
    return {
        'students':       result,
        'days_inactive':  days_inactive,
        'total_students': len(seen_sids),
    }


# ═══════════════════════════════════════════════════════════════════
#  AI DIRECTIVES
# ═══════════════════════════════════════════════════════════════════

@router.get('/directives')
def list_directives(db: Session = Depends(get_db),
                    current: Lecturer = Depends(get_current_lecturer)):
    rows = db.query(TeacherAiDirective).filter(
        TeacherAiDirective.lecturer_id == current.id
    ).order_by(TeacherAiDirective.created_at.desc()).all()
    return [
        {
            'id':          d.id,
            'student_id':  d.student_id,
            'course_id':   d.course_id,
            'directive':   d.directive,
            'instruction': d.directive,
            'label':       d.label,
            'is_active':   d.is_active,
            'created_at':  d.created_at.isoformat() if d.created_at else None,
        }
        for d in rows
    ]

@router.post('/directive')
def create_directive(req: DirectiveCreate,
                     db: Session = Depends(get_db),
                     current: Lecturer = Depends(get_current_lecturer)):
    if not req.directive.strip():
        raise HTTPException(400, 'Directive text is required')
    d = TeacherAiDirective(
        lecturer_id = current.id,
        student_id  = req.student_id,
        course_id   = req.course_id,
        directive   = req.directive.strip(),
        label       = req.label,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return {'id': d.id, 'status': 'created'}

@router.patch('/directive/{directive_id}')
def update_directive(directive_id: int, req: DirectiveUpdate,
                     db: Session = Depends(get_db),
                     current: Lecturer = Depends(get_current_lecturer)):
    d = db.query(TeacherAiDirective).filter(
        TeacherAiDirective.id          == directive_id,
        TeacherAiDirective.lecturer_id == current.id,
    ).first()
    if not d:
        raise HTTPException(404, 'Directive not found')
    if req.directive is not None: d.directive = req.directive
    if req.label     is not None: d.label     = req.label
    if req.is_active is not None: d.is_active = req.is_active
    db.commit()
    return {'status': 'updated'}

@router.delete('/directive/{directive_id}')
def delete_directive(directive_id: int,
                     db: Session = Depends(get_db),
                     current: Lecturer = Depends(get_current_lecturer)):
    d = db.query(TeacherAiDirective).filter(
        TeacherAiDirective.id          == directive_id,
        TeacherAiDirective.lecturer_id == current.id,
    ).first()
    if not d:
        raise HTTPException(404, 'Directive not found')
    db.delete(d)
    db.commit()
    return {'status': 'deleted'}


# ═══════════════════════════════════════════════════════════════════
#  AWARD POINTS
# ═══════════════════════════════════════════════════════════════════

@router.post('/award-points')
def award_points(req: AwardPointsRequest,
                 db: Session = Depends(get_db),
                 current: Lecturer = Depends(get_current_lecturer)):
    if req.points < 1 or req.points > 500:
        raise HTTPException(400, 'Points must be between 1 and 500')

    from services.points_service import award_topic_points
    result = award_topic_points(
        student_id = req.student_id,
        course_id  = req.course_id,
        topic_id   = req.topic_id,
        points     = req.points,
        reason     = f'lecturer_award: {req.reason}',
        db         = db,
        source_id  = f'lecturer_{current.id}',
    )

    db.add(TeacherPointAward(
        lecturer_id = current.id,
        student_id  = req.student_id,
        course_id   = req.course_id,
        topic_id    = req.topic_id,
        points      = req.points,
        reason      = req.reason,
    ))
    db.add(Notification(
        receiver_type = 'student',
        receiver_id   = req.student_id,
        type          = 'points_awarded',
        title         = f'🎁 +{req.points} points from your lecturer!',
        body          = (
            f'{current.name} awarded you {req.points} points '
            f'in {req.topic_id.replace("_", " ")}. Reason: {req.reason}'
        ),
        action_url    = '/student/progress',
    ))
    db.commit()

    return {
        'status':         'awarded',
        'points_awarded': req.points,
        'fcl_changed':    result.get('fcl_changed', False),
        'new_fcl':        result.get('new_fcl'),
    }


# ═══════════════════════════════════════════════════════════════════
#  BULK TIP
# ═══════════════════════════════════════════════════════════════════

@router.post('/messages/bulk-tip')
def bulk_tip(req: BulkTipRequest,
             db: Session = Depends(get_db),
             current: Lecturer = Depends(get_current_lecturer)):
    from services.llm_service import call_groq
    prompt = (
        f'Give a short (2–3 sentence) actionable study tip for a tertiary student '
        f'struggling with {req.topic_id.replace("_", " ")}. '
        + (f'Context: {req.custom_note}' if req.custom_note else '')
        + ' Be encouraging, specific, and academically appropriate.'
    )
    try:
        tip_text, _, _ = call_groq(prompt=prompt, max_tokens=150, temperature=0.7)
    except Exception:
        tip_text = f'Continue practising {req.topic_id.replace("_", " ")} methodically.'

    topic_label = req.topic_id.replace('_', ' ').title()
    for sid in req.student_ids:
        db.add(Notification(
            receiver_type = 'student',
            receiver_id   = sid,
            sender_type   = 'lecturer',
            sender_id     = current.id,
            type          = 'teacher_tip',
            title         = f'💡 Study tip: {topic_label}',
            body          = tip_text,
            action_url    = f'/student/quizzes?topic={req.topic_id}',
        ))
    db.commit()
    return {
        'status':      'sent',
        'recipients':  len(req.student_ids),
        'tip_preview': tip_text[:120],
    }


# ═══════════════════════════════════════════════════════════════════
#  COURSE ASSIGNMENTS (read-only)
# ═══════════════════════════════════════════════════════════════════

@router.get('/course-assignments/{lecturer_id}')
def course_assignments(lecturer_id: int, db: Session = Depends(get_db),
                       current: Lecturer = Depends(get_current_lecturer)):
    lecturer = db.query(Lecturer).filter(Lecturer.id == lecturer_id).first()
    if not lecturer:
        raise HTTPException(404, 'Lecturer not found')
    result = []
    for lca in lecturer.course_assignments:
        pcl = lca.pcl
        result.append({
            'id':             lca.id,
            'course_id':      pcl.course_id,
            'course_name':    pcl.course.name,
            'course_code':    pcl.course.code,
            'programme_id':   pcl.programme_id,
            'programme_name': pcl.programme.name,
            'level':          pcl.level,
            'semester':       pcl.semester,
        })
    return result


# ═══════════════════════════════════════════════════════════════════
#  STUDENT DEEP-DIVE
# ═══════════════════════════════════════════════════════════════════

@router.get('/student/{student_id}/deep-dive')
def student_deep_dive(student_id: int, db: Session = Depends(get_db),
                      current: Lecturer = Depends(get_current_lecturer)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(404, 'Student not found')

    assessments = db.query(Assessment).filter(
        Assessment.student_id == student_id
    ).order_by(Assessment.created_at.desc()).limit(50).all()

    total      = len(assessments)
    correct    = sum(1 for a in assessments if a.is_correct)
    accuracy   = round(correct / total * 100) if total > 0 else 0
    avg_hints  = round(sum(a.hints_used or 0 for a in assessments) / total, 2) if total > 0 else 0

    try:
        from services.llm_service import call_groq
        prompt = (
            f'Tertiary student: accuracy={accuracy}%, avg_hints={avg_hints}, '
            f'total_questions={total}. '
            'In 2 sentences, give a specific lecturer recommendation. Be actionable.'
        )
        rec, _, _ = call_groq(prompt=prompt, max_tokens=100)
    except Exception:
        rec = f'Student has {accuracy}% accuracy. Recommend targeted revision sessions.'

    return {
        'student_id':         student_id,
        'name':               student.name,
        'programme_name':     student.programme.name if student.programme else '—',
        'current_level':      student.current_level,
        'accuracy':           accuracy,
        'avg_hint_density':   avg_hints,
        'total_questions':    total,
        'ai_recommendations': rec,
    }
