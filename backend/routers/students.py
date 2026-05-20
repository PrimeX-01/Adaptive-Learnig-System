from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import (
    Student, StudentSubject, Assessment, StudentPreference,
    ConversationSession, Subject, TopicFcl,          
)
from auth import get_current_student
from services.fcl_service import get_subject_fcl, get_overall_fcl, get_topic_fcl, get_or_create_topic_fcl
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

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
        'learning_style': pref.preferred_learning_style if pref else 'visual',   # <-- ADD THIS LINE
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
        assess = db.query(Assessment).filter(
            Assessment.student_id == student_id,
            Assessment.subject_id == subj_id
        ).all()
        accuracy = (sum(1 for a in assess if a.is_correct) / len(assess) * 100) if assess else None
        if accuracy is not None:
            all_accuracy.append(accuracy)
        # Count topics for this subject (any that have been initialised)
        topics_count = db.query(TopicFcl).filter(
            TopicFcl.student_id == student_id,
            TopicFcl.subject_id == subj_id
        ).count()
        # For now, "mastered" is not used; can be implemented later.
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
    # Historical FCL changes are no longer stored separately.
    # Returning an empty list prevents frontend errors.
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
    # To get topic FCL, we need the subject_id. We'll look it up from the topic.
    # We assume topic_id corresponds to a known topic in the subject_topic mapping.
    # For simplicity, we can find the first subject that contains this topic in the topic_fcl table.
    record = db.query(TopicFcl).filter(
        TopicFcl.student_id == student_id,
        TopicFcl.topic_id == topic_id
    ).first()
    if record:
        fcl = record.current_fcl
    else:
        fcl = 5
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