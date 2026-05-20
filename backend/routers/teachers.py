from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from db.database import get_db
from db.models import Student, StudentSubject, Subject, Assessment
from auth import get_current_student
from services.llm_service import call_groq, MODEL_LONG
from services.fcl_service import get_subject_fcl, get_overall_fcl, get_or_create_topic_fcl
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get('/dashboard/{class_id}')
def get_dashboard(class_id: int, subject_code: str = None,
                  db: Session = Depends(get_db),
                  current_user = Depends(get_current_student)):
    if not current_user.is_teacher:
        raise HTTPException(403, 'Teacher access only')
    
    # Get all student-subject enrollments where this teacher is responsible
    q = db.query(StudentSubject).filter(StudentSubject.teacher_id == current_user.id)
    if subject_code:
        subj = db.query(Subject).filter(Subject.code == subject_code).first()
        if subj:
            q = q.filter(StudentSubject.subject_id == subj.id)
    enrollments = q.all()
    
    student_data, at_risk = [], []
    for e in enrollments:
        sid, subj_id = e.student_id, e.subject_id
        
        # Use new FCL system: get subject FCL (average of its topics)
        subject_fcl = get_subject_fcl(sid, subj_id, db)
        # For overall FCL (not used per student per subject, but we might need it for risk)
        overall_fcl = get_overall_fcl(sid, db)
        
        # Get assessments for this student & subject
        assess = db.query(Assessment).filter(
            Assessment.student_id == sid,
            Assessment.subject_id == subj_id
        ).all()
        accuracy = sum(1 for a in assess if a.is_correct) / len(assess) * 100 if assess else 0
        hint_dens = sum(a.hints_used for a in assess) / len(assess) if assess else 0
        
        # At‑risk logic: low subject FCL (≤5) OR high hint density (>2.0)
        is_at_risk = subject_fcl <= 5 or hint_dens > 2.0
        
        entry = {
            'student_id': sid,
            'name': e.student.name,
            'grade': e.student.grade,
            'subject_name': e.subject.name,
            'subject_code': e.subject.code,
            'fcl_level': subject_fcl,          # subject FCL (float, average of topics)
            'accuracy': round(accuracy, 1),
            'hint_density': round(hint_dens, 2),
            'is_at_risk': is_at_risk
        }
        student_data.append(entry)
        if is_at_risk:
            at_risk.append({**entry, 'risk_reason': 'Low FCL' if subject_fcl <= 5 else 'High hints'})
    
    # FCL distribution across this teacher's students (using subject FCL, rounded to integer band)
    buckets = {'Low (1-4)': 0, 'Developing (5-7)': 0, 'Proficient (8-10)': 0, 'Advanced (11+)': 0}
    for s in student_data:
        f = s['fcl_level']
        if f <= 4:
            buckets['Low (1-4)'] += 1
        elif f <= 7:
            buckets['Developing (5-7)'] += 1
        elif f <= 10:
            buckets['Proficient (8-10)'] += 1
        else:
            buckets['Advanced (11+)'] += 1
    
    # Subjects this teacher teaches (distinct)
    teacher_subjects = db.query(Subject).join(
        StudentSubject, StudentSubject.subject_id == Subject.id
    ).filter(StudentSubject.teacher_id == current_user.id).distinct().all()
    
    return {
        'teacher_subjects': [{'id': s.id, 'name': s.name, 'code': s.code} for s in teacher_subjects],
        'students': student_data,
        'at_risk': at_risk,
        'total_students': len(student_data),
        'fcl_distribution': [{'fcl_label': k, 'count': v} for k, v in buckets.items()]
    }

@router.get('/student/{student_id}/deep-dive')
def student_deep_dive(student_id: int, subject_code: str = None,
                      db: Session = Depends(get_db),
                      current_user = Depends(get_current_student)):
    if not current_user.is_teacher:
        raise HTTPException(403, 'Teacher access only')
    
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(404, 'Student not found')
    
    # Get all assessments for this student
    assess = db.query(Assessment).filter(Assessment.student_id == student_id).all()
    accuracy = sum(1 for a in assess if a.is_correct) / len(assess) * 100 if assess else 0
    avg_hint_density = sum(a.hints_used for a in assess) / max(len(assess), 1) if assess else 0
    
    # Get overall FCL (using new system)
    overall_fcl = get_overall_fcl(student_id, db)
    
    # Prepare AI prompt (uses overall FCL as context)
    prompt = (f'Student {student.name} has overall FCL {overall_fcl} and '
              f'{round(accuracy, 1)}% quiz accuracy with {round(avg_hint_density, 1)} hints/question. '
              'Provide 2-3 specific, actionable teaching recommendations. Max 80 words.')
    
    try:
        ai_rec, _, _ = call_groq(
            prompt=prompt,
            max_tokens=200,
            temperature=0.7,
            model=MODEL_LONG
        )
    except Exception as e:
        logger.error(f"Groq AI recommendation failed: {e}")
        ai_rec = "Consider reviewing foundational concepts and encouraging daily practice."
    
    return {
        'name': student.name,
        'accuracy': round(accuracy, 1),
        'sessions_week': 0,
        'avg_hint_density': round(avg_hint_density, 2),
        'ai_recommendations': ai_rec,
        'shap_explanation': []
    }