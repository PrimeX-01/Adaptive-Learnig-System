from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import Message, Notification, Student
from db.schemas import SendMessageRequest, BulkTipRequest
from auth import get_current_student
from services.llm_service import call_groq, MODEL_PRIMARY, MODEL_LONG
import os

router = APIRouter()

@router.post('/send')
def send_message(req: SendMessageRequest, db: Session=Depends(get_db),
                 current_user=Depends(get_current_student)):
    receiver = db.query(Student).filter(Student.id==req.receiver_id).first()
    if not receiver: raise HTTPException(404, 'Recipient not found')
    msg = Message(sender_id=current_user.id, receiver_id=req.receiver_id,
                  subject_id=req.subject_id, subject=req.subject,
                  body=req.body, thread_id=req.thread_id)
    db.add(msg); db.flush()
    db.add(Notification(
        student_id=req.receiver_id, sender_id=current_user.id,
        subject_id=req.subject_id, type='new_message',
        title=f'New message from {current_user.name}',
        body=req.subject, action_url='/messages'))
    db.commit()
    return {'message_id': msg.id, 'status': 'sent'}

@router.get('/inbox/{student_id}')
def get_inbox(student_id: int, db: Session=Depends(get_db),
              current_user=Depends(get_current_student)):
    msgs = db.query(Message).filter(Message.receiver_id==student_id).order_by(Message.created_at.desc()).all()
    return [{'id':m.id,'sender_name':m.sender.name,'sender_id':m.sender_id,
             'subject':m.subject,'body':m.body,'is_read':m.is_read,
             'subject_id':m.subject_id,'thread_id':m.thread_id,
             'created_at':str(m.created_at)} for m in msgs]

@router.get('/sent/{student_id}')
def get_sent(student_id: int, db: Session=Depends(get_db),
             current_user=Depends(get_current_student)):
    msgs = db.query(Message).filter(Message.sender_id==student_id).order_by(Message.created_at.desc()).all()
    return [{'id':m.id,'receiver_name':m.receiver.name,'receiver_id':m.receiver_id,
             'subject':m.subject,'body':m.body,'is_read':m.is_read,
             'created_at':str(m.created_at)} for m in msgs]

@router.patch('/read/{message_id}')
def mark_read(message_id: int, db: Session=Depends(get_db),
              current_user=Depends(get_current_student)):
    msg = db.query(Message).filter(Message.id==message_id).first()
    if msg and msg.receiver_id==current_user.id: msg.is_read=True; db.commit()
    return {'status': 'ok'}

@router.get('/notifications/{student_id}')
def get_notifications(student_id: int, db: Session=Depends(get_db),
                      current_user=Depends(get_current_student)):
    notifs = db.query(Notification).filter(
        Notification.student_id==student_id
    ).order_by(Notification.created_at.desc()).limit(20).all()
    return [{'id':n.id,'type':n.type,'title':n.title,'body':n.body,
             'is_read':n.is_read,'action_url':n.action_url,
             'subject_id':n.subject_id,'created_at':str(n.created_at)} for n in notifs]

@router.post('/bulk-tip')
def bulk_groq_tip(req: BulkTipRequest, db: Session=Depends(get_db),
                  current_user=Depends(get_current_student)):
    if not current_user.is_teacher:
        raise HTTPException(403, 'Teachers only')
    prompt = (f'Write a short, encouraging improvement tip (2 sentences) for students '
              f'struggling with {req.topic_id.replace("_"," ")}. '
              f'Custom note from teacher: {req.custom_note or "none"}. '
              'Start with "You". Be practical and specific.')
    # Updated call_groq signature:
    tip_text, _, _ = call_groq(
        prompt=prompt,
        max_tokens=150,
        temperature=0.7,
        model=MODEL_LONG
    )
    for sid in req.student_ids:
        db.add(Notification(
            student_id=sid, sender_id=current_user.id, type='teacher_tip',
            title=f'Tip from {current_user.name}: {req.topic_id.replace("_"," ").title()}',
            body=tip_text, action_url=f'/quiz?topic={req.topic_id}'))
    db.commit()
    return {'sent_to': len(req.student_ids), 'tip_preview': tip_text[:100]}