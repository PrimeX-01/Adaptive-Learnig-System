from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from collections import defaultdict

from db.database import get_db
from db.models import (
    Student, Grade, Class, Subject, ClassSubject,
    StudentClassEnrollment, StudentCourseEnrollment,
    Faculty, Programme, Course, ProgrammeCourseLevel,
    Assessment, TopicFcl, ConversationSession,
    VarkScore, StyleInteraction, ComprehensionEvent,
    MoodLog, Notification, ReviewSchedule, HintRequest,
)
from auth import get_current_student

router = APIRouter(prefix='/api/students', tags=['Students'])


# ═══════════════════════════════════════════════════════════════════
#  SCHEMAS
# ═══════════════════════════════════════════════════════════════════

class ProfileUpdate(BaseModel):
    name:                    Optional[str] = None
    username:                Optional[str] = None
    bio:                     Optional[str] = None
    profile_picture:         Optional[str] = None
    preferred_learning_style:Optional[str] = None

class MoodRequest(BaseModel):
    mood: str


# ═══════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════

def _time_ago(dt: datetime) -> str:
    if not dt:
        return 'recently'
    try:
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.utcnow()
        diff = now - dt
        mins = int(diff.total_seconds() / 60)
        if mins < 1:   return 'just now'
        if mins < 60:  return f'{mins}m ago'
        h = mins // 60
        if h < 24:     return f'{h}h ago'
        return f'{h // 24}d ago'
    except Exception:
        return 'recently'


def _get_subject_fcl(student_id: int, subject_id: int, db: Session) -> float:
    rows = db.execute(text(
        'SELECT COALESCE(total_points, 0) FROM topic_fcl '
        'WHERE student_id=:sid AND subject_id=:subid AND is_active=true'
    ), {'sid': student_id, 'subid': subject_id}).fetchall()
    if not rows:
        return 1.0
    fcls = [max(1, r[0] // 1000) for r in rows]
    return round(sum(fcls) / len(fcls), 1)


def _get_course_fcl(student_id: int, course_id: int, db: Session) -> float:
    rows = db.execute(text(
        'SELECT COALESCE(total_points, 0) FROM topic_fcl '
        'WHERE student_id=:sid AND course_id=:cid AND is_active=true'
    ), {'sid': student_id, 'cid': course_id}).fetchall()
    if not rows:
        return 1.0
    fcls = [max(1, r[0] // 1000) for r in rows]
    return round(sum(fcls) / len(fcls), 1)


def _get_overall_fcl(student_id: int, student: Student, db: Session) -> float:
    rows = db.execute(text(
        'SELECT COALESCE(total_points, 0) FROM topic_fcl '
        'WHERE student_id=:sid AND is_active=true'
    ), {'sid': student_id}).fetchall()
    if not rows:
        return 1.0
    fcls = [max(1, r[0] // 1000) for r in rows]
    return round(sum(fcls) / len(fcls), 1)


# ═══════════════════════════════════════════════════════════════════
#  DASHBOARD
# ═══════════════════════════════════════════════════════════════════

@router.get('/dashboard')
def student_dashboard(db: Session = Depends(get_db),
                      current: Student = Depends(get_current_student)):
    sid = current.id

    # ── Subjects / courses ────────────────────────────────────────
    subjects_out = []
    fcl_values   = []

    if current.student_type == 'school':
        class_subjects = db.query(ClassSubject).filter(
            ClassSubject.class_id == current.class_id
        ).all() if current.class_id else []

        for cs in class_subjects:
            subj = cs.subject
            sfcl = _get_subject_fcl(sid, subj.id, db)
            fcl_values.append(sfcl)
            assessments = db.query(Assessment).filter(
                Assessment.student_id == sid,
                Assessment.subject_id == subj.id,
            ).all()
            accuracy = (
                round(sum(1 for a in assessments if a.is_correct) / len(assessments) * 100, 1)
                if assessments else None
            )
            subjects_out.append({
                'id':        subj.id,
                'name':      subj.name,
                'code':      subj.code,
                'fcl_level': round(sfcl, 1),
                'accuracy':  accuracy,
                'type':      'subject',
            })

    else:  # tertiary
        enrollments = db.query(StudentCourseEnrollment).filter(
            StudentCourseEnrollment.student_id == sid
        ).all()
        for enr in enrollments:
            pcl    = enr.pcl
            course = pcl.course
            cfcl   = _get_course_fcl(sid, course.id, db)
            fcl_values.append(cfcl)
            assessments = db.query(Assessment).filter(
                Assessment.student_id == sid,
                Assessment.course_id  == course.id,
            ).all()
            accuracy = (
                round(sum(1 for a in assessments if a.is_correct) / len(assessments) * 100, 1)
                if assessments else None
            )
            subjects_out.append({
                'id':        course.id,
                'name':      course.name,
                'code':      course.code,
                'fcl_level': round(cfcl, 1),
                'accuracy':  accuracy,
                'type':      'course',
                'level':     pcl.level,
                'semester':  pcl.semester,
            })

    all_assessments = db.query(Assessment).filter(Assessment.student_id == sid).all()
    topic_records   = db.query(TopicFcl).filter(
        TopicFcl.student_id == sid, TopicFcl.is_active == True
    ).all()
    total_points = sum(t.total_points for t in topic_records if t.total_points is not None)
    avg_fcl      = round(sum(fcl_values) / len(fcl_values), 1) if fcl_values else None

    stats = {
        'subjects_count':    len(subjects_out),
        'quizzes_completed': len(all_assessments),
        'avg_fcl':           avg_fcl,
        'points':            total_points,
    }

    # ── Recent quiz activity ───────────────────────────────────────
    recent_raw = (
        db.query(Assessment)
        .filter(Assessment.student_id == sid)
        .order_by(Assessment.created_at.desc())
        .limit(40).all()
    )
    grouped = defaultdict(list)
    for a in recent_raw:
        key = (a.topic_id, a.created_at.date() if a.created_at else 'unknown')
        grouped[key].append(a)
    recent_quizzes = []
    for (topic_id, day), group in list(grouped.items())[:4]:
        correct  = sum(1 for a in group if a.is_correct)
        score    = round(correct / len(group) * 100) if group else 0
        subj_name = topic_id.replace('_', ' ').title()
        if group[0].subject_id:
            s = db.query(Subject).filter(Subject.id == group[0].subject_id).first()
            if s: subj_name = s.name
        elif group[0].course_id:
            c = db.query(Course).filter(Course.id == group[0].course_id).first()
            if c: subj_name = c.name
        recent_quizzes.append({
            'id':           f'{topic_id}-{day}',
            'title':        topic_id.replace('_', ' ').title(),
            'subject_name': subj_name,
            'score':        score,
            'created_at':   group[0].created_at.isoformat() if group[0].created_at else None,
        })

    # ── VARK profile ───────────────────────────────────────────────
    vark = db.query(VarkScore).filter(VarkScore.student_id == sid).first()
    if vark:
        total = vark.v_score + vark.a_score + vark.r_score + vark.k_score or 1
        vark_profile = {
            'v': round(vark.v_score / total * 100),
            'a': round(vark.a_score / total * 100),
            'r': round(vark.r_score / total * 100),
            'k': round(vark.k_score / total * 100),
        }
    else:
        style_map = {
            'visual':      {'v': 60, 'a': 15, 'r': 15, 'k': 10},
            'auditory':    {'v': 10, 'a': 60, 'r': 20, 'k': 10},
            'reading':     {'v': 15, 'a': 10, 'r': 60, 'k': 15},
            'kinesthetic': {'v': 10, 'a': 15, 'r': 15, 'k': 60},
        }
        vark_profile = style_map.get(current.learning_style or 'reading', style_map['reading'])

    # ── Recent activity ────────────────────────────────────────────
    cutoff   = datetime.utcnow() - timedelta(days=7)
    sessions = (
        db.query(ConversationSession)
        .filter(ConversationSession.student_id == sid,
                ConversationSession.started_at >= cutoff)
        .order_by(ConversationSession.started_at.desc())
        .limit(5).all()
    )
    activity = []
    for s in sessions:
        name = '—'
        if s.subject_id:
            subj = db.query(Subject).filter(Subject.id == s.subject_id).first()
            if subj: name = subj.name
        elif s.course_id:
            crs = db.query(Course).filter(Course.id == s.course_id).first()
            if crs: name = crs.name
        activity.append({
            'description': f'AI Tutor session — {name}',
            'time_ago':    _time_ago(s.started_at),
        })
    for a in recent_raw[:5]:
        status = 'Correct' if a.is_correct else 'Incorrect'
        activity.append({
            'description': f'{status} answer in {a.topic_id.replace("_", " ").title()}',
            'time_ago':    _time_ago(a.created_at),
        })
    activity = activity[:6]

    return {
        'stats':           stats,
        'subjects':        subjects_out,
        'recent_quizzes':  recent_quizzes,
        'vark_profile':    vark_profile,
        'recent_activity': activity,
        'student_type':    current.student_type,
        'current_level':   current.current_level,
        'current_semester':current.current_semester,
    }


# ═══════════════════════════════════════════════════════════════════
#  PROFILE
# ═══════════════════════════════════════════════════════════════════

@router.get('/{student_id}/profile')
def get_profile(student_id: int, db: Session = Depends(get_db),
                current: Student = Depends(get_current_student)):
    s = db.query(Student).filter(Student.id == student_id).first()
    if not s:
        raise HTTPException(404, 'Student not found')

    grade_label = None
    class_name  = None
    if s.grade_id:
        g = db.query(Grade).filter(Grade.id == s.grade_id).first()
        grade_label = g.label if g else None
    if s.class_id:
        c = db.query(Class).filter(Class.id == s.class_id).first()
        class_name = c.name if c else None

    faculty_name   = None
    programme_name = None
    if s.faculty_id:
        f = db.query(Faculty).filter(Faculty.id == s.faculty_id).first()
        faculty_name = f.name if f else None
    if s.programme_id:
        p = db.query(Programme).filter(Programme.id == s.programme_id).first()
        programme_name = p.name if p else None

    vark = db.query(VarkScore).filter(VarkScore.student_id == student_id).first()
    vark_data = None
    if vark:
        total = vark.v_score + vark.a_score + vark.r_score + vark.k_score or 1
        vark_data = {
            'v': round(vark.v_score / total * 100),
            'a': round(vark.a_score / total * 100),
            'r': round(vark.r_score / total * 100),
            'k': round(vark.k_score / total * 100),
            'total_interactions': vark.total_interactions,
        }

    return {
        'id':                s.id,
        'name':              s.name,
        'email':             s.email,
        'username':          s.username,
        'bio':               s.bio,
        'profile_picture':   s.profile_picture,
        'student_type':      s.student_type,
        'learning_style':    s.learning_style,
        'preferred_learning_style': s.learning_style,
        # school
        'grade_id':          s.grade_id,
        'grade_label':       grade_label,
        'class_id':          s.class_id,
        'class_name':        class_name,
        # tertiary
        'faculty_id':        s.faculty_id,
        'faculty_name':      faculty_name,
        'programme_id':      s.programme_id,
        'programme_name':    programme_name,
        'current_level':     s.current_level,
        'current_semester':  s.current_semester,
        'vark':              vark_data,
    }


@router.patch('/{student_id}/profile')
def update_profile(student_id: int, body: ProfileUpdate,
                   db: Session = Depends(get_db),
                   current: Student = Depends(get_current_student)):
    s = db.query(Student).filter(Student.id == student_id).first()
    if not s:
        raise HTTPException(404, 'Student not found')
    if body.name            is not None: s.name            = body.name.strip() or s.name
    if body.username        is not None: s.username        = body.username.strip() or None
    if body.bio             is not None: s.bio             = body.bio.strip() or None
    if body.profile_picture is not None: s.profile_picture = body.profile_picture
    if body.preferred_learning_style is not None:
        s.learning_style = body.preferred_learning_style
    db.commit()
    return {'message': 'Profile updated successfully'}


# ═══════════════════════════════════════════════════════════════════
#  SUBJECT / COURSE PERFORMANCE (ENRICHED FOR PROGRESS PAGE)
# ═══════════════════════════════════════════════════════════════════

@router.get('/{student_id}/subject-performance')
def subject_performance(student_id: int, db: Session = Depends(get_db),
                        current: Student = Depends(get_current_student)):
    s = db.query(Student).filter(Student.id == student_id).first()
    if not s:
        raise HTTPException(404, 'Student not found')

    subjects_data = []
    all_fcl       = []

    if s.student_type == 'school':
        class_subjects = db.query(ClassSubject).filter(
            ClassSubject.class_id == s.class_id
        ).all() if s.class_id else []

        for cs in class_subjects:
            subj     = cs.subject
            sfcl     = _get_subject_fcl(student_id, subj.id, db)
            all_fcl.append(sfcl)
            assess   = db.query(Assessment).filter(
                Assessment.student_id == student_id,
                Assessment.subject_id == subj.id,
            ).all()
            accuracy = (
                round(sum(1 for a in assess if a.is_correct) / len(assess) * 100, 1)
                if assess else None
            )
            # Find teacher for this subject in this class
            teacher_name = None
            tcs = cs.teacher_assignment
            if tcs and tcs.teacher:
                teacher_name = tcs.teacher.name

            # total hints in this subject
            total_hints = db.query(HintRequest).filter(
                HintRequest.student_id == student_id,
                HintRequest.subject_id == subj.id,
            ).count()

            # topic mastery list (safeguard against None current_fcl)
            topics = db.query(TopicFcl).filter(
                TopicFcl.student_id == student_id,
                TopicFcl.subject_id == subj.id,
                TopicFcl.is_active == True,
            ).all()
            topics_out = [
                {
                    'topic_id':     t.topic_id,
                    'mastery_prob': (t.current_fcl or 1) / 20.0,
                }
                for t in topics
            ]

            subjects_data.append({
                'subject_id':       subj.id,
                'subject_name':     subj.name,
                'subject_code':     subj.code,
                'fcl_level':        sfcl,
                'accuracy':         accuracy,
                'teacher_name':     teacher_name,
                'performance_label': (
                    'Excellent' if accuracy and accuracy >= 80 else
                    'Good'      if accuracy and accuracy >= 60 else
                    'Needs Support' if accuracy else 'Not Started'
                ),
                'total_hints':      total_hints,
                'topics':           topics_out,
            })

    else:  # tertiary
        enrollments = db.query(StudentCourseEnrollment).filter(
            StudentCourseEnrollment.student_id == student_id
        ).all()
        for enr in enrollments:
            pcl    = enr.pcl
            course = pcl.course
            cfcl   = _get_course_fcl(student_id, course.id, db)
            all_fcl.append(cfcl)
            assess = db.query(Assessment).filter(
                Assessment.student_id == student_id,
                Assessment.course_id  == course.id,
            ).all()
            accuracy = (
                round(sum(1 for a in assess if a.is_correct) / len(assess) * 100, 1)
                if assess else None
            )
            lecturer_name = None
            if pcl.lecturer_assignment and pcl.lecturer_assignment.lecturer:
                lecturer_name = pcl.lecturer_assignment.lecturer.name

            total_hints = db.query(HintRequest).filter(
                HintRequest.student_id == student_id,
                HintRequest.course_id == course.id,
            ).count()

            topics = db.query(TopicFcl).filter(
                TopicFcl.student_id == student_id,
                TopicFcl.course_id == course.id,
                TopicFcl.is_active == True,
            ).all()
            topics_out = [
                {
                    'topic_id':     t.topic_id,
                    'mastery_prob': (t.current_fcl or 1) / 20.0,
                }
                for t in topics
            ]

            subjects_data.append({
                'subject_id':   course.id,
                'subject_name': course.name,
                'subject_code': course.code,
                'fcl_level':    cfcl,
                'accuracy':     accuracy,
                'teacher_name': lecturer_name,
                'level':        pcl.level,
                'semester':     pcl.semester,
                'performance_label': (
                    'Excellent' if accuracy and accuracy >= 80 else
                    'Good'      if accuracy and accuracy >= 60 else
                    'Needs Support' if accuracy else 'Not Started'
                ),
                'total_hints':  total_hints,
                'topics':       topics_out,
            })

    avg_fcl     = round(sum(all_fcl) / len(all_fcl), 1) if all_fcl else None
    all_acc     = [s['accuracy'] for s in subjects_data if s['accuracy'] is not None]
    overall_acc = round(sum(all_acc) / len(all_acc), 1) if all_acc else None

    return {
        'subjects': subjects_data,
        'overall':  {
            'avg_fcl':        avg_fcl,
            'avg_accuracy':   overall_acc,
            'subjects_count': len(subjects_data),
            'overall_label': (
                'Excellent'     if overall_acc and overall_acc >= 80 else
                'Good'          if overall_acc and overall_acc >= 60 else
                'Needs Support' if overall_acc else 'No Data Yet'
            ),
        },
    }


# ═══════════════════════════════════════════════════════════════════
#  TOPIC MASTERY & FCL (unchanged)
# ═══════════════════════════════════════════════════════════════════

@router.get('/{student_id}/topic-mastery')
def topic_mastery(student_id: int, subject_id: Optional[int] = None,
                  course_id: Optional[int] = None,
                  db: Session = Depends(get_db),
                  current: Student = Depends(get_current_student)):
    q = db.query(TopicFcl).filter(
        TopicFcl.student_id == student_id,
        TopicFcl.is_active  == True,
    )
    if subject_id: q = q.filter(TopicFcl.subject_id == subject_id)
    if course_id:  q = q.filter(TopicFcl.course_id  == course_id)
    records = q.all()
    return [
        {
            'topic_id':            r.topic_id,
            'topic_name':          r.topic_id.replace('_', ' ').title(),
            'subject_id':          r.subject_id,
            'course_id':           r.course_id,
            'mastery':             'mastered' if (r.current_fcl or 1) >= 10 else 'learning',
            'mastery_prob':        (r.current_fcl or 1) / 20.0,
            'current_fcl':         r.current_fcl or 1,
            'total_points':        r.total_points or 0,
            'points_within_level': (r.total_points or 0) % 1000,
            'points_to_next_fcl':  max(0, ((r.current_fcl or 1) + 1) * 1000 - (r.total_points or 0)),
        }
        for r in records
    ]


@router.get('/{student_id}/fcl-history')
def fcl_history(student_id: int, db: Session = Depends(get_db),
                current: Student = Depends(get_current_student)):
    return []   # placeholder — populated as students take quizzes


# ═══════════════════════════════════════════════════════════════════
#  ADAPTATION EVENTS (unchanged)
# ═══════════════════════════════════════════════════════════════════

@router.get('/{student_id}/adaptation-events')
def adaptation_events(student_id: int, limit: int = 5,
                      db: Session = Depends(get_db),
                      current: Student = Depends(get_current_student)):
    events = db.query(ComprehensionEvent).filter(
        ComprehensionEvent.student_id == student_id
    ).order_by(ComprehensionEvent.created_at.desc()).limit(limit).all()
    return [
        {
            'id':         e.id,
            'title':      e.title,
            'message':    e.message,
            'event_type': e.event_type,
            'created_at': e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ]


# ═══════════════════════════════════════════════════════════════════
#  HINT ANALYTICS (unchanged)
# ═══════════════════════════════════════════════════════════════════

@router.get('/{student_id}/hint-analytics')
def hint_analytics(student_id: int, db: Session = Depends(get_db),
                   current: Student = Depends(get_current_student)):
    rows = db.execute(text('''
        SELECT topic_id,
               COUNT(*)                              AS total_hints,
               AVG(hint_level_requested)             AS avg_level,
               COUNT(*)::float / NULLIF(
                   (SELECT COUNT(*) FROM assessments a
                    WHERE a.student_id = hr.student_id
                      AND a.topic_id   = hr.topic_id), 0
               )                                     AS hint_density
        FROM hint_requests hr
        WHERE hr.student_id = :sid
        GROUP BY topic_id, student_id
        ORDER BY total_hints DESC
        LIMIT 10
    '''), {'sid': student_id}).fetchall()
    return [
        {
            'topic':        r[0].replace('_', ' ').title(),
            'total_hints':  r[1],
            'avg_level':    round(float(r[2] or 0), 1),
            'hint_density': round(float(r[3] or 0), 2),
        }
        for r in rows
    ]


# ═══════════════════════════════════════════════════════════════════
#  ACTIVITY FEED (unchanged)
# ═══════════════════════════════════════════════════════════════════

@router.get('/{student_id}/activity')
def get_activity(student_id: int, timeframe: str = 'week',
                 db: Session = Depends(get_db),
                 current: Student = Depends(get_current_student)):
    cutoffs = {
        '24h':  timedelta(hours=24),
        'week': timedelta(weeks=1),
        'month':timedelta(days=30),
    }
    since = datetime.utcnow() - cutoffs.get(timeframe, timedelta(weeks=1))
    activity = []

    sessions = db.query(ConversationSession).filter(
        ConversationSession.student_id == student_id,
        ConversationSession.started_at >= since,
        ConversationSession.ended_at.isnot(None),
    ).order_by(ConversationSession.started_at.desc()).limit(15).all()

    for s in sessions:
        duration = None
        if s.started_at and s.ended_at:
            duration = max(1, int((s.ended_at - s.started_at).total_seconds() / 60))
        name = '—'
        if s.subject_id:
            subj = db.query(Subject).filter(Subject.id == s.subject_id).first()
            if subj: name = subj.name
        elif s.course_id:
            crs = db.query(Course).filter(Course.id == s.course_id).first()
            if crs: name = crs.name
        activity.append({
            'type':             'ai_tutor',
            'subject_name':     name,
            'duration_minutes': duration,
            'score':            None,
            'timestamp':        s.started_at.isoformat(),
        })

    rows = db.query(Assessment).filter(
        Assessment.student_id == student_id,
        Assessment.created_at >= since,
    ).order_by(Assessment.created_at.desc()).limit(100).all()
    grouped = defaultdict(list)
    for r in rows:
        grouped[(r.topic_id, r.created_at.date())].append(r)
    for (topic_id, _day), group in grouped.items():
        correct = sum(1 for a in group if a.is_correct)
        score   = round(correct / len(group) * 100, 1)
        name = topic_id
        if group[0].subject_id:
            subj = db.query(Subject).filter(Subject.id == group[0].subject_id).first()
            if subj: name = subj.name
        elif group[0].course_id:
            crs = db.query(Course).filter(Course.id == group[0].course_id).first()
            if crs: name = crs.name
        activity.append({
            'type':           'quiz',
            'subject_name':   name,
            'topic_id':       topic_id,
            'score':          score,
            'questions_count':len(group),
            'timestamp':      group[0].created_at.isoformat(),
        })

    activity.sort(key=lambda x: x['timestamp'], reverse=True)
    return activity[:25]


# ═══════════════════════════════════════════════════════════════════
#  MOOD (unchanged)
# ═══════════════════════════════════════════════════════════════════

@router.post('/mood')
def log_mood(req: MoodRequest, db: Session = Depends(get_db),
             current: Student = Depends(get_current_student)):
    db.add(MoodLog(student_id=current.id, mood=req.mood))
    db.commit()
    return {'status': 'mood logged', 'mood': req.mood}


# ═══════════════════════════════════════════════════════════════════
#  ENROLLED SUBJECTS (unchanged)
# ═══════════════════════════════════════════════════════════════════

@router.get('/{student_id}/enrolled-subjects')
def enrolled_subjects(student_id: int, db: Session = Depends(get_db),
                      current: Student = Depends(get_current_student)):
    s = db.query(Student).filter(Student.id == student_id).first()
    if not s:
        raise HTTPException(404, 'Student not found')

    result = []
    if s.student_type == 'school' and s.class_id:
        class_subjects = db.query(ClassSubject).filter(
            ClassSubject.class_id == s.class_id
        ).all()
        for cs in class_subjects:
            sfcl = _get_subject_fcl(student_id, cs.subject_id, db)
            result.append({
                'subject_id':    cs.subject.id,
                'subject_code':  cs.subject.code,
                'subject_name':  cs.subject.name,
                'fcl_level':     sfcl,
                'learning_style':s.learning_style or 'reading',
                'type':          'subject',
            })
    else:
        enrollments = db.query(StudentCourseEnrollment).filter(
            StudentCourseEnrollment.student_id == student_id
        ).all()
        for enr in enrollments:
            pcl    = enr.pcl
            course = pcl.course
            cfcl   = _get_course_fcl(student_id, course.id, db)
            result.append({
                'subject_id':    course.id,
                'subject_code':  course.code,
                'subject_name':  course.name,
                'fcl_level':     cfcl,
                'learning_style':s.learning_style or 'reading',
                'type':          'course',
                'level':         pcl.level,
                'semester':      pcl.semester,
            })
    return result


# ═══════════════════════════════════════════════════════════════════
#  QUICK COUNTS (unchanged)
# ═══════════════════════════════════════════════════════════════════

@router.get('/{student_id}/assessments-count')
def assessments_count(student_id: int, db: Session = Depends(get_db),
                      current: Student = Depends(get_current_student)):
    return db.query(Assessment).filter(Assessment.student_id == student_id).count()


@router.get('/{student_id}/total-points')
def total_points(student_id: int, db: Session = Depends(get_db),
                 current: Student = Depends(get_current_student)):
    total = db.query(func.sum(TopicFcl.total_points)).filter(
        TopicFcl.student_id == student_id,
        TopicFcl.is_active   == True,
    ).scalar()
    return total or 0