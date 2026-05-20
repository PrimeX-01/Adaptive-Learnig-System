from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import Subject, StudentSubject, FCLHistory, TopicMastery, Assessment, Student
from db.schemas import SubjectEnrollRequest, UpdateTeacherRequest
from auth import get_current_student

router = APIRouter()

@router.get('/available')
def get_available_subjects(db: Session = Depends(get_db)):
    return [{'id': s.id, 'name': s.name, 'code': s.code, 'description': s.description}
            for s in db.query(Subject).all()]

@router.get('/enrolled/{student_id}')
def get_enrolled(student_id: int, db: Session=Depends(get_db),
                 current_user=Depends(get_current_student)):
    enrollments = db.query(StudentSubject).filter(
        StudentSubject.student_id==student_id).all()
    result = []
    for e in enrollments:
        fcl_row = db.query(FCLHistory).filter(
            FCLHistory.student_id==student_id,
            FCLHistory.subject_id==e.subject_id
        ).order_by(FCLHistory.updated_at.desc()).first()
        fcl = fcl_row.fcl_level if fcl_row else None
        mastery_rows = db.query(TopicMastery).filter(
            TopicMastery.student_id==student_id,
            TopicMastery.subject_id==e.subject_id).all()
        assessments = db.query(Assessment).filter(
            Assessment.student_id==student_id,
            Assessment.subject_id==e.subject_id).all()
        accuracy = (sum(1 for a in assessments if a.is_correct)/len(assessments)*100
                    if assessments else None)
        mastered = sum(1 for m in mastery_rows if m.mastery_level=='mastered')
        result.append({
            'subject_id':      e.subject_id,
            'subject_name':    e.subject.name,
            'subject_code':    e.subject.code,
            'teacher_id':      e.teacher_id,
            'teacher_name':    e.teacher.name if e.teacher else None,
            'fcl_level':       fcl,
            'mastered_topics': mastered,
            'total_topics':    len(mastery_rows),
            'accuracy':        round(accuracy, 1) if accuracy else None,
        })
    return result

@router.post('/enroll/{student_id}')
def enroll(student_id: int, req: SubjectEnrollRequest,
           db: Session=Depends(get_db), current_user=Depends(get_current_student)):
    subj = db.query(Subject).filter(Subject.code==req.subject_code).first()
    if not subj: raise HTTPException(404, f'Subject {req.subject_code} not found')
    if db.query(StudentSubject).filter(
            StudentSubject.student_id==student_id,
            StudentSubject.subject_id==subj.id).first():
        raise HTTPException(409, f'Already enrolled in {subj.name}')
    if req.teacher_id:
        t = db.query(Student).filter(Student.id==req.teacher_id, Student.is_teacher==True).first()
        if not t: raise HTTPException(400, 'teacher_id does not match a registered teacher')
    db.add(StudentSubject(student_id=student_id, subject_id=subj.id, teacher_id=req.teacher_id))
    db.commit()
    return {'message': f'Enrolled in {subj.name}', 'subject_id': subj.id}

@router.patch('/teacher/{student_id}')
def update_teacher(student_id: int, req: UpdateTeacherRequest,
                   db: Session=Depends(get_db), current_user=Depends(get_current_student)):
    subj = db.query(Subject).filter(Subject.code==req.subject_code).first()
    if not subj: raise HTTPException(404, 'Subject not found')
    t = db.query(Student).filter(Student.id==req.teacher_id, Student.is_teacher==True).first()
    if not t: raise HTTPException(400, 'No teacher found with that ID. Ask your teacher for their system User ID.')
    e = db.query(StudentSubject).filter(
        StudentSubject.student_id==student_id,
        StudentSubject.subject_id==subj.id).first()
    if not e: raise HTTPException(404, 'Not enrolled in this subject. Enroll first.')
    e.teacher_id = req.teacher_id
    db.commit()
    return {'message': f'Teacher updated for {subj.name}', 'teacher_name': t.name}

@router.get('/teacher-lookup')
def teacher_lookup(email: str, db: Session=Depends(get_db),
                   current_user=Depends(get_current_student)):
    t = db.query(Student).filter(Student.email==email, Student.is_teacher==True).first()
    if not t: raise HTTPException(404, 'No teacher found with that email address')
    return {'teacher_id': t.id, 'teacher_name': t.name}

@router.delete('/unenroll/{student_id}/{subject_code}')
def unenroll(student_id: int, subject_code: str,
             db: Session=Depends(get_db), current_user=Depends(get_current_student)):
    subj = db.query(Subject).filter(Subject.code==subject_code).first()
    if not subj: raise HTTPException(404, 'Subject not found')
    e = db.query(StudentSubject).filter(
        StudentSubject.student_id==student_id,
        StudentSubject.subject_id==subj.id).first()
    if not e: raise HTTPException(404, 'Not enrolled in this subject')
    db.delete(e); db.commit()
    return {'message': f'Unenrolled from {subj.name}'}
