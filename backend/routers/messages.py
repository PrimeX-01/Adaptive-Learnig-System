from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import Message, Notification, Student
from db.schemas import SendMessageRequest, BulkTipRequest
from auth import get_current_student
from services.llm_service import call_groq, MODEL_PRIMARY, MODEL_LONG
import os

router = APIRouter()


# ══════════════════════════════════════════════════════════════════
#  SEND MESSAGE
#  CHANGED: Notification now uses receiver_type/receiver_id/
#  sender_type/sender_id instead of old student_id/sender_id.
#  Message model also updated to use sender_type/receiver_type.
# ══════════════════════════════════════════════════════════════════

@router.post('/send')
def send_message(req: SendMessageRequest,
                 db: Session = Depends(get_db),
                 current_user = Depends(get_current_student)):
    receiver = db.query(Student).filter(Student.id == req.receiver_id).first()
    if not receiver:
        raise HTTPException(404, 'Recipient not found')

    msg = Message(
        sender_type   = 'student',
        sender_id     = current_user.id,
        receiver_type = 'student',
        receiver_id   = req.receiver_id,
        subject_id    = req.subject_id,
        subject       = req.subject,
        body          = req.body,
        thread_id     = req.thread_id,
    )
    db.add(msg)
    db.flush()

    db.add(Notification(
        receiver_type = 'student',
        receiver_id   = req.receiver_id,
        sender_type   = 'student',
        sender_id     = current_user.id,
        subject_id    = req.subject_id,
        type          = 'new_message',
        title         = f'New message from {current_user.name}',
        body          = req.subject,
        action_url    = '/student/messages',
    ))
    db.commit()
    return {'message_id': msg.id, 'status': 'sent'}


# ══════════════════════════════════════════════════════════════════
#  INBOX
#  CHANGED: query uses receiver_type + receiver_id.
#  We can't use .sender relationship since Message no longer has
#  a direct FK to students — sender_id is polymorphic.
#  We look up sender name manually based on sender_type.
# ══════════════════════════════════════════════════════════════════

@router.get('/inbox/{student_id}')
def get_inbox(student_id: int,
              db: Session = Depends(get_db),
              current_user = Depends(get_current_student)):
    msgs = db.query(Message).filter(
        Message.receiver_type == 'student',
        Message.receiver_id   == student_id,
    ).order_by(Message.created_at.desc()).all()

    result = []
    for m in msgs:
        sender_name = _resolve_sender_name(m.sender_type, m.sender_id, db)
        result.append({
            'id':          m.id,
            'sender_name': sender_name,
            'sender_id':   m.sender_id,
            'sender_type': m.sender_type,
            'subject':     m.subject,
            'body':        m.body,
            'is_read':     m.is_read,
            'subject_id':  m.subject_id,
            'course_id':   m.course_id,
            'thread_id':   m.thread_id,
            'created_at':  str(m.created_at),
        })
    return result


@router.get('/sent/{student_id}')
def get_sent(student_id: int,
             db: Session = Depends(get_db),
             current_user = Depends(get_current_student)):
    msgs = db.query(Message).filter(
        Message.sender_type == 'student',
        Message.sender_id   == student_id,
    ).order_by(Message.created_at.desc()).all()

    result = []
    for m in msgs:
        receiver_name = _resolve_sender_name(m.receiver_type, m.receiver_id, db)
        result.append({
            'id':            m.id,
            'receiver_name': receiver_name,
            'receiver_id':   m.receiver_id,
            'receiver_type': m.receiver_type,
            'subject':       m.subject,
            'body':          m.body,
            'is_read':       m.is_read,
            'created_at':    str(m.created_at),
        })
    return result


@router.patch('/read/{message_id}')
def mark_read(message_id: int,
              db: Session = Depends(get_db),
              current_user = Depends(get_current_student)):
    msg = db.query(Message).filter(Message.id == message_id).first()
    if (msg and msg.receiver_type == 'student'
            and msg.receiver_id == current_user.id):
        msg.is_read = True
        db.commit()
    return {'status': 'ok'}


# ══════════════════════════════════════════════════════════════════
#  NOTIFICATIONS
#  CHANGED: query uses receiver_type + receiver_id.
# ══════════════════════════════════════════════════════════════════

@router.get('/notifications/{student_id}')
def get_notifications(student_id: int,
                      db: Session = Depends(get_db),
                      current_user = Depends(get_current_student)):
    notifs = db.query(Notification).filter(
        Notification.receiver_type == 'student',
        Notification.receiver_id   == student_id,
    ).order_by(Notification.created_at.desc()).limit(20).all()

    return [
        {
            'id':         n.id,
            'type':       n.type,
            'title':      n.title,
            'body':       n.body,
            'is_read':    n.is_read,
            'action_url': n.action_url,
            'subject_id': n.subject_id,
            'course_id':  n.course_id,
            'created_at': str(n.created_at),
        }
        for n in notifs
    ]


@router.patch('/notifications/read/{notif_id}')
def mark_notification_read(notif_id: int,
                            db: Session = Depends(get_db),
                            current_user = Depends(get_current_student)):
    n = db.query(Notification).filter(Notification.id == notif_id).first()
    if n and n.receiver_id == current_user.id:
        n.is_read = True
        db.commit()
    return {'status': 'ok'}


# ══════════════════════════════════════════════════════════════════
#  BULK TIP
#  CHANGED: current_user.is_teacher → current_user.role check.
#  But this endpoint should actually be on the teacher/lecturer
#  routers. Here it is kept for backwards compat — the role check
#  now uses the role string instead of the old boolean.
# ══════════════════════════════════════════════════════════════════

@router.post('/bulk-tip')
def bulk_groq_tip(req: BulkTipRequest,
                  db: Session = Depends(get_db),
                  current_user = Depends(get_current_student)):
    # CHANGED: was current_user.is_teacher (boolean, old schema)
    # Now checks role string — teachers and lecturers can both send tips
    if current_user.role not in ('teacher', 'lecturer'):
        raise HTTPException(403, 'Teachers and lecturers only')

    prompt = (
        f'Write a short, encouraging improvement tip (2 sentences) for students '
        f'struggling with {req.topic_id.replace("_", " ")}. '
        f'Custom note from educator: {req.custom_note or "none"}. '
        'Start with "You". Be practical and specific.'
    )
    tip_text, _, _ = call_groq(
        prompt      = prompt,
        max_tokens  = 150,
        temperature = 0.7,
        model       = MODEL_LONG,
    )

    for sid in req.student_ids:
        db.add(Notification(
            receiver_type = 'student',
            receiver_id   = sid,
            sender_type   = current_user.role,
            sender_id     = current_user.id,
            type          = 'teacher_tip',
            title         = (
                f'Tip from {current_user.name}: '
                f'{req.topic_id.replace("_", " ").title()}'
            ),
            body          = tip_text,
            action_url    = f'/student/quizzes?topic={req.topic_id}',
        ))
    db.commit()
    return {'sent_to': len(req.student_ids), 'tip_preview': tip_text[:100]}


# ══════════════════════════════════════════════════════════════════
#  HELPER — resolve a sender/receiver name from type + id
#  CHANGED: new schema has separate principal tables, so we look
#  up the name from the correct table based on the type string.
# ══════════════════════════════════════════════════════════════════

def _resolve_sender_name(principal_type: str, principal_id: int,
                          db: Session) -> str:
    from sqlalchemy import text
    table_map = {
        'student':  'students',
        'teacher':  'teachers',
        'lecturer': 'lecturers',
        'admin':    'admins',
    }
    table = table_map.get(principal_type)
    if not table:
        return '—'
    try:
        row = db.execute(
            text(f'SELECT name FROM {table} WHERE id=:id'),
            {'id': principal_id}
        ).fetchone()
        return row[0] if row else '—'
    except Exception:
        return '—'
