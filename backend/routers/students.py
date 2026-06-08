from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func


from db.database import get_db
from db.models import (
    Student, StudentSubject, Assessment, StudentPreference,
    ConversationSession, Subject, TopicFcl, ComprehensionEvent, MoodLog,
)
from auth import get_current_student
from services.fcl_service import get_subject_fcl, get_overall_fcl, get_topic_fcl, get_or_create_topic_fcl
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------- Helper ----------
def _time_ago(dt: datetime) -> str:
    """Convert a datetime to a human-readable 'time ago' string."""
    if not dt:
        return 'recently'
    if dt.tzinfo is not None:
        now = datetime.now(dt.tzinfo)
    else:
        now = datetime.utcnow()
    diff = now - dt
    mins = int(diff.total_seconds() / 60)
    if mins < 1:
        return 'just now'
    if mins < 60:
        return f'{mins}m ago'
    hours = mins // 60
    if hours < 24:
        return f'{hours}h ago'
    days = hours // 24
    return f'{days}d ago'


# ---------- Dashboard Endpoint ----------
@router.get('/dashboard')
def student_dashboard(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_student),
):
    """
    Returns a complete snapshot of the student's dashboard.
    This endpoint reads directly from the database each time it is called,
    so any new quiz results or activity will be reflected immediately.
    """
    student_id = current_user.id

    enrollments = db.query(StudentSubject).filter(
        StudentSubject.student_id == student_id
    ).all()
    subjects_out = []
    fcl_values = []
    for e in enrollments:
        subj = db.query(Subject).filter(Subject.id == e.subject_id).first()
        if not subj:
            continue
        subject_fcl = get_subject_fcl(student_id, e.subject_id, db)
        fcl_values.append(subject_fcl)
        assessments = db.query(Assessment).filter(
            Assessment.student_id == student_id,
            Assessment.subject_id == e.subject_id,
        ).all()
        accuracy = (round(sum(1 for a in assessments if a.is_correct) / len(assessments) * 100, 1)
                    if assessments else None)
        subjects_out.append({
            'id': e.subject_id,
            'name': subj.name,
            'code': subj.code,
            'fcl_level': round(subject_fcl, 1),
            'accuracy': accuracy,
        })
    all_assessments = db.query(Assessment).filter(Assessment.student_id == student_id).all()
    topic_records = db.query(TopicFcl).filter(TopicFcl.student_id == student_id).all()
    total_points = sum(t.total_points for t in topic_records)
    avg_fcl = round(sum(fcl_values) / len(fcl_values), 1) if fcl_values else None
    stats = {
        'subjects_count': len(subjects_out),
        'quizzes_completed': len(all_assessments),
        'avg_fcl': avg_fcl,
        'points': total_points,
    }

    recent_assessments = (db.query(Assessment).filter(Assessment.student_id == student_id)
                          .order_by(Assessment.created_at.desc()).limit(40).all())
    grouped = defaultdict(list)
    for a in recent_assessments:
        key = (a.topic_id, a.created_at.date() if a.created_at else 'unknown')
        grouped[key].append(a)
    recent_quizzes = []
    for (topic_id, day), group in list(grouped.items())[:4]:
        correct = sum(1 for a in group if a.is_correct)
        score = round(correct / len(group) * 100) if group else 0
        subj = db.query(Subject).filter(Subject.id == group[0].subject_id).first()
        recent_quizzes.append({
            'id': f'{topic_id}-{day}',
            'title': topic_id.replace('_', ' ').replace('-', ' ').title(),
            'subject_name': subj.name if subj else topic_id,
            'score': score,
            'created_at': group[0].created_at.isoformat() if group[0].created_at else None,
        })

    pref = db.query(StudentPreference).filter(StudentPreference.student_id == student_id).first()
    dominant = (pref.preferred_learning_style if pref else 'reading') or 'reading'
    style_map = {
        'visual': {'v': 60, 'a': 15, 'r': 15, 'k': 10},
        'auditory': {'v': 10, 'a': 60, 'r': 20, 'k': 10},
        'reading': {'v': 15, 'a': 10, 'r': 60, 'k': 15},
        'kinesthetic': {'v': 10, 'a': 15, 'r': 15, 'k': 60},
    }
    vark_profile = style_map.get(dominant, style_map['reading'])

    cutoff = datetime.utcnow() - timedelta(days=7)
    activity = []
    sessions = (db.query(ConversationSession).filter(ConversationSession.student_id == student_id,
                ConversationSession.started_at >= cutoff).order_by(ConversationSession.started_at.desc()).limit(5).all())
    for s in sessions:
        subj = (db.query(Subject).filter(Subject.id == s.subject_id).first() if s.subject_id else None)
        activity.append({
            'description': f'AI Tutor session{" — " + subj.name if subj else ""}',
            'time_ago': _time_ago(s.started_at),
        })
    for a in recent_assessments[:5]:
        subj = db.query(Subject).filter(Subject.id == a.subject_id).first()
        status = 'Correct' if a.is_correct else 'Incorrect'
        activity.append({
            'description': f'{status} answer in {a.topic_id.replace("_", " ").title()}{" — " + subj.name if subj else ""}',
            'time_ago': _time_ago(a.created_at),
        })
    activity.sort(key=lambda x: x['time_ago'])
    activity = activity[:6]

    return {
        'stats': stats,
        'subjects': subjects_out,
        'recent_quizzes': recent_quizzes,
        'vark_profile': vark_profile,
        'recent_activity': activity,
    }


# ---------- Profile Endpoints ----------
class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    grade: Optional[int] = None
    age: Optional[int] = None
    bio: Optional[str] = None
    preferred_learning_style: Optional[str] = None
    profile_picture: Optional[str] = None


@router.get('/{student_id}/profile')
def get_profile(student_id: int, db: Session = Depends(get_db),
                current_user = Depends(get_current_student)):
    s = db.query(Student).filter(Student.id == student_id).first()
    pref = db.query(StudentPreference).filter(StudentPreference.student_id == student_id).first()
    if not s:
        raise HTTPException(404, 'Student not found')
    return {
        'id': s.id,
        'name': s.name,
        'grade': s.grade,
        'preferred_modality': pref.preferred_modality if pref else 'text',
        'username': s.username,
        'email': s.email,
        'age': s.age,
        'bio': s.bio,
        'profile_picture': s.profile_picture,
        'preferred_learning_style': pref.preferred_learning_style if pref else 'visual',
        'learning_style': pref.preferred_learning_style if pref else 'visual',
    }


@router.patch('/{student_id}/profile')
def update_profile(student_id: int, body: ProfileUpdate,
                   db: Session = Depends(get_db),
                   current_user = Depends(get_current_student)):
    s = db.query(Student).filter(Student.id == student_id).first()
    pref = db.query(StudentPreference).filter(StudentPreference.student_id == student_id).first()
    if not s:
        raise HTTPException(404, 'Student not found')
    if body.username is not None:
        s.username = body.username.strip() or None
    if body.email is not None:
        s.email = body.email.strip() or None
    if body.name is not None:
        s.name = body.name.strip() or s.name
    if body.bio is not None:
        s.bio = body.bio.strip() or None
    if body.age is not None:
        s.age = body.age
    if body.grade is not None:
        s.grade = body.grade
    if body.profile_picture is not None:
        s.profile_picture = body.profile_picture
    if body.preferred_learning_style is not None:
        if pref:
            pref.preferred_learning_style = body.preferred_learning_style
        else:
            pref = StudentPreference(student_id=student_id, preferred_learning_style=body.preferred_learning_style)
            db.add(pref)
    db.commit()
    db.refresh(s)
    return {'message': 'Profile updated successfully'}


@router.get('/{student_id}/subject-performance')
def subject_performance(student_id: int, db: Session = Depends(get_db),
                        current_user = Depends(get_current_student)):
    enrollments = db.query(StudentSubject).filter(StudentSubject.student_id == student_id).all()
    subjects_data = []
    all_fcl = []
    all_accuracy = []
    for e in enrollments:
        subj_id = e.subject_id
        subject_fcl = get_subject_fcl(student_id, subj_id, db)
        all_fcl.append(subject_fcl)
        assess = db.query(Assessment).filter(Assessment.student_id == student_id, Assessment.subject_id == subj_id).all()
        accuracy = (sum(1 for a in assess if a.is_correct) / len(assess) * 100) if assess else None
        if accuracy is not None:
            all_accuracy.append(accuracy)
        topics_count = db.query(TopicFcl).filter(TopicFcl.student_id == student_id, TopicFcl.subject_id == subj_id).count()
        def label(acc):
            return ('Excellent' if acc and acc >= 80 else
                    'Good' if acc and acc >= 60 else
                    'Needs Support' if acc else 'Not Started')
        subjects_data.append({
            'subject_id': subj_id,
            'subject_name': e.subject.name,
            'subject_code': e.subject.code,
            'teacher_name': e.teacher.name if e.teacher else None,
            'fcl_level': subject_fcl,
            'accuracy': round(accuracy, 1) if accuracy else None,
            'mastered_topics': 0,
            'total_topics': topics_count,
            'performance_label': label(accuracy),
        })
    overall_acc = sum(all_accuracy) / len(all_accuracy) if all_accuracy else None
    return {
        'subjects': subjects_data,
        'overall': {
            'avg_fcl': round(sum(all_fcl) / len(all_fcl), 1) if all_fcl else None,
            'avg_accuracy': round(overall_acc, 1) if overall_acc else None,
            'subjects_count': len(subjects_data),
            'overall_label': ('Excellent' if overall_acc and overall_acc >= 80 else
                              'Good' if overall_acc and overall_acc >= 60 else
                              'Needs Support' if overall_acc else 'No Data Yet'),
        }
    }


@router.get('/{student_id}/fcl-history')
def fcl_history(student_id: int, subject_id: int = None,
                db: Session = Depends(get_db),
                current_user = Depends(get_current_student)):
    return []


@router.get('/{student_id}/topic-mastery')
def topic_mastery(student_id: int, subject_id: int = None,
                  db: Session = Depends(get_db),
                  current_user = Depends(get_current_student)):
    q = db.query(TopicFcl).filter(TopicFcl.student_id == student_id)
    if subject_id:
        q = q.filter(TopicFcl.subject_id == subject_id)
    records = q.all()
    return [
        {
            'topic_id': r.topic_id,
            'topic_name': r.topic_id.replace('_', ' ').title(),
            'subject_id': r.subject_id,
            'mastery': 'mastered' if r.current_fcl >= 10 else 'learning',
            'mastery_prob': r.current_fcl / 13.0,
            'current_points': r.total_points,
            'points_needed': (r.current_fcl + 1) * 1000 - r.total_points if r.current_fcl < 13 else 0,
        }
        for r in records
    ]


@router.get('/all')
def get_all_students(db: Session = Depends(get_db),
                     current_user = Depends(get_current_student)):
    return [
        {'id': s.id, 'name': s.name, 'grade': s.grade, 'is_teacher': s.is_teacher}
        for s in db.query(Student).all()
    ]


@router.get('/{student_id}/fcl/{topic_id}')
def student_fcl_for_topic(student_id: int, topic_id: str,
                          db: Session = Depends(get_db),
                          current_user = Depends(get_current_student)):
    record = db.query(TopicFcl).filter(
        TopicFcl.student_id == student_id,
        TopicFcl.topic_id == topic_id
    ).first()
    fcl = record.current_fcl if record else 5
    pref = db.query(StudentPreference).filter(StudentPreference.student_id == student_id).first()
    return {
        'fcl_level': fcl,
        'preferred_modality': pref.preferred_modality if pref else 'text',
    }


@router.get('/{student_id}/hint-analytics')
def hint_analytics(student_id: int, db: Session = Depends(get_db),
                   current_user = Depends(get_current_student)):
    TOPICS = [
        'mathematics_algebra', 'mathematics_geometry',
        'science_biology', 'english_comprehension', 'social_studies',
    ]
    result = []
    for topic in TOPICS:
        qs = db.query(Assessment).filter(
            Assessment.student_id == student_id,
            Assessment.topic_id == topic
        ).all()
        density = sum(a.hints_used for a in qs) / len(qs) if qs else 0
        result.append({'topic': topic.replace('_', ' ').title(), 'hint_density': density})
    return result


@router.get('/{student_id}/activity')
def get_activity(student_id: int, timeframe: str = 'week',
                 db: Session = Depends(get_db),
                 current_user = Depends(get_current_student)):
    cutoffs = {
        '24h': timedelta(hours=24),
        'week': timedelta(weeks=1),
        'month': timedelta(days=30),
        'year': timedelta(days=365),
    }
    since = datetime.utcnow() - cutoffs.get(timeframe, timedelta(weeks=1))
    activity = []
    sessions = db.query(ConversationSession).filter(
        ConversationSession.student_id == student_id,
        ConversationSession.started_at >= since,
        ConversationSession.ended_at.isnot(None),
    ).order_by(ConversationSession.started_at.desc()).limit(20).all()
    for s in sessions:
        duration = None
        if s.started_at and s.ended_at:
            duration = max(1, int((s.ended_at - s.started_at).total_seconds() / 60))
        subj = db.query(Subject).filter(Subject.id == s.subject_id).first() if s.subject_id else None
        activity.append({
            'type': 'ai_tutor',
            'subject_name': subj.name if subj else None,
            'topic_id': None,
            'duration_minutes': duration,
            'score': None,
            'questions_count': None,
            'timestamp': s.started_at.isoformat(),
        })
    rows = db.query(Assessment).filter(
        Assessment.student_id == student_id,
        Assessment.created_at >= since,
    ).order_by(Assessment.created_at.desc()).limit(200).all()
    grouped = defaultdict(list)
    for r in rows:
        grouped[(r.topic_id, r.created_at.date())].append(r)
    for (topic_id, _day), group in grouped.items():
        correct = sum(1 for a in group if a.is_correct)
        score = round(correct / len(group) * 100, 1)
        subj = db.query(Subject).filter(Subject.id == group[0].subject_id).first() if group[0].subject_id else None
        activity.append({
            'type': 'quiz',
            'subject_name': subj.name if subj else None,
            'topic_id': topic_id,
            'duration_minutes': None,
            'score': score,
            'questions_count': len(group),
            'timestamp': group[0].created_at.isoformat(),
        })
    activity.sort(key=lambda x: x['timestamp'], reverse=True)
    return activity[:30]


@router.get('/{student_id}/topic-points')
def get_topic_points(student_id: int, subject_id: int, topic_id: str,
                     db: Session = Depends(get_db),
                     current_user = Depends(get_current_student)):
    record = db.query(TopicFcl).filter(
        TopicFcl.student_id == student_id,
        TopicFcl.subject_id == subject_id,
        TopicFcl.topic_id == topic_id
    ).first()
    if not record:
        return {'current_points': 0, 'total_points': 0, 'current_fcl': 5, 'points_needed': 1000}
    needed = (record.current_fcl + 1) * 1000 - record.total_points if record.current_fcl < 13 else 0
    return {
        'current_points': record.total_points,
        'points_to_next_fcl': max(0, needed),
        'current_fcl': record.current_fcl,
    }


# ===================== NEW PERSONALISATION ENDPOINTS =====================

class MoodRequest(BaseModel):
    mood: str


@router.post('/mood')
def log_mood(req: MoodRequest, db: Session = Depends(get_db),
             current_user = Depends(get_current_student)):
    mood_log = MoodLog(student_id=current_user.id, mood=req.mood)
    db.add(mood_log)
    db.commit()
    return {'status': 'mood logged', 'mood': req.mood}


@router.get('/{student_id}/adaptation-events')
def get_adaptation_events(student_id: int, limit: int = 5,
                           db: Session = Depends(get_db),
                           current_user = Depends(get_current_student)):
    events = db.query(ComprehensionEvent).filter(
        ComprehensionEvent.student_id == student_id
    ).order_by(ComprehensionEvent.created_at.desc()).limit(limit).all()
    return [
        {
            'id': e.id,
            'title': e.title,
            'message': e.message,
            'event_type': e.event_type,
            'created_at': e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ]


@router.get('/{student_id}/assessments-count')
def get_assessments_count(student_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_student)):
    count = db.query(Assessment).filter(Assessment.student_id == student_id).count()
    return count


@router.get('/{student_id}/total-points')
def get_total_points(student_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_student)):
    total = db.query(func.sum(TopicFcl.total_points)).filter(TopicFcl.student_id == student_id).scalar() or 0
    return total